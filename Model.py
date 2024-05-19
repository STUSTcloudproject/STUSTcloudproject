from realsense_helper import get_profiles
from RealSenseRecorder import RealSenseRecorder, Args
import tool 
import os

class Model:
    def __init__(self):
        self.recorder = None
        self.controller_callback = None

    def recive_from_realsense_recorder(self, mode, data):
        if mode == 'record_imgs':
            self.send_to_controller(mode, data)

    def recive_from_controller(self, config_dict):
        if config_dict['mode'] == 'get_realsense_profiles':
            return self.get_realsense_profiles()
        elif config_dict['mode'] == 'check_dir' or config_dict['mode'] == 'check_file':
            return self.check_path(config_dict)
        elif config_dict['mode'] == "start_preview":
            self.send_to_realsense_recorder('start_preview', data=config_dict)
        elif config_dict['mode'] == 'stop_record':
            self.send_to_realsense_recorder('stop_record')
        elif config_dict['mode'] == 'start_record':
            self.send_to_realsense_recorder('start_record')
            
            
    def send_to_controller(self, mode, data):
        if mode == 'record_imgs':
            self.controller_callback(mode, data)

    def send_to_realsense_recorder(self, mode, data=None):
        if mode == 'start_preview':
            self.start_realsense_preview(mode, data)
        elif mode == 'stop_record':
            self.stop_realsense_recorder(mode)
        elif mode == 'start_record':
            self.start_realsense_recorder(mode)

    def set_controller_callback(self, controller_callback):
        self.controller_callback = controller_callback

    def get_realsense_profiles(self):
        color_profiles, depth_profiles = get_profiles()
        return tool.update_profile(color_profiles, depth_profiles)

    def start_realsense_preview(self, mode, config_dict):
        if self.recorder:
            self.recorder.recive_from_model('stop_record')
        args = Args(
            output_folder=config_dict['selected_path'],
            record_rosbag=config_dict['selected_items_dict']['Record rosbag'],
            record_imgs=config_dict['selected_items_dict']['Record imgs'],
            playback_rosbag=config_dict['selected_items_dict']['Playback rosbag'],
            overwrite=True,
            width=config_dict['realsense_selection'][0][0],
            height=config_dict['realsense_selection'][0][1],
            depth_fmt=config_dict['realsense_selection'][0][3],
            color_fmt=config_dict['realsense_selection'][1][3],
            fps=config_dict['realsense_selection'][0][2]
        )
        
        self.recorder = RealSenseRecorder(args, self.recive_from_realsense_recorder)
        self.recorder.recive_from_model(mode)

    def stop_realsense_recorder(self, mode):
        if self.recorder:
            self.recorder.recive_from_model(mode)

    def start_realsense_recorder(self, mode):
        if self.recorder:
            self.recorder.recive_from_model(mode)

    def check_path(self, config_dict):
        check_type = config_dict['mode']
        path = config_dict['data']
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