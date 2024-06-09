import multiprocessing
import threading
import time
import numpy as np
import ctypes
from queue import Queue
import open3d as o3d

class PointCloudManager:
    def __init__(self, depth_image_shape, data_queue, shared_depth_image, stop_event, intrinsics_dict, voxel_size=0.02):
        """
        初始化 PointCloudManager。

        參數:
        depth_image_shape (tuple): 深度圖像的形狀 (height, width)。
        data_queue (multiprocessing.Queue): 用於接收新數據的隊列。
        shared_depth_image (multiprocessing.Array): 共享的深度圖像數組。
        stop_event (multiprocessing.Event): 用於停止所有線程的事件。
        intrinsics_dict (dict): 相機內參字典，包含 'fx', 'fy', 'ppx', 'ppy'。
        voxel_size (float, optional): 體素大小，用於下採樣點雲。預設為 0.02。
        """
        self.data_queue = data_queue
        self.depth_image_shape = depth_image_shape
        self.shared_depth_image = shared_depth_image
        self.stop_event = stop_event
        self.intrinsics_dict = intrinsics_dict
        self.voxel_size = voxel_size
        self.threads = []
        self.point_cloud_queue = Queue()
        self.point_clouds = []
        self.transformation_matrices = []

    def add_point_cloud(self):
        """
        從數據隊列中獲取深度圖像，並將其添加到點雲隊列中。
        """
        while not self.stop_event.is_set():
            if not self.data_queue.empty():
                signal = self.data_queue.get()  # 接收信號
                if signal:
                    depth_image_np = np.frombuffer(self.shared_depth_image.get_obj(), dtype=np.uint16).reshape(self.depth_image_shape)
                    self.point_cloud_queue.put(depth_image_np)

    def visualize_point_cloud(self):
        """
        可視化點雲數據。
        """
        vis = o3d.visualization.Visualizer()
        vis.create_window(window_name='Point Cloud Visualizer')
        
        # 創建一個初始的虛擬點雲數據以避免 Open3D 警告
        initial_points = np.random.rand(5, 3)
        pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(initial_points))
        vis.add_geometry(pcd)

        while not self.stop_event.is_set():
            if not self.point_cloud_queue.empty():
                depth_image_np = self.point_cloud_queue.get()
                
                # 將深度圖像轉換為點雲
                points = self.convert_depth_to_pointcloud(depth_image_np)
                new_pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(points))
                new_pcd = new_pcd.voxel_down_sample(self.voxel_size)
                new_pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=self.voxel_size * 2, max_nn=30))

                if len(self.point_clouds) > 0:
                    # 與上一个點雲進行配準
                    transformation_icp, _ = self.pairwise_registration(self.point_clouds[-1], new_pcd)
                    new_pcd.transform(transformation_icp)
                    self.transformation_matrices.append(transformation_icp)

                self.point_clouds.append(new_pcd)
                combined_pcd = self.get_combined_point_cloud()

                # 更新點雲數據並渲染
                pcd.points = combined_pcd.points
                pcd.colors = combined_pcd.colors
                vis.update_geometry(pcd)
                vis.poll_events()
                vis.update_renderer()
            else:
                pass
                #time.sleep(0.1)

        vis.destroy_window()

    def convert_depth_to_pointcloud(self, depth_image):
        """
        將深度圖像轉換為點雲。

        參數:
        depth_image (np.ndarray): 深度圖像數組。

        回傳:
        np.ndarray: 點雲數據。
        """
        fx, fy = self.intrinsics_dict['fx'], self.intrinsics_dict['fy']
        cx, cy = self.intrinsics_dict['ppx'], self.intrinsics_dict['ppy']

        height, width = depth_image.shape
        x, y = np.meshgrid(np.arange(width), np.arange(height))
        z = depth_image / 1000.0  # 轉換為米

        x = (x - cx) * z / fx
        y = (y - cy) * z / fy

        # 翻轉 x 和 y 軸
        x = -x
        y = -y

        points = np.stack((x, y, z), axis=-1).reshape(-1, 3)
        return points

    def pairwise_registration(self, source, target):
        """
        使用 ICP 算法進行配準。

        參數:
        source (o3d.geometry.PointCloud): 來源點雲。
        target (o3d.geometry.PointCloud): 目標點雲。

        回傳:
        tuple: 包含配準矩陣和信息矩陣的元組。
        """
        print("Apply point-to-plane ICP")
        icp_coarse = o3d.pipelines.registration.registration_icp(
            source, target, self.voxel_size * 15, np.identity(4),
            o3d.pipelines.registration.TransformationEstimationPointToPlane())
        icp_fine = o3d.pipelines.registration.registration_icp(
            source, target, self.voxel_size * 1.5, icp_coarse.transformation,
            o3d.pipelines.registration.TransformationEstimationPointToPlane())
        transformation_icp = icp_fine.transformation
        information_icp = o3d.pipelines.registration.get_information_matrix_from_point_clouds(
            source, target, self.voxel_size * 1.5, icp_fine.transformation)
        return transformation_icp, information_icp

    def get_combined_point_cloud(self):
        """
        獲取合併的點雲。

        回傳:
        o3d.geometry.PointCloud: 合併後的點雲。
        """
        combined_pcd = o3d.geometry.PointCloud()
        for pcd in self.point_clouds:
            combined_pcd += pcd
        return combined_pcd

    def start(self):
        """
        啟動點雲管理器。
        """
        t1 = threading.Thread(target=self.add_point_cloud)
        t2 = threading.Thread(target=self.visualize_point_cloud)
        t1.start()
        t2.start()
        self.threads.append(t1)
        self.threads.append(t2)

    def join(self):
        """
        等待所有線程結束。
        """
        for t in self.threads:
            t.join()

def run_point_cloud_manager(depth_image_shape, data_queue, shared_depth_image, stop_event, intrinsics_dict):
    """
    運行點雲管理器。

    參數:
    depth_image_shape (tuple): 深度圖像的形狀 (height, width)。
    data_queue (multiprocessing.Queue): 用於接收新數據的隊列。
    shared_depth_image (multiprocessing.Array): 共享的深度圖像數組。
    stop_event (multiprocessing.Event): 用於停止所有線程的事件。
    intrinsics_dict (dict): 相機內參字典，包含 'fx', 'fy', 'ppx', 'ppy'。
    """
    point_cloud_manager = PointCloudManager(depth_image_shape, data_queue, shared_depth_image, stop_event, intrinsics_dict)
    point_cloud_manager.start()
    point_cloud_manager.join()
