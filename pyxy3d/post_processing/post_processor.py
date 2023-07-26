import typing
import pyxy3d.logger

logger = pyxy3d.logger.get(__name__)

from time import sleep, time
from queue import Queue
import cv2
from PyQt6.QtCore import QObject, pyqtSignal

import sys
from PyQt6.QtWidgets import QApplication
from pyxy3d.configurator import Configurator
from pathlib import Path
import numpy as np
from numba.typed import Dict, List
from pyxy3d import __root__
import pandas as pd
from pyxy3d.cameras.camera_array import CameraArray
from pyxy3d.recording.recorded_stream import RecordedStream, RecordedStreamPool
from pyxy3d.cameras.synchronizer import Synchronizer
from pyxy3d.recording.video_recorder import VideoRecorder
from pyxy3d.triangulate.sync_packet_triangulator import (
    SyncPacketTriangulator,
    triangulate_sync_index,
)
from pyxy3d.interface import FramePacket, Tracker
from pyxy3d.trackers.tracker_enum import TrackerEnum

# specify a source directory (with recordings)
from pyxy3d.helper import copy_contents
from pyxy3d.export import xyz_to_trc

class PostProcessor:
    """
    The post processer operates independently of the session. It does not need to worry about camera management.
    Provide it with a path to the directory that contains the following:
    - config.toml
    - frame_time.csv 
    - .mp4 files
    

    """
    # progress_update = pyqtSignal(dict)  # {"stage": str, "percent":int}

    def __init__(self,recording_path:Path, tracker_enum:TrackerEnum):
        self.recording_path = recording_path
        self.tracker_enum = tracker_enum
        
        self.config = Configurator(self.recording_path)

    def create_xy(self):
        """
        Reads through all .mp4  files in the recording path and applies the tracker to them
        The xy_TrackerName.csv file is saved out to the same directory by the VideoRecorder
        """
        frame_times = pd.read_csv(Path(self.recording_path, "frame_time_history.csv"))
        sync_index_count = len(frame_times["sync_index"].unique())

        fps_recording = self.config.get_fps_recording()
        logger.info("Creating pool of playback streams to begin processing")
        stream_pool = RecordedStreamPool(
            directory=self.recording_path,
            config=self.config,
            fps_target=fps_recording,
            tracker=self.tracker_enum.value(),
        )

        synchronizer = Synchronizer(stream_pool.streams, fps_target=fps_recording)

        logger.info(
            "Creating video recorder to record (x,y) data estimates from PointPacket delivered by Tracker"
        )
        output_suffix = self.tracker_enum.name
        
        # it is the videorecorder that will save the (x,y) landmark positionsj
        video_recorder = VideoRecorder(synchronizer, suffix=output_suffix)

        # these (x,y) positions will be stored within the subdirectory of the recording folder
        # this destination subfolder is named to align with the tracker_enum.name
        destination_folder = Path(self.recording_path, self.tracker_enum.name)
        video_recorder.start_recording(
            destination_folder=destination_folder,
            include_video=True,
            show_points=True,
            store_point_history=True
        )
        logger.info("Initiate playback and processing")
        stream_pool.play_videos()

        while video_recorder.recording:
            sleep(1)
            percent_complete = int((video_recorder.sync_index / sync_index_count) * 100)
            logger.info(f"(Stage 1 of 2): {percent_complete}% of frames processed for (x,y) landmark detection")

    def create_xyz(self, include_trc = True) -> None:
        """
        creates xyz_{tracker name}.csv file within the recording_path directory

        Uses the two functions above, first creating the xy points based on the tracker if they 
        don't already exist, the triangulating them. Makes use of an internal method self.triangulate_xy_data
        
        """

        output_suffix = self.tracker_enum.name

        tracker_output_path = Path(self.recording_path, self.tracker_enum.name)
        # locate xy_{tracker name}.csv
        xy_csv_path = Path(tracker_output_path, f"xy_{output_suffix}.csv")

        # create if it doesn't already exist
        if not xy_csv_path.exists():
            self.create_xy()

        # load in 2d data and triangulate it
        logger.info("Reading in (x,y) data..")
        xy_data = pd.read_csv(xy_csv_path)
        logger.info("Beginning data triangulation")
        xyz_history = self.triangulate_xy_data(xy_data)
        xyz_data = pd.DataFrame(xyz_history)
        xyz_csv_path = Path(tracker_output_path, f"xyz_{output_suffix}.csv")
        xyz_data.to_csv(xyz_csv_path)

        # only include trc if wanted and only if there is actually good data to export
        if include_trc and xyz_data.shape[0] > 0:
           xyz_to_trc(xyz_csv_path, tracker = self.tracker_enum.value()) 

    def triangulate_xy_data(self, xy_data: pd.DataFrame) -> Dict[str, List]:
        
        camera_array = self.config.get_camera_array()
        # assemble numba compatible dictionary
        projection_matrices = Dict()
        for port, cam in camera_array.cameras.items():
            logger.info(f"At port {port}, the projection matrix is {cam.projection_matrix}")
            projection_matrices[int(port)] = cam.projection_matrix

        xyz_history = {
            "sync_index": [],
            "point_id": [],
            "x_coord": [],
            "y_coord": [],
            "z_coord": [],
        }

        sync_index_max = xy_data["sync_index"].max()

        start = time()
        last_log_update = int(start)  # only report progress each second

        for index in xy_data["sync_index"].unique():
            active_index = xy_data["sync_index"] == index
            port = xy_data["port"][active_index].to_numpy()
            point_ids = xy_data["point_id"][active_index].to_numpy()
            img_loc_x = xy_data["img_loc_x"][active_index].to_numpy()
            img_loc_y = xy_data["img_loc_y"][active_index].to_numpy()
            imgs_xy = np.vstack([img_loc_x, img_loc_y]).T

            # the fancy part
            point_id_xyz, points_xyz = triangulate_sync_index(
                projection_matrices, port, point_ids, imgs_xy
            )

            if len(point_id_xyz) > 0:
                # there are points to store so store them...
                xyz_history["sync_index"].extend([index] * len(point_id_xyz))
                xyz_history["point_id"].extend(point_id_xyz)

                points_xyz = np.array(points_xyz)
                xyz_history["x_coord"].extend(points_xyz[:, 0].tolist())
                xyz_history["y_coord"].extend(points_xyz[:, 1].tolist())
                xyz_history["z_coord"].extend(points_xyz[:, 2].tolist())

            # only log percent complete each second
            if int(time()) - last_log_update >= 1:
                percent_complete = int(100*(index/sync_index_max))
                logger.info(
                    f"(Stage 2 of 2): Triangulation of (x,y) point estimates is {percent_complete}% complete"
                )
                last_log_update = int(time())

        return xyz_history
