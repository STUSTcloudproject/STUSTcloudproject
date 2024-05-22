import json
import time
import datetime
import os
import sys
import threading

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
    def __init__(self, args):
        self.args = args
        self.config = None
        self.times = [0, 0, 0, 0, 0, 0]
        self.load_config()
        self.thread = None
        self.stop_event = threading.Event()

    def load_config(self):
        if self.args.config is not None:
            with open(self.args.config) as json_file:
                self.config = json.load(json_file)
                initialize_config(self.config)
                check_folder_structure(self.config['path_dataset'])
        
        assert self.config is not None
        self.config['debug_mode'] = self.args.debug_mode

    def execute(self):
        print("====================================")
        print("Configuration")
        print("====================================")
        for key, val in self.config.items():
            print(f"{key:40} : {val}")

        if self.args.make:
            self.execute_step("make_fragments", "run", 0)
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

    def execute_step(self, module_name, function_name, index):
        if self.stop_event.is_set():
            return
        start_time = time.time()
        module = __import__(module_name)
        getattr(module, function_name)(self.config)
        self.times[index] = time.time() - start_time

    def print_elapsed_time(self):
        print("====================================")
        print("Elapsed time (in h:m:s)")
        print("====================================")
        steps = ["Making fragments", "Register fragments", "Refine registration", "Integrate frames", "SLAC", "SLAC Integrate"]
        for i, step in enumerate(steps):
            print(f"- {step:20} {datetime.timedelta(seconds=self.times[i])}")
        print(f"- Total               {datetime.timedelta(seconds=sum(self.times))}")
        sys.stdout.flush()

    def run(self):
        self.thread = threading.Thread(target=self.execute)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join()

# Usage Example
if __name__ == "__main__":
    args = Args_run_system(
        config='E:/PointCloud_qt_gui/realsense.json',
        make=True,
        register=True,
        refine=True,
        integrate=True,
        slac=False,
        slac_integrate=False,
        debug_mode=True
    )
    system = ReconstructionSystem(args)
    system.run()
    # 添加一個示例來停止線程
    time.sleep(5)  # 這裡只是等待5秒來模擬運行中的一些操作
    system.stop()
