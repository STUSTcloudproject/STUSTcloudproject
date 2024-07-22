from PyQt5.QtWidgets import QApplication
import sys
from gui import MainInterface

class View:
    def __init__(self):
        # 初始化 Qt 應用程序
        self.app = QApplication(sys.argv)
        # 創建主界面實例並設置回調函式
        self.main_interface = MainInterface(callback_to_view=self.recive_from_gui)
        # 從主界面獲取 GUI 回調函式
        self.send_to_gui = self.main_interface.get_gui_callback()
        # 初始化控制器回調函式
        self.controller_callback = None

    def show(self):
        # 顯示主界面
        self.main_interface.show()
        # 進入應用程序的主事件循環
        sys.exit(self.app.exec_())

    def recive_from_gui(self, mode, selected_items_dict=None, realsense_selection=None, selected_path=None, data=None):
        """
        從 GUI 接收數據並根據模式處理
        """
        print(f"GUI Callback: Mode: {mode}")
        if mode == "get_realsense_profiles":
            return self.send_to_controller("get_realsense_profiles", selected_items_dict)
        elif mode == "start_preview":
            self.send_to_controller(
                mode, 
                selected_items_dict=selected_items_dict, 
                realsense_selection=realsense_selection, 
                selected_path=selected_path
            )
        elif mode == "check_dir":
            return self.send_to_controller("check_dir", data=data)
        elif mode == "check_file":
            return self.send_to_controller("check_file", data=data)
        elif mode in ["stop_record", "start_record"]:
            self.send_to_controller(mode)
        elif mode == "start_run_system":
            self.send_to_controller(
                mode, 
                selected_items_dict=selected_items_dict, 
                selected_path=selected_path
            )
        elif mode == "start_view_system":
            self.send_to_controller(
                mode,
                selected_items_dict=selected_items_dict
            )

    def set_controller_callback(self, controller_callback):
        """
        設置控制器回調函式
        """
        self.controller_callback = controller_callback

    def send_to_controller(self, mode, selected_items_dict=None, realsense_selection=None, selected_path=None, data=None):
        """
        向控制器發送數據
        """
        return self.controller_callback(
            mode, 
            selected_items_dict=selected_items_dict, 
            realsense_selection=realsense_selection, 
            selected_path=selected_path,
            data=data
        )
    
    def recive_from_controller(self, mode, data):
        """
        從控制器接收數據並處理
        """
        if mode == "record_imgs":
            self.send_to_gui("record_imgs", data)
        elif mode == "show_error":
            self.send_to_gui("show_error", data)
        elif mode == "terminal_print":
            self.send_to_gui("terminal_print", data)
