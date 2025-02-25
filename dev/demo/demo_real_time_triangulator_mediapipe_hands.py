
""""
THINGS ARE WORKING ON APR 16 AT 6:57 AM.
In the future I think I want to change it so that the charuco tracker factory is not
a default, but something that has to be made explicit....
"""
# %%
import pyxy3d.logger

logger = pyxy3d.logger.get(__name__)
import sys
from pathlib import Path
from queue import Queue
from time import sleep

from PySide6.QtWidgets import QApplication

from pyxy3d import __root__
from pyxy3d.cameras.camera_array import (CameraArray, CameraData,
                                         get_camera_array)
from pyxy3d.cameras.synchronizer import Synchronizer
from pyxy3d.configurator import Configurator
from pyxy3d.gui.vizualize.realtime_triangulation_widget import \
    RealTimeTriangulationWidget
from pyxy3d.interface import FramePacket, PointPacket, SyncPacket
from pyxy3d.session.session import LiveSession
from pyxy3d.trackers.charuco_tracker import Charuco, CharucoTracker
from pyxy3d.trackers.hand_tracker import HandTracker
from pyxy3d.triangulate.sync_packet_triangulator import SyncPacketTriangulator
from pyxy3d.trackers.tracker_enum import TrackerEnum

app = QApplication(sys.argv)
session_path = Path(__root__,"dev", "sample_sessions", "low_res")

session = LiveSession(session_path)
tracker = TrackerEnum.HAND

session.load_stream_tools(tracker=tracker) 
session._adjust_resolutions()

config = Configurator(session_path)
camera_array = config.get_camera_array()

logger.info(f"Creating RecordedStreamPool")
# stream_pool = RecordedStreamPool(session_path, tracker_factory=charuco_tracker_factory, fps_target=100)
logger.info("Creating Synchronizer")
syncr = Synchronizer(session.streams, fps_target=12)

real_time_triangulator = SyncPacketTriangulator(camera_array, syncr)
xyz_queue = Queue()

real_time_triangulator.subscribe(xyz_queue)

real_time_widget = RealTimeTriangulationWidget(camera_array,xyz_queue)
 
real_time_widget.show()
sys.exit(app.exec())