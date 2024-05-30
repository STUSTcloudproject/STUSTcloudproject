import multiprocessing
import threading
import time
import numpy as np
import ctypes

class PointCloudManager:
    def __init__(self, depth_image_shape, data_queue, shared_depth_image, stop_event):
        self.data_queue = data_queue
        self.depth_image_shape = depth_image_shape
        self.shared_depth_image = shared_depth_image
        self.stop_event = stop_event
        self.threads = []

    def add_point_cloud(self):
        while not self.stop_event.is_set():
            if not self.data_queue.empty():
                intrinsics_dict = self.data_queue.get()
                depth_image_np = np.frombuffer(self.shared_depth_image.get_obj(), dtype=np.uint16).reshape(self.depth_image_shape)
                print("Point cloud data added:", depth_image_np.shape, intrinsics_dict)
                # 這裡你可以添加處理點雲數據的代碼
                time.sleep(0.1)

    def visualize_point_cloud(self):
        while not self.stop_event.is_set():
            print("Visualizing point cloud data...")
            time.sleep(1)

    def start(self):
        t1 = threading.Thread(target=self.add_point_cloud)
        t2 = threading.Thread(target=self.visualize_point_cloud)
        t1.start()
        t2.start()
        self.threads.append(t1)
        self.threads.append(t2)

    def join(self):
        for t in self.threads:
            t.join()

def run_point_cloud_manager(depth_image_shape, data_queue, shared_depth_image, stop_event):
    point_cloud_manager = PointCloudManager(depth_image_shape, data_queue, shared_depth_image, stop_event)
    point_cloud_manager.start()
    point_cloud_manager.join()
