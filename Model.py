import realsense as rs
import tool 
import os

class Model:
    def __init__(self):
        self.recorder = None
        self.controller_callback = None

    def recive_from_controller(self, config_dict):
        if config_dict['mode'] == 'get_realsense_profiles':
            return self.get_realsense_profiles()
        elif config_dict['mode'] == 'check_dir' or config_dict['mode'] == 'check_file':
            return self.check_path(config_dict)
        elif config_dict['mode'] == "start_preview":
            self.send_to_realsense_recorder('start_preview', data=config_dict)
        elif config_dict['mode'] == 'start_record':
            self.send_to_realsense_recorder('start_record')
        elif config_dict['mode'] == 'stop_record':
            self.send_to_realsense_recorder('stop_record')
        elif config_dict['mode'] == 'start_run_system':
            self.send_to_reconstruction_system('start_run_system', data=config_dict)
             
    def send_to_controller(self, mode, data):
        if mode == 'record_imgs':
            self.controller_callback(mode, data)
        elif mode == 'show_error':
            self.controller_callback(mode, data)

    def send_to_reconstruction_system(self, mode, data):
        if mode == 'start_run_system':
            self.start_reconstruction_system(mode, data)

    def send_to_realsense_recorder(self, mode, data=None):
        if mode == 'start_preview':
            self.start_realsense_preview(mode, data)
        elif mode == 'stop_record':
            self.stop_realsense_recorder(mode)
        elif mode == 'start_record':
            self.start_realsense_recorder(mode)

    def recive_from_realsense_recorder(self, mode, data):
        if mode == 'record_imgs':
            self.send_to_controller(mode, data)
        elif mode == 'show_error':
            self.send_to_controller(mode, data)

    def start_reconstruction_system(self, mode, data):
        selected_items_dict = data['selected_items_dict']
        if mode == 'start_run_system':
            args = rs.Args_run_system(
                config=data['selected_path'], 
                make=selected_items_dict['Make'], 
                register=selected_items_dict['Register'], 
                refine=selected_items_dict['Refine'], 
                integrate=selected_items_dict['Integrate'], 
                slac=selected_items_dict['Slac'], 
                slac_integrate=selected_items_dict['Slac integrate'], 
                debug_mode=selected_items_dict['Debug mode']
                )
            self.reconstruction_system = rs.ReconstructionSystem(args)
            self.reconstruction_system.run()

    def stop_reconstruction_system(self, mode):
        if self.reconstruction_system:
            self.reconstruction_system.stop()

    def set_controller_callback(self, controller_callback):
        self.controller_callback = controller_callback

    def get_realsense_profiles(self):
        color_profiles, depth_profiles = rs.get_profiles()
        return tool.update_profile(color_profiles, depth_profiles)

    def start_realsense_preview(self, mode, config_dict):
        if self.recorder:
            self.recorder.recive_from_model('stop_record')
        args = rs.Args(
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
        print(args.depth_fmt, args.color_fmt, args.fps)
        self.recorder = rs.RealSenseRecorder(args, self.recive_from_realsense_recorder)
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
            if not os.path.isdir(path):
                return "NotExist"
            elif not os.listdir(path):
                return "Empty"
            else:
                files = os.listdir(path)
                if "realsense.bag" in files:
                    return "ContainsRealsenseBag"
                else:
                    return "ContainsOtherFiles"