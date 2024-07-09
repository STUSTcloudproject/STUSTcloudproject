import open3d as o3d
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering
import numpy as np
import platform
import threading
import queue

isMacOS = (platform.system() == "Darwin")

def erase_points_process(x, y, radius, points, view_matrix, proj_matrix, frame_width, frame_height, result_queue):
    screen_points = np.zeros((points.shape[0], 2))

    for i, point in enumerate(points):
        screen_points[i] = world_to_screen(point, view_matrix, proj_matrix, frame_width, frame_height)

    distances = np.linalg.norm(screen_points - np.array([x, y]), axis=1)
    mask = distances > radius
    new_points = points[mask]

    result_queue.put(new_points)

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
        self.point_cloud_loaded = False

        self.is_erasing = False
        self.erase_radius = 10
        self.erase_mode = False
        self.last_mouse_pos = [0, 0]

        self._setup_menu_bar()
        self._setup_settings_panel()

        self.window.set_on_layout(self._on_layout)
        self._scene.set_on_mouse(self._on_mouse_event)

        self.view_ctrls.visible = True
        self.point_cloud_ctrls.visible = True
        self._settings_panel.visible = True
        gui.Application.instance.menubar.set_checked(AppWindow.MENU_SHOW_SETTINGS, self.view_ctrls.visible)

        self.generate_random_point_cloud()
        self.erase_queue = queue.Queue()

        self.eraser_thread = None

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
        grid = gui.VGrid(2, 0.25 * em)
        
        grid.add_child(gui.Label("BG Color"))
        self._bg_color = gui.ColorEdit()
        self._bg_color.color_value = gui.Color(1, 1, 1)
        self._bg_color.set_on_value_changed(self._on_bg_color_changed)
        grid.add_child(self._bg_color)

        self.view_ctrls.add_child(grid)

    def _setup_point_cloud_controls(self):
        em = self.window.theme.font_size
        vgrid = gui.VGrid(2, 0.25 * em)
        
        self._erase_mode_checkbox = gui.Checkbox("Eraser mode")
        self._erase_mode_checkbox.set_on_checked(self._on_erase_mode_changed)
        vgrid.add_child(self._erase_mode_checkbox)

        # Add an empty label or space for new line
        vgrid.add_child(gui.Label(""))

        vgrid.add_child(gui.Label("Eraser size"))
        self._erase_size_slider = gui.Slider(gui.Slider.DOUBLE)
        self._erase_size_slider.set_limits(5, 50)
        self._erase_size_slider.double_value = self.erase_radius
        self._erase_size_slider.set_on_value_changed(self._on_erase_size_changed)
        vgrid.add_child(self._erase_size_slider)

        self.point_cloud_ctrls.add_child(vgrid)


    def _on_erase_mode_changed(self, is_checked):
        self.erase_mode = is_checked
        if self.erase_mode:
            self._scene.set_view_controls(gui.SceneWidget.Controls.PICK_POINTS)
        else:
            self._scene.set_view_controls(gui.SceneWidget.Controls.ROTATE_CAMERA)
        print(f"Eraser mode set to {self.erase_mode}")

    def _on_erase_size_changed(self, value):
        self.erase_radius = value
        print(f"Eraser size set to {self.erase_radius}")

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
        self.point_cloud = o3d.geometry.PointCloud()
        self.point_cloud.points = o3d.utility.Vector3dVector(points)
        self._scene.scene.add_geometry("PointCloud", self.point_cloud, self.material)
        self.point_cloud_loaded = True
        self._scene.setup_camera(60.0, self.point_cloud.get_axis_aligned_bounding_box(), self.point_cloud.get_center())
        print("Random point cloud generated")

    def load_point_cloud(self, path):
        try:
            pcd = o3d.io.read_point_cloud(path)
            if not pcd.has_points():
                print(f"Failed to load point cloud from {path}. Exiting.")
                return

            if self.point_cloud_loaded:
                self._scene.scene.remove_geometry("PointCloud")

            self.point_cloud = pcd
            self._scene.scene.add_geometry("PointCloud", self.point_cloud, self.material)
            self.point_cloud_loaded = True
            self._scene.setup_camera(60.0, pcd.get_axis_aligned_bounding_box(), pcd.get_center())
            print("Point cloud loaded successfully")

        except Exception as e:
            print(f"Failed to load point cloud: {e}")

    def _on_mouse_event(self, event):
        if self.erase_mode:
            if event.type == gui.MouseEvent.Type.BUTTON_DOWN and event.is_button_down(gui.MouseButton.LEFT):
                self.is_erasing = True
                self.last_mouse_pos = [event.x, event.y]
                self._erase_points(event.x, event.y)
                return gui.SceneWidget.EventCallbackResult.CONSUMED

            if event.type == gui.MouseEvent.Type.BUTTON_UP and not event.is_button_down(gui.MouseButton.LEFT):
                self.is_erasing = False
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
        view_matrix = self._scene.scene.camera.get_view_matrix()
        proj_matrix = self._scene.scene.camera.get_projection_matrix()
        frame_width = self._scene.frame.width
        frame_height = self._scene.frame.height

        if self.eraser_thread is not None and self.eraser_thread.is_alive():
            return  # Avoid starting a new thread if the previous one is still running

        self.eraser_thread = threading.Thread(target=self._erase_points_thread, args=(x, y, points, view_matrix, proj_matrix, frame_width, frame_height))
        self.eraser_thread.start()

    def _erase_points_thread(self, x, y, points, view_matrix, proj_matrix, frame_width, frame_height):
        screen_points = np.zeros((points.shape[0], 2))

        for i, point in enumerate(points):
            screen_points[i] = world_to_screen(point, view_matrix, proj_matrix, frame_width, frame_height)

        distances = np.linalg.norm(screen_points - np.array([x, y]), axis=1)
        mask = distances > self.erase_radius
        new_points = points[mask]

        self.erase_queue.put(new_points)

        # Use post_to_main_thread to update the point cloud on the main thread
        gui.Application.instance.post_to_main_thread(self.window, self._update_point_cloud_from_queue)

    def _update_point_cloud_from_queue(self):
        try:
            new_points = self.erase_queue.get_nowait()
            self._update_point_cloud(new_points)
        except queue.Empty:
            print("No result returned from erase process")

    def _update_point_cloud(self, new_points):
        self.point_cloud.points = o3d.utility.Vector3dVector(new_points)
        self._scene.scene.remove_geometry("PointCloud")
        self._scene.scene.add_geometry("PointCloud", self.point_cloud, self.material)
        self._scene.force_redraw()

def main():
    gui.Application.instance.initialize()
    w = AppWindow(1024, 768)
    gui.Application.instance.run()

if __name__ == "__main__":
    main()
