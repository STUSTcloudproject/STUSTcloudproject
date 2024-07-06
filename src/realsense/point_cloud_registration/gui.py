import open3d as o3d
import numpy as np
import threading
import copy
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering
import platform
import os

isMacOS = (platform.system() == "Darwin")

class AppWindow:
    MENU_OPEN = 1
    MENU_EXPORT = 2
    MENU_QUIT = 3
    MENU_SHOW_SETTINGS = 11
    MENU_FUNCTION1 = 12
    MENU_FUNCTION2 = 13
    MENU_STATUS_PANEL = 14
    MENU_ABOUT = 21

    def __init__(self, width, height):
        self.window = gui.Application.instance.create_window("Open3D", width, height)
        w = self.window  # to make the code more concise

        self._scene = gui.SceneWidget()
        self._scene.scene = rendering.Open3DScene(w.renderer)
        self._scene.scene.set_background([1, 1, 1, 1])  # 设置背景为白色
        w.add_child(self._scene)

        

        # 默认平移和旋转步长
        self.translation_step = 0.0002
        self.rotation_step = 0.002

        self.source_hidden = False
        self.target_hidden = False

        # 点云文件容器
        self.point_clouds = []
        self.current_target_idx = 0
        self.current_source_idx = 1

        # 撤销和重做堆栈
        self.undo_stack = []
        self.redo_stack = []

        # 合并标志
        self.merged = False

        # Set up the menu bar
        self._setup_menu_bar()

        # Set up settings panel
        self._setup_settings_panel()

        # Set up status panel
        self._setup_status_panel()

        # Set up layout
        w.set_on_layout(self._on_layout)

        self.material = rendering.MaterialRecord()
        self.material.shader = "defaultUnlit"
        self.point_cloud_loaded = False

        # 初始化时勾选所有项
        self.view_ctrls.visible = True
        self.function1_ctrls.visible = True
        self.function2_ctrls.visible = True
        self.status_panel.visible = True
        self._settings_panel.visible = True

        # 更新菜单栏中的勾选状态
        gui.Application.instance.menubar.set_checked(AppWindow.MENU_SHOW_SETTINGS, self.view_ctrls.visible)
        gui.Application.instance.menubar.set_checked(AppWindow.MENU_FUNCTION1, self.function1_ctrls.visible)
        gui.Application.instance.menubar.set_checked(AppWindow.MENU_FUNCTION2, self.function2_ctrls.visible)
        gui.Application.instance.menubar.set_checked(AppWindow.MENU_STATUS_PANEL, self.status_panel.visible)

        # 注册键盘事件
        self.window.set_on_key(self._on_key)

        # 添加锁以避免连续触发
        self.lock = threading.Lock()
        self.is_processing = False

    def _setup_menu_bar(self):
        if gui.Application.instance.menubar is None:
            if isMacOS:
                app_menu = gui.Menu()
                app_menu.add_item("About", AppWindow.MENU_ABOUT)
                app_menu.add_separator()
                app_menu.add_item("Quit", AppWindow.MENU_QUIT)
            file_menu = gui.Menu()
            file_menu.add_item("Open...", AppWindow.MENU_OPEN)
            file_menu.add_item("Export Current Image...", AppWindow.MENU_EXPORT)
            if not isMacOS:
                file_menu.add_separator()
                file_menu.add_item("Quit", AppWindow.MENU_QUIT)
            settings_menu = gui.Menu()
            settings_menu.add_item("View Controls", AppWindow.MENU_SHOW_SETTINGS)
            settings_menu.add_item("Function 1", AppWindow.MENU_FUNCTION1)
            settings_menu.add_item("Function 2", AppWindow.MENU_FUNCTION2)
            settings_menu.add_item("Status Panel", AppWindow.MENU_STATUS_PANEL)
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
        self.window.set_on_menu_item_activated(AppWindow.MENU_EXPORT, self._on_menu_export)
        self.window.set_on_menu_item_activated(AppWindow.MENU_QUIT, self._on_menu_quit)
        self.window.set_on_menu_item_activated(AppWindow.MENU_SHOW_SETTINGS, self._on_menu_toggle_view_controls)
        self.window.set_on_menu_item_activated(AppWindow.MENU_FUNCTION1, self._on_menu_toggle_function1)
        self.window.set_on_menu_item_activated(AppWindow.MENU_FUNCTION2, self._on_menu_toggle_function2)
        self.window.set_on_menu_item_activated(AppWindow.MENU_STATUS_PANEL, self._on_menu_toggle_status_panel)
        self.window.set_on_menu_item_activated(AppWindow.MENU_ABOUT, self._on_menu_about)

    def _setup_settings_panel(self):
        em = self.window.theme.font_size
        separation_height = int(round(0.5 * em))

        self._settings_panel = gui.Vert(0, gui.Margins(0.25 * em, 0.25 * em, 0.25 * em, 0.25 * em))

        # View Controls
        self.view_ctrls = gui.CollapsableVert("View controls", 0.25 * em, gui.Margins(em, 0, 0, 0))

        grid = gui.VGrid(2, 0.25 * em)
        grid.add_child(gui.Label("BG Color"))
        self._bg_color = gui.ColorEdit()
        self._bg_color.color_value = gui.Color(1, 1, 1)  # 设置默认颜色为白色
        self._bg_color.set_on_value_changed(self._on_bg_color_changed)
        grid.add_child(self._bg_color)

        grid.add_child(gui.Label("Point Cloud Color"))
        self._pc_color_mode = gui.Combobox()
        self._pc_color_mode.add_item("Original")
        self._pc_color_mode.add_item("Custom")
        self._pc_color_mode.set_on_selection_changed(self._on_pc_color_mode_changed)
        grid.add_child(self._pc_color_mode)

        self._pc_color = gui.ColorEdit()
        self._pc_color.color_value = gui.Color(0.5, 0.5, 0.5)
        self._pc_color.set_on_value_changed(self._on_pc_color_changed)
        grid.add_child(self._pc_color)

        self.view_ctrls.add_child(grid)
        self._settings_panel.add_child(self.view_ctrls)

        # Function 1 Controls
        self.function1_ctrls = gui.CollapsableVert("Function 1 Controls", 0.25 * em, gui.Margins(em, 0, 0, 0))
        self.function1_ctrls.add_child(gui.Label("Function 1 specific settings"))

        self._btn_next_source = gui.Button("Next Source (N)")
        self._btn_next_source.set_on_clicked(self._switch_source)
        self.function1_ctrls.add_child(self._btn_next_source)

        self._btn_switch_target = gui.Button("Switch Target (B)")
        self._btn_switch_target.set_on_clicked(self._switch_target)
        self.function1_ctrls.add_child(self._btn_switch_target)

        # 设置平移步长滑动条
        self._translation_step_slider = gui.Slider(gui.Slider.DOUBLE)
        self._translation_step_slider.set_limits(0.1, 30.0)
        self._translation_step_slider.double_value = 15  # 设置默认值为 15
        self.translation_step = 15 / 10000  # 根据比例调整平移步长
        self._translation_step_slider.set_on_value_changed(self._on_translation_step_changed)
        self.function1_ctrls.add_child(gui.Label("Translation Step"))
        self.function1_ctrls.add_child(self._translation_step_slider)

        # 设置旋转步长滑动条
        self._rotation_step_slider = gui.Slider(gui.Slider.DOUBLE)
        self._rotation_step_slider.set_limits(0.1, 30.0)
        self._rotation_step_slider.double_value = 15  # 设置默认值为 15
        self.rotation_step = 15 / 1000  # 根据比例调整旋转步长
        self._rotation_step_slider.set_on_value_changed(self._on_rotation_step_changed)
        self.function1_ctrls.add_child(gui.Label("Rotation Step"))
        self.function1_ctrls.add_child(self._rotation_step_slider)

        self._btn_start_registration = gui.Button("Start Registration (R)")
        self._btn_start_registration.set_on_clicked(self._on_start_registration)
        self.function1_ctrls.add_child(self._btn_start_registration)

        self._btn_undo = gui.Button("Undo (Z)")
        self._btn_undo.set_on_clicked(self._on_undo)
        self.function1_ctrls.add_child(self._btn_undo)

        self._btn_redo = gui.Button("Redo (Y)")
        self._btn_redo.set_on_clicked(self._on_redo)
        self.function1_ctrls.add_child(self._btn_redo)

        # 添加合并点云按钮
        self._btn_merge = gui.Button("Merge Point Clouds (M)")
        self._btn_merge.set_on_clicked(self._merge_point_clouds)
        self.function1_ctrls.add_child(self._btn_merge)

        self._settings_panel.add_child(self.function1_ctrls)

        # Function 2 Controls
        self.function2_ctrls = gui.CollapsableVert("Function 2 Controls", 0.25 * em, gui.Margins(em, 0, 0, 0))
        self.function2_ctrls.add_child(gui.Label("Function 2 specific settings"))
        self._settings_panel.add_child(self.function2_ctrls)

        self.window.add_child(self._settings_panel)


    def _setup_status_panel(self):
        em = self.window.theme.font_size
        self.status_panel = gui.Vert(0.25 * em, gui.Margins(em, 0, 0, 0))

        self.source_label = gui.Label(f"Current Source: {self.current_source_idx if len(self.point_clouds) > 1 else 'N/A'}")
        self.target_label = gui.Label(f"Current Target: {self.current_target_idx if len(self.point_clouds) > 0 else 'N/A'}")

        self.status_panel.add_child(self.source_label)
        self.status_panel.add_child(self.target_label)

        self._chk_source_visible = gui.Checkbox("Show Source")
        self._chk_source_visible.checked = not self.source_hidden
        self._chk_source_visible.set_on_checked(self._on_toggle_source_visibility)
        self.status_panel.add_child(self._chk_source_visible)

        self._chk_target_visible = gui.Checkbox("Show Target")
        self._chk_target_visible.checked = not self.target_hidden
        self._chk_target_visible.set_on_checked(self._on_toggle_target_visibility)
        self.status_panel.add_child(self._chk_target_visible)

        self.window.add_child(self.status_panel)

    def _on_layout(self, layout_context):
        r = self.window.content_rect
        self._scene.frame = r
        width = 17 * layout_context.theme.font_size
        height = min(r.height, self._settings_panel.calc_preferred_size(layout_context, gui.Widget.Constraints()).height)
        self._settings_panel.frame = gui.Rect(r.get_right() - width, r.y, width, height)

        status_panel_width = 20 * layout_context.theme.font_size
        status_panel_height = self.status_panel.calc_preferred_size(layout_context, gui.Widget.Constraints()).height
        self.status_panel.frame = gui.Rect(r.x, r.get_bottom() - status_panel_height, status_panel_width, status_panel_height)


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
        self.load(filename)

    def _on_menu_export(self):
        pass

    def _on_menu_quit(self):
        gui.Application.instance.quit()

    def _on_menu_toggle_view_controls(self):
        self.view_ctrls.visible = not self.view_ctrls.visible
        self._update_settings_panel_visibility()

    def _on_menu_toggle_function1(self):
        self.function1_ctrls.visible = not self.function1_ctrls.visible
        self._update_settings_panel_visibility()

    def _on_menu_toggle_function2(self):
        self.function2_ctrls.visible = not self.function2_ctrls.visible
        self._update_settings_panel_visibility()

    def _on_menu_toggle_status_panel(self):
        self.status_panel.visible = not self.status_panel.visible
        self._update_settings_panel_visibility()

    def _update_settings_panel_visibility(self):
        any_visible = self.view_ctrls.visible or self.function1_ctrls.visible or self.function2_ctrls.visible or self.status_panel.visible
        self._settings_panel.visible = any_visible

        gui.Application.instance.menubar.set_checked(AppWindow.MENU_SHOW_SETTINGS, self.view_ctrls.visible)
        gui.Application.instance.menubar.set_checked(AppWindow.MENU_FUNCTION1, self.function1_ctrls.visible)
        gui.Application.instance.menubar.set_checked(AppWindow.MENU_FUNCTION2, self.function2_ctrls.visible)
        gui.Application.instance.menubar.set_checked(AppWindow.MENU_STATUS_PANEL, self.status_panel.visible)

        # Force layout update
        self.window.set_needs_layout()

    def _on_menu_about(self):
        pass

    def _on_bg_color_changed(self, color):
        self._scene.scene.set_background([color.red, color.green, color.blue, color.alpha])

    def _on_pc_color_mode_changed(self, text, index):
        print(f"Color mode changed: {text}")

        if not self.point_cloud_loaded:
            self._show_warning_dialog("Please load a point cloud file first.")
            self._pc_color_mode.selected_index = 0  # Reset to "Original"
            return

        if text == "Original":
            self.material.shader = "defaultUnlit"
        else:
            self.material.shader = "defaultLit"
            self.material.base_color = [
                self._pc_color.color_value.red,
                self._pc_color.color_value.green,
                self._pc_color.color_value.blue,
                self._pc_color.color_value.alpha,
            ]
        self._update_point_cloud_color()

    def _on_pc_color_changed(self, color):
        if not self.point_cloud_loaded:
            self._show_warning_dialog("Please load a point cloud file first.")
            return

        if self._pc_color_mode.selected_text == "Custom":
            self.material.base_color = [color.red, color.green, color.blue, color.alpha]
            self._update_point_cloud_color()

    def _update_point_cloud_color(self):
        if self.point_cloud_loaded:
            # 更新材质颜色
            if self.material.shader == "defaultLit":
                self.material.base_color = [
                    self._pc_color.color_value.red,
                    self._pc_color.color_value.green,
                    self._pc_color.color_value.blue,
                    self._pc_color.color_value.alpha,
                ]
            self._scene.scene.remove_geometry("Source")
            self._scene.scene.remove_geometry("Target")
            self._scene.scene.add_geometry("Source", self.point_clouds[self.current_source_idx], self.material)
            self._scene.scene.add_geometry("Target", self.point_clouds[self.current_target_idx], self.material)
            print("Point cloud color updated")

    def _show_warning_dialog(self, message):
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

    def load(self, path):
        try:
            pcd = o3d.io.read_point_cloud(path)
            if not pcd.has_points():
                print(f"Failed to load point cloud from {path}. Exiting.")
                return
            
            if len(self.point_clouds) == 0:
                # 第一个点云作为target
                self.point_clouds.append(pcd)
                pcd.paint_uniform_color([0.5, 0.5, 0.5])
                self.current_target_idx = 0
                self._scene.scene.add_geometry("Target", pcd, self.material)
            elif len(self.point_clouds) == 1:
                # 第二个点云作为source
                self.point_clouds.append(pcd)
                pcd.paint_uniform_color([0, 0, 1])
                self.current_source_idx = 1
                self._scene.scene.add_geometry("Source", pcd, self.material)
            else:
                # 之后的点云暂时不显示
                self.point_clouds.append(pcd)
            
            self.point_cloud_loaded = True
            self._scene.setup_camera(5.0, self._scene.scene.bounding_box, self._scene.scene.bounding_box.get_center())
            self._update_status_panel()
            print("Point cloud loaded successfully")

        except Exception as e:
            print(f"Failed to load point cloud: {e}")

    def _on_key(self, event):
        if event.type == gui.KeyEvent.DOWN:
            with self.lock:
                if self.is_processing:
                    return
                if event.key == gui.KeyName.N:
                    self._switch_source()
                elif event.key == gui.KeyName.B:
                    self._switch_target()
                elif self.merged:
                    self._show_warning_dialog("In merged mode, press 'N' or 'B' to exit.")
                    return
                elif event.key == gui.KeyName.W:
                    self._translate_point_cloud([0, self.translation_step, 0])  # 平移步长缩放 100 倍
                elif event.key == gui.KeyName.S:
                    self._translate_point_cloud([0, -self.translation_step, 0])
                elif event.key == gui.KeyName.A:
                    self._translate_point_cloud([-self.translation_step, 0, 0])
                elif event.key == gui.KeyName.D:
                    self._translate_point_cloud([self.translation_step, 0, 0])
                elif event.key == gui.KeyName.Q:
                    self._translate_point_cloud([0, 0, self.translation_step])
                elif event.key == gui.KeyName.E:
                    self._translate_point_cloud([0, 0, -self.translation_step])
                elif event.key == gui.KeyName.I:
                    self._rotate_point_cloud([self.rotation_step, 0, 0])  # 旋转步长缩放 100 倍
                elif event.key == gui.KeyName.K:
                    self._rotate_point_cloud([-self.rotation_step, 0, 0])
                elif event.key == gui.KeyName.J:
                    self._rotate_point_cloud([0, self.rotation_step, 0])
                elif event.key == gui.KeyName.L:
                    self._rotate_point_cloud([0, -self.rotation_step, 0])
                elif event.key == gui.KeyName.U:
                    self._rotate_point_cloud([0, 0, self.rotation_step])
                elif event.key == gui.KeyName.O:
                    self._rotate_point_cloud([0, 0, -self.rotation_step])
                elif event.key == gui.KeyName.R:
                    self._on_start_registration()
                elif event.key == gui.KeyName.Z:
                    self._on_undo()
                elif event.key == gui.KeyName.Y:
                    self._on_redo()
                elif event.key == gui.KeyName.M:
                    self._merge_point_clouds()



    def _translate_point_cloud(self, translation):
        if self.current_source_idx >= len(self.point_clouds):
            self._show_warning_dialog("Please load a source point cloud first.")
            return

        self.undo_stack.append(copy.deepcopy(self.point_clouds[self.current_source_idx]))  # 保存当前状态
        self.redo_stack.clear()  # 清空重做堆栈

        source_pcd = self.point_clouds[self.current_source_idx]
        source_pcd.translate(translation)
        self._scene.scene.remove_geometry("Source")
        self._scene.scene.add_geometry("Source", source_pcd, self.material)
        self._scene.force_redraw()

    def _rotate_point_cloud(self, rotation):
        if self.current_source_idx >= len(self.point_clouds):
            self._show_warning_dialog("Please load a source point cloud first.")
            return

        self.undo_stack.append(copy.deepcopy(self.point_clouds[self.current_source_idx]))  # 保存当前状态
        self.redo_stack.clear()  # 清空重做堆栈

        source_pcd = self.point_clouds[self.current_source_idx]
        R = source_pcd.get_rotation_matrix_from_xyz(rotation)
        source_pcd.rotate(R, center=source_pcd.get_center())
        self._scene.scene.remove_geometry("Source")
        self._scene.scene.add_geometry("Source", source_pcd, self.material)
        self._scene.force_redraw()

    def _switch_source(self):
        if self.merged:
            self._scene.scene.remove_geometry("Merged")
            self.merged = False
            self.undo_stack.clear()
            self.redo_stack.clear()

        if len(self.point_clouds) < 3:
            self._show_warning_dialog("No more point clouds to switch to as source.")
            return
        if self.source_hidden:
            self.source_hidden = False
            self._chk_source_visible.checked = True
        else:
            self.current_source_idx = (self.current_source_idx + 1) % len(self.point_clouds)
            if self.current_source_idx == self.current_target_idx:
                self.current_source_idx = (self.current_source_idx + 1) % len(self.point_clouds)

        self.undo_stack.clear()
        self.redo_stack.clear()

        new_source = self.point_clouds[self.current_source_idx]
        new_source.paint_uniform_color([0, 0, 1])  # 蓝色
        self._scene.scene.remove_geometry("Source")
        self._scene.scene.add_geometry("Source", new_source, self.material)

        if not self.target_hidden:
            new_target = self.point_clouds[self.current_target_idx]
            self._scene.scene.add_geometry("Target", new_target, self.material)

        self._scene.setup_camera(5.0, self._scene.scene.bounding_box, self._scene.scene.bounding_box.get_center())
        self._update_status_panel()
        print(f"Switched to source {self.current_source_idx}")

    def _switch_target(self):
        if self.merged:
            self._scene.scene.remove_geometry("Merged")
            self.merged = False
            self.undo_stack.clear()
            self.redo_stack.clear()

        if len(self.point_clouds) < 2:
            self._show_warning_dialog("No more point clouds to switch to as target.")
            return
        if self.target_hidden:
            self.target_hidden = False
            self._chk_target_visible.checked = True
        else:
            self.current_target_idx, self.current_source_idx = self.current_source_idx, self.current_target_idx

        self.undo_stack.clear()
        self.redo_stack.clear()

        new_target = self.point_clouds[self.current_target_idx]
        new_source = self.point_clouds[self.current_source_idx]

        new_target.paint_uniform_color([0.5, 0.5, 0.5])  # 灰色
        new_source.paint_uniform_color([0, 0, 1])  # 蓝色

        self._scene.scene.remove_geometry("Source")
        self._scene.scene.remove_geometry("Target")
        self._scene.scene.add_geometry("Target", new_target, self.material)
        self._scene.scene.add_geometry("Source", new_source, self.material)
        self._scene.setup_camera(5.0, self._scene.scene.bounding_box, self._scene.scene.bounding_box.get_center())
        self._update_status_panel()
        print(f"Switched target to {self.current_target_idx} and source to {self.current_source_idx}")


    def _on_translation_step_changed(self, value):
        self.translation_step = value / 10000
        print(f"Translation step set to {self.translation_step}")

    def _on_rotation_step_changed(self, value):
        self.rotation_step = value / 1000
        print(f"Rotation step set to {self.rotation_step}")

    def _on_start_registration(self):
        if self.is_processing:
            self._show_warning_dialog("Registration is already in progress.")
            return
        
        if len(self.point_clouds) < 2:
            self._show_warning_dialog("Please load at least two point clouds.")
            return

        self.is_processing = True
        print("Starting registration...")
        threading.Thread(target=self._run_registration).start()

    def _run_registration(self):
        try:
            source = self.point_clouds[self.current_source_idx]
            target = self.point_clouds[self.current_target_idx]

            voxel_size = 0.05  # 可以根据你的数据调整体素大小
            source_down, source_fpfh = self._preprocess_point_cloud(source, voxel_size)
            target_down, target_fpfh = self._preprocess_point_cloud(target, voxel_size)

            result_ransac = self._execute_global_registration(source_down, target_down, source_fpfh, target_fpfh, voxel_size)
            result_icp = self._refine_registration(source, target, voxel_size, result_ransac)

            self.undo_stack.append(copy.deepcopy(self.point_clouds[self.current_source_idx]))  # 保存当前状态
            self.redo_stack.clear()  # 清空重做堆栈

            source.transform(result_icp.transformation)
            self._update_geometry()

        except Exception as e:
            self._show_warning_dialog(f"Registration failed: {e}")

        finally:
            self.is_processing = False

    def _preprocess_point_cloud(self, pcd, voxel_size):
        pcd_down = pcd.voxel_down_sample(voxel_size)
        pcd_down.estimate_normals(
            o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2.0, max_nn=30))
        pcd_fpfh = o3d.pipelines.registration.compute_fpfh_feature(
            pcd_down,
            o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 5.0, max_nn=100))
        return pcd_down, pcd_fpfh

    def _execute_global_registration(self, source_down, target_down, source_fpfh, target_fpfh, voxel_size):
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

    def _refine_registration(self, source, target, voxel_size, result_ransac):
        source.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2.0, max_nn=30))
        target.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2.0, max_nn=30))
        distance_threshold = voxel_size * 0.4
        result = o3d.pipelines.registration.registration_icp(
            source, target, distance_threshold, result_ransac.transformation,
            o3d.pipelines.registration.TransformationEstimationPointToPlane())
        return result

    def _update_geometry(self):
        self._scene.scene.remove_geometry("Source")
        self._scene.scene.add_geometry("Source", self.point_clouds[self.current_source_idx], self.material)
        self._scene.force_redraw()

    def _on_undo(self):
        if not self.undo_stack:
            self._show_warning_dialog("No actions to undo.")
            return

        self.redo_stack.append(copy.deepcopy(self.point_clouds[self.current_source_idx]))  # 保存当前状态
        last_state = self.undo_stack.pop()  # 获取上一个状态
        self.point_clouds[self.current_source_idx] = last_state

        self._scene.scene.remove_geometry("Source")
        self._scene.scene.add_geometry("Source", self.point_clouds[self.current_source_idx], self.material)
        self._scene.force_redraw()

    def _on_redo(self):
        if not self.redo_stack:
            self._show_warning_dialog("No actions to redo.")
            return

        self.undo_stack.append(copy.deepcopy(self.point_clouds[self.current_source_idx]))  # 保存当前状态
        next_state = self.redo_stack.pop()  # 获取下一个状态
        self.point_clouds[self.current_source_idx] = next_state

        self._scene.scene.remove_geometry("Source")
        self._scene.scene.add_geometry("Source", self.point_clouds[self.current_source_idx], self.material)
        self._scene.force_redraw()

    def _on_toggle_source_visibility(self, is_checked):
        if self.current_source_idx >= len(self.point_clouds):
            self._show_warning_dialog("No source point cloud loaded.")
            self._chk_source_visible.checked = False
            return

        self.source_hidden = not is_checked
        if is_checked:
            self._scene.scene.add_geometry("Source", self.point_clouds[self.current_source_idx], self.material)
        else:
            self._scene.scene.remove_geometry("Source")
        self._scene.force_redraw()

    def _on_toggle_target_visibility(self, is_checked):
        if self.current_target_idx >= len(self.point_clouds):
            self._show_warning_dialog("No target point cloud loaded.")
            self._chk_target_visible.checked = False
            return

        self.target_hidden = not is_checked
        if is_checked:
            self._scene.scene.add_geometry("Target", self.point_clouds[self.current_target_idx], self.material)
        else:
            self._scene.scene.remove_geometry("Target")
        self._scene.force_redraw()

    def _merge_point_clouds(self):
        if len(self.point_clouds) < 2:
            self._show_warning_dialog("Please load at least two point clouds to merge.")
            return

        merged_pcd = o3d.geometry.PointCloud()
        for pcd in self.point_clouds:
            merged_pcd += pcd

        self._scene.scene.clear_geometry()
        self._scene.scene.add_geometry("Merged", merged_pcd, self.material)
        self._scene.setup_camera(5.0, self._scene.scene.bounding_box, self._scene.scene.bounding_box.get_center())
        self.merged = True
        self.undo_stack.clear()
        self.redo_stack.clear()
        print("Point clouds merged successfully")


    def _update_status_panel(self):
        self.source_label.text = f"Current Source: {self.current_source_idx if len(self.point_clouds) > 1 else 'N/A'}"
        self.target_label.text = f"Current Target: {self.current_target_idx if len(self.point_clouds) > 0 else 'N/A'}"
        self._chk_source_visible.checked = not self.source_hidden
        self._chk_target_visible.checked = not self.target_hidden

def main():
    gui.Application.instance.initialize()
    w = AppWindow(1024, 768)
    gui.Application.instance.run()

if __name__ == "__main__":
    main()
