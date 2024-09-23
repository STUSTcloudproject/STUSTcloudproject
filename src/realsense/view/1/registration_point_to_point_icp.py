import open3d as o3d
import numpy as np
import time

def preprocess_point_cloud(pcd, voxel_size):
    """
    預處理點雲，包括體素降采樣和法線估計。
    
    :param pcd: 原始點雲
    :param voxel_size: 進行降采樣的體素大小
    :return: 降采樣後的點雲
    """
    pcd_down = pcd.voxel_down_sample(voxel_size)
    pcd_down.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2.0, max_nn=30)
    )
    return pcd_down

def point_to_point_icp(source, target, voxel_size=0.05, max_iteration=100):
    """
    使用 Point-to-Point ICP 配準源點雲和目標點雲。
    
    :param source: 源點雲
    :param target: 目標點雲
    :param voxel_size: 進行降采樣的體素大小
    :param max_iteration: ICP 的最大迭代次數
    :return: ICP 配準結果
    """
    print("Starting Point-to-Point ICP...")
    start_time = time.time()

    source_down = preprocess_point_cloud(source, voxel_size)
    target_down = preprocess_point_cloud(target, voxel_size)

    threshold = voxel_size * 1.5  # ICP 允許的最大對應點距離
    transformation = np.identity(4)

    reg_p2p = o3d.pipelines.registration.registration_icp(
        source_down, target_down, threshold, transformation,
        o3d.pipelines.registration.TransformationEstimationPointToPoint(),
        o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=max_iteration)
    )

    print(f"ICP result: {reg_p2p.transformation}")
    end_time = time.time()
    print(f"Point-to-Point ICP time: {end_time - start_time:.6f} seconds")

    return reg_p2p

if __name__ == "__main__":
    source = o3d.io.read_point_cloud("source.ply")
    target = o3d.io.read_point_cloud("target.ply")
    result = point_to_point_icp(source, target)
    o3d.visualization.draw_geometries([source.transform(result.transformation), target])
