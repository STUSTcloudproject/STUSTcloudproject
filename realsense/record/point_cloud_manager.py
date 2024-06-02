import multiprocessing
import threading
import time
import numpy as np
import ctypes
from queue import Queue
import open3d as o3d

class PointCloudManager:
    def __init__(self, depth_image_shape, data_queue, shared_depth_image, stop_event, intrinsics_dict):
        self.data_queue = data_queue
        self.depth_image_shape = depth_image_shape
        self.shared_depth_image = shared_depth_image
        self.stop_event = stop_event
        self.intrinsics_dict = intrinsics_dict
        self.threads = []
        self.point_cloud_queue = Queue()

    def add_point_cloud(self):
        while not self.stop_event.is_set():
            if not self.data_queue.empty():
                signal = self.data_queue.get()  # 接收信号
                if signal:
                    depth_image_np = np.frombuffer(self.shared_depth_image.get_obj(), dtype=np.uint16).reshape(self.depth_image_shape)
                    
                    self.point_cloud_queue.put(depth_image_np)
                    

    def visualize_point_cloud(self):
        vis = o3d.visualization.Visualizer()
        vis.create_window(window_name='Point Cloud Visualizer')
        
        # 创建一个初始的虚拟点云数据以避免Open3D警告
        initial_points = np.random.rand(100, 3)
        pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(initial_points))
        vis.add_geometry(pcd)

        while not self.stop_event.is_set():
            if not self.point_cloud_queue.empty():
                depth_image_np = self.point_cloud_queue.get()
                #print("Visualizing point cloud data:", depth_image_np.shape)

                # 将深度图像转换为点云
                points = self.convert_depth_to_pointcloud(depth_image_np)
                pcd.points = o3d.utility.Vector3dVector(points)

                # 更新点云数据并渲染
                vis.update_geometry(pcd)
                vis.poll_events()
                vis.update_renderer()
            else:
                time.sleep(0.1)

        vis.destroy_window()

    def convert_depth_to_pointcloud(self, depth_image):
        fx, fy = self.intrinsics_dict['fx'], self.intrinsics_dict['fy']
        cx, cy = self.intrinsics_dict['ppx'], self.intrinsics_dict['ppy']

        height, width = depth_image.shape
        x, y = np.meshgrid(np.arange(width), np.arange(height))
        z = depth_image / 1000.0  # 转换为米

        x = (x - cx) * z / fx
        y = (y - cy) * z / fy

        # 翻转 x 和 y 轴
        x = -x
        y = -y

        points = np.stack((x, y, z), axis=-1).reshape(-1, 3)
        return points

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

def run_point_cloud_manager(depth_image_shape, data_queue, shared_depth_image, stop_event, intrinsics_dict):
    point_cloud_manager = PointCloudManager(depth_image_shape, data_queue, shared_depth_image, stop_event, intrinsics_dict)
    point_cloud_manager.start()
    point_cloud_manager.join()
