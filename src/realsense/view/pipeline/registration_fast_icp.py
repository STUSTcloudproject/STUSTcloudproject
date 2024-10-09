import open3d as o3d
import numpy as np
import time

import open3d as o3d

def perform_fast_registration(source, target, voxel_size=0.05):
    """
    执行快速配准。
    
    参数:
    source (open3d.geometry.PointCloud): 源点云
    target (open3d.geometry.PointCloud): 目标点云
    
    返回:
    open3d.pipelines.registration.RegistrationResult: 配准结果，包含用于将源点云对齐到目标点云的变换矩阵。
    """
    print("Starting fast registration...")
    start_time = time.time()

    # 预处理点云
    preprocess_start = time.time()
    source_down, source_fpfh = preprocess_point_cloud(source, voxel_size)
    target_down, target_fpfh = preprocess_point_cloud(target, voxel_size)
    preprocess_end = time.time()
    print(f"Preprocessing time: {preprocess_end - preprocess_start:.6f} seconds")

    # 直接使用 ICP 进行全局配准，跳过 RANSAC 和 FPFH 匹配
    icp_global_registration_start = time.time()
    result_icp_global = o3d.pipelines.registration.registration_icp(
        source_down, target_down, voxel_size * 1.5, np.identity(4),
        o3d.pipelines.registration.TransformationEstimationPointToPlane(),
        o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=2000)
    )
    icp_global_registration_end = time.time()
    print(f"ICP global registration time: {icp_global_registration_end - icp_global_registration_start:.6f} seconds")

    # ICP 精细配准
    refine_registration_start = time.time()
    result_icp = refine_registration(source, target, voxel_size, result_icp_global)
    refine_registration_end = time.time()
    print(f"Refine registration time: {refine_registration_end - refine_registration_start:.6f} seconds")

    end_time = time.time()
    print(f"Total registration time: {end_time - start_time:.6f} seconds")

    return result_icp

def preprocess_point_cloud(pcd, voxel_size):
    """
    预处理点云，包括体素降采样和特征提取。

    参数:
    pcd (open3d.geometry.PointCloud): 输入的点云对象
    voxel_size (float): 用于降采样的体素大小

    返回:
    pcd_down (open3d.geometry.PointCloud): 降采样后的点云
    pcd_fpfh (open3d.pipelines.registration.Feature): 点云的FPFH特征
    """
    pcd_down = pcd.voxel_down_sample(voxel_size)
    pcd_down.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2.0, max_nn=30)
    )
    pcd_fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        pcd_down,
        o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 5.0, max_nn=100)
    )
    return pcd_down, pcd_fpfh


def execute_fast_global_registration(source_down, target_down, source_fpfh, target_fpfh, voxel_size):
    """
    执行快速全局配准（使用 FastGlobalRegistration 类实现）。

    参数:
    source_down (open3d.geometry.PointCloud): 降采样后的源点云
    target_down (open3d.geometry.PointCloud): 降采样后的目标点云
    source_fpfh (open3d.pipelines.registration.Feature): 源点云的FPFH特征
    target_fpfh (open3d.pipelines.registration.Feature): 目标点云的FPFH特征
    voxel_size (float): 体素大小，用于确定配准过程中的距离阈值

    返回:
    result (open3d.pipelines.registration.RegistrationResult): FGR配准结果，包含初步的变换矩阵。
    """
    distance_threshold = voxel_size * 0.5

    # 设置 FGR 的选项
    option = o3d.pipelines.registration.FastGlobalRegistrationOption()
    option.maximum_correspondence_distance = distance_threshold
    option.iteration_number = 64  # 您可以根据需要调整迭代次数

    # 创建 FGR 对象
    fgr = o3d.pipelines.registration.FastGlobalRegistration(source_fpfh, target_fpfh, option)

    # 执行配准
    result = fgr.compute(source_down, target_down)
    
    return result


def refine_registration(source, target, voxel_size, result_global):
    """
    使用ICP算法对初步配准结果进行精细配准。

    参数:
    source (open3d.geometry.PointCloud): 源点云
    target (open3d.geometry.PointCloud): 目标点云
    voxel_size (float): 体素大小，用于确定ICP算法中的距离阈值
    result_global (open3d.pipelines.registration.RegistrationResult): 初步全局配准结果

    返回:
    result (open3d.pipelines.registration.RegistrationResult): ICP精细配准结果，包含更准确的变换矩阵。
    """
    source.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2.0, max_nn=30)
    )
    target.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2.0, max_nn=30)
    )
    distance_threshold = voxel_size * 0.4
    result = o3d.pipelines.registration.registration_icp(
        source, target, distance_threshold, result_global.transformation,
        o3d.pipelines.registration.TransformationEstimationPointToPlane()
    )
    return result
