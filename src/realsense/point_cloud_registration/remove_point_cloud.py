import open3d as o3d
import numpy as np

def create_bounding_box(min_bound, max_bound):
    """创建一个3D边界框。"""
    bounding_box = o3d.geometry.AxisAlignedBoundingBox(min_bound, max_bound)
    bounding_box.color = [1, 0, 0]  # 红色边界框
    return bounding_box

def update_bounding_box(bounding_box, translation):
    """更新边界框的位置。"""
    bounding_box.translate(translation, relative=True)

def resize_bounding_box(bounding_box, scale, axis):
    """调整边界框的大小。"""
    min_bound = np.asarray(bounding_box.get_min_bound())
    max_bound = np.asarray(bounding_box.get_max_bound())
    center = (min_bound + max_bound) / 2

    if axis == 'x':
        extent = (max_bound[0] - min_bound[0]) * scale
        min_bound[0] = center[0] - extent / 2
        max_bound[0] = center[0] + extent / 2
    elif axis == 'y':
        extent = (max_bound[1] - min_bound[1]) * scale
        min_bound[1] = center[1] - extent / 2
        max_bound[1] = center[1] + extent / 2
    elif axis == 'z':
        extent = (max_bound[2] - min_bound[2]) * scale
        min_bound[2] = center[2] - extent / 2
        max_bound[2] = center[2] + extent / 2

    bounding_box.min_bound = min_bound
    bounding_box.max_bound = max_bound
    bounding_box.color = [1, 0, 0]  # 保持颜色为红色
    return bounding_box

def remove_points_within_bounding_box(pcd, bounding_box):
    indices = bounding_box.get_point_indices_within_bounding_box(pcd.points)
    if len(indices) == 0:
        print("No points within the bounding box.")
        return
    mask = np.ones(len(pcd.points), dtype=bool)
    mask[indices] = False
    pcd.points = o3d.utility.Vector3dVector(np.asarray(pcd.points)[mask])
    if pcd.has_colors():
        pcd.colors = o3d.utility.Vector3dVector(np.asarray(pcd.colors)[mask])
    if pcd.has_normals():
        pcd.normals = o3d.utility.Vector3dVector(np.asarray(pcd.normals)[mask])

def keep_points_within_bounding_box(pcd, bounding_box):
    """只保留边界框内的点云。"""
    indices = bounding_box.get_point_indices_within_bounding_box(pcd.points)
    pcd.points = o3d.utility.Vector3dVector(np.asarray(pcd.points)[indices])
    if pcd.has_colors():
        pcd.colors = o3d.utility.Vector3dVector(np.asarray(pcd.colors)[indices])
    if pcd.has_normals():
        pcd.normals = o3d.utility.Vector3dVector(np.asarray(pcd.normals)[indices])

class UndoRedoManager:
    def __init__(self):
        self.undo_stack = []
        self.redo_stack = []

    def save_state(self, pcd):
        state = (np.asarray(pcd.points).copy(), np.asarray(pcd.colors).copy())
        self.undo_stack.append(state)
        self.redo_stack.clear()  # Clear redo stack whenever a new action is taken

    def undo(self, pcd):
        if self.undo_stack:
            state = self.undo_stack.pop()
            self.redo_stack.append((np.asarray(pcd.points).copy(), np.asarray(pcd.colors).copy()))
            self._restore_state(state, pcd)

    def redo(self, pcd):
        if self.redo_stack:
            state = self.redo_stack.pop()
            self.undo_stack.append((np.asarray(pcd.points).copy(), np.asarray(pcd.colors).copy()))
            self._restore_state(state, pcd)

    def _restore_state(self, state, pcd):
        points, colors = state
        pcd.points = o3d.utility.Vector3dVector(points)
        pcd.colors = o3d.utility.Vector3dVector(colors)

def main(point_cloud_file=None):
    global pcd, bounding_box, undo_redo_manager, vis

    if point_cloud_file is None:
        # 生成随机点云
        points = np.random.rand(1000, 3)
        colors = np.random.rand(1000, 3)
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        pcd.colors = o3d.utility.Vector3dVector(colors)
    else:
        pcd = o3d.io.read_point_cloud(point_cloud_file)

    # 初始化边界框
    min_bound = pcd.get_min_bound() - 0.1
    max_bound = pcd.get_max_bound() + 0.1
    bounding_box = create_bounding_box(min_bound, max_bound)

    undo_redo_manager = UndoRedoManager()
    undo_redo_manager.save_state(pcd)  # 保存初始状态

    # 创建可视化窗口
    vis = o3d.visualization.VisualizerWithKeyCallback()
    vis.create_window()

    # 添加几何体
    vis.add_geometry(pcd)
    vis.add_geometry(bounding_box)

    def update_geometry_and_view(vis):
        vis.update_geometry(pcd)
        vis.update_geometry(bounding_box)
        vis.poll_events()
        vis.update_renderer()

    def move_bounding_box_callback(vis, direction, axis):
        global bounding_box
        translation = np.zeros(3)
        translation[axis] = 0.1 * direction
        update_bounding_box(bounding_box, translation)
        update_geometry_and_view(vis)
        return False

    def resize_bounding_box_callback(vis, scale, axis):
        global bounding_box
        bounding_box = resize_bounding_box(bounding_box, scale, axis)
        update_geometry_and_view(vis)
        return False

    def remove_points_callback(vis):
        undo_redo_manager.save_state(pcd)
        remove_points_within_bounding_box(pcd, bounding_box)
        update_geometry_and_view(vis)
        return False

    def keep_points_callback(vis):
        undo_redo_manager.save_state(pcd)
        keep_points_within_bounding_box(pcd, bounding_box)
        update_geometry_and_view(vis)
        return False

    def undo_callback(vis):
        undo_redo_manager.undo(pcd)
        update_geometry_and_view(vis)
        return False

    def redo_callback(vis):
        undo_redo_manager.redo(pcd)
        update_geometry_and_view(vis)
        return False
    
    def reset_view(vis):
        # 移除当前的几何体
        vis.clear_geometries()
        
        # 重新计算边界框
        min_bound = pcd.get_min_bound() - 0.1
        max_bound = pcd.get_max_bound() + 0.1
        global bounding_box
        bounding_box = create_bounding_box(min_bound, max_bound)
        
        # 重新添加几何体
        vis.add_geometry(pcd)
        vis.add_geometry(bounding_box)
        
        # 重置视图
        vis.reset_view_point(True)
        update_geometry_and_view(vis)
        return False

    # 注册按键回调函数
    vis.register_key_callback(ord('A'), lambda vis: move_bounding_box_callback(vis, -1, 0))
    vis.register_key_callback(ord('D'), lambda vis: move_bounding_box_callback(vis, 1, 0))
    vis.register_key_callback(ord('W'), lambda vis: move_bounding_box_callback(vis, 1, 1))
    vis.register_key_callback(ord('S'), lambda vis: move_bounding_box_callback(vis, -1, 1))
    vis.register_key_callback(ord('Q'), lambda vis: move_bounding_box_callback(vis, 1, 2))
    vis.register_key_callback(ord('E'), lambda vis: move_bounding_box_callback(vis, -1, 2))

    vis.register_key_callback(ord('J'), lambda vis: resize_bounding_box_callback(vis, 0.9, 'x'))
    vis.register_key_callback(ord('L'), lambda vis: resize_bounding_box_callback(vis, 1.1, 'x'))
    vis.register_key_callback(ord('I'), lambda vis: resize_bounding_box_callback(vis, 1.1, 'y'))
    vis.register_key_callback(ord('K'), lambda vis: resize_bounding_box_callback(vis, 0.9, 'y'))
    vis.register_key_callback(ord('U'), lambda vis: resize_bounding_box_callback(vis, 1.1, 'z'))
    vis.register_key_callback(ord('O'), lambda vis: resize_bounding_box_callback(vis, 0.9, 'z'))

    vis.register_key_callback(ord('R'), remove_points_callback)
    vis.register_key_callback(ord('P'), keep_points_callback)

    vis.register_key_callback(ord('Z'), undo_callback)
    vis.register_key_callback(ord('Y'), redo_callback)

    vis.register_key_callback(ord('V'), reset_view)

    print("按键说明：")
    print("A/D: 左右移动边界框")
    print("W/S: 前后移动边界框")
    print("Q/E: 上下移动边界框")
    print("J/L: 缩小/放大边界框X轴")
    print("I/K: 放大/缩小边界框Y轴")
    print("U/O: 放大/缩小边界框Z轴")
    print("R: 移除边界框内的点")
    print("P: 保留边界框内的点")
    print("V: 重置视图")
    print("Z: 撤销")
    print("Y: 重做")
    

    # 运行可视化
    vis.run()
    vis.destroy_window()

if __name__ == "__main__":
    import sys  
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main("bun000.ply")
