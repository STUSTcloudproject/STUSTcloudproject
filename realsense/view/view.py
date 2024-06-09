import os
import sys
# 將當前文件的目錄添加到 sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import o3d_gui

class ViewSystem:
    def __init__(self, callback=None):
        """
        初始化 ViewSystem 類別。

        參數:
        callback (callable, optional): 回調函數。預設為 None。
        """
        self.callback = callback

    def run(self):
        """
        啟動視圖系統。
        """
        try:
            print("\n\nView System is running\n\n")
            o3d_gui.run()  # 執行 Open3D GUI
        except Exception as e:
            print(f"Error starting run: {e}")
            self.send_to_model("show_error", {"title": "Error starting run", "message": str(e)})

    def receive_from_model(self, mode, data=None):
        """
        從模型接收消息。

        參數:
        mode (str): 模式。
        data (dict, optional): 附加數據。預設為 None。
        """
        try:
            if mode == "start_view_system":
                self.run()
        except Exception as e:
            print(f"Error receiving from model: {e}")
            self.send_to_model("show_error", {"title": "Error receiving from model", "message": str(e)})

    def send_to_model(self, mode, data=None):
        """
        發送消息到模型。

        參數:
        mode (str): 模式。
        data (dict, optional): 附加數據。預設為 None。
        """
        if self.callback is not None:
            try:
                if mode == "show_error" or mode == "terminal_print":
                    self.callback(mode, data)
            except Exception as e:
                print(f"Error sending to model: {e}")
                if mode != "show_error":
                    self.callback("show_error", {"title": "Error sending to model", "message": str(e)})

# 使用範例
if __name__ == "__main__":
    system = ViewSystem()
    system.run()
