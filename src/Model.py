import realsense as rs
import tool
import os

class Model:
    def __init__(self):
        """
        初始化模型並設置初始狀態
        """
        self.recorder = None
        self.controller_callback = None
        self.reconstruction_system = None
        self.view_system = None

    def recive_from_controller(self, config_dict):
        """
        從控制器接收數據並根據模式進行處理

        參數:
        config_dict (dict): 包含操作模式和相關數據的字典
        """
        mode = config_dict['mode']
        if mode == 'get_realsense_profiles':
            return self.get_realsense_profiles()
        elif mode in ['check_dir', 'check_file']:
            return self.check_path(config_dict)
        elif mode == 'start_preview':
            self.send_to_realsense_recorder('start_preview', data=config_dict)
        elif mode == 'start_record':
            self.send_to_realsense_recorder('start_record')
        elif mode == 'stop_record':
            self.send_to_realsense_recorder('stop_record')
            self.send_to_reconstruction_system('stop_run_system')
            self.send_to_view_system('stop_view_system')
        elif mode == 'start_run_system':
            self.send_to_reconstruction_system('start_run_system', data=config_dict)
        elif mode == 'start_view_system':
            self.send_to_view_system('start_view_system', data=config_dict)

    def send_to_controller(self, mode, data):
        """
        向控制器發送數據

        參數:
        mode (str): 操作模式
        data (any): 要發送的數據
        """
        if mode in ['record_imgs', 'show_error', 'terminal_print']:
            self.controller_callback(mode, data)

    def send_to_view_system(self, mode, data=None):
        """
        向視圖系統發送數據並啟動視圖系統

        參數:
        mode (str): 操作模式
        """
        if mode == 'start_view_system':
            self.start_view_system(mode, data)
        elif mode == 'stop_view_system':
            self.stop_view_system(mode)

    def send_to_reconstruction_system(self, mode, data=None):
        """
        向重建系統發送數據並啟動或停止重建系統

        參數:
        mode (str): 操作模式
        data (dict, optional): 附加數據
        """
        if mode == 'start_run_system':
            self.start_reconstruction_system(mode, data)
        elif mode == 'stop_run_system':
            self.stop_reconstruction_system(mode)

    def send_to_realsense_recorder(self, mode, data=None):
        """
        向 Realsense 錄製器發送數據並啟動或停止錄製

        參數:
        mode (str): 操作模式
        data (dict, optional): 附加數據
        """
        if mode == 'start_preview':
            self.start_realsense_preview(mode, data)
        elif mode == 'stop_record':
            self.stop_realsense_recorder(mode)
        elif mode == 'start_record':
            self.start_realsense_recorder(mode)

    def recive_from_realsense_recorder(self, mode, data):
        """
        從 Realsense 錄製器接收數據並處理

        參數:
        mode (str): 操作模式
        data (any): 附加數據
        """
        if mode in ['record_imgs', 'show_error']:
            self.send_to_controller(mode, data)

    def recive_from_reconstruction_system(self, mode, data):
        """
        從重建系統接收數據並處理

        參數:
        mode (str): 操作模式
        data (any): 附加數據
        """
        if mode in ['show_error', 'terminal_print']:
            self.send_to_controller(mode, data)

    def recive_from_view_system(self, mode, data):
        """
        從視圖系統接收數據並處理

        參數:
        mode (str): 操作模式
        data (any): 附加數據
        """
        if mode in ['show_error', 'terminal_print']:
            self.send_to_controller(mode, data)

    def start_reconstruction_system(self, mode, data):
        """
        啟動重建系統並傳遞所需參數

        參數:
        mode (str): 操作模式
        data (dict): 附加數據
        """
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
            self.reconstruction_system = rs.ReconstructionSystem(args, self.recive_from_reconstruction_system)
            self.reconstruction_system.recive_from_model('start_run_system')

    def stop_reconstruction_system(self, mode):
        """
        停止重建系統

        參數:
        mode (str): 操作模式
        """
        if self.reconstruction_system:
            self.reconstruction_system.recive_from_model('stop_run_system')

    def set_controller_callback(self, controller_callback):
        """
        設置控制器回調函式

        參數:
        controller_callback (function): 控制器回調函式
        """
        self.controller_callback = controller_callback

    def get_realsense_profiles(self):
        """
        獲取 Realsense 設定檔

        回傳:
        dict: 更新後的設定檔
        """
        color_profiles, depth_profiles = rs.get_profiles()
        return tool.update_profile(color_profiles, depth_profiles)

    def start_realsense_preview(self, mode, config_dict):
        """
        啟動 Realsense 預覽並傳遞所需參數

        參數:
        mode (str): 操作模式
        config_dict (dict): 配置字典
        """
        if self.recorder:
            self.recorder.recive_from_model('stop_record')
        args = rs.Args(
            output_folder=config_dict['selected_path'],
            record_rosbag=config_dict['selected_items_dict']['Record rosbag'],
            record_imgs=config_dict['selected_items_dict']['Record imgs'],
            playback_rosbag=config_dict['selected_items_dict']['Playback rosbag'],
            calculate_overlap=config_dict['selected_items_dict']['Point Cloud'],
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
        """
        停止 Realsense 錄製器

        參數:
        mode (str): 操作模式
        """
        if self.recorder:
            self.recorder.recive_from_model(mode)

    def start_realsense_recorder(self, mode):
        """
        啟動 Realsense 錄製器

        參數:
        mode (str): 操作模式
        """
        if self.recorder:
            self.recorder.recive_from_model(mode)

    def start_view_system(self, mode, data):     
        self.view_system = rs.ViewSystem(self.recive_from_view_system)
        self.view_system.recive_from_model(mode, data)

    def stop_view_system(self, mode):
        if self.view_system:
            self.view_system.recive_from_model(mode)

    def check_path(self, config_dict):
        """
        檢查路徑是否存在及其狀態

        參數:
        config_dict (dict): 包含檢查類型和路徑的字典

        回傳:
        bool 或 str: 路徑狀態或檢查結果
        """
        check_type = config_dict['mode']
        path = config_dict['data']
        
        if check_type == 'check_file':
            return os.path.isfile(path)
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
