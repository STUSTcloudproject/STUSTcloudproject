import open3d as o3d
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering
import platform

isMacOS = (platform.system() == "Darwin")

class AppWindow:
    MENU_OPEN = 1   
    MENU_QUIT = 3
    MENU_SHOW_SETTINGS = 11
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

        self.material = rendering.MaterialRecord()
        self.material.shader = "defaultUnlit"
        self.point_cloud_loaded = False

        # 初始化UI組件
        self._setup_menu_bar()
        self._setup_settings_panel()

        # 設置佈局
        self.window.set_on_layout(self._on_layout)

        # 初始化時勾選所有項
        self.view_ctrls.visible = True
        self._settings_panel.visible = True

        # 更新菜單欄中的勾選狀態
        gui.Application.instance.menubar.set_checked(AppWindow.MENU_SHOW_SETTINGS, self.view_ctrls.visible)

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
            if not isMacOS:
                file_menu.add_separator()
                file_menu.add_item("Quit", AppWindow.MENU_QUIT)
            settings_menu = gui.Menu()
            settings_menu.add_item("View Controls", AppWindow.MENU_SHOW_SETTINGS)
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
        self.window.set_on_menu_item_activated(AppWindow.MENU_ABOUT, self._on_menu_about)

    def _setup_settings_panel(self):
        """
        設置設置面板
        """
        em = self.window.theme.font_size

        self._settings_panel = gui.Vert(0, gui.Margins(0.25 * em, 0.25 * em, 0.25 * em, 0.25 * em))

        # 視圖控制
        self.view_ctrls = gui.CollapsableVert("View controls", 0.25 * em, gui.Margins(em, 0, 0, 0))
        self._setup_view_controls()
        self._settings_panel.add_child(self.view_ctrls)

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

        self.view_ctrls.add_child(grid)

    def _on_layout(self, layout_context):
        """
        視窗佈局變化時觸發
        """
        r = self.window.content_rect
        self._scene.frame = r
        width = 17 * layout_context.theme.font_size
        height = min(r.height, self._settings_panel.calc_preferred_size(layout_context, gui.Widget.Constraints()).height)
        self._settings_panel.frame = gui.Rect(r.get_right() - width, r.y, width, height)

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
        self.load_point_cloud(filename)

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

    def _update_settings_panel_visibility(self):
        """
        更新設置面板的可見性
        """
        self._settings_panel.visible = self.view_ctrls.visible
        gui.Application.instance.menubar.set_checked(AppWindow.MENU_SHOW_SETTINGS, self.view_ctrls.visible)

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

    def load_point_cloud(self, path):
        """
        加載點雲文件
        參數:
        path (str): 文件路徑
        """
        try:
            pcd = o3d.io.read_point_cloud(path)
            if not pcd.has_points():
                print(f"Failed to load point cloud from {path}. Exiting.")
                return

            if self.point_cloud_loaded:
                self._scene.scene.remove_geometry("PointCloud")

            self._scene.scene.add_geometry("PointCloud", pcd, self.material)
            self.point_cloud_loaded = True
            self._scene.setup_camera(60.0, pcd.get_axis_aligned_bounding_box(), pcd.get_center())
            print("Point cloud loaded successfully")

        except Exception as e:
            print(f"Failed to load point cloud: {e}")

def main():
    gui.Application.instance.initialize()
    w = AppWindow(1024, 768)
    gui.Application.instance.run()

if __name__ == "__main__":
    main()
