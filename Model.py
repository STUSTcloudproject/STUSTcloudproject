from realsense_helper import get_profiles
from RealSenseRecorder import RealSenseRecorder, Args
import tool
import os

class Model:
    def __init__(self):
        self.recorder = None

    def callback_from_controller(self, config_dict):
        if config_dict['mode'] == 'get_realsense_profiles':
            return self.get_realsense_profiles()
        elif config_dict['mode'] == 'check_dir' or config_dict['mode'] == 'check_file':
            return self.check_path(config_dict)
        elif config_dict['mode'] == "Record":
            self.start_realsense_recorder(config_dict)
        elif config_dict['mode'] == 'Stop_Record':
            self.stop_realsense_recorder()
            

    def get_realsense_profiles(self):
        color_profiles, depth_profiles = get_profiles()
        return tool.update_profile(color_profiles, depth_profiles)

    def start_realsense_recorder(self, config_dict):
        if self.recorder:
            self.recorder.stop_record()

        args = Args(
            output_folder=config_dict['selected_path'],
            record_rosbag=config_dict['mode'] == 'Record',
            record_imgs=config_dict['mode'] == 'RunSystem',
            playback_rosbag=config_dict['mode'] == 'View',
            overwrite=True,
            width=config_dict['realsense_selection'][0][0],
            height=config_dict['realsense_selection'][0][1],
            depth_fmt=config_dict['realsense_selection'][0][3],
            color_fmt=config_dict['realsense_selection'][1][3],
            fps=config_dict['realsense_selection'][0][2]
        )
        
        self.recorder = RealSenseRecorder(args)
        self.recorder.start_record()

    def stop_realsense_recorder(self):
        if self.recorder:
            self.recorder.stop_record()
            self.recorder = None

    def check_path(self, config_dict):
        check_type = config_dict['mode']
        path = config_dict['data']
        print(f'check path {check_type} {path}')
        if check_type == 'check_file':
            if os.path.isfile(path):
                return True
            else:
                return False
        elif check_type == 'check_dir':
            if os.path.isdir(path):
                return True
            else:
                return False