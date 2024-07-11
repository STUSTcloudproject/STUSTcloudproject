import open3d as o3d
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering
from open3d.visualization.gui import SceneWidget
import numpy as np
import platform
import threading
import queue
import copy

isMacOS = (platform.system() == "Darwin")

def erase_points_process(x, y, radius, points, colors, view_matrix, proj_matrix, frame_width, frame_height, result_queue):
    screen_points = np.zeros((points.shape[0], 2))

    for i, point in enumerate(points):
        screen_points[i] = world_to_screen(point, view_matrix, proj_matrix, frame_width, frame_height)

    distances = np.linalg.norm(screen_points - np.array([x, y]), axis=1)
    mask = distances > radius
    new_points = points[mask]
    new_colors = colors[mask] if colors.size else colors

    result_queue.put((new_points, new_colors))

def world_to_screen(point, view_matrix, proj_matrix, frame_width, frame_height):
    point_h = np.array([point[0], point[1], point[2], 1.0])

    ndc_point = proj_matrix @ (view_matrix @ point_h)
    if ndc_point[3] != 0:
        ndc_point /= ndc_point[3]

    screen_x = ((ndc_point[0] + 1) / 2.0) * frame_width
    screen_y = ((1 - ndc_point[1]) / 2.0) * frame_height

    # 微调 Y 坐标，增加一个偏移量来对齐
    offset_y = 30  # 将这个值设置为负数，以向上移动
    screen_y += offset_y

    return np.array([screen_x, screen_y])

class AppWindow:
    MENU_OPEN = 1
    MENU_QUIT = 3
    MENU_SHOW_SETTINGS = 11
    MENU_SHOW_POINT_CLOUD_CONTROLS = 12
    MENU_ABOUT = 21

    def __init__(self, width, height):
        self.window = gui.Application.instance.create_window("Open3D", width, height)
        self._scene = gui.SceneWidget()
        self._scene.scene = rendering.Open3DScene(self.window.renderer)
        self._scene.scene.set_background([1, 1, 1, 1])
        self.window.add_child(self._scene)

        self.material = rendering.MaterialRecord()
        self.material.shader = "defaultUnlit"
        self.material.base_color = [1, 1, 1, 1]  # 设置为白色，避免覆盖点云颜色
        self.material.point_size = 5.0

        self.point_cloud_loaded = False

        self.length = 0

        self.is_erasing = False
        self.erase_radius = 10
        self.erase_mode = False
        self.bounding_box_mode = False
        self.bounding_box = None
        self.original_colors = None
        self.translation_step_bbox = 10.0  # 邊界框平移步長
        self.translation_step_pc = 10.0  # 點雲平移步長
        self.rotation_step_pc = 10.0  # 點雲旋轉步長
        self.resize_step_bbox = 10.0  # 邊界框缩放步長
        self.refresh_view_on_mode_change = True  # 切换模式时刷新视角

        self.last_mouse_pos = [0, 0]

        self.undo_stack = []
        self.redo_stack = []

        self._setup_menu_bar()
        self._setup_settings_panel()

        self.window.set_on_layout(self._on_layout)
        self._scene.set_on_mouse(self._on_mouse_event)
        self.window.set_on_key(self._on_key_event)

        self.view_ctrls.visible = True
        self.point_cloud_ctrls.visible = True
        self._settings_panel.visible = True
        gui.Application.instance.menubar.set_checked(AppWindow.MENU_SHOW_SETTINGS, self.view_ctrls.visible)

        self.generate_random_point_cloud()
        self.erase_queue = queue.Queue()

        self.eraser_thread = None
        self.erase_lock = threading.Lock()

    def _setup_menu_bar(self):
        if gui.Application.instance.menubar is None:
            if isMacOS:
                app_menu = gui.Menu()
                app_menu.add_item("About", AppWindow.MENU_ABOUT)
                app_menu.add_separator()
                app_menu.add_item("Quit", AppWindow.MENU_QUIT)
            file_menu = gui.Menu()
            file_menu.add_item("Open...", AppWindow.MENU_OPEN)
            if not isMacOS:
                file_menu.add_separator()
                file_menu.add_item("Quit", AppWindow.MENU_QUIT)
            settings_menu = gui.Menu()
            settings_menu.add_item("View Controls", AppWindow.MENU_SHOW_SETTINGS)
            settings_menu.add_item("Point Cloud Controls", AppWindow.MENU_SHOW_POINT_CLOUD_CONTROLS)
            help_menu = gui.Menu()
            help_menu.add_item("About", AppWindow.MENU_ABOUT)

            menu = gui.Menu()
            if isMacOS:
                menu.add_menu("Example", app_menu)
                menu.add_menu("File", file_menu)
                menu.add_menu("Settings", settings_menu)
            else:
                menu.add_menu("File", file_menu)
                menu.add_menu("Settings", settings_menu)
                menu.add_menu("Help", help_menu)
            gui.Application.instance.menubar = menu

        self.window.set_on_menu_item_activated(AppWindow.MENU_OPEN, self._on_menu_open)
        self.window.set_on_menu_item_activated(AppWindow.MENU_QUIT, self._on_menu_quit)
        self.window.set_on_menu_item_activated(AppWindow.MENU_SHOW_SETTINGS, self._on_menu_toggle_view_controls)
        self.window.set_on_menu_item_activated(AppWindow.MENU_SHOW_POINT_CLOUD_CONTROLS, self._on_menu_toggle_point_cloud_controls)
        self.window.set_on_menu_item_activated(AppWindow.MENU_ABOUT, self._on_menu_about)

        gui.Application.instance.menubar.set_checked(AppWindow.MENU_SHOW_SETTINGS, True)
        gui.Application.instance.menubar.set_checked(AppWindow.MENU_SHOW_POINT_CLOUD_CONTROLS, True)

    def _setup_settings_panel(self):
        em = self.window.theme.font_size

        self._settings_panel = gui.Vert(0, gui.Margins(0.25 * em, 0.25 * em, 0.25 * em, 0.25 * em))

        self.view_ctrls = gui.CollapsableVert("View controls", 0.25 * em, gui.Margins(em, 0, 0, 0))
        self._setup_view_controls()
        self._settings_panel.add_child(self.view_ctrls)
        
        self.point_cloud_ctrls = gui.CollapsableVert("Point Cloud Controls", 0.25 * em, gui.Margins(em, 0, 0, 0))
        self._setup_point_cloud_controls()
        self._settings_panel.add_child(self.point_cloud_ctrls)

        self.window.add_child(self._settings_panel)

    def _setup_view_controls(self):
        em = self.window.theme.font_size
        grid1 = gui.VGrid(2, 0.25 * em)
        
        grid1.add_child(gui.Label("BG Color"))
        self._bg_color = gui.ColorEdit()
        self._bg_color.color_value = gui.Color(1, 1, 1)
        self._bg_color.set_on_value_changed(self._on_bg_color_changed)
        grid1.add_child(self._bg_color)
        
        grid2 = gui.VGrid(2, 0.25 * em)
        grid2.add_child(gui.Label("Refresh view on mode change"))
        self._refresh_view_checkbox = gui.Checkbox("")
        self._refresh_view_checkbox.checked = True
        self._refresh_view_checkbox.set_on_checked(self._on_refresh_view_checked)
        grid2.add_child(self._refresh_view_checkbox)

        grid3 = gui.VGrid(2, 0.25 * em)
        self._button = gui.Button("Refresh view ( V )")
        self._button.set_on_clicked(self._refresh_view)
        grid2.add_child(self._button)

        self.view_ctrls.add_child(grid1)
        self.view_ctrls.add_child(grid2)
        self.view_ctrls.add_child(grid3)

    def _refresh_view(self):
        self._scene.setup_camera(60.0, self.point_cloud.get_axis_aligned_bounding_box(), self.point_cloud.get_center())

    def _on_refresh_view_checked(self, is_checked):
        self.refresh_view_on_mode_change = is_checked

    def _setup_point_cloud_controls(self):
        em = self.window.theme.font_size
        vert = gui.Vert(0.25 * em)  # 使用 gui.Vert 代替 gui.VGrid

        self._erase_mode_checkbox = gui.Checkbox("Eraser mode ( F )")
        self._erase_mode_checkbox.set_on_checked(
            lambda is_checked: self._on_mode_changed("erase", is_checked)
        )
        vert.add_child(self._erase_mode_checkbox)

        # Create Bounding Box mode checkbox
        self._bounding_box_mode_checkbox = gui.Checkbox("Bounding Box Mode ( G )")
        self._bounding_box_mode_checkbox.set_on_checked(
            lambda is_checked: self._on_mode_changed("bounding_box", is_checked)
        )
        vert.add_child(self._bounding_box_mode_checkbox)

        
        # Add translation step label and slider vertically
        self._translation_step_hbox = gui.Horiz(0.25 * em)
        self._translation_step_hbox.add_child(gui.Label("Translation step"))
        self._translation_step_slider = gui.Slider(gui.Slider.DOUBLE)
        self._translation_step_slider.set_limits(1, 100.0)
        self._translation_step_slider.double_value = self.translation_step_pc
        self._translation_step_slider.set_on_value_changed(self._on_translation_step_pc_changed)
        self._translation_step_hbox.add_child(self._translation_step_slider)
        self._translation_step_hbox.visible = True
        vert.add_child(self._translation_step_hbox)

        # Add rotation step label and slider vertically
        self._rotation_step_hbox = gui.Horiz(0.25 * em)
        self._rotation_step_hbox.add_child(gui.Label("Rotation step"))
        self._rotation_step_slider = gui.Slider(gui.Slider.DOUBLE)
        self._rotation_step_slider.set_limits(1, 100.0)  # 设置旋转步长范围
        self._rotation_step_slider.double_value = self.rotation_step_pc
        self._rotation_step_slider.set_on_value_changed(self._on_rotation_step_pc_changed)
        self._rotation_step_hbox.add_child(self._rotation_step_slider)
        self._rotation_step_hbox.visible = True
        vert.add_child(self._rotation_step_hbox)

        # Add Eraser size label and slider horizontally
        self._hbox = gui.Horiz(0.25 * em)
        self._hbox.add_child(gui.Label("Eraser size"))
        self._erase_size_slider = gui.Slider(gui.Slider.DOUBLE)
        self._erase_size_slider.set_limits(5, 50)
        self._erase_size_slider.double_value = self.erase_radius
        self._erase_size_slider.set_on_value_changed(self._on_erase_size_changed)
        self._hbox.add_child(self._erase_size_slider)

        self._hbox.visible = False  # 默认隐藏
        vert.add_child(self._hbox)

        # Add translation step label and slider horizontally
        self._translation_hbox = gui.Horiz(0.25 * em)
        self._translation_hbox.add_child(gui.Label("Translation step"))
        self._translation_step_bbox_slider = gui.Slider(gui.Slider.DOUBLE)
        self._translation_step_bbox_slider.set_limits(1, 100.0)
        self._translation_step_bbox_slider.double_value = self.translation_step_bbox
        self._translation_step_bbox_slider.set_on_value_changed(self._on_translation_step_bbox_changed)
        self._translation_hbox.add_child(self._translation_step_bbox_slider)

        self._translation_hbox.visible = False  # 默认隐藏
        vert.add_child(self._translation_hbox)

        # Add resize step label and slider horizontally
        self._resize_hbox = gui.Horiz(0.25 * em)
        self._resize_hbox.add_child(gui.Label("Resize step"))
        self._resize_step_bbox_slider = gui.Slider(gui.Slider.DOUBLE)
        self._resize_step_bbox_slider.set_limits(1, 100.0)
        self._resize_step_bbox_slider.double_value = self.resize_step_bbox
        self._resize_step_bbox_slider.set_on_value_changed(self._on_resize_step_bbox_changed)
        self._resize_hbox.add_child(self._resize_step_bbox_slider)

        self._resize_hbox.visible = False  # 默认隐藏
        vert.add_child(self._resize_hbox)
        
        self.point_cloud_ctrls.add_child(vert)

    def _on_translation_step_pc_changed(self, value):
        self.translation_step_pc = value
        print(f"Point cloud translation step set to {self.translation_step_pc}")

    def _on_rotation_step_pc_changed(self, value):
        self.rotation_step_pc = value
        print(f"Point cloud rotation step set to {self.rotation_step_pc}")

    def _on_translation_step_bbox_changed(self, value):
        self.translation_step_bbox = value
        print(f"Bounding box translation step set to {self.translation_step_bbox}")

    def _on_resize_step_bbox_changed(self, value):
        self.resize_step_bbox = value
        print(f"Bounding box resize step set to {self.resize_step_bbox}")

    def _on_mode_changed(self, mode, is_checked):
        if mode == "erase":
            self._erase_mode_checkbox.checked = is_checked
            self.erase_mode = is_checked
            self._toggle_erase_mode(is_checked)
        elif mode == "bounding_box":
            self._bounding_box_mode_checkbox.checked = is_checked
            self.bounding_box_mode = is_checked
            self._toggle_bounding_box_mode(is_checked)
            
        # Force layout update
        self.window.set_needs_layout()

        if not self.erase_mode and not self.bounding_box_mode:
            self._translation_step_hbox.visible = True
            self._rotation_step_hbox.visible = True
        else:
            self._translation_step_hbox.visible = False
            self._rotation_step_hbox.visible = False

        if self.refresh_view_on_mode_change and is_checked and self.point_cloud_loaded:
            self._scene.setup_camera(60.0, self.point_cloud.get_axis_aligned_bounding_box(), self.point_cloud.get_center())

        print(f"Eraser mode set to {self.erase_mode}")
        print(f"Bounding Box Mode set to {self.bounding_box_mode}")

    def _toggle_erase_mode(self, is_checked):
        self.erase_mode = is_checked
        if is_checked:
            self.bounding_box_mode = False
            self._bounding_box_mode_checkbox.checked = False
            self._scene.set_view_controls(gui.SceneWidget.Controls.PICK_POINTS)
            self._hbox.visible = True  # 显示 Eraser size
            self._translation_hbox.visible = False  # 确保隐藏 Translation step
            self._resize_hbox.visible = False  # 确保隐藏 Resize step
            self._hide_bounding_box()  # 确保隐藏边界框
            self._restore_original_colors()
        else:
            self._scene.set_view_controls(gui.SceneWidget.Controls.ROTATE_CAMERA)
            self._hbox.visible = False  # 隐藏 Eraser size

    def _toggle_bounding_box_mode(self, is_checked):
        self.bounding_box_mode = is_checked
        if is_checked:
            self.erase_mode = False
            self._erase_mode_checkbox.checked = False
            self._scene.set_view_controls(gui.SceneWidget.Controls.ROTATE_CAMERA)  # Adjust as needed
            self._hbox.visible = False  # 隐藏 Eraser size
            self._translation_hbox.visible = True  # 显示 Translation step
            self._resize_hbox.visible = True  # 显示 Resize step
            self._show_bounding_box()
        else:
            self._scene.set_view_controls(gui.SceneWidget.Controls.ROTATE_CAMERA)
            self._translation_hbox.visible = False  # 隐藏 Translation step
            self._resize_hbox.visible = False  # 隐藏 Resize step
            self._hide_bounding_box()  # 确保隐藏边界框
            self._restore_original_colors()

    def _restore_original_colors(self):
        if not self.point_cloud_loaded or self.original_colors is None:
            return
        
        # 恢复所有点的原始颜色
        self.point_cloud.colors = o3d.utility.Vector3dVector(self.original_colors)

        # 重新添加点云以更新颜色
        self._scene.scene.remove_geometry("PointCloud")
        self._scene.scene.add_geometry("PointCloud", self.point_cloud, self.material)
        self._scene.force_redraw()
        self.original_colors = None

        print("Restored original colors")

    def _on_erase_size_changed(self, value):
        self.erase_radius = value
        print(f"Eraser size set to {self.erase_radius}")

    def _show_bounding_box(self):
        if not self.point_cloud_loaded or len(self.point_cloud.points) == 0:
            self._show_warning_dialog("No points available to create a bounding box.")
            return

        bounds = self.point_cloud.get_axis_aligned_bounding_box()
        self.bounding_box = bounds
        self.bounding_box.color = [1, 0, 0]

        # 设置材料属性
        material = rendering.MaterialRecord()
        material.shader = "unlitLine"
        material.line_width = 2.0
        material.base_color = [1, 0, 0, 1]  # 设置基础颜色

        # 确保添加到场景的几何体具有所有必要的属性
        if self._scene.scene.has_geometry("BoundingBox"):
            self._scene.scene.remove_geometry("BoundingBox")
        self._scene.scene.add_geometry("BoundingBox", self.bounding_box, material)
        self._scene.force_redraw()

    def _hide_bounding_box(self):
        if self.bounding_box is not None:
            self._scene.scene.remove_geometry("BoundingBox")
            self.bounding_box = None

    def _on_key_event(self, event):
        """
        键盘事件处理
        参数:
        event (gui.KeyEvent): 键盘事件
        """
        if event.type == gui.KeyEvent.Type.DOWN:
            if event.key == gui.KeyName.Z:
                self._on_undo()
            elif event.key == gui.KeyName.Y:
                self._on_redo()
            elif event.key == gui.KeyName.V:
                self._refresh_view()
            if event.key == gui.KeyName.F:
                # 切换 Eraser 模式
                self._on_mode_changed("erase", not self.erase_mode)
            elif event.key == gui.KeyName.G:
                # 切换边界框模式
                self._on_mode_changed("bounding_box", not self.bounding_box_mode)
            elif event.key == gui.KeyName.X:
                self._export_current_point_cloud()

            if not self.bounding_box_mode and not self.erase_mode:
                if event.key == gui.KeyName.A:
                    self._translate_point_cloud(axis='x', delta = -(self.length * self.translation_step_pc) / 1000)
                elif event.key == gui.KeyName.D:
                    self._translate_point_cloud(axis='x', delta = (self.length * self.translation_step_pc) / 1000)
                elif event.key == gui.KeyName.W:
                    self._translate_point_cloud(axis='y', delta = (self.length * self.translation_step_pc) / 1000)
                elif event.key == gui.KeyName.S:
                    self._translate_point_cloud(axis='y', delta = -(self.length * self.translation_step_pc) / 1000)
                elif event.key == gui.KeyName.Q:
                    self._translate_point_cloud(axis='z', delta = (self.length * self.translation_step_pc) / 1000)
                elif event.key == gui.KeyName.E:
                    self._translate_point_cloud(axis='z', delta = -(self.length * self.translation_step_pc) / 1000)
                elif event.key == gui.KeyName.J:
                    self._rotate_point_cloud(axis='y', delta=np.radians(-(0.25 + ((self.rotation_step_pc - 1) / 99) * (45 - 0.25))))
                elif event.key == gui.KeyName.L:
                    self._rotate_point_cloud(axis='y', delta=np.radians(0.25 + ((self.rotation_step_pc - 1) / 99) * (45 - 0.25)))
                elif event.key == gui.KeyName.I:
                    self._rotate_point_cloud(axis='x', delta=np.radians(-(0.25 + ((self.rotation_step_pc - 1) / 99) * (45 - 0.25))))
                elif event.key == gui.KeyName.K:
                    self._rotate_point_cloud(axis='x', delta=np.radians(0.25 + ((self.rotation_step_pc - 1) / 99) * (45 - 0.25)))
                elif event.key == gui.KeyName.U:
                    self._rotate_point_cloud(axis='z', delta=np.radians(-(0.25 + ((self.rotation_step_pc - 1) / 99) * (45 - 0.25))))
                elif event.key == gui.KeyName.O:
                    self._rotate_point_cloud(axis='z', delta=np.radians(0.25 + ((self.rotation_step_pc - 1) / 99) * (45 - 0.25)))
            elif self.bounding_box_mode:
                if event.key == gui.KeyName.A:
                    self._translate_bounding_box(axis='x', delta = -(self.length * self.translation_step_bbox) / 1000)
                elif event.key == gui.KeyName.D:
                    self._translate_bounding_box(axis='x', delta = (self.length * self.translation_step_bbox) / 1000)
                elif event.key == gui.KeyName.W:
                    self._translate_bounding_box(axis='y', delta = (self.length * self.translation_step_bbox) / 1000)
                elif event.key == gui.KeyName.S:
                    self._translate_bounding_box(axis='y', delta = -(self.length * self.translation_step_bbox) / 1000)
                elif event.key == gui.KeyName.Q:
                    self._translate_bounding_box(axis='z', delta = (self.length * self.translation_step_bbox) / 1000)
                elif event.key == gui.KeyName.E:
                    self._translate_bounding_box(axis='z', delta = -(self.length * self.translation_step_bbox) / 1000)
                elif event.key == gui.KeyName.J:
                    self._resize_bounding_box(axis='x', delta = -(self.length * self.resize_step_bbox) / 1000)
                elif event.key == gui.KeyName.L:
                    self._resize_bounding_box(axis='x', delta = (self.length * self.resize_step_bbox) / 1000)
                elif event.key == gui.KeyName.I:
                    self._resize_bounding_box(axis='y', delta = -(self.length * self.resize_step_bbox) / 1000)
                elif event.key == gui.KeyName.K:
                    self._resize_bounding_box(axis='y', delta = (self.length * self.resize_step_bbox) / 1000)
                elif event.key == gui.KeyName.U:
                    self._resize_bounding_box(axis='z', delta = -(self.length * self.resize_step_bbox) / 1000)
                elif event.key == gui.KeyName.O:
                    self._resize_bounding_box(axis='z', delta = (self.length * self.resize_step_bbox) / 1000)
                elif event.key == gui.KeyName.R:
                    self._remove_points_inside_bbox()
                elif event.key == gui.KeyName.P:
                    self._preserve_points_inside_bbox()
                elif event.key == gui.KeyName.H:  # 添加 H 键的处理
                    self._highlight_points_inside_bbox()
            elif self.erase_mode:
                pass  # 在擦除模式下没有按键事件处理

    def _export_current_point_cloud(self):
        """
        导出当前点云
        """
        if not self.point_cloud_loaded:
            self._show_warning_dialog("No point cloud available for export.")
            return
        
        dlg = gui.FileDialog(gui.FileDialog.SAVE, "Choose file to save", self.window.theme)
        dlg.add_filter(".ply", "PLY files (.ply)")
        dlg.set_on_cancel(self._on_file_dialog_cancel)
        dlg.set_on_done(self._on_save_dialog_done)
        self.window.show_dialog(dlg)

    def _on_save_dialog_done(self, filename):
        """
        完成文件保存选择时触发
        参数:
        filename (str): 选择的文件名
        """
        self.window.close_dialog()
        if not self.point_cloud_loaded:
            self._show_warning_dialog("No point cloud available for export.")
            return
        
        try:
            o3d.io.write_point_cloud(filename, self.point_cloud)
            print(f"Point cloud exported as {filename}")
        except Exception as e:
            self._show_warning_dialog(f"Failed to export point cloud: {e}")
            

    def _highlight_points_inside_bbox(self):
        if not self.point_cloud_loaded or self.bounding_box is None:
            return

        print("Highlighting points inside bounding box")
        points = np.asarray(self.point_cloud.points)
        o3d_points = o3d.utility.Vector3dVector(points)
        mask = self.bounding_box.get_point_indices_within_bounding_box(o3d_points)
        mask_set = set(mask)

        # 确保 self.original_colors 是 numpy 数组
        if self.original_colors is None:
            self.original_colors = np.asarray(self.point_cloud.colors).copy()
        
        colors = np.asarray(self.point_cloud.colors)  # 确保 colors 是 numpy 数组

        # 恢复所有点的原始颜色
        colors = self.original_colors.copy()

        # 更新边界框内点的颜色为红色
        for i in range(len(colors)):
            if i in mask_set:
                colors[i] = [1, 0, 0]  # 红色

        self.point_cloud.colors = o3d.utility.Vector3dVector(colors)

        # 重新添加点云以更新颜色
        self._scene.scene.remove_geometry("PointCloud")
        self._scene.scene.add_geometry("PointCloud", self.point_cloud, self.material)
        self._scene.force_redraw()

        print("Points inside bounding box highlighted")

    def _remove_points_inside_bbox(self):
        if not self.point_cloud_loaded or self.bounding_box is None:
            return

        self._restore_original_colors()

        # 保存当前状态
        self._save_current_state()

        points = np.asarray(self.point_cloud.points)
        o3d_points = o3d.utility.Vector3dVector(points)
        mask = self.bounding_box.get_point_indices_within_bounding_box(o3d_points)
        mask = np.isin(np.arange(len(points)), mask, invert=True)

        new_points = points[mask]
        new_colors = np.asarray(self.point_cloud.colors)[mask]

        self._update_point_cloud(new_points, new_colors)

        self.original_colors = None

    def _preserve_points_inside_bbox(self):
        if not self.point_cloud_loaded or self.bounding_box is None:
            return

        self._restore_original_colors()

        # 保存当前状态
        self._save_current_state()


        points = np.asarray(self.point_cloud.points)
        o3d_points = o3d.utility.Vector3dVector(points)
        mask = self.bounding_box.get_point_indices_within_bounding_box(o3d_points)

        new_points = points[mask]
        new_colors = np.asarray(self.point_cloud.colors)[mask]

        self._update_point_cloud(new_points, new_colors)


    def _translate_point_cloud(self, axis, delta):
        if not self.point_cloud_loaded:
            return

        self._save_current_state()

        points = np.asarray(self.point_cloud.points)

        if axis == 'x':
            points[:, 0] += delta
        elif axis == 'y':
            points[:, 1] += delta
        elif axis == 'z':
            points[:, 2] += delta

        self.point_cloud.points = o3d.utility.Vector3dVector(points)
        self._scene.scene.remove_geometry("PointCloud")
        self._scene.scene.add_geometry("PointCloud", self.point_cloud, self.material)
        self._scene.force_redraw()

    def _rotate_point_cloud(self, axis, delta):
        if not self.point_cloud_loaded:
            return

        self._save_current_state()

        points = np.asarray(self.point_cloud.points)
        centroid = np.mean(points, axis=0)
        points -= centroid

        if axis == 'x':
            R = np.array([[1, 0, 0],
                          [0, np.cos(delta), -np.sin(delta)],
                          [0, np.sin(delta), np.cos(delta)]])
        elif axis == 'y':
            R = np.array([[np.cos(delta), 0, np.sin(delta)],
                          [0, 1, 0],
                          [-np.sin(delta), 0, np.cos(delta)]])
        elif axis == 'z':
            R = np.array([[np.cos(delta), -np.sin(delta), 0],
                          [np.sin(delta), np.cos(delta), 0],
                          [0, 0, 1]])

        points = np.dot(points, R.T)
        points += centroid

        self.point_cloud.points = o3d.utility.Vector3dVector(points)
        self._scene.scene.remove_geometry("PointCloud")
        self._scene.scene.add_geometry("PointCloud", self.point_cloud, self.material)
        self._scene.force_redraw()

    def _resize_bounding_box(self, axis, delta):
        if self.bounding_box is None:
            return

        min_bound = np.array(self.bounding_box.min_bound)
        max_bound = np.array(self.bounding_box.max_bound)

        if axis == 'x':
            max_bound[0] += delta
        elif axis == 'y':
            max_bound[1] += delta
        elif axis == 'z':
            max_bound[2] += delta

        self.bounding_box = o3d.geometry.AxisAlignedBoundingBox(min_bound, max_bound)
        self.bounding_box.color = [1, 0, 0]

        # 设置材料属性
        material = rendering.MaterialRecord()
        material.shader = "unlitLine"
        material.line_width = 2.0
        material.base_color = [1, 0, 0, 1]  # 设置基础颜色

        # 确保添加到场景的几何体具有所有必要的属性
        if self._scene.scene.has_geometry("BoundingBox"):
            self._scene.scene.remove_geometry("BoundingBox")
        self._scene.scene.add_geometry("BoundingBox", self.bounding_box, material)
        self._scene.force_redraw()

    def _translate_bounding_box(self, axis, delta):
        if self.bounding_box is None:
            return

        min_bound = np.array(self.bounding_box.min_bound)
        max_bound = np.array(self.bounding_box.max_bound)

        translation = np.zeros(3)
        if axis == 'x':
            translation[0] = delta
        elif axis == 'y':
            translation[1] = delta
        elif axis == 'z':
            translation[2] = delta

        min_bound += translation
        max_bound += translation

        self.bounding_box = o3d.geometry.AxisAlignedBoundingBox(min_bound, max_bound)
        self.bounding_box.color = [1, 0, 0]

        # 设置材料属性
        material = rendering.MaterialRecord()
        material.shader = "unlitLine"
        material.line_width = 2.0
        material.base_color = [1, 0, 0, 1]  # 设置基础颜色

        # 确保添加到场景的几何体具有所有必要的属性
        if self._scene.scene.has_geometry("BoundingBox"):
            self._scene.scene.remove_geometry("BoundingBox")
        self._scene.scene.add_geometry("BoundingBox", self.bounding_box, material)
        self._scene.force_redraw()

    def _toggle_highlight_points(self):
        if self.bounding_box is None or not self.point_cloud_loaded:
            return

        points = np.asarray(self.point_cloud.points)
        mask = self.bounding_box.get_point_indices_within_bounding_box(points)
        mask_set = set(mask)

        if self.original_colors is None:
            self.original_colors = np.asarray(self.point_cloud.colors)

        colors = np.asarray(self.point_cloud.colors)
        for i in range(len(colors)):
            if i in mask_set:
                colors[i] = [1, 0, 0]  # 红色
            else:
                colors[i] = self.original_colors[i]

        self.point_cloud.colors = o3d.utility.Vector3dVector(colors)
        self._scene.force_redraw()

    def _on_layout(self, layout_context):
        r = self.window.content_rect
        self._scene.frame = r
        width = 17 * layout_context.theme.font_size
        height = min(r.height, self._settings_panel.calc_preferred_size(layout_context, gui.Widget.Constraints()).height)
        self._settings_panel.frame = gui.Rect(r.get_right() - width, r.y, width, height)

    def _on_menu_open(self):
        dlg = gui.FileDialog(gui.FileDialog.OPEN, "Choose file to load", self.window.theme)
        dlg.add_filter(".xyz .xyzn .xyzrgb .ply .pcd .pts", "Point cloud files (.xyz, .xyzn, .xyzrgb, .ply, .pcd, .pts)")
        dlg.add_filter("", "All files")
        dlg.set_on_cancel(self._on_file_dialog_cancel)
        dlg.set_on_done(self._on_load_dialog_done)
        self.window.show_dialog(dlg)

    def _on_file_dialog_cancel(self):
        self.window.close_dialog()

    def _on_load_dialog_done(self, filename):
        self.window.close_dialog()
        self.load_point_cloud(filename)

    def _on_menu_quit(self):
        gui.Application.instance.quit()

    def _on_menu_toggle_view_controls(self):
        self.view_ctrls.visible = not self.view_ctrls.visible
        self._update_settings_panel_visibility()

    def _on_menu_toggle_point_cloud_controls(self):
        self.point_cloud_ctrls.visible = not self.point_cloud_ctrls.visible
        self._update_settings_panel_visibility()

    def _update_settings_panel_visibility(self):
        any_visible = self.view_ctrls.visible or self.point_cloud_ctrls.visible
        self._settings_panel.visible = any_visible
        gui.Application.instance.menubar.set_checked(AppWindow.MENU_SHOW_SETTINGS, self.view_ctrls.visible)
        gui.Application.instance.menubar.set_checked(AppWindow.MENU_SHOW_POINT_CLOUD_CONTROLS, self.point_cloud_ctrls.visible)
        self.window.set_needs_layout()

    def _on_menu_about(self):
        pass

    def _on_bg_color_changed(self, color):
        self._scene.scene.set_background([color.red, color.green, color.blue, color.alpha])

    def generate_random_point_cloud(self):
        num_points = 5000
        points = np.random.uniform(-1, 1, size=(num_points, 3))
        colors = np.random.uniform(0.0, 1.0, size=(num_points, 3))  # 确保生成的颜色更均匀
        self.point_cloud = o3d.geometry.PointCloud()
        self.point_cloud.points = o3d.utility.Vector3dVector(points)
        self.point_cloud.colors = o3d.utility.Vector3dVector(colors)
        self._scene.scene.add_geometry("PointCloud", self.point_cloud, self.material)
        self.point_cloud_loaded = True
        self._scene.setup_camera(60.0, self.point_cloud.get_axis_aligned_bounding_box(), self.point_cloud.get_center())
        self.length = self.get_point_cloud_length()
        print("Random point cloud generated")

    def load_point_cloud(self, path):
        try:
            pcd = o3d.io.read_point_cloud(path)
            if not pcd.has_points():
                self._show_warning_dialog(f"Failed to load point cloud from {path}. No points found.")
                return

            if self.point_cloud_loaded:
                self._scene.scene.remove_geometry("PointCloud")

            self.point_cloud = pcd

            # 确保点云有颜色信息
            if not self.point_cloud.has_colors():
                num_points = np.asarray(self.point_cloud.points).shape[0]
                colors = np.ones((num_points, 3)) * 0.5  # 默认灰色
                self.point_cloud.colors = o3d.utility.Vector3dVector(colors)

            self._scene.scene.add_geometry("PointCloud", self.point_cloud, self.material)
            self.point_cloud_loaded = True
            if self.refresh_view_on_mode_change:
                self._scene.setup_camera(60.0, pcd.get_axis_aligned_bounding_box(), pcd.get_center())
            self.length = self.get_point_cloud_length()    
            print("Point cloud loaded successfully")

            # 如果边界框模式启用，更新边界框
            if self.bounding_box_mode:
                self._show_bounding_box()

            self.original_colors = None

        except Exception as e:
            self._show_warning_dialog(f"Failed to load point cloud: {e}")

    def get_point_cloud_length(self):
        if not self.point_cloud_loaded:
            print("No point cloud loaded.")
            return None

        bbox = self.point_cloud.get_axis_aligned_bounding_box()
        min_bound = bbox.min_bound
        max_bound = bbox.max_bound
        length = np.linalg.norm(max_bound - min_bound)
        print(f"Point cloud length: {length}")
        return length

    def _show_warning_dialog(self, message):
        """
        顯示警告對話框
        參數:
        message (str): 警告信息
        """
        print(f"Warning: {message}")
        dlg = gui.Dialog("Warning")
        dlg_layout = gui.Vert(0.25 * self.window.theme.font_size,
                              gui.Margins(0.5 * self.window.theme.font_size,
                                          0.5 * self.window.theme.font_size,
                                          0.5 * self.window.theme.font_size,
                                          0.5 * self.window.theme.font_size))
        dlg_layout.add_child(gui.Label(message))

        ok = gui.Button("OK")
        ok.set_on_clicked(self.window.close_dialog)

        h = gui.Horiz()
        h.add_stretch()
        h.add_child(ok)
        h.add_stretch()
        dlg_layout.add_child(h)
        dlg.add_child(dlg_layout)
        self.window.show_dialog(dlg)

    def _on_mouse_event(self, event):
        if self.erase_mode:
            if event.type == gui.MouseEvent.Type.BUTTON_DOWN and event.is_button_down(gui.MouseButton.LEFT):
                self.is_erasing = True
                self.last_mouse_pos = [event.x, event.y]
                self._save_current_state()  # 在按下左键时保存初始状态
                self._erase_points(event.x, event.y)
                return gui.SceneWidget.EventCallbackResult.CONSUMED

            if event.type == gui.MouseEvent.Type.BUTTON_UP and not event.is_button_down(gui.MouseButton.LEFT):
                self.is_erasing = False
                self._save_current_state()  # 在释放左键时保存最终状态
                return gui.SceneWidget.EventCallbackResult.CONSUMED

            if event.type == gui.MouseEvent.Type.DRAG and self.is_erasing:
                self._erase_along_path(self.last_mouse_pos, [event.x, event.y])
                self.last_mouse_pos = [event.x, event.y]
                return gui.SceneWidget.EventCallbackResult.CONSUMED

        return gui.SceneWidget.EventCallbackResult.IGNORED

    def _erase_along_path(self, start, end):
        num_steps = max(1, int(np.linalg.norm(np.array(start) - np.array(end)) / self.erase_radius))
        for i in range(num_steps + 1):
            x = int(start[0] + (end[0] - start[0]) * i / num_steps)
            y = int(start[1] + (end[1] - start[1]) * i / num_steps)
            self._erase_points(x, y)

    def _erase_points(self, x, y):
        if not self.point_cloud_loaded:
            return

        points = np.asarray(self.point_cloud.points)
        colors = np.asarray(self.point_cloud.colors)
        view_matrix = self._scene.scene.camera.get_view_matrix()
        proj_matrix = self._scene.scene.camera.get_projection_matrix()
        frame_width = self._scene.frame.width
        frame_height = self._scene.frame.height

        if self.eraser_thread is not None and self.eraser_thread.is_alive():
            return  # Avoid starting a new thread if the previous one is still running

        self.eraser_thread = threading.Thread(target=self._erase_points_thread, args=(x, y, points, colors, view_matrix, proj_matrix, frame_width, frame_height))
        self.eraser_thread.start()

    def _erase_points_thread(self, x, y, points, colors, view_matrix, proj_matrix, frame_width, frame_height):
        with self.erase_lock:
            screen_points = np.zeros((points.shape[0], 2))

            for i, point in enumerate(points):
                screen_points[i] = world_to_screen(point, view_matrix, proj_matrix, frame_width, frame_height)

            distances = np.linalg.norm(screen_points - np.array([x, y]), axis=1)
            mask = distances > self.erase_radius
            new_points = points[mask]
            new_colors = colors[mask] if colors.size else colors

            self.erase_queue.put((new_points, new_colors))

            # Use post_to_main_thread to update the point cloud on the main thread
            gui.Application.instance.post_to_main_thread(self.window, self._update_point_cloud_from_queue)

    def _update_point_cloud_from_queue(self):
        try:
            new_points, new_colors = self.erase_queue.get_nowait()
            self._update_point_cloud(new_points, new_colors)
        except queue.Empty:
            print("No result returned from erase process")

    def _update_point_cloud(self, new_points, new_colors):
        self.point_cloud.points = o3d.utility.Vector3dVector(new_points)
        self.point_cloud.colors = o3d.utility.Vector3dVector(new_colors)
        if self._scene.scene.has_geometry("PointCloud"):
            self._scene.scene.remove_geometry("PointCloud")
        self._scene.scene.add_geometry("PointCloud", self.point_cloud, self.material)
        self._scene.force_redraw()

    def _save_current_state(self):
        """
        保存当前点云状态到undo栈
        """
        self.undo_stack.append(copy.deepcopy(self.point_cloud))
        self.redo_stack.clear()  # 清空redo栈
        print("Saved current state")

    def _on_undo(self):
        """
        撤销操作
        """
        if not self.undo_stack:
            self._show_warning_dialog("No actions to undo.")
            return

        self.redo_stack.append(copy.deepcopy(self.point_cloud))
        last_state = self.undo_stack.pop()
        self.point_cloud = last_state

        self._scene.scene.remove_geometry("PointCloud")
        self._scene.scene.add_geometry("PointCloud", self.point_cloud, self.material)
        self._scene.force_redraw()

    def _on_redo(self):
        """
        重做操作
        """
        if not self.redo_stack:
            self._show_warning_dialog("No actions to redo.")
            return
        
        self.undo_stack.append(copy.deepcopy(self.point_cloud))
        next_state = self.redo_stack.pop()
        self.point_cloud = next_state

        self._scene.scene.remove_geometry("PointCloud")
        self._scene.scene.add_geometry("PointCloud", self.point_cloud, self.material)
        self._scene.force_redraw()

def main():
    gui.Application.instance.initialize()
    w = AppWindow(1024, 768)
    gui.Application.instance.run()

if __name__ == "__main__":
    main()
