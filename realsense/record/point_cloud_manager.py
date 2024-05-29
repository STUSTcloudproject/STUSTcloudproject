import open3d as o3d
import numpy as np
import threading
import queue
import pyrealsense2 as rs
import time

class PointCloudManager:
    def __init__(self, voxel_size=0.05):
        self.voxel_size = voxel_size
        self.all_points = o3d.geometry.PointCloud()
        self.overlapping_points = o3d.geometry.PointCloud()  # 用于存储重叠部分的点云
        self.octree = o3d.geometry.Octree(max_depth=10)
        self.octree.convert_from_point_cloud(self.all_points, size_expand=0.01)
        self.vis = None
        self.vis_thread = threading.Thread(target=self._create_visualizer)
        self.vis_thread.start()

        self.point_cloud_queue = queue.Queue()
        self.queue_lock = threading.Lock()  # 添加锁以确保线程安全
        self.processing_thread = threading.Thread(target=self._process_point_clouds)
        self.processing_thread.start()

    def _create_visualizer(self):
        self.vis = o3d.visualization.Visualizer()
        self.vis.create_window()
        self.vis.add_geometry(self.all_points)
        self.vis.add_geometry(self.overlapping_points)
        while True:
            self.update_visualizer()

    def add_point_cloud(self, depth_image, intrinsics):
        with self.queue_lock:  # 确保线程安全
            self.point_cloud_queue.put((depth_image, intrinsics))

    def _process_point_clouds(self):
        while True:
            try:
                with self.queue_lock:  # 确保线程安全
                    if not self.point_cloud_queue.empty():
                        depth_image, intrinsics = self.point_cloud_queue.get()
                        points = self.generate_point_cloud(depth_image, intrinsics)
                        points = points.astype(np.float64)  # 确保数据类型为 float64
                        new_point_cloud = o3d.geometry.PointCloud()
                        new_point_cloud.points = o3d.utility.Vector3dVector(points)
                        self.all_points += new_point_cloud

                        # 检测重叠部分
                        overlapping_points = self.detect_overlap(points)
                        if len(overlapping_points) > 0:  # 确保有重叠点
                            self.overlapping_points.points = o3d.utility.Vector3dVector(overlapping_points)
                            self.overlapping_points.paint_uniform_color([1, 0, 0])  # 设置重叠部分为红色

                        self.octree = o3d.geometry.Octree(max_depth=10)
                        self.octree.convert_from_point_cloud(self.all_points, size_expand=0.01)
            except Exception as e:
                print(f"Error processing point cloud: {e}")

    def generate_point_cloud(self, depth_image, intrinsics):
        height, width = depth_image.shape
        fx, fy = intrinsics.fx, intrinsics.fy
        ppx, ppy = intrinsics.ppx, intrinsics.ppy

        x = np.linspace(0, width - 1, width)
        y = np.linspace(0, height - 1, height)
        xv, yv = np.meshgrid(x, y)

        z = depth_image / 1000.0  # Convert depth to meters
        x = (xv - ppx) * z / fx
        y = (yv - ppy) * z / fy
        points = np.stack((x, y, z), axis=-1).reshape(-1, 3)
        return points

    def detect_overlap(self, new_points):
        overlapping_points = []
        for point in new_points:
            found, node = self.octree.locate_leaf_node(point)
            if found:
                overlapping_points.append(point)
        return np.array(overlapping_points, dtype=np.float64)

    def update_visualizer(self):
        if self.vis is not None:
            self.vis.update_geometry(self.all_points)
            self.vis.update_geometry(self.overlapping_points)  # 更新重叠部分的可视化
            self.vis.poll_events()
            self.vis.update_renderer()
            print("Update visualizer")
            time.sleep(2)  # 添加延迟，减少更新频率

    def close_visualizer(self):
        if self.vis is not None:
            self.vis.destroy_window()
