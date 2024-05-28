from PyQt5.QtWidgets import QApplication
import sys
from gui import MainInterface

class View:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.main_interface = MainInterface(callback_to_view=self.recive_from_gui)
        self.send_to_gui = self.main_interface.get_gui_callback()
        self.controller_callback = None

    def show(self):
        self.main_interface.show()
        sys.exit(self.app.exec_())

    def recive_from_gui(self, mode, selected_items_dict = None, realsense_selection=None, selected_path=None, data=None):
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
            
        elif mode == "stop_record" or mode == "start_record":
            self.send_to_controller(mode)
        
        elif mode == "start_run_system":
           self.send_to_controller(
                mode, 
                selected_items_dict=selected_items_dict, 
                selected_path=selected_path
                )


    def set_controller_callback(self, controller_callback):
        self.controller_callback = controller_callback

    def send_to_controller(self, mode, selected_items_dict = None, realsense_selection=None, selected_path=None, data=None):
        return self.controller_callback(
            mode, 
            selected_items_dict=selected_items_dict, 
            realsense_selection=realsense_selection, 
            selected_path=selected_path,
            data=data
            )
    
    def recive_from_controller(self, mode, data):
        if mode == "record_imgs":
            self.send_to_gui("record_imgs", data)
        elif mode == "show_error":
            self.send_to_gui("show_error", data)
        elif mode == "terminal_print":
            self.send_to_gui("terminal_print", data)