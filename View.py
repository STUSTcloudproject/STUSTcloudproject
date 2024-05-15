from PyQt5.QtWidgets import QApplication
import sys
from gui import MainInterface

class View:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.main_interface = MainInterface(callback_to_view=self.gui_callback)
        self.controller_callback = None

    def show(self):
        self.main_interface.show()
        sys.exit(self.app.exec_())

    def gui_callback(self, mode, selected_items_dict = None, realsense_selection=None, selected_path=None):
        print(f"GUI Callback: Mode: {mode}")
        if mode == "get_realsense_profiles":
            return self.callback_to_controller("get_realsense_profiles", selected_items_dict)
        elif mode == "Record" or mode == "RunSystem" or mode == "View":
            self.callback_to_controller(
                mode, 
                selected_items_dict=selected_items_dict, 
                realsense_selection=realsense_selection, 
                selected_path=selected_path
                )


    def set_controller_callback(self, controller_callback):
        self.controller_callback = controller_callback

    def callback_to_controller(self, mode, selected_items_dict = None, realsense_selection=None, selected_path=None):
        return self.controller_callback(
            mode, 
            selected_items_dict=selected_items_dict, 
            realsense_selection=realsense_selection, 
            selected_path=selected_path
            )