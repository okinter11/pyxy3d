# this class is only a way to hold data related to the stereocamera triangulation.
# These will load from a config file (.toml) and provide a way for the 3D triangulation
# and plotting to manage the parameters. It feels like some duplication of the camera object,
# but I want something that is designed to be simple and not actually manage the cameras, just
# organize the saved data

import logging

LOG_FILE = r"log\stereo_triangulator.log"
LOG_LEVEL = logging.DEBUG
# LOG_LEVEL = logging.INFO

LOG_FORMAT = " %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s"
logging.basicConfig(filename=LOG_FILE, filemode="w", format=LOG_FORMAT, level=LOG_LEVEL)

from queue import Queue
from threading import Thread, Event
from dataclasses import dataclass
import math
from os.path import exists
import toml
import numpy as np
import pandas as pd
import scipy
from pathlib import Path
import sys

from src.triangulate.paired_point_stream import PairedPointStream
from src.cameras.camera_array import CameraData


class StereoTriangulator:
    def __init__(self, camera_A: CameraData, camera_B: CameraData, in_q: Queue):

        self.camera_A = camera_A
        self.camera_B = camera_B
        self.portA = camera_A.port
        self.portB = camera_B.port
        self.pair = (self.portA, self.portB)

        self.build_projection_matrices()

        self.in_q = in_q
        self.out_q = Queue(-1)
        self.stop = Event()

        self.thread = Thread(target=self.create_3D_points, args=[], daemon=True)
        self.thread.start()

    def build_projection_matrices(self):

        rot_A = self.camera_A.rotation
        trans_A = np.array(self.camera_A.translation)
        rot_trans_A = np.concatenate([rot_A, trans_A], axis=-1)
        mtx_A = self.camera_A.camera_matrix
        self.proj_A = mtx_A @ rot_trans_A  # projection matrix for CamA

        rot_B = self.camera_B.rotation
        trans_B = np.array(self.camera_B.translation)
        rot_trans_B = np.concatenate([rot_B, trans_B], axis=-1)
        mtx_B = self.camera_B.camera_matrix
        self.proj_B = mtx_B @ rot_trans_B  # projection matrix for CamB

    def create_3D_points(self):
        while not self.stop.is_set():
            points_packet = self.in_q.get()
            all_points_3D = []

            # this is a clear candidate for vectorization...going to not worry about it now

            for point_id, x_A, y_A, x_B, y_B in zip(
                points_packet.point_id,
                points_packet.loc_img_x_A,
                points_packet.loc_img_y_A,
                points_packet.loc_img_x_B,
                points_packet.loc_img_y_A,
            ):
                point_A = (x_A, y_A)
                point_B = (x_B, y_B)
                # time = (time_A+time_B)/2

                point_3D = self.triangulate(point_A, point_B)
                all_points_3D.append(point_3D)
            all_points_3D = np.array(all_points_3D)
            # packet = TriangulatedPointsPacket(pair=self.pair, time)
            logging.debug(f"Placing current bundle of 3d points on queue")
            logging.debug(all_points_3D)
            self.out_q.put(all_points_3D)

    def triangulate(self, point_A, point_B):

        point_A = self.undistort(point_A, self.camera_A)
        point_B = self.undistort(point_B, self.camera_B)

        A = [
            point_A[1] * self.proj_A[2, :] - self.proj_A[1, :],
            self.proj_A[0, :] - point_A[0] * self.proj_A[2, :],
            point_B[1] * self.proj_B[2, :] - self.proj_B[1, :],
            self.proj_B[0, :] - point_B[0] * self.proj_B[2, :],
        ]
        A = np.array(A).reshape((4, 4))

        B = A.transpose() @ A
        U, s, Vh = scipy.linalg.svd(B, full_matrices=False)
        coord_3D = Vh[3, 0:3] / Vh[3, 3]
        return coord_3D

    def undistort(self, point, camera: CameraData, iter_num=3):
        # implementing a function described here: https://yangyushi.github.io/code/2020/03/04/opencv-undistort.html
        # supposedly a better implementation than OpenCV
        k1, k2, p1, p2, k3 = camera.distortion[0]
        fx, fy = camera.camera_matrix[0, 0], camera.camera_matrix[1, 1]
        cx, cy = camera.camera_matrix[:2, 2]
        x, y = float(point[0]), float(point[1])

        x = (x - cx) / fx
        x0 = x
        y = (y - cy) / fy
        y0 = y

        for _ in range(iter_num):
            r2 = x**2 + y**2
            k_inv = 1 / (1 + k1 * r2 + k2 * r2**2 + k3 * r2**3)
            delta_x = 2 * p1 * x * y + p2 * (r2 + 2 * x**2)
            delta_y = p1 * (r2 + 2 * y**2) + 2 * p2 * x * y
            x = (x0 - delta_x) * k_inv
            y = (y0 - delta_y) * k_inv
        return np.array((x * fx + cx, y * fy + cy))


@dataclass
class TriangulatedPointsPacket:
    pair: tuple  # parent pair
    time: float  # mean time
    point_ids: list
    xyz: np.ndarray


if __name__ == "__main__":

    from src.recording.recorded_stream import RecordedStreamPool
    from src.cameras.synchronizer import Synchronizer
    from src.calibration.charuco import Charuco
    from src.calibration.corner_tracker import CornerTracker
    from src.cameras.camera_array import CameraArrayBuilder, CameraArray, CameraData

    repo = str(Path(__file__)).split("src")[0]

    calibration_data = Path(repo, "sessions", "iterative_adjustment")
    camera_array = CameraArrayBuilder(calibration_data).get_camera_array()

    # create playback streams to provide to synchronizer
    ports = [0, 2]
    recorded_stream_pool = RecordedStreamPool(ports, calibration_data)
    syncr = Synchronizer(
        recorded_stream_pool.streams, fps_target=None
    )  # no fps target b/c not playing back for visual display
    recorded_stream_pool.play_videos()

    # create a corner tracker to locate board corners
    charuco = Charuco(
        4, 5, 11, 8.5, aruco_scale=0.75, square_size_overide_cm=5.25, inverted=True
    )
    trackr = CornerTracker(charuco)

    # create a commmon point finder to grab charuco corners shared between the pair of ports
    pairs = [(0, 2)]
    point_stream = PairedPointStream(
        synchronizer=syncr,
        pairs=pairs,
        tracker=trackr,
    )

    camA, camB = camera_array.cameras[0], camera_array.cameras[2]
    pair = (camA.port, camB.port)

    test_pair_out_q = Queue(-1)
    triangulatr = StereoTriangulator(camA, camB, test_pair_out_q)
    frames_processed = 0

    while True:
        paired_points = point_stream.out_q.get()
        if paired_points.pair == (0, 2):
            test_pair_out_q.put(paired_points)

        # print(all_pairs_common_points)
        # pair_points = all_pairs_common_points[pair]
        # if pair_points is not None:
        # triangulatr.in_q.put(paired_points)
        points_3D = triangulatr.out_q.get()
        print(points_3D)
        frames_processed += 1
        print(f"Frames Processed: {frames_processed}")
