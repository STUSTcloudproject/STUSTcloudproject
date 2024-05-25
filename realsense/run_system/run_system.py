import json
import time
import datetime
import os
import sys
import threading
import multiprocessing

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from os.path import isfile
import open3d as o3d
from open3d_example import check_folder_structure
from initialize_config import initialize_config, dataset_loader

class Args_run_system:
    def __init__(self, config=None, make=False, register=False, refine=False, integrate=False, slac=False, slac_integrate=False, debug_mode=False):
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
        self.args = args
        self.callback = callback
        self.config = None
        self.times = [0, 0, 0, 0, 0, 0]
        self.load_config()
        self.thread = None
        self.manager = multiprocessing.Manager()
        self.stop_event = self.manager.Event()  # 使用 multiprocessing.Manager 提供的 Event

    def load_config(self):
        try:
            if self.args.config is not None:
                with open(self.args.config) as json_file:
                    self.config = json.load(json_file)
                    initialize_config(self.config)
                    check_folder_structure(self.config['path_dataset'])

            assert self.config is not None
            self.config['debug_mode'] = self.args.debug_mode
        except Exception as e:
            print(f"Error loading config: {e}")
            self.send_to_model("show_error", {"title": "Error loading config", "message": str(e)})

    def execute(self):
        try:
            print("====================================")
            print("Configuration")
            print("====================================")
            for key, val in self.config.items():
                print(f"{key:40} : {val}")

            if self.args.make:
                self.execute_step("make_fragments", "run", 0, self.stop_event)
            if self.args.register:
                self.execute_step("register_fragments", "run", 1)
            if self.args.refine:
                self.execute_step("refine_registration", "run", 2)
            if self.args.integrate:
                self.execute_step("integrate_scene", "run", 3)
            if self.args.slac:
                self.execute_step("slac", "run", 4)
            if self.args.slac_integrate:
                self.execute_step("slac_integrate", "run", 5)

            self.print_elapsed_time()
        except Exception as e:
            print(f"Error during execution: {e}")
            self.send_to_model("show_error", {"title": "Error during execution", "message": str(e)})

    def execute_step(self, module_name, function_name, index, stop_event=None):
        try:
            if self.stop_event.is_set():
                return
            start_time = time.time()
            module = __import__(module_name)
            if stop_event:
                getattr(module, function_name)(self.config, stop_event)
            else:
                getattr(module, function_name)(self.config)
            self.times[index] = time.time() - start_time
        except Exception as e:
            print(f"Error in execute_step {module_name}: {e}")
            self.send_to_model("show_error", {"title": f"Error in execute_step {module_name}", "message": str(e)})

    def print_elapsed_time(self):
        try:
            print("====================================")
            print("Elapsed time (in h:m:s)")
            print("====================================")
            steps = ["Making fragments", "Register fragments", "Refine registration", "Integrate frames", "SLAC", "SLAC Integrate"]
            for i, step in enumerate(steps):
                print(f"- {step:20} {datetime.timedelta(seconds=self.times[i])}")
            print(f"- Total               {datetime.timedelta(seconds=sum(self.times))}")
            sys.stdout.flush()
        except Exception as e:
            print(f"Error printing elapsed time: {e}")
            self.send_to_model("show_error", {"title": "Error printing elapsed time", "message": str(e)})

    def run(self):
        try:
            print("\n\nReconstruction System is running\n\n")
            self.thread = threading.Thread(target=self.execute)
            self.thread.start()
        except Exception as e:
            print(f"Error starting run: {e}")
            self.send_to_model("show_error", {"title": "Error starting run", "message": str(e)})

    def stop(self):
        try:
            print("\n\nReconstruction System is stopping\n\n")
            self.stop_event.set()
            if self.thread is not None:
                self.thread.join()
        except Exception as e:
            print(f"Error stopping run: {e}")
            self.send_to_model("show_error", {"title": "Error stopping run", "message": str(e)})

    def recive_from_model(self, mode, data=None):
        try:
            if mode == "start_run_system":
                self.run()
            elif mode == "stop_run_system":
                self.stop()
        except Exception as e:
            print(f"Error receiving from model: {e}")
            self.send_to_model("show_error", {"title": "Error receiving from model", "message": str(e)})

    def send_to_model(self, mode, data=None):
        if self.callback is not None:
            try:
                if mode == "show_error":
                    self.callback(mode, data)
            except Exception as e:
                print(f"Error sending to model: {e}")
                if mode != "show_error":
                    self.callback("show_error", {"title": "Error sending to model", "message": str(e)})

# Usage Example
if __name__ == "__main__":
    args = Args_run_system(
        config='E:/MVC_gui/realsense.json',
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
    time.sleep(10)  # 這裡只是等待5秒來模擬運行中的一些操作
    system.stop()
