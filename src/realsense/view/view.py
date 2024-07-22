import os
import sys
import multiprocessing
from open3d.visualization import gui

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import o3d_gui
import PointCloud_Mesh_Editor
import registration_manual_automatic
import remove_point_cloud_gui
import online_processing


def run_view_system(data):
    try:
        print("\n\nView System is running\n\n")
        gui.Application.instance.initialize()
        if data['Visualization']:
            app_window = o3d_gui.AppWindow(1024, 768)
        elif data['Registration']:
            app_window = registration_manual_automatic.AppWindow(1024, 768)
        elif data['Point Cloud Remove']:
            app_window = remove_point_cloud_gui.AppWindow(1024, 768)
        elif data['PointCloud Mesh Editor']:
            app_window = PointCloud_Mesh_Editor.AppWindow(1024, 768)
        elif data['Depth Stream']:
            app_window = online_processing.PipelineController()
        gui.Application.instance.run()  # 初始化和运行 Open3D GUI
    except Exception as e:
        print(f"Error starting run: {e}")

class ViewSystem:
    def __init__(self, callback=None):
        self.callback = callback
        self.process = None

    def start_new_process(self, data):
        try:
            multiprocessing.set_start_method('spawn', force=True)  # 使用 spawn 方法
            self.process = multiprocessing.Process(target=run_view_system, args=(data,))
            self.process.start()
        except Exception as e:
            print(f"Error starting new process: {e}")
            self.send_to_model("show_error", {"title": "Error starting new process", "message": str(e)})

    def stop_process(self):
        if self.process is not None:
            self.process.terminate()
            self.process.join()
            self.process = None

    def recive_from_model(self, mode, data=None):
        try:
            if mode == "start_view_system":
                self.start_new_process(data['selected_items_dict'])
            elif mode == "stop_view_system":
                self.stop_process()
        except Exception as e:
            print(f"Error receiving from model: {e}")
            self.send_to_model("show_error", {"title": "Error receiving from model", "message": str(e)})

    def send_to_model(self, mode, data=None):
        if self.callback is not None:
            try:
                if mode == "show_error" or mode == "terminal_print":
                    self.callback(mode, data)
            except Exception as e:
                print(f"Error sending to model: {e}")
                if mode != "show_error":
                    self.callback("show_error", {"title": "Error sending to model", "message": str(e)})

# 示例用法
if __name__ == "__main__":
    data = {
        'selected_items_dict': {
            'Depth Stream': False,
            'Registration': True,
            'Point Cloud Remove': False,
            'PointCloud Mesh Editor': False,
            'Visualization': False
        }
    }
    system = ViewSystem()
    system.recive_from_model("start_view_system", data)

    # 模拟按键操作，在需要关闭时调用stop_process
    import time
    time.sleep(5)  # 模拟一些操作
    system.recive_from_model("stop_view_system")
