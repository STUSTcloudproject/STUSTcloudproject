import open3d as o3d
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering
import platform
import sys
import threading
import os

isMacOS = (platform.system() == "Darwin")

class AppWindow:
    MENU_OPEN = 1
    MENU_QUIT = 3
    MENU_SHOW_SETTINGS = 11
    MENU_ABOUT = 21

    def __init__(self, width, height):
        self.pcds = []
        self.current_index = -1
        self.imported_filenames = []

        self.window = gui.Application.instance.create_window("Open3D", width, height)
        self._scene = gui.SceneWidget()
        self._scene.scene = rendering.Open3DScene(self.window.renderer)
        self._scene.scene.set_background([1, 1, 1, 1])
        self.window.add_child(self._scene)

        self.material = rendering.MaterialRecord()
        self.material.shader = "defaultUnlit"
        self.point_cloud_loaded = False

        self._setup_menu_bar()
        self._setup_settings_panel()

        self.window.set_on_layout(self._on_layout)
        self.window.set_on_key(self._on_key_event)

        self.view_ctrls.visible = True
        self._settings_panel.visible = True

        self.refresh_view_on_mode_change = True

        gui.Application.instance.menubar.set_checked(AppWindow.MENU_SHOW_SETTINGS, self.view_ctrls.visible)

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
        em = self.window.theme.font_size
        self._settings_panel = gui.Vert(0, gui.Margins(0.25 * em, 0.25 * em, 0.25 * em, 0.25 * em))

        self.view_ctrls = gui.CollapsableVert("View controls", 0.25 * em, gui.Margins(em, 0, 0, 0))
        self._setup_view_controls()
        self._settings_panel.add_child(self.view_ctrls)

        self.label = gui.Label("No Point Cloud Loaded")
        self._settings_panel.add_child(self.label)

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

        self.view_ctrls.add_child(grid1)
        self.view_ctrls.add_child(grid2)

    def _on_refresh_view_checked(self, is_checked):
        self.refresh_view_on_mode_change = is_checked

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

    def _update_settings_panel_visibility(self):
        self._settings_panel.visible = self.view_ctrls.visible
        gui.Application.instance.menubar.set_checked(AppWindow.MENU_SHOW_SETTINGS, self.view_ctrls.visible)
        self.window.set_needs_layout()

    def _on_menu_about(self):
        pass

    def _on_bg_color_changed(self, color):
        self._scene.scene.set_background([color.red, color.green, color.blue, color.alpha])

    def load_point_cloud(self, path):
        try:
            pcd = o3d.io.read_point_cloud(path)
            if not pcd.has_points():
                print(f"Failed to load point cloud from {path}. Exiting.")
                return

            self.pcds.append(pcd)
            if len(self.pcds) == 1:
                self.show_point_cloud(0)
                if self.refresh_view_on_mode_change: 
                    self._scene.setup_camera(60.0, pcd.get_axis_aligned_bounding_box(), pcd.get_center())
            self.update_label()
            print("Point cloud loaded successfully")

        except Exception as e:
            print(f"Failed to load point cloud: {e}")

    def show_point_cloud(self, index):
        self._scene.scene.clear_geometry()
        self._scene.scene.add_geometry(f"pcd{index}", self.pcds[index], self.material)
        self.current_index = index
        self.update_label()
        if self.refresh_view_on_mode_change: 
            self._scene.setup_camera(60.0, self.pcds[index].get_axis_aligned_bounding_box(), self.pcds[index].get_center())

    def next_point_cloud(self):
        if not self.pcds:
            return
        next_index = (self.current_index + 1) % len(self.pcds)
        self.show_point_cloud(next_index)

    def delete_current_point_cloud(self):
        if not self.pcds:
            return
        del self.pcds[self.current_index]
        if self.pcds:
            self.current_index %= len(self.pcds)
            self.show_point_cloud(self.current_index)
        else:
            self._scene.scene.clear_geometry()
            self.current_index = -1
        self.update_label()

    def save_current_point_cloud(self):
        # 删除导入的文件
        for filename in self.imported_filenames:
            try:
                os.remove(filename)
                print(f"Deleted {filename}")
            except OSError as e:
                print(f"Error deleting file {filename}: {e}")

        # 清空文件名容器
        self.imported_filenames.clear()

        if not self.pcds:
            print("No point cloud to save")
            return

        # 保存所有点云
        for i, pcd in enumerate(self.pcds, start=1):
            filename = f"pc{i}.ply"
            o3d.io.write_point_cloud(filename, pcd)
            self.imported_filenames.append(filename)
            print(f"Saved {filename}")



    def _on_key_event(self, event):
        if event.type == gui.KeyEvent.Type.DOWN:
            if event.key == gui.KeyName.N:
                self.next_point_cloud()
            elif event.key == gui.KeyName.D:
                self.delete_current_point_cloud()
            elif event.key == gui.KeyName.X:
                self.save_current_point_cloud()

    def update_label(self):
        if self.pcds:
            self.label.text = f"Point Cloud {self.current_index + 1} / {len(self.pcds)}"
        else:
            self.label.text = "No Point Cloud Loaded"

    def run(self):
        def read_stdin():
            while True:
                line = sys.stdin.readline().strip()
                if line:
                    print(f"Received filename: {line}")
                    gui.Application.instance.post_to_main_thread(
                        self.window, lambda: self.load_point_cloud(line)
                    )
                    self.imported_filenames.append(line)

        threading.Thread(target=read_stdin, daemon=True).start()
        gui.Application.instance.run()

def main():
    gui.Application.instance.initialize()
    w = AppWindow(1024, 768)
    w.run()

if __name__ == "__main__":
    print("Starting Open3D Online Processing PC Visualizer")
    sys.stdout.flush()
    main()
