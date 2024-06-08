class Controller:
    def __init__(self, model, view):
        """
        初始化控制器並設置模型和視圖的回調函式

        參數:
        model (Model): 模型實例
        view (View): 視圖實例
        """
        self.model = model
        self.view = view
        # 設置視圖的控制器回調函式
        self.view.set_controller_callback(self.recive_from_view)
        # 設置模型的控制器回調函式
        self.model.set_controller_callback(self.recive_from_model)

    def recive_from_view(self, mode, selected_items_dict=None, realsense_selection=None, selected_path=None, data=None):
        """
        從視圖接收數據並根據模式進行處理

        參數:
        mode (str): 操作模式
        selected_items_dict (dict): 選擇的項目字典
        realsense_selection (list): Realsense 選擇
        selected_path (str): 選擇的路徑
        data (any): 附加數據
        """
        # 統一處理不同模式的調用
        if mode in ["get_realsense_profiles", "start_preview", "stop_record", "start_record", "check_dir", "check_file", "start_run_system", "start_view_system"]:
            if realsense_selection is None:
                # 這個空列表是為了避免在沒有選擇 realsense 的情況下出現錯誤
                realsense_selection = [[0, 0, 0, 0], [0, 0, 0, 0]]
            return self.send_to_model(
                mode, 
                selected_items_dict=selected_items_dict,
                realsense_selection=realsense_selection, 
                selected_path=selected_path,
                data=data
            )

    def recive_from_model(self, mode, data):
        """
        從模型接收數據並根據模式進行處理

        參數:
        mode (str): 操作模式
        data (any): 模型傳回的數據
        """
        if mode == "record_imgs":
            self.send_to_view("record_imgs", data)
        elif mode == "show_error":
            self.send_to_view("show_error", data)
        elif mode == "terminal_print":
            self.send_to_view("terminal_print", data)

    def send_to_view(self, mode, data):
        """
        向視圖發送數據

        參數:
        mode (str): 操作模式
        data (any): 要發送的數據
        """
        self.view.recive_from_controller(mode, data)
        
    def send_to_model(self, mode, **kwargs):
        """
        向模型發送數據

        參數:
        mode (str): 操作模式
        kwargs (dict): 其他參數
        """
        config_dict = {"mode": mode}
        config_dict.update(kwargs)
        return self.model.recive_from_controller(config_dict)
    
    def run(self):
        """
        啟動應用程式，顯示視圖
        """
        self.view.show()
