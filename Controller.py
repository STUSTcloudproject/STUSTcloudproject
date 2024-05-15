class Controller:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.view.set_controller_callback(self.callback_from_view)

    def callback_from_view(self, mode, selected_items_dict=None, realsense_selection=None, selected_path=None):
        if mode == "get_realsense_profiles":
            return self.model.callback_from_controller({"mode": mode})
        elif mode == "Record" or mode == "RunSystem" or mode == "View":
            config_dict = {
                "mode": mode,
                "selected_items_dict": selected_items_dict,
                "realsense_selection": realsense_selection,
                "selected_path": selected_path
            }
            self.model.callback_from_controller(config_dict)
        
        elif mode == "Stop_Record":
            self.model.callback_from_controller({"mode": mode})

    def run(self):
        self.view.show()
