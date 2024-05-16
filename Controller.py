class Controller:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.view.set_controller_callback(self.callback_from_view)

    def handle_mode(self, mode, **kwargs):
        config_dict = {"mode": mode}
        config_dict.update(kwargs)
        return self.model.callback_from_controller(config_dict)

    def callback_from_view(self, mode, selected_items_dict=None, realsense_selection=None, selected_path=None, data=None):
        # 統一處理不同模式的調用
        if mode in ["get_realsense_profiles", "Record", "RunSystem", "View", "Stop_Record", "check_dir", "check_file"]:
            if realsense_selection == None:
                #這個空列表是為了避免在沒有選擇realsense的情況下出現錯誤
                realsense_selection = [[0, 0, 0, 0], [0, 0, 0, 0]]
            return self.handle_mode(
                mode, 
                selected_items_dict=selected_items_dict,
                realsense_selection=realsense_selection, 
                selected_path=selected_path,
                data=data
                )

    def run(self):
        self.view.show()
