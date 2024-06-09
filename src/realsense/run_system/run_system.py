import json
import time
import datetime
import os
import sys
import threading
import multiprocessing
import traceback

# 將當前文件的目錄添加到 sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from os.path import isfile
import open3d as o3d
from open3d_example import check_folder_structure
from initialize_config import initialize_config, dataset_loader

class Args_run_system:
    def __init__(self, config=None, make=False, register=False, refine=False, integrate=False, slac=False, slac_integrate=False, debug_mode=False):
        """
        初始化 Args_run_system 類別。

        參數:
        config (str, optional): 配置文件路徑。預設為 None。
        make (bool, optional): 是否生成碎片。預設為 False。
        register (bool, optional): 是否註冊碎片。預設為 False。
        refine (bool, optional): 是否優化註冊。預設為 False。
        integrate (bool, optional): 是否整合場景。預設為 False。
        slac (bool, optional): 是否執行 SLAC。預設為 False。
        slac_integrate (bool, optional): 是否執行 SLAC 整合。預設為 False。
        debug_mode (bool, optional): 是否啟用調試模式。預設為 False。
        """
        self.config = config
        self.make = make
        self.register = register
        self.refine = refine
        self.integrate = integrate
        self.slac = slac
        self.slac_integrate = slac_integrate
        self.debug_mode = debug_mode

class ReconstructionSystem:
    def __init__(self, args, callback=None):
        """
        初始化 ReconstructionSystem 類別。

        參數:
        args (Args_run_system): 配置參數。
        callback (callable, optional): 回調函數。預設為 None。
        """
        self.args = args
        self.callback = callback
        self.config = None
        self.times = [0, 0, 0, 0, 0, 0]
        self.thread = None
        self.manager = multiprocessing.Manager()
        self.stop_event = self.manager.Event()  # 使用 multiprocessing.Manager 提供的 Event
        self.message_queue = self.manager.Queue()
        self.monitor_event = threading.Event()
        self.monitor_thread = threading.Thread(target=self.monitor_messages)
        self.monitor_thread.start()

    def monitor_messages(self):
        """
        監控訊息佇列，並將其發送到模型。
        """
        while not self.monitor_event.is_set():
            try:
                message = self.message_queue.get(timeout=1)
                if message:
                    self.send_to_model("terminal_print", {"owner": "run_system", "message": message})
                    print(f"multiprocess : {message}")
            except:
                continue
        
        # 在 monitor_event 被設置後，確保佇列中的所有訊息都被處理完畢
        while not self.message_queue.empty():
            try:
                message = self.message_queue.get_nowait()
                if message:
                    self.send_to_model("terminal_print", {"owner": "run_system", "message": message})
                    print(f"multiprocess : {message}")
            except:
                break

    def load_config(self, message_queue=None):
        """
        加載配置文件。

        參數:
        message_queue (multiprocessing.Queue, optional): 訊息佇列。預設為 None。
        """
        try:
            if self.args.config is not None:
                with open(self.args.config, encoding='utf-8') as json_file:
                    self.config = json.load(json_file)
                    initialize_config(self.config, message_queue)
                    check_folder_structure(self.config['path_dataset'])

            assert self.config is not None
            self.config['debug_mode'] = self.args.debug_mode
        except Exception as e:
            tb = traceback.format_exc()
            print(f"Error loading config: {e}\n{tb}")
            self.send_to_model("show_error", {"title": "Error loading config", "message": str(e)})

    def execute(self):
        """
        執行重建系統的主要流程。
        """
        try:
            self.load_config(self.message_queue)
            
            self.message_queue.put("====================================")
            self.message_queue.put("Configuration")
            self.message_queue.put("====================================")
            for key, val in self.config.items():
                self.message_queue.put(f"{key:40} : {val}")

            if self.args.make:
                self.execute_step("make_fragments", "run", 0, self.stop_event, self.message_queue)
            if self.args.register:
                self.execute_step("register_fragments", "run", 1, self.stop_event, self.message_queue)
            if self.args.refine:
                self.execute_step("refine_registration", "run", 2, self.stop_event, self.message_queue)
            if self.args.integrate:
                self.execute_step("integrate_scene", "run", 3, self.stop_event, self.message_queue)
            if self.args.slac:
                self.execute_step("slac", "run", 4, self.stop_event, self.message_queue)
            if self.args.slac_integrate:
                self.execute_step("slac_integrate", "run", 5, self.stop_event, self.message_queue)

            while not self.message_queue.empty():
                time.sleep(0.5)

            self.print_elapsed_time()
            if not self.stop_event.is_set():
                self.message_queue.put("Reconstruction System finished")
            else:
                self.message_queue.put("Reconstruction System was forcibly stopped")
            self.monitor_event.set()
        except Exception as e:
            tb = traceback.format_exc()
            print(f"Error during execution: {e}\n{tb}")
            self.send_to_model("show_error", {"title": "Error during execution", "message": str(e)})

    def execute_step(self, module_name, function_name, index, stop_event=None, message_queue=None):
        """
        執行特定步驟。

        參數:
        module_name (str): 模組名稱。
        function_name (str): 函數名稱。
        index (int): 步驟索引。
        stop_event (multiprocessing.Event, optional): 停止事件。預設為 None。
        message_queue (multiprocessing.Queue, optional): 訊息佇列。預設為 None。
        """
        try:
            if self.stop_event.is_set():
                return
            start_time = time.time()
            module = __import__(module_name)
            if stop_event:
                if message_queue:
                    getattr(module, function_name)(self.config, stop_event, message_queue)
                else:
                    getattr(module, function_name)(self.config, stop_event)
            else:
                getattr(module, function_name)(self.config)
            self.times[index] = time.time() - start_time
        except Exception as e:
            tb = traceback.format_exc()
            print(f"Error in execute_step {module_name}: {e}")
            print(tb)
            self.send_to_model("show_error", {"title": f"Error in execute_step {module_name}", "message": str(e)})

    def print_elapsed_time(self):
        """
        輸出每個步驟的執行時間。
        """
        try:
            self.message_queue.put("====================================")
            self.message_queue.put("Elapsed time (in h:m:s)")
            self.message_queue.put("====================================")
            steps = ["Making fragments", "Register fragments", "Refine registration", "Integrate frames", "SLAC", "SLAC Integrate"]
            for i, step in enumerate(steps):
                self.message_queue.put(f"- {step:20} {datetime.timedelta(seconds=self.times[i])}")
            self.message_queue.put(f"- Total               {datetime.timedelta(seconds=sum(self.times))}")
            sys.stdout.flush()
        except Exception as e:
            print(f"Error printing elapsed time: {e}")
            self.send_to_model("show_error", {"title": "Error printing elapsed time", "message": str(e)})

    def run(self):
        """
        啟動重建系統。
        """
        try:
            print("\n\nReconstruction System is running\n\n")
            self.thread = threading.Thread(target=self.execute)
            self.thread.start()
        except Exception as e:
            print(f"Error starting run: {e}")
            self.send_to_model("show_error", {"title": "Error starting run", "message": str(e)})

    def stop(self):
        """
        停止重建系統。
        """
        try:
            print("\n\nReconstruction System is stopping\n\n")
            self.stop_event.set()
            if self.thread is not None:
                self.thread.join()
        except Exception as e:
            print(f"Error stopping run: {e}")
            self.send_to_model("show_error", {"title": "Error stopping run", "message": str(e)})

    def recive_from_model(self, mode, data=None):
        """
        從模型接收消息。

        參數:
        mode (str): 模式。
        data (dict, optional): 附加數據。預設為 None。
        """
        try:
            if mode == "start_run_system":
                self.run()
            elif mode == "stop_run_system":
                self.stop()
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
    args = Args_run_system(
        config='realsense.json',
        make=True,
        register=True,
        refine=True,
        integrate=True,
        slac=False,
        slac_integrate=False,
        debug_mode=False
    )
    system = ReconstructionSystem(args)
    system.run()
    # 添加一個示例來停止線程
    time.sleep(10)  # 這裡只是等待10秒來模擬運行中的一些操作
    system.stop()
