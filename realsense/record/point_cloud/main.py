import open3d as o3d
import numpy as np

def load_point_clouds(voxel_size=0.0):
    pcds = []
    for i in range(5):  # 假設有5個點雲文件
        pcd = o3d.io.read_point_cloud(f"E:\\MVC_gui\\realsense\\record\\point_cloud\\point_cloud_{i}.ply")
        pcd_down = pcd.voxel_down_sample(voxel_size)
        pcd_down.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2, max_nn=30))
        pcds.append(pcd_down)
    return pcds

def pairwise_registration(source, target, voxel_size):
    print("Apply point-to-plane ICP")
    icp_coarse = o3d.pipelines.registration.registration_icp(
        source, target, voxel_size * 15, np.identity(4),
        o3d.pipelines.registration.TransformationEstimationPointToPlane())
    icp_fine = o3d.pipelines.registration.registration_icp(
        source, target, voxel_size * 1.5, icp_coarse.transformation,
        o3d.pipelines.registration.TransformationEstimationPointToPlane())
    transformation_icp = icp_fine.transformation
    information_icp = o3d.pipelines.registration.get_information_matrix_from_point_clouds(
        source, target, voxel_size * 1.5, icp_fine.transformation)
    return transformation_icp, information_icp

def full_registration(pcds, voxel_size):
    pose_graph = o3d.pipelines.registration.PoseGraph()
    odometry = np.identity(4)
    pose_graph.nodes.append(o3d.pipelines.registration.PoseGraphNode(odometry))

    for source_id in range(len(pcds)):
        for target_id in range(source_id + 1, len(pcds)):
            transformation_icp, information_icp = pairwise_registration(pcds[source_id], pcds[target_id], voxel_size)
            if target_id == source_id + 1:  # odometry case
                odometry = np.dot(transformation_icp, odometry)
                pose_graph.nodes.append(o3d.pipelines.registration.PoseGraphNode(np.linalg.inv(odometry)))
                pose_graph.edges.append(o3d.pipelines.registration.PoseGraphEdge(source_id, target_id, transformation_icp, information_icp, uncertain=False))
            else:  # loop closure case
                pose_graph.edges.append(o3d.pipelines.registration.PoseGraphEdge(source_id, target_id, transformation_icp, information_icp, uncertain=True))
    return pose_graph

def run():
    voxel_size = 0.02  # voxel size for downsampling
    pcds_down = load_point_clouds(voxel_size)
    
    print("Full registration ...")
    pose_graph = full_registration(pcds_down, voxel_size)
    
    print("Optimizing PoseGraph ...")
    option = o3d.pipelines.registration.GlobalOptimizationOption(
        max_correspondence_distance=voxel_size * 1.5,
        edge_prune_threshold=0.25,
        preference_loop_closure=1.0,
        reference_node=0)
    o3d.pipelines.registration.global_optimization(
        pose_graph,
        o3d.pipelines.registration.GlobalOptimizationLevenbergMarquardt(),
        o3d.pipelines.registration.GlobalOptimizationConvergenceCriteria(),
        option)

    print("Transform points and display")
    for point_id in range(len(pcds_down)):
        print(pose_graph.nodes[point_id].pose)
        pcds_down[point_id].transform(pose_graph.nodes[point_id].pose)
    o3d.visualization.draw_geometries(pcds_down)

    print("Make a combined point cloud")
    pcd_combined = o3d.geometry.PointCloud()
    for point_id in range(len(pcds_down)):
        pcd_combined += pcds_down[point_id]
    pcd_combined_down = pcd_combined.voxel_down_sample(voxel_size)
    o3d.io.write_point_cloud("multiway_registration.ply", pcd_combined_down)
    
    # Surface reconstruction
    print("Surface reconstruction ...")
    pcd_combined.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))
    poisson_mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd_combined, depth=9)[0]
    bbox = pcd_combined.get_axis_aligned_bounding_box()
    p_mesh_crop = poisson_mesh.crop(bbox)
    o3d.visualization.draw_geometries([p_mesh_crop])

if __name__ == "__main__":
    run()
