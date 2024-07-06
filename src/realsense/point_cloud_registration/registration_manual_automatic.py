import open3d as o3d
import numpy as np
import copy
import threading
import queue

def filter_outliers(pcd, nb_neighbors=20, std_ratio=2.0):
    cl, ind = pcd.remove_statistical_outlier(nb_neighbors=nb_neighbors, std_ratio=std_ratio)
    pcd_filtered = pcd.select_by_index(ind)
    return pcd_filtered

def preprocess_point_cloud(pcd, voxel_size):
    pcd_down = pcd.voxel_down_sample(voxel_size)
    pcd_down.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2.0,
                                             max_nn=30))
    pcd_fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        pcd_down,
        o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 5.0,
                                             max_nn=100))
    return pcd_down, pcd_fpfh

def execute_global_registration(source_down, target_down, source_fpfh, target_fpfh, voxel_size):
    distance_threshold = voxel_size * 1.5
    result = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
        source_down, target_down, source_fpfh, target_fpfh, True,
        distance_threshold,
        o3d.pipelines.registration.TransformationEstimationPointToPoint(False),
        4, [
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnEdgeLength(0.9),
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(distance_threshold)
        ], o3d.pipelines.registration.RANSACConvergenceCriteria(4000000, 500))
    return result

def refine_registration(source, target, voxel_size, result_ransac):
    source.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2.0, max_nn=30))
    target.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2.0, max_nn=30))
    distance_threshold = voxel_size * 0.4
    result = o3d.pipelines.registration.registration_icp(
        source, target, distance_threshold, result_ransac.transformation,
        o3d.pipelines.registration.TransformationEstimationPointToPlane())
    return result

def draw_registration_result(source, target, transformation=np.eye(4), source_color=[0, 0, 1], target_color=[0.5, 0.5, 0.5]):
    source_temp = copy.deepcopy(source)
    target_temp = copy.deepcopy(target)
    source_temp.paint_uniform_color(source_color)
    target_temp.paint_uniform_color(target_color)
    source_temp.transform(transformation)
    o3d.visualization.draw_geometries([source_temp, target_temp])

def register_on_key(vis, point_clouds, current_target_idx, current_source_idx, voxel_size, update_queue, is_processing, undo_stack, redo_stack):
    if is_processing[0]:
        print("Registration is already in progress.")
        return

    def run_registration():
        is_processing[0] = True
        source = point_clouds[current_source_idx[0]]
        target = point_clouds[current_target_idx[0]]
        source_down, source_fpfh = preprocess_point_cloud(source, voxel_size)
        target_down, target_fpfh = preprocess_point_cloud(target, voxel_size)

        print(f"Applying global registration for point cloud ")
        result_ransac = execute_global_registration(source_down, target_down, source_fpfh, target_fpfh, voxel_size)
        print("Global registration result:")
        print(result_ransac)

        print("Applying local refinement")
        result_icp = refine_registration(source, target, voxel_size, result_ransac)
        print("Refinement result:")
        print(result_icp)

        # 将当前状态推入撤销堆栈，并清空重做堆栈
        undo_stack.append(copy.deepcopy(source))
        redo_stack.clear()

        # 更新source点云
        source.transform(result_icp.transformation)
        
        # 将更新信息放入队列
        update_queue.put(source)
        is_processing[0] = False

    threading.Thread(target=run_registration).start()

def translate_point_cloud(pcd, translation, vis, is_processing, undo_stack, redo_stack):
    if is_processing[0]:
        print("Operation not allowed during registration.")
        return
    is_processing[0] = True

    # 将当前状态推入撤销堆栈，并清空重做堆栈
    undo_stack.append(copy.deepcopy(pcd))
    redo_stack.clear()

    pcd.translate(translation)
    vis.update_geometry(pcd)
    vis.poll_events()
    vis.update_renderer()
    is_processing[0] = False

def rotate_point_cloud(pcd, rotation, vis, is_processing, undo_stack, redo_stack, center=True):
    if is_processing[0]:
        print("Operation not allowed during registration.")
        return
    is_processing[0] = True

    # 将当前状态推入撤销堆栈，并清空重做堆栈
    undo_stack.append(copy.deepcopy(pcd))
    redo_stack.clear()

    R = pcd.get_rotation_matrix_from_xyz(rotation)
    if center:
        pcd.rotate(R, center=pcd.get_center())
    else:
        pcd.rotate(R)
    vis.update_geometry(pcd)
    vis.poll_events()
    vis.update_renderer()
    is_processing[0] = False

def undo_last_action(vis, point_clouds, current_source_idx, current_target_idx, is_processing, undo_stack, redo_stack):
    if is_processing[0]:
        print("Operation not allowed during registration.")
        return
    if not undo_stack:
        print("No actions to undo.")
        return
    is_processing[0] = True

    # 从撤销堆栈中弹出最后一个状态并推入重做堆栈
    last_state = undo_stack.pop()
    redo_stack.append(copy.deepcopy(point_clouds[current_source_idx[0]]))
    point_clouds[current_source_idx[0]] = last_state

    vis.clear_geometries()
    vis.add_geometry(point_clouds[current_source_idx[0]])
    vis.add_geometry(point_clouds[current_target_idx[0]])
    vis.poll_events()
    vis.update_renderer()
    is_processing[0] = False
    print("Undid last action.")

def redo_last_action(vis, point_clouds, current_source_idx, current_target_idx, is_processing, undo_stack, redo_stack):
    if is_processing[0]:
        print("Operation not allowed during registration.")
        return
    if not redo_stack:
        print("No actions to redo.")
        return
    is_processing[0] = True

    # 从重做堆栈中弹出最后一个状态并推入撤销堆栈
    last_state = redo_stack.pop()
    undo_stack.append(copy.deepcopy(point_clouds[current_source_idx[0]]))
    point_clouds[current_source_idx[0]] = last_state

    vis.clear_geometries()
    vis.add_geometry(point_clouds[current_source_idx[0]])
    vis.add_geometry(point_clouds[current_target_idx[0]])
    vis.poll_events()
    vis.update_renderer()
    is_processing[0] = False
    print("Redid last action.")

def switch_source(vis, point_clouds, current_target_idx, current_source_idx, is_processing, undo_stack, redo_stack):
    if is_processing[0]:
        print("Operation not allowed during registration.")
        return
    is_processing[0] = True
    # 清空撤销和重做堆栈
    undo_stack.clear()
    redo_stack.clear()
    # 切換到下一個 source
    current_source_idx[0] = (current_source_idx[0] + 1) % len(point_clouds)
    if current_source_idx[0] == current_target_idx[0]:
        current_source_idx[0] = (current_source_idx[0] + 1) % len(point_clouds)
    new_source = point_clouds[current_source_idx[0]]
    target = point_clouds[current_target_idx[0]]
    vis.clear_geometries()
    vis.add_geometry(new_source)
    vis.add_geometry(target)
    vis.poll_events()
    vis.update_renderer()
    is_processing[0] = False
    print(f"Switched to source {current_source_idx[0]}")

def switch_target(vis, point_clouds, current_target_idx, current_source_idx, is_processing, undo_stack, redo_stack):
    if is_processing[0]:
        print("Operation not allowed during registration.")
        return
    is_processing[0] = True
    # 清空撤销和重做堆栈
    undo_stack.clear()
    redo_stack.clear()
    # 切換基底
    current_target_idx[0], current_source_idx[0] = current_source_idx[0], current_target_idx[0]
    new_source = point_clouds[current_source_idx[0]]
    new_target = point_clouds[current_target_idx[0]]

    # 更新颜色
    new_source.paint_uniform_color([0, 0, 1])  # 蓝色
    new_target.paint_uniform_color([0.5, 0.5, 0.5])  # 灰色

    vis.clear_geometries()
    vis.add_geometry(new_source)
    vis.add_geometry(new_target)
    vis.poll_events()
    vis.update_renderer()
    is_processing[0] = False
    print(f"Switched targetto {current_target_idx[0]} and source to {current_source_idx[0]}")

def merge_point_clouds(vis, point_clouds, is_processing, save=False):
    if is_processing[0]:
        print("Operation not allowed during registration.")
        return
    is_processing[0] = True

    merged_pcd = o3d.geometry.PointCloud()
    for pcd in point_clouds:
        merged_pcd += pcd

    if save:
        o3d.io.write_point_cloud("merged_point_cloud.ply", merged_pcd)
        print("Merged point cloud saved as 'merged_point_cloud.ply'.")

    vis.clear_geometries()
    vis.add_geometry(merged_pcd)
    vis.poll_events()
    vis.update_renderer()
    is_processing[0] = False
    print("Merged all point clouds into one.")

def save_merged_point_cloud(vis, point_clouds, is_processing):
    merge_point_clouds(vis, point_clouds, is_processing, save=True)

def main():
    voxel_size = 0.05  # 可以根据你的数据调整体素大小

    # 使用用户指定的点云文件路径
    file_paths = [
        "pc1.ply",
        "pc2.ply",
        "pc3.ply",
        #"bun000.ply",
        #"bun045.ply",
        #"bun090.ply",
        #"bun180.ply",
        #"bun270.ply",
        #"bun315.ply",
        #"top2.ply",
    ]

    point_clouds = []
    for file_path in file_paths:
        pcd = o3d.io.read_point_cloud(file_path)
        if not pcd.has_points():
            print(f"Failed to load point cloud from {file_path}. Exiting.")
            return
        point_clouds.append(pcd)

    # 使用统计滤波删除离群点
    point_clouds = [filter_outliers(pcd, nb_neighbors=20, std_ratio=2.0) for pcd in point_clouds]

    # 设置点云颜色
    for i, pcd in enumerate(point_clouds):
        if i == 0:  # 设置第一个点云为灰色（基底）
            pcd.paint_uniform_color([0.5, 0.5, 0.5])
        else:  # 设置其他点云为蓝色（源）
            pcd.paint_uniform_color([0, 0, 1])

    # 创建可视化窗口
    vis = o3d.visualization.VisualizerWithKeyCallback()
    vis.create_window()
    vis.add_geometry(point_clouds[0])
    vis.add_geometry(point_clouds[1])

    # 创建队列用于线程间通信
    update_queue = queue.Queue()

    # 创建标志跟踪配准状态
    is_processing = [False]
    current_target_idx = [0]
    current_source_idx = [1]

    # 撤销和重做堆栈
    undo_stack = []
    redo_stack = []

    # 注册键盘事件
    translation_step = 0.0004  # 手动控制的平移步长，调小精度提高
    rotation_step = 0.002  # 手动控制的旋转步长，保持不变

    vis.register_key_callback(ord("R"), lambda vis: register_on_key(vis, point_clouds, current_target_idx, current_source_idx, voxel_size, update_queue, is_processing, undo_stack, redo_stack))
    vis.register_key_callback(ord("W"), lambda vis: translate_point_cloud(point_clouds[current_source_idx[0]], [0, translation_step, 0], vis, is_processing, undo_stack, redo_stack))
    vis.register_key_callback(ord("S"), lambda vis: translate_point_cloud(point_clouds[current_source_idx[0]], [0, -translation_step, 0], vis, is_processing, undo_stack, redo_stack))
    vis.register_key_callback(ord("A"), lambda vis: translate_point_cloud(point_clouds[current_source_idx[0]], [-translation_step, 0, 0], vis, is_processing, undo_stack, redo_stack))
    vis.register_key_callback(ord("D"), lambda vis: translate_point_cloud(point_clouds[current_source_idx[0]], [translation_step, 0, 0], vis, is_processing, undo_stack, redo_stack))
    vis.register_key_callback(ord("Q"), lambda vis: translate_point_cloud(point_clouds[current_source_idx[0]], [0, 0, translation_step], vis, is_processing, undo_stack, redo_stack))
    vis.register_key_callback(ord("E"), lambda vis: translate_point_cloud(point_clouds[current_source_idx[0]], [0, 0, -translation_step], vis, is_processing, undo_stack, redo_stack))
    vis.register_key_callback(ord("I"), lambda vis: rotate_point_cloud(point_clouds[current_source_idx[0]], [rotation_step, 0, 0], vis, is_processing, undo_stack, redo_stack))
    vis.register_key_callback(ord("K"), lambda vis: rotate_point_cloud(point_clouds[current_source_idx[0]], [-rotation_step, 0, 0], vis, is_processing, undo_stack, redo_stack))
    vis.register_key_callback(ord("J"), lambda vis: rotate_point_cloud(point_clouds[current_source_idx[0]], [0, rotation_step, 0], vis, is_processing, undo_stack, redo_stack))
    vis.register_key_callback(ord("L"), lambda vis: rotate_point_cloud(point_clouds[current_source_idx[0]], [0, -rotation_step, 0], vis, is_processing, undo_stack, redo_stack))
    vis.register_key_callback(ord("U"), lambda vis: rotate_point_cloud(point_clouds[current_source_idx[0]], [0, 0, rotation_step], vis, is_processing, undo_stack, redo_stack))
    vis.register_key_callback(ord("O"), lambda vis: rotate_point_cloud(point_clouds[current_source_idx[0]], [0, 0, -rotation_step], vis, is_processing, undo_stack, redo_stack))
    vis.register_key_callback(ord("N"), lambda vis: switch_source(vis, point_clouds, current_target_idx, current_source_idx, is_processing, undo_stack, redo_stack))
    vis.register_key_callback(ord("B"), lambda vis: switch_target(vis, point_clouds, current_target_idx, current_source_idx, is_processing, undo_stack, redo_stack))
    vis.register_key_callback(ord("Z"), lambda vis: undo_last_action(vis, point_clouds, current_source_idx, current_target_idx, is_processing, undo_stack, redo_stack))
    vis.register_key_callback(ord("Y"), lambda vis: redo_last_action(vis, point_clouds, current_source_idx, current_target_idx, is_processing, undo_stack, redo_stack))
    vis.register_key_callback(ord("M"), lambda vis: merge_point_clouds(vis, point_clouds, is_processing))
    vis.register_key_callback(ord("P"), lambda vis: save_merged_point_cloud(vis, point_clouds, is_processing))

    def update_visualization(vis):
        while not update_queue.empty():
            updated_source = update_queue.get()
            vis.update_geometry(updated_source)
            vis.update_geometry(point_clouds[current_target_idx[0]])
            vis.poll_events()
            vis.update_renderer()
        return False

    vis.register_animation_callback(update_visualization)

    print("Press 'R' to start the registration process.")
    print("Press 'N' to switch to the next source point cloud.")
    print("Press 'B' to switch the target (base) point cloud.")
    print("Press 'Z' to undo the last action.")
    print("Press 'Y' to redo the last action.")
    print("Press 'M' to merge all point clouds.")
    print("Press 'P' to save the merged point cloud.")
    print("Use W, A, S, D, Q, E to translate the source point cloud.")
    print("Use I, J, K, L, U, O to rotate the source point cloud.")
    vis.run()
    vis.destroy_window()

if __name__ == "__main__":
    main()

