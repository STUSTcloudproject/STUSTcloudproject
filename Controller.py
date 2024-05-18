class Controller:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.view.set_controller_callback(self.recive_from_view)
        self.model.set_controller_callback(self.recive_from_model)

    def recive_from_view(self, mode, selected_items_dict=None, realsense_selection=None, selected_path=None, data=None):
        # 統一處理不同模式的調用
        if mode in ["get_realsense_profiles", "start_record", "stop_record", "check_dir", "check_file"]:
            if realsense_selection == None:
                #這個空列表是為了避免在沒有選擇realsense的情況下出現錯誤
                realsense_selection = [[0, 0, 0, 0], [0, 0, 0, 0]]
            return self.send_to_model(
                mode, 
                selected_items_dict=selected_items_dict,
                realsense_selection=realsense_selection, 
                selected_path=selected_path,
                data=data
                )

    def recive_from_model(self, mode, data):
        if mode == "record_imgs":
            self.send_to_view("record_imgs", data)

    def send_to_view(self, mode, data):
        self.view.recive_from_controller(mode, data)
        
    def send_to_model(self, mode, **kwargs):
        config_dict = {"mode": mode}
        config_dict.update(kwargs)
        return self.model.recive_from_controller(config_dict)
    
    def run(self):
        self.view.show()

