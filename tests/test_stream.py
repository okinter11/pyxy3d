from pathlib import Path
from queue import Queue
from time import sleep

import cv2
from pyxy3d import __root__
from pyxy3d.helper import copy_contents
from pyxy3d.calibration.charuco import Charuco
from pyxy3d.trackers.charuco_tracker import CharucoTracker
from pyxy3d.recording.recorded_stream import RecordedStream
from pyxy3d.interface import FramePacket

import pyxy3d.logger

logger = pyxy3d.logger.get(__name__)
def test_stream():
    
    # use a general video file with a charuco for convenience
    original_data_path= Path(__root__, "tests", "sessions", "4_cam_recording")
    destination_path =Path(__root__, "tests", "sessions_copy_delete", "4_cam_recording")
    copy_contents(original_data_path,destination_path)


    recording_directory = Path(
        __root__, "tests", "sessions", "post_monocal", "calibration", "extrinsic"
    )

    charuco = Charuco(
        4, 5, 11, 8.5, aruco_scale=0.75, square_size_overide_cm=5.25, inverted=True
    )

    charuco_tracker = CharucoTracker(charuco)
    
    stream  = RecordedStream(recording_directory,port=1,rotation_count=0, tracker=charuco_tracker, fps_target=6)
    frame_q = Queue()
    stream.subscribe(frame_q)
    stream.play_video()
    stream.pause()
   
    sleep(1)  
    logger.info(f"Stream frame index is {stream.frame_index}") 
    sleep(1)  
    logger.info(f"Stream frame index is {stream.frame_index}") 
    
    stream.unpause()
    
    while True:
        frame_packet = frame_q.get()
    
        if frame_packet.frame is None:
            break
   
        if stream.frame_index  == 10:
            logger.info("Testing pause/unpause functionality")
            stream.pause()
            sleep(.5)
            test_index = stream.frame_index
            sleep(.1)
            # make sure that stream doesn't advance with pause
            assert(test_index == stream.frame_index)
            stream.unpause()

        if stream.frame_index == 15:
            logger.info("Testing ability to jump forward")
            target_frame = 20
            stream.pause()
            stream.jump_to(target_frame)
            sleep(.2) # need to make sure fps_target wait plays out
            assert(stream.frame_index == 20)
           
            logger.info(f"After attempting to jump to target frame {target_frame} ") 
            current_frame = int(stream.capture.get(cv2.CAP_PROP_POS_FRAMES))
            logger.info(f"Current frame is now {current_frame}")
            assert(current_frame == 20)
            stream.unpause()

        cv2.imshow("Test", frame_packet.frame_with_points)

   
        key = cv2.waitKey(1)
        if key == ord("q"):
            break

if __name__ == "__main__":
    test_stream()
    
