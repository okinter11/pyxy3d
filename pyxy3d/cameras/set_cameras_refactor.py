# %%
 
from pathlib import Path
from pyxy3d.cameras.camera_array_builder import CameraArrayBuilder    
from pyxy3d import __root__
import numpy as np
from dataclasses import dataclass
import toml
 
@dataclass
class StereoPair:
    primary_port: int
    secondary_port: int
    error: float
    translation: np.ndarray
    rotation: np.ndarray
    
    @property
    def pair(self):
        return (self.primary_port,self.secondary_port)

    @property
    def transformation(self):
    
        R_stack = np.vstack([self.rotation, np.array([0,0,0])])
        t_stack = np.vstack([self.translation, np.array([1])])
        Tranformation = np.hstack([R_stack,t_stack])
        return Tranformation


def get_inverted_stereopair(stereo_pair:StereoPair)->StereoPair:
    primary_port = stereo_pair.secondary_port
    secondary_port = stereo_pair.primary_port
    error = stereo_pair.error

    inverted_transformation = np.linalg.inv(stereo_pair.transformation)
    rotation = inverted_transformation[0:3,0:3]
    translation = inverted_transformation[0:3,3:]
    
    inverted_stereopair = StereoPair(primary_port = primary_port,
                                     secondary_port = secondary_port,
                                     error = error,
                                     translation = translation,
                                     rotation = rotation)
    return inverted_stereopair

session_directory = Path(__root__,  "tests", "3_cameras_middle")
config_path = Path(session_directory, "config.toml")
config = toml.load(config_path)

stereopairs = {}

for key, params in config.items():
    if key.split("_")[0] == "stereo":
        port_A = int(key.split("_")[1])
        port_B = int(key.split("_")[2])

        rotation = np.array(params["rotation"], dtype=np.float64)
        translation = np.array(params["translation"], dtype=np.float64)
        error = float(params["RMSE"])

        new_stereopair = StereoPair(primary_port = port_A,
                                    secondary_port = port_B,
                                    error = error,
                                    translation = translation,
                                    rotation = rotation)

        stereopairs[new_stereopair.pair] = new_stereopair


inverted_stereopairs = {}

for pair, stereopair in stereopairs.items():
    a,b = pair
    inverted_pair = (b,a)
    inverted_stereopairs[inverted_pair] = get_inverted_stereopair(stereopair)
# %%

# so I tihn