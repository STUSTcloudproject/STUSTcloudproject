# main.py

import open3d as o3d
import numpy as np
import threading
import copy
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering
import platform
import time


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
        """
        初始化應用視窗
        參數:
        width (int): 視窗寬度
        height (int): 視窗高度
        """
        self.window = gui.Application.instance.create_window("Open3D", width, height)
        self._scene = gui.SceneWidget()
        self._scene.scene = rendering.Open3DScene(self.window.renderer)
        self._scene.scene.set_background([1, 1, 1, 1])  # 設置背景為白色
        self.window.add_child(self._scene)

        # 默認平移和旋轉步長
        self.translation_step = 0.0002
        self.rotation_step = 0.002

        self.source_hidden = False
        self.target_hidden = False

        # 點雲文件容器
        self.point_clouds = []
        self.current_target_idx = 0
        self.current_source_idx = 1

        # 撤銷和重做堆疊
        self.undo_stack = []
        self.redo_stack = []

        self.point_cloud_colors = []
        self.show_original_colors = False

        # 合併標誌
        self.merged = False

        self.merged_pcd = None

        # 初始化UI組件
        self._setup_menu_bar()
        self._setup_settings_panel()
        self._setup_status_panel()

        # 設置佈局
        self.window.set_on_layout(self._on_layout)

        self.material = rendering.MaterialRecord()
        self.material.shader = "defaultUnlit"
        self.point_cloud_loaded = False

        # 初始化時勾選所有項
        self.view_ctrls.visible = True
        self.function1_ctrls.visible = True
        self.function2_ctrls.visible = True
        self.status_panel.visible = True
        self._settings_panel.visible = True

        # 更新菜單欄中的勾選狀態
        gui.Application.instance.menubar.set_checked(AppWindow.MENU_SHOW_SETTINGS, self.view_ctrls.visible)
        gui.Application.instance.menubar.set_checked(AppWindow.MENU_FUNCTION1, self.function1_ctrls.visible)
        gui.Application.instance.menubar.set_checked(AppWindow.MENU_FUNCTION2, self.function2_ctrls.visible)
        gui.Application.instance.menubar.set_checked(AppWindow.MENU_STATUS_PANEL, self.status_panel.visible)

        # 註冊鍵盤事件
        self.window.set_on_key(self._on_key)

        # 添加鎖以避免連續觸發
        self.lock = threading.Lock()
        self.is_processing = False

    def _setup_menu_bar(self):
        """
        設置菜單欄
        """
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
        """
        設置設置面板
        """
        em = self.window.theme.font_size
        separation_height = int(round(0.5 * em))

        self._settings_panel = gui.Vert(0, gui.Margins(0.25 * em, 0.25 * em, 0.25 * em, 0.25 * em))

        # 視圖控制
        self.view_ctrls = gui.CollapsableVert("View controls", 0.25 * em, gui.Margins(em, 0, 0, 0))
        self._setup_view_controls()
        self._settings_panel.add_child(self.view_ctrls)

        # 功能1控制
        self.function1_ctrls = gui.CollapsableVert("Function 1 Controls", 0.25 * em, gui.Margins(em, 0, 0, 0))
        self._setup_function1_controls()
        self._settings_panel.add_child(self.function1_ctrls)

        # 功能2控制
        self.function2_ctrls = gui.CollapsableVert("Function 2 Controls", 0.25 * em, gui.Margins(em, 0, 0, 0))
        self.function2_ctrls.add_child(gui.Label("Function 2 specific settings"))
        self._settings_panel.add_child(self.function2_ctrls)

        self.window.add_child(self._settings_panel)

    def _setup_view_controls(self):
        """
        設置視圖控制組件
        """
        em = self.window.theme.font_size
        grid = gui.VGrid(2, 0.25 * em)
        
        grid.add_child(gui.Label("BG Color"))
        self._bg_color = gui.ColorEdit()
        self._bg_color.color_value = gui.Color(1, 1, 1)  # 設置默認顏色為白色
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

        self._btn_reset_camera = gui.Button("Reset Camera (C)")
        self._btn_reset_camera.set_on_clicked(self._reset_camera_view)
        self.view_ctrls.add_child(self._btn_reset_camera)


    def _setup_function1_controls(self):
        """
        設置功能1控制組件
        """
        self.function1_ctrls.add_child(gui.Label("Function 1 specific settings"))

        self._btn_next_source = gui.Button("Next Source (N)")
        self._btn_next_source.set_on_clicked(self._switch_source)
        self.function1_ctrls.add_child(self._btn_next_source)

        self._btn_switch_target = gui.Button("Switch Target (B)")
        self._btn_switch_target.set_on_clicked(self._switch_target)
        self.function1_ctrls.add_child(self._btn_switch_target)

        self._setup_translation_rotation_sliders()

        self._btn_start_registration = gui.Button("Start Registration (R)")
        self._btn_start_registration.set_on_clicked(self._on_start_registration)
        self.function1_ctrls.add_child(self._btn_start_registration)

        self._btn_undo = gui.Button("Undo (Z)")
        self._btn_undo.set_on_clicked(self._on_undo)
        self.function1_ctrls.add_child(self._btn_undo)

        self._btn_redo = gui.Button("Redo (Y)")
        self._btn_redo.set_on_clicked(self._on_redo)
        self.function1_ctrls.add_child(self._btn_redo)

        self._btn_merge = gui.Button("Merge Point Clouds (M)")
        self._btn_merge.set_on_clicked(self._merge_point_clouds)
        self.function1_ctrls.add_child(self._btn_merge)

        self._btn_cancel_merge = gui.Button("Cancel Merge (P)")
        self._btn_cancel_merge.set_on_clicked(self._cancel_merge)
        self.function1_ctrls.add_child(self._btn_cancel_merge)

        self._btn_export_merged_point_cloud = gui.Button("Export Merged Point Cloud (X)")
        self._btn_export_merged_point_cloud.set_on_clicked(self._export_merged_point_cloud)
        self.function1_ctrls.add_child(self._btn_export_merged_point_cloud)

    def _setup_translation_rotation_sliders(self):
        """
        設置平移和旋轉步長滑動條
        """
        self._translation_step_slider = gui.Slider(gui.Slider.DOUBLE)
        self._translation_step_slider.set_limits(0.1, 30.0)
        self._translation_step_slider.double_value = 15  # 設置默認值為 15
        self.translation_step = 15 / 10000  # 根據比例調整平移步長
        self._translation_step_slider.set_on_value_changed(self._on_translation_step_changed)
        self.function1_ctrls.add_child(gui.Label("Translation Step"))
        self.function1_ctrls.add_child(self._translation_step_slider)

        self._rotation_step_slider = gui.Slider(gui.Slider.DOUBLE)
        self._rotation_step_slider.set_limits(0.1, 30.0)
        self._rotation_step_slider.double_value = 15  # 設置默認值為 15
        self.rotation_step = 15 / 1000  # 根據比例調整旋轉步長
        self._rotation_step_slider.set_on_value_changed(self._on_rotation_step_changed)
        self.function1_ctrls.add_child(gui.Label("Rotation Step"))
        self.function1_ctrls.add_child(self._rotation_step_slider)

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

        self._chk_show_original_colors = gui.Checkbox("Show Original Colors")
        self._chk_show_original_colors.checked = self.show_original_colors
        self._chk_show_original_colors.set_on_checked(self._on_toggle_show_original_colors)
        self.status_panel.add_child(self._chk_show_original_colors)

        self.window.add_child(self.status_panel)

    def _on_toggle_show_original_colors(self, is_checked):
        self.show_original_colors = is_checked
        self._update_point_cloud_colors()

    def _update_point_cloud_colors(self):
        print("Updating point cloud colors...")
        
        for idx, pcd in enumerate(self.point_clouds):
            if self.show_original_colors:
                print(f"Applying original colors to point cloud {idx}")
                original_colors = self.point_cloud_colors[idx]
                print(f"Original colors for point cloud {idx}: {original_colors[:5]}")  # 打印前5個顏色作為示例
                pcd.colors = o3d.utility.Vector3dVector(original_colors)
            else:
                if idx == self.current_target_idx:
                    print(f"Applying gray color to point cloud {idx}")
                    pcd.paint_uniform_color([0.5, 0.5, 0.5])  # 灰色
                else:
                    print(f"Applying blue color to point cloud {idx}")
                    pcd.paint_uniform_color([0, 0, 1])  # 藍色

        # 如果在合併模式下，需要重新合併所有點雲到 merged_pcd
        if self.merged:
            self.merged_pcd = o3d.geometry.PointCloud()
            for pcd in self.point_clouds:
                self.merged_pcd += pcd
            self._scene.scene.clear_geometry()
            self._scene.scene.add_geometry("Merged", self.merged_pcd, self.material)
        else:
            # 非合併模式下，分別更新 Source 和 Target
            if self.current_source_idx < len(self.point_clouds):
                source_pcd = self.point_clouds[self.current_source_idx]
                self._scene.scene.remove_geometry("Source")
                self._scene.scene.add_geometry("Source", source_pcd, self.material)

            if self.current_target_idx < len(self.point_clouds):
                target_pcd = self.point_clouds[self.current_target_idx]
                self._scene.scene.remove_geometry("Target")
                self._scene.scene.add_geometry("Target", target_pcd, self.material)

        self._scene.force_redraw()
        print("Point cloud colors updated")


    def _on_layout(self, layout_context):
        """
        視窗佈局變化時觸發
        """
        r = self.window.content_rect
        self._scene.frame = r
        width = 17 * layout_context.theme.font_size
        height = min(r.height, self._settings_panel.calc_preferred_size(layout_context, gui.Widget.Constraints()).height)
        self._settings_panel.frame = gui.Rect(r.get_right() - width, r.y, width, height)

        status_panel_width = 20 * layout_context.theme.font_size
        status_panel_height = self.status_panel.calc_preferred_size(layout_context, gui.Widget.Constraints()).height
        self.status_panel.frame = gui.Rect(r.x, r.get_bottom() - status_panel_height, status_panel_width, status_panel_height)

    def _on_menu_open(self):
        """
        點擊菜單中的“Open”選項時觸發
        """
        dlg = gui.FileDialog(gui.FileDialog.OPEN, "Choose file to load", self.window.theme)
        dlg.add_filter(".xyz .xyzn .xyzrgb .ply .pcd .pts", "Point cloud files (.xyz, .xyzn, .xyzrgb, .ply, .pcd, .pts)")
        dlg.add_filter("", "All files")
        dlg.set_on_cancel(self._on_file_dialog_cancel)
        dlg.set_on_done(self._on_load_dialog_done)
        self.window.show_dialog(dlg)

    def _on_file_dialog_cancel(self):
        """
        點擊文件選擇對話框中的取消按鈕時觸發
        """
        self.window.close_dialog()

    def _on_load_dialog_done(self, filename):
        """
        完成文件選擇時觸發
        參數:
        filename (str): 選擇的文件名
        """
        self.window.close_dialog()
        self.load(filename)

    def _on_menu_export(self):
        """
        點擊菜單中的“Export”選項時觸發
        """
        pass

    def _on_menu_quit(self):
        """
        點擊菜單中的“Quit”選項時觸發
        """
        gui.Application.instance.quit()

    def _on_menu_toggle_view_controls(self):
        """
        點擊菜單中的“View Controls”選項時觸發
        """
        self.view_ctrls.visible = not self.view_ctrls.visible
        self._update_settings_panel_visibility()

    def _on_menu_toggle_function1(self):
        """
        點擊菜單中的“Function 1”選項時觸發
        """
        self.function1_ctrls.visible = not self.function1_ctrls.visible
        self._update_settings_panel_visibility()

    def _on_menu_toggle_function2(self):
        """
        點擊菜單中的“Function 2”選項時觸發
        """
        self.function2_ctrls.visible = not self.function2_ctrls.visible
        self._update_settings_panel_visibility()

    def _on_menu_toggle_status_panel(self):
        """
        點擊菜單中的“Status Panel”選項時觸發
        """
        self.status_panel.visible = not self.status_panel.visible
        self._update_settings_panel_visibility()

    def _update_settings_panel_visibility(self):
        """
        更新設置面板的可見性
        """
        any_visible = self.view_ctrls.visible or self.function1_ctrls.visible or self.function2_ctrls.visible or self.status_panel.visible
        self._settings_panel.visible = any_visible

        gui.Application.instance.menubar.set_checked(AppWindow.MENU_SHOW_SETTINGS, self.view_ctrls.visible)
        gui.Application.instance.menubar.set_checked(AppWindow.MENU_FUNCTION1, self.function1_ctrls.visible)
        gui.Application.instance.menubar.set_checked(AppWindow.MENU_FUNCTION2, self.function2_ctrls.visible)
        gui.Application.instance.menubar.set_checked(AppWindow.MENU_STATUS_PANEL, self.status_panel.visible)

        # 強制佈局更新
        self.window.set_needs_layout()

    def _on_menu_about(self):
        """
        點擊菜單中的“About”選項時觸發
        """
        pass

    def _on_bg_color_changed(self, color):
        """
        更改背景顏色時觸發
        參數:
        color (gui.Color): 新的顏色
        """
        self._scene.scene.set_background([color.red, color.green, color.blue, color.alpha])

    def _on_pc_color_mode_changed(self, text, index):
        """
        更改點雲顏色模式時觸發
        參數:
        text (str): 選擇的顏色模式
        index (int): 選擇的索引
        """
        print(f"Color mode changed: {text}")

        if not self.point_cloud_loaded:
            self._show_warning_dialog("Please load a point cloud file first.")
            self._pc_color_mode.selected_index = 0  # 重置為“Original”
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
        """
        更改點雲顏色時觸發
        參數:
        color (gui.Color): 新的顏色
        """
        if not self.point_cloud_loaded:
            self._show_warning_dialog("Please load a point cloud file first.")
            return

        if self._pc_color_mode.selected_text == "Custom":
            self.material.base_color = [color.red, color.green, color.blue, color.alpha]
            self._update_point_cloud_color()

    def _update_point_cloud_color(self):
        """
        更新點雲顏色
        """
        if self.point_cloud_loaded:
            if self.material.shader == "defaultLit":
                self.material.base_color = [
                    self._pc_color.color_value.red,
                    self._pc_color.color_value.green,
                    self._pc_color.color_value.blue,
                    self._pc_color.color_value.alpha,
                ]

            if self.current_source_idx < len(self.point_clouds):
                self._scene.scene.remove_geometry("Source")
                self._scene.scene.add_geometry("Source", self.point_clouds[self.current_source_idx], self.material)

            if self.current_target_idx < len(self.point_clouds):
                self._scene.scene.remove_geometry("Target")
                self._scene.scene.add_geometry("Target", self.point_clouds[self.current_target_idx], self.material)

            self._scene.force_redraw()
            print("Point cloud color updated")


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

    def load(self, path):
        try:
            pcd = o3d.io.read_point_cloud(path)
            if not pcd.has_points():
                print(f"Failed to load point cloud from {path}. Exiting.")
                return
            
            # 保存原始顏色，如果沒有則設置為灰色
            if pcd.has_colors():
                print("Point cloud has colors")
                colors = np.asarray(pcd.colors)
                print(f"Loaded colors: {colors[:5]}")  # 打印前5個顏色作為示例
                self.point_cloud_colors.append(colors.copy())  # 保存颜色的副本
            else:
                print("Point cloud does not have colors")
                self.point_cloud_colors.append(np.full((len(pcd.points), 3), [0.5, 0.5, 0.5]))

            is_first_load = len(self.point_clouds) == 0

            if is_first_load:
                self.point_clouds.append(pcd)
                if not self.show_original_colors:
                    pcd.paint_uniform_color([0.5, 0.5, 0.5])
                self.current_target_idx = 0
                self._scene.scene.add_geometry("Target", pcd, self.material)
            elif len(self.point_clouds) == 1:
                self.point_clouds.append(pcd)
                if not self.show_original_colors:
                    pcd.paint_uniform_color([0, 0, 1])
                self.current_source_idx = 1
                self._scene.scene.add_geometry("Source", pcd, self.material)
            else:
                self.point_clouds.append(pcd)

            self.point_cloud_loaded = True
            self._update_status_panel()
            print("Point cloud loaded successfully")

            original_colors = self.point_cloud_colors[-1]  # 改为读取最新加入的点云颜色
            print(f"Original colors: {original_colors[:5]}")  # 打印前5個顏色作為示例

            if is_first_load:
                self._reset_camera_view()

        except Exception as e:
            print(f"Failed to load point cloud: {e}")


    def _on_key(self, event):
        """
        鍵盤事件處理
        參數:
        event (gui.KeyEvent): 鍵盤事件
        """
        if event.type == gui.KeyEvent.DOWN:
            with self.lock:
                if self.is_processing:
                    return
                if event.key == gui.KeyName.N:
                    self._switch_source()
                elif event.key == gui.KeyName.B:
                    self._switch_target()
                elif event.key == gui.KeyName.W:
                    self._translate_point_cloud([0, self.translation_step, 0])  # 平移步長縮放 100 倍
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
                    self._rotate_point_cloud([self.rotation_step, 0, 0])  # 旋轉步長縮放 100 倍
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
                elif event.key == gui.KeyName.C:
                    self._reset_camera_view()
                elif event.key == gui.KeyName.P:
                    self._cancel_merge()
                elif event.key == gui.KeyName.X:  # 新的导出快捷键
                    self._export_merged_point_cloud()

    def _cancel_merge(self):
        """
        取消合併模式，恢復 Source 和 Target
        """
        if not self.merged:
            self._show_warning_dialog("Not in merged mode.")
            return

        self._scene.scene.remove_geometry("Merged")
        self.merged = False

        # 恢復 Source 和 Target
        if self.current_source_idx < len(self.point_clouds):
            source_pcd = self.point_clouds[self.current_source_idx]
            self._scene.scene.add_geometry("Source", source_pcd, self.material)
        if self.current_target_idx < len(self.point_clouds):
            target_pcd = self.point_clouds[self.current_target_idx]
            self._scene.scene.add_geometry("Target", target_pcd, self.material)

        self.undo_stack.clear()
        self.redo_stack.clear()

        self._update_status_panel()
        print("Cancelled merge mode, restored Source and Target.")


    def _reset_camera_view(self):
        """
        重設相機視角
        """
        self._scene.setup_camera(60.0, self._scene.scene.bounding_box, self._scene.scene.bounding_box.get_center())


    def _translate_point_cloud(self, translation):
        """
        平移點雲
        參數:
        translation (list): 平移向量
        """

        if self.merged:
            self._show_warning_dialog("Cannot translate in merged mode. Press 'P' to exit merged mode.")
            return

        if self.current_source_idx >= len(self.point_clouds):
            self._show_warning_dialog("Please load a source point cloud first.")
            return

        self.undo_stack.append(copy.deepcopy(self.point_clouds[self.current_source_idx]))  # 保存當前狀態
        self.redo_stack.clear()  # 清空重做堆疊

        source_pcd = self.point_clouds[self.current_source_idx]
        source_pcd.translate(translation)
        self._scene.scene.remove_geometry("Source")
        self._scene.scene.add_geometry("Source", source_pcd, self.material)
        self._scene.force_redraw()

    def _rotate_point_cloud(self, rotation):
        """
        旋轉點雲
        參數:
        rotation (list): 旋轉向量
        """

        if self.merged:
            self._show_warning_dialog("Cannot rotate in merged mode. Press 'P' to exit merged mode.")
            return

        if self.current_source_idx >= len(self.point_clouds):
            self._show_warning_dialog("Please load a source point cloud first.")
            return

        self.undo_stack.append(copy.deepcopy(self.point_clouds[self.current_source_idx]))  # 保存當前狀態
        self.redo_stack.clear()  # 清空重做堆疊

        source_pcd = self.point_clouds[self.current_source_idx]
        R = source_pcd.get_rotation_matrix_from_xyz(rotation)
        source_pcd.rotate(R, center=source_pcd.get_center())
        self._scene.scene.remove_geometry("Source")
        self._scene.scene.add_geometry("Source", source_pcd, self.material)
        self._scene.force_redraw()

    def _switch_source(self):
        if self.merged:
            self._show_warning_dialog("Cannot switch source in merged mode. Press 'P' to exit merged mode.")
            return

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
        if self.show_original_colors:
            new_source.colors = o3d.utility.Vector3dVector(self.point_cloud_colors[self.current_source_idx])
        else:
            new_source.paint_uniform_color([0, 0, 1])  # 藍色
        self._scene.scene.remove_geometry("Source")
        self._scene.scene.add_geometry("Source", new_source, self.material)

        if not self.target_hidden:
            new_target = self.point_clouds[self.current_target_idx]
            if self.show_original_colors:
                new_target.colors = o3d.utility.Vector3dVector(self.point_cloud_colors[self.current_target_idx])
            else:
                new_target.paint_uniform_color([0.5, 0.5, 0.5])  # 灰色
            self._scene.scene.add_geometry("Target", new_target, self.material)

        self._update_status_panel()
        print(f"Switched to source {self.current_source_idx}")

    def _switch_target(self):
        if self.merged:
            self._show_warning_dialog("Cannot switch target in merged mode. Press 'P' to exit merged mode.")
            return

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

        if self.show_original_colors:
            new_target.colors = o3d.utility.Vector3dVector(self.point_cloud_colors[self.current_target_idx])
            new_source.colors = o3d.utility.Vector3dVector(self.point_cloud_colors[self.current_source_idx])
        else:
            new_target.paint_uniform_color([0.5, 0.5, 0.5])  # 灰色
            new_source.paint_uniform_color([0, 0, 1])  # 藍色

        self._scene.scene.remove_geometry("Source")
        self._scene.scene.remove_geometry("Target")
        self._scene.scene.add_geometry("Target", new_target, self.material)
        self._scene.scene.add_geometry("Source", new_source, self.material)
        self._update_status_panel()
        print(f"Switched target to {self.current_target_idx} and source to {self.current_source_idx}")



    def _on_translation_step_changed(self, value):
        """
        更改平移步長時觸發
        參數:
        value (float): 新的平移步長
        """
        self.translation_step = value / 10000
        print(f"Translation step set to {self.translation_step}")

    def _on_rotation_step_changed(self, value):
        """
        更改旋轉步長時觸發
        參數:
        value (float): 新的旋轉步長
        """
        self.rotation_step = value / 1000
        print(f"Rotation step set to {self.rotation_step}")

    def _on_start_registration(self):
        """
        開始點雲配準時觸發
        """

        if self.merged:
            self._show_warning_dialog("Cannot start registration in merged mode. Press 'P' to exit merged mode.")
            return

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
        """
        執行點雲配準
        """
        try:
            source = self.point_clouds[self.current_source_idx]
            target = self.point_clouds[self.current_target_idx]

            voxel_size = 0.05  # 可以根據你的數據調整體素大小
            source_down, source_fpfh = self._preprocess_point_cloud(source, voxel_size)
            target_down, target_fpfh = self._preprocess_point_cloud(target, voxel_size)

            result_ransac = self._execute_global_registration(source_down, target_down, source_fpfh, target_fpfh, voxel_size)
            result_icp = self._refine_registration(source, target, voxel_size, result_ransac)

            self.undo_stack.append(copy.deepcopy(self.point_clouds[self.current_source_idx]))  # 保存當前狀態
            self.redo_stack.clear()  # 清空重做堆疊

            source.transform(result_icp.transformation)
            self._update_geometry()

        except Exception as e:
            self._show_warning_dialog(f"Registration failed: {e}")

        finally:
            self.is_processing = False

    def _preprocess_point_cloud(self, pcd, voxel_size):
        """
        預處理點雲
        參數:
        pcd (open3d.geometry.PointCloud): 點雲對象
        voxel_size (float): 體素大小
        返回:
        pcd_down (open3d.geometry.PointCloud): 降採樣後的點雲
        pcd_fpfh (open3d.pipelines.registration.Feature): FPFH特徵
        """
        pcd_down = pcd.voxel_down_sample(voxel_size)
        pcd_down.estimate_normals(
            o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2.0, max_nn=30))
        pcd_fpfh = o3d.pipelines.registration.compute_fpfh_feature(
            pcd_down,
            o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 5.0, max_nn=100))
        return pcd_down, pcd_fpfh

    def _execute_global_registration(self, source_down, target_down, source_fpfh, target_fpfh, voxel_size):
        """
        執行全局配準
        參數:
        source_down (open3d.geometry.PointCloud): 降採樣後的源點雲
        target_down (open3d.geometry.PointCloud): 降採樣後的目標點雲
        source_fpfh (open3d.pipelines.registration.Feature): 源點雲的FPFH特徵
        target_fpfh (open3d.pipelines.registration.Feature): 目標點雲的FPFH特徵
        voxel_size (float): 體素大小
        返回:
        result (open3d.pipelines.registration.RegistrationResult): 配準結果
        """
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
        """
        精細配準
        參數:
        source (open3d.geometry.PointCloud): 源點雲
        target (open3d.geometry.PointCloud): 目標點雲
        voxel_size (float): 體素大小
        result_ransac (open3d.pipelines.registration.RegistrationResult): 初步配準結果
        返回:
        result (open3d.pipelines.registration.RegistrationResult): 精細配準結果
        """
        source.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2.0, max_nn=30))
        target.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2.0, max_nn=30))
        distance_threshold = voxel_size * 0.4
        result = o3d.pipelines.registration.registration_icp(
            source, target, distance_threshold, result_ransac.transformation,
            o3d.pipelines.registration.TransformationEstimationPointToPlane())
        return result

    def _update_geometry(self):
        """
        更新幾何對象
        """
        self._scene.scene.remove_geometry("Source")
        self._scene.scene.add_geometry("Source", self.point_clouds[self.current_source_idx], self.material)
        self._scene.force_redraw()

    def _on_undo(self):
        """
        撤銷操作
        """

        if self.merged:
            self._show_warning_dialog("Cannot undo in merged mode. Press 'P' to exit merged mode.")
            return

        if not self.undo_stack:
            self._show_warning_dialog("No actions to undo.")
            return

        self.redo_stack.append(copy.deepcopy(self.point_clouds[self.current_source_idx]))  # 保存當前狀態
        last_state = self.undo_stack.pop()  # 獲取上一個狀態
        self.point_clouds[self.current_source_idx] = last_state

        self._update_point_cloud_colors()

        self._scene.scene.remove_geometry("Source")
        self._scene.scene.add_geometry("Source", self.point_clouds[self.current_source_idx], self.material)
        self._scene.force_redraw()

    def _on_redo(self):
        """
        重做操作
        """

        if self.merged:
            self._show_warning_dialog("Cannot redo in merged mode. Press 'P' to exit merged mode.")
            return

        if not self.redo_stack:
            self._show_warning_dialog("No actions to redo.")
            return

        self.undo_stack.append(copy.deepcopy(self.point_clouds[self.current_source_idx]))  # 保存當前狀態
        next_state = self.redo_stack.pop()  # 獲取下一個狀態
        self.point_clouds[self.current_source_idx] = next_state
        
        self._update_point_cloud_colors()

        self._scene.scene.remove_geometry("Source")
        self._scene.scene.add_geometry("Source", self.point_clouds[self.current_source_idx], self.material)
        self._scene.force_redraw()

    def _on_toggle_source_visibility(self, is_checked):
        """
        切換源點雲可見性
        參數:
        is_checked (bool): 源點雲是否可見
        """
        
        if self.merged:
            self._show_warning_dialog("Cannot toggle source visibility in merged mode. Press 'P' to exit merged mode.")
            return

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
        """
        切換目標點雲可見性
        參數:
        is_checked (bool): 目標點雲是否可見
        """

        if self.merged:
            self._show_warning_dialog("Cannot toggle target visibility in merged mode. Press 'P' to exit merged mode.")
            return

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
        """
        合併所有點雲
        """

        if self.merged:
            self._show_warning_dialog("Cannot translate in merged mode. Press 'P' to exit merged mode.")
            return

        if len(self.point_clouds) < 2:
            self._show_warning_dialog("Please load at least two point clouds to merge.")
            return

        if not self._chk_source_visible.checked:
            self._chk_source_visible.checked = True
            self._on_toggle_source_visibility(True)
        
        if not self._chk_target_visible.checked:
            self._chk_target_visible.checked = True
            self._on_toggle_target_visibility(True)

        merged_pcd = o3d.geometry.PointCloud()
        for pcd in self.point_clouds:
            merged_pcd += pcd

        self._scene.scene.clear_geometry()
        self._scene.scene.add_geometry("Merged", merged_pcd, self.material)
        #self._scene.setup_camera(60.0, self._scene.scene.bounding_box, self._scene.scene.bounding_box.get_center())
        self.merged_pcd = merged_pcd
        self.merged = True
        self.undo_stack.clear()
        self.redo_stack.clear()
        print("Point clouds merged successfully")

    def _export_merged_point_cloud(self):
        """
        导出合并后的点云
        """
        if self.merged_pcd is None:
            self._show_warning_dialog("No merged point cloud available for export.")
            return
        
        dlg = gui.FileDialog(gui.FileDialog.SAVE, "Choose file to save", self.window.theme)
        dlg.add_filter(".ply", "PLY files (.ply)")
        dlg.set_on_cancel(self._on_file_dialog_cancel)
        dlg.set_on_done(self._on_save_dialog_done)
        self.window.show_dialog(dlg)

    def _on_save_dialog_done(self, filename):
        """
        完成文件保存选择时触发
        參數:
        filename (str): 选择的文件名
        """
        self.window.close_dialog()
        if self.merged_pcd is None:
            self._show_warning_dialog("No merged point cloud available for export.")
            return
        
        try:
            o3d.io.write_point_cloud(filename, self.merged_pcd)
            print(f"Merged point cloud exported as {filename}")
        except Exception as e:
            self._show_warning_dialog(f"Failed to export merged point cloud: {e}")

    def _on_file_dialog_cancel(self):
        """
        點擊文件選擇對話框中的取消按鈕時觸發
        """
        self.window.close_dialog()

    def _update_status_panel(self):
        """
        更新狀態面板
        """
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
