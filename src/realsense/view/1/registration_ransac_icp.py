import open3d as o3d
import numpy as np
import time  # 用于计算时间

def perform_registration(source, target, voxel_size=0.05, 
                         ransac_distance_multiplier=1.5, 
                         ransac_max_iterations=4000000, 
                         ransac_max_validation=500, 
                         icp_distance_multiplier=0.4):
    """
    执行自动配准。
    
    参数:
    source (open3d.geometry.PointCloud): 源点云
    target (open3d.geometry.PointCloud): 目标点云
    voxel_size (float): 体素大小，用于降采样
    ransac_distance_multiplier (float): RANSAC配准时的距离阈值倍数
    ransac_max_iterations (int): RANSAC的最大迭代次数
    ransac_max_validation (int): RANSAC的最大验证次数
    icp_distance_multiplier (float): ICP算法中的距离阈值倍数

    返回:
    open3d.pipelines.registration.RegistrationResult: 配准结果，包含用于将源点云对齐到目标点云的变换矩阵。
    """
    print("Starting registration...")
    start_time = time.time()

    preprocess_start = time.time()
    source_down, source_fpfh = preprocess_point_cloud(source, voxel_size)
    target_down, target_fpfh = preprocess_point_cloud(target, voxel_size)
    print(f"target's down point count {len(target_down.points)}")
    print(f"source's down point count {len(source_down.points)}")
    preprocess_end = time.time()
    print(f"Preprocessing time: {preprocess_end - preprocess_start:.6f} seconds")

    global_registration_start = time.time()
    result_ransac = execute_global_registration(
        source_down, target_down, source_fpfh, target_fpfh, voxel_size, 
        ransac_distance_multiplier, ransac_max_iterations, ransac_max_validation
    )
    global_registration_end = time.time()
    print(f"Global registration time: {global_registration_end - global_registration_start:.6f} seconds")

    refine_registration_start = time.time()
    result_icp = refine_registration(source, target, voxel_size, result_ransac, icp_distance_multiplier)
    refine_registration_end = time.time()
    print(f"Refine registration time: {refine_registration_end - refine_registration_start:.6f} seconds")

    end_time = time.time()
    print(f"Total registration time: {end_time - start_time:.6f} seconds")

    return result_icp

def preprocess_point_cloud(pcd, voxel_size):
    """
    预处理点云，包括体素降采样和法线估计。

    参数:
    pcd (open3d.geometry.PointCloud): 输入的点云对象
    voxel_size (float): 用于降采样的体素大小

    返回:
    pcd_down (open3d.geometry.PointCloud): 降采样后的点云
    pcd_fpfh (open3d.pipelines.registration.Feature): 点云的FPFH特征
    """
    start_time = time.time()
    
    pcd_down = pcd.voxel_down_sample(voxel_size)
    pcd_down.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2.0, max_nn=30))
    pcd_fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        pcd_down,
        o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 5.0, max_nn=100))

    end_time = time.time()
    print(f"Preprocess point cloud time: {end_time - start_time:.6f} seconds")
    
    return pcd_down, pcd_fpfh

def execute_global_registration(source_down, target_down, source_fpfh, target_fpfh, voxel_size, 
                                ransac_distance_multiplier, ransac_max_iterations, ransac_max_validation):
    """
    执行基于特征匹配的全局配准。

    参数:
    source_down (open3d.geometry.PointCloud): 降采样后的源点云
    target_down (open3d.geometry.PointCloud): 降采样后的目标点云
    source_fpfh (open3d.pipelines.registration.Feature): 源点云的FPFH特征
    target_fpfh (open3d.pipelines.registration.Feature): 目标点云的FPFH特征
    voxel_size (float): 体素大小，用于确定配准过程中的距离阈值
    ransac_distance_multiplier (float): RANSAC的距离阈值倍数
    ransac_max_iterations (int): RANSAC的最大迭代次数
    ransac_max_validation (int): RANSAC的最大验证次数

    返回:
    result (open3d.pipelines.registration.RegistrationResult): RANSAC配准结果，包含初步的变换矩阵。
    """
    start_time = time.time()
    
    distance_threshold = voxel_size * ransac_distance_multiplier
    result = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
        source_down, target_down, source_fpfh, target_fpfh, True,
        distance_threshold,
        o3d.pipelines.registration.TransformationEstimationPointToPoint(False),
        4, [
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnEdgeLength(0.9),
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(distance_threshold)
        ], o3d.pipelines.registration.RANSACConvergenceCriteria(max_iteration=ransac_max_iterations, confidence=0.999))  # 修正此行
    
    end_time = time.time()
    print(f"Global registration time: {end_time - start_time:.6f} seconds")

    return result


def refine_registration(source, target, voxel_size, result_ransac, icp_distance_multiplier):
    """
    使用ICP算法对初步配准结果进行精细配准。

    参数:
    source (open3d.geometry.PointCloud): 源点云
    target (open3d.geometry.PointCloud): 目标点云
    voxel_size (float): 体素大小，用于确定ICP算法中的距离阈值
    result_ransac (open3d.pipelines.registration.RegistrationResult): 初步RANSAC配准结果
    icp_distance_multiplier (float): ICP的距离阈值倍数

    返回:
    result (open3d.pipelines.registration.RegistrationResult): ICP精细配准结果，包含更准确的变换矩阵。
    """
    start_time = time.time()

    source.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2.0, max_nn=30))
    target.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2.0, max_nn=30))
    distance_threshold = voxel_size * icp_distance_multiplier
    result = o3d.pipelines.registration.registration_icp(
        source, target, distance_threshold, result_ransac.transformation,
        o3d.pipelines.registration.TransformationEstimationPointToPlane())

    end_time = time.time()
    print(f"Refine registration time: {end_time - start_time:.6f} seconds")

    return result
