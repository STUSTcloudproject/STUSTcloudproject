import open3d as o3d
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering
import platform
import pymeshlab

isMacOS = (platform.system() == "Darwin")

class AppWindow:
    MENU_OPEN = 1 
    MENU_EXPORT_MERGED_POINT_CLOUD = 2  
    MENU_QUIT = 3
    MENU_SHOW_SETTINGS = 11
    MENU_ABOUT = 21
    MENU_POINT_CLOUD_OPERATIONS = 30
    MENU_DOWNSAMPLE = 31
    MENU_GENERATE_MESH = 32
    MENU_SAMPLE_POINTS = 33
    MENU_UNDO = 40
    MENU_REDO = 41

    def __init__(self, width, height):
        """
        初始化應用視窗
        參數:
        width (int): 視窗寬度
        height (int): 視窗高度
        """
        
        self.undo_stack = []
        self.redo_stack = []

        self.voxel_size = 0.001
        self.num_points = 10000

        self.depth = 8
        self.fulldepth = 5
        self.scale = 1.1
        self.samplespernode = 1.5
        self.pointweight = 4.0
        self.iters = 8
        self.threads = 16

        self.window = gui.Application.instance.create_window("Open3D", width, height)
        self._scene = gui.SceneWidget()
        self._scene.scene = rendering.Open3DScene(self.window.renderer)
        self._scene.scene.set_background([1, 1, 1, 1])  # 設置背景為白色
        self.window.add_child(self._scene)

        self.material = rendering.MaterialRecord()
        self.material.shader = "defaultUnlit"
        self.point_cloud_loaded = False

        self.loaded_pcd = None
        self.loaded_mesh = None
        
        self.show_wireframe = True

        # 初始化UI組件
        self._setup_menu_bar()
        self._setup_settings_panel()

        # 設置佈局
        self.window.set_on_layout(self._on_layout)

        # 绑定快捷键回调
        self.window.set_on_key(self._on_key)

        # 初始化時勾選所有項
        self.view_ctrls.visible = True
        self._settings_panel.visible = True

        # 更新菜單欄中的勾選狀態
        gui.Application.instance.menubar.set_checked(AppWindow.MENU_SHOW_SETTINGS, self.view_ctrls.visible)

    def _on_key(self, event):
        if event.type == gui.KeyEvent.DOWN:
            if event.key == gui.KeyName.Z:
                self._on_menu_undo()
            elif event.key == gui.KeyName.Y:
                self._on_menu_redo()
            elif event.key == gui.KeyName.X:
                self._export_merged_point_cloud()

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
            file_menu.add_item("Export Merged Point Cloud\tX", AppWindow.MENU_EXPORT_MERGED_POINT_CLOUD)
            if not isMacOS:
                file_menu.add_separator()
                file_menu.add_item("Quit", AppWindow.MENU_QUIT)
            settings_menu = gui.Menu()
            settings_menu.add_item("View Controls", AppWindow.MENU_SHOW_SETTINGS)
            help_menu = gui.Menu()
            help_menu.add_item("About", AppWindow.MENU_ABOUT)

            point_cloud_menu = gui.Menu()
            point_cloud_menu.add_item("Downsample", AppWindow.MENU_DOWNSAMPLE)
            point_cloud_menu.add_item("Generate Mesh", AppWindow.MENU_GENERATE_MESH)
            point_cloud_menu.add_item("Sample Points from Mesh", AppWindow.MENU_SAMPLE_POINTS)

            edit_menu = gui.Menu()
            edit_menu.add_item("Undo\tZ", AppWindow.MENU_UNDO)
            edit_menu.add_item("Redo\tY", AppWindow.MENU_REDO)

            menu = gui.Menu()
            if isMacOS:
                menu.add_menu("Example", app_menu)
                menu.add_menu("File", file_menu)
                menu.add_menu("Edit", edit_menu)
                menu.add_menu("Process", point_cloud_menu)
                menu.add_menu("Settings", settings_menu)
            else:
                menu.add_menu("File", file_menu)
                menu.add_menu("Edit", edit_menu)
                menu.add_menu("Process", point_cloud_menu)
                menu.add_menu("Settings", settings_menu)
                menu.add_menu("Help", help_menu)
            gui.Application.instance.menubar = menu

        self.window.set_on_menu_item_activated(AppWindow.MENU_OPEN, self._on_menu_open)
        self.window.set_on_menu_item_activated(AppWindow.MENU_EXPORT_MERGED_POINT_CLOUD, self._on_menu_export_merged_point_cloud)
        self.window.set_on_menu_item_activated(AppWindow.MENU_QUIT, self._on_menu_quit)
        self.window.set_on_menu_item_activated(AppWindow.MENU_SHOW_SETTINGS, self._on_menu_toggle_view_controls)
        self.window.set_on_menu_item_activated(AppWindow.MENU_ABOUT, self._on_menu_about)

        self.window.set_on_menu_item_activated(AppWindow.MENU_DOWNSAMPLE, self._on_menu_downsample)
        self.window.set_on_menu_item_activated(AppWindow.MENU_GENERATE_MESH, self._on_menu_generate_mesh)
        self.window.set_on_menu_item_activated(AppWindow.MENU_SAMPLE_POINTS, self._on_menu_sample_points)

        self.window.set_on_menu_item_activated(AppWindow.MENU_UNDO, self._on_menu_undo)
        self.window.set_on_menu_item_activated(AppWindow.MENU_REDO, self._on_menu_redo)

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

        # 降采样控制
        self.downsample_ctrls = gui.CollapsableVert("Downsample controls", 0.25 * em, gui.Margins(em, 0, 0, 0))
        self._setup_downsample_controls()
        self._settings_panel.add_child(self.downsample_ctrls)

        self.generate_mesh_ctrls = gui.CollapsableVert("Generate Mesh controls", 0.25 * em, gui.Margins(em, 0, 0, 0))
        self._setup_generate_mesh_controls()
        self._settings_panel.add_child(self.generate_mesh_ctrls)


        self.sample_points_from_mesh_ctrls = gui.CollapsableVert("Sample Points from Mesh controls", 0.25 * em, gui.Margins(em, 0, 0, 0))
        self._setup_sample_points_from_mesh_controls()
        self._settings_panel.add_child(self.sample_points_from_mesh_ctrls)
        
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

        self._show_wireframe_checkbox = gui.Checkbox("Show Wireframe")
        self._show_wireframe_checkbox.checked = self.show_wireframe
        self._show_wireframe_checkbox.set_on_checked(self._on_show_wireframe_changed)
        grid.add_child(self._show_wireframe_checkbox)

        self.view_ctrls.add_child(grid)

    def _setup_downsample_controls(self):
        """
        設置降采样控制組件
        """
        em = self.window.theme.font_size
        grid = gui.VGrid(2, 0.25 * em)

        grid.add_child(gui.Label("Voxel Size * 10"))
        self._voxel_size_slider = gui.Slider(gui.Slider.DOUBLE)
        self._voxel_size_slider.set_limits(0.001, 0.1)  # 设置滑块的最小值和最大值
        self._voxel_size_slider.double_value = self.voxel_size  # 设置默认值
        self._voxel_size_slider.set_on_value_changed(self._on_voxel_size_changed)
        grid.add_child(self._voxel_size_slider)

        self.downsample_ctrls.add_child(grid)

    def _setup_generate_mesh_controls(self):
        """
        設置网格生成控制组件
        """
        em = self.window.theme.font_size
        grid = gui.VGrid(2, 0.25 * em)

        grid.add_child(gui.Label("Depth"))
        self._depth_slider = gui.Slider(gui.Slider.INT)
        self._depth_slider.set_limits(5, 12)  # 设置滑块的最小值和最大值
        self._depth_slider.int_value = 8  # 设置默认值
        grid.add_child(self._depth_slider)

        grid.add_child(gui.Label("Full Depth"))
        self._fulldepth_slider = gui.Slider(gui.Slider.INT)
        self._fulldepth_slider.set_limits(3, 8)  # 设置滑块的最小值和最大值
        self._fulldepth_slider.int_value = 5  # 设置默认值
        grid.add_child(self._fulldepth_slider)

        grid.add_child(gui.Label("Scale"))
        self._scale_slider = gui.Slider(gui.Slider.DOUBLE)
        self._scale_slider.set_limits(0.5, 2.0)  # 设置滑块的最小值和最大值
        self._scale_slider.double_value = 1.1  # 设置默认值
        grid.add_child(self._scale_slider)

        grid.add_child(gui.Label("Samples per Node"))
        self._samplespernode_slider = gui.Slider(gui.Slider.DOUBLE)
        self._samplespernode_slider.set_limits(0.5, 5.0)  # 设置滑块的最小值和最大值
        self._samplespernode_slider.double_value = 1.5  # 设置默认值
        grid.add_child(self._samplespernode_slider)

        grid.add_child(gui.Label("Point Weight"))
        self._pointweight_slider = gui.Slider(gui.Slider.DOUBLE)
        self._pointweight_slider.set_limits(0.0, 10.0)  # 设置滑块的最小值和最大值
        self._pointweight_slider.double_value = 4.0  # 设置默认值
        grid.add_child(self._pointweight_slider)

        grid.add_child(gui.Label("Iterations"))
        self._iters_slider = gui.Slider(gui.Slider.INT)
        self._iters_slider.set_limits(1, 20)  # 设置滑块的最小值和最大值
        self._iters_slider.int_value = 8  # 设置默认值
        grid.add_child(self._iters_slider)

        grid.add_child(gui.Label("Threads"))
        self._threads_slider = gui.Slider(gui.Slider.INT)
        self._threads_slider.set_limits(1, 32)  # 设置滑块的最小值和最大值
        self._threads_slider.int_value = 16  # 设置默认值
        grid.add_child(self._threads_slider)

        self.generate_mesh_ctrls.add_child(grid)
    def _setup_sample_points_from_mesh_controls(self):
        """
        設置从网格生成点云控制组件
        """
        em = self.window.theme.font_size
        grid = gui.VGrid(2, 0.25 * em)

        grid.add_child(gui.Label("Number of Points"))
        self._num_points_slider = gui.Slider(gui.Slider.INT)
        self._num_points_slider.set_limits(100, 50000)  # 设置滑块的最小值和最大值
        self._num_points_slider.int_value = self.num_points  # 设置默认值
        self._num_points_slider.set_on_value_changed(self._on_num_points_changed)
        grid.add_child(self._num_points_slider)

        self.sample_points_from_mesh_ctrls.add_child(grid)

    def _on_show_wireframe_changed(self, is_checked):
        """
        更改顯示線框選項時觸發
        參數:
        is_checked (bool): 新的選項狀態
        """
        self.show_wireframe = is_checked
        if self.loaded_mesh is not None:
            self.update_mesh(self.loaded_mesh)

    def _on_voxel_size_changed(self, value):
        """
        更改体素大小时触发
        參數:
        value (float): 新的体素大小
        """
        self.voxel_size = value

    def _on_num_points_changed(self, value):
        """
        更改采样点数时触发
        參數:
        value (int): 新的采样点数
        """
        self.num_points = value

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

    def _on_menu_export_merged_point_cloud(self):
        """
        點擊菜單中的“Export Merged Point Cloud”選項時觸發
        """
        self._export_merged_point_cloud()

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

    def _on_menu_downsample(self):
        try:
            if self.point_cloud_loaded:
                voxel_size = self.voxel_size / 10  # 使用滑块设置的体素大小
                self.undo_stack.append(self.loaded_pcd)  # 保存当前状态到撤销栈
                downsampled_pcd = self.downsample_point_cloud(self.loaded_pcd, voxel_size)
                if downsampled_pcd is not None:
                    self.update_point_cloud(downsampled_pcd)
                    self.redo_stack.clear()  # 清空重做栈
                else:
                    print("Failed to downsample point cloud")
            else:
                print("No point cloud loaded")
        except Exception as e:
            print(f"Failed to downsample point cloud: {e}")

    def _on_menu_generate_mesh(self):
        """
        點擊菜單中的“Generate Mesh”選項時觸發
        """
        try:
            if self.point_cloud_loaded:
                mesh = self.generate_mesh_from_point_cloud(self.loaded_pcd)
                if mesh is not None:
                    self.undo_stack.append(self.loaded_pcd)  # 保存当前点云到撤销栈
                    self.redo_stack.clear()  # 清空重做栈
                    self.update_mesh(mesh)
                    self.save_mesh(mesh, "generated_mesh.ply")
                else:
                    print("Failed to generate mesh")
            else:
                print("No point cloud loaded")
        except Exception as e:
            print(f"Failed to generate mesh: {e}")

    def _on_menu_sample_points(self):
        """
        點擊菜單中的“Sample Points from Mesh”選項時觸發
        """
        try:
            if self.loaded_mesh is not None:
                # 从网格中采样点云
                sample_points_count = int(self.num_points)   # 设置采样点的数量
                sampled_pcd = self.loaded_mesh.sample_points_poisson_disk(number_of_points=sample_points_count)

                if sampled_pcd is not None:
                    self.undo_stack.append(self.loaded_mesh)  # 保存当前网格到撤销栈
                    self.redo_stack.clear()  # 清空重做栈
                    self.update_point_cloud(sampled_pcd)
                    print(f"Sampled {sample_points_count} points from the mesh")
                else:
                    print("Failed to sample points from the mesh")
            else:
                print("No mesh loaded")
        except Exception as e:
            print(f"Failed to sample points from mesh: {e}")

    def _on_menu_undo(self):
        """
        撤销操作
        """
        if self.undo_stack:
            self.redo_stack.append(self.loaded_pcd if self.point_cloud_loaded else self.loaded_mesh)
            geom = self.undo_stack.pop()
            if isinstance(geom, o3d.geometry.PointCloud):
                self.update_point_cloud(geom)
            elif isinstance(geom, o3d.geometry.TriangleMesh):
                self.update_mesh(geom)
            print("Undo operation performed")

    def _on_menu_redo(self):
        """
        重做操作
        """
        if self.redo_stack:
            self.undo_stack.append(self.loaded_pcd if self.point_cloud_loaded else self.loaded_mesh)
            geom = self.redo_stack.pop()
            if isinstance(geom, o3d.geometry.PointCloud):
                self.update_point_cloud(geom)
            elif isinstance(geom, o3d.geometry.TriangleMesh):
                self.update_mesh(geom)
            print("Redo operation performed")

    def _on_bg_color_changed(self, color):
        """
        更改背景顏色時觸發
        參數:
        color (gui.Color): 新的顏色
        """
        self._scene.scene.set_background([color.red, color.green, color.blue, color.alpha])

    def downsample_point_cloud(self, pcd, voxel_size):
        """对点云进行体素下采样"""
        try:
            downsampled_pcd = pcd.voxel_down_sample(voxel_size)
            return downsampled_pcd
        except Exception as e:
            print(f"Failed to downsample point cloud: {e}")
            return None

    def generate_mesh_from_point_cloud(self, pcd):
        """
        使用PyMeshLab从点云生成网格并进行平滑处理
        參數:
        pcd (o3d.geometry.PointCloud): 输入的点云
        返回:
        mesh (o3d.geometry.TriangleMesh): 生成的三角网格
        """
        try:
            # 从滑块获取参数值
            depth = self._depth_slider.int_value
            fulldepth = self._fulldepth_slider.int_value
            scale = self._scale_slider.double_value
            samplespernode = self._samplespernode_slider.double_value
            pointweight = self._pointweight_slider.double_value
            iters = self._iters_slider.int_value
            threads = self._threads_slider.int_value

            # 将点云保存为临时文件以供pymeshlab使用
            temp_pcd_file = "temp.ply"
            o3d.io.write_point_cloud(temp_pcd_file, pcd)

            # 使用pymeshlab生成网格
            ms = pymeshlab.MeshSet()
            ms.load_new_mesh(temp_pcd_file)
            ms.compute_normal_for_point_clouds()
            ms.generate_surface_reconstruction_screened_poisson(
                depth=depth,
                fulldepth=fulldepth,
                scale=scale,
                samplespernode=samplespernode,
                pointweight=pointweight,
                iters=iters,
                threads=threads
            )
            ms.apply_filter('apply_coord_laplacian_smoothing', stepsmoothnum=5)

            # 保存生成的网格为临时文件
            temp_mesh_file = "temp_mesh.ply"
            ms.save_current_mesh(temp_mesh_file)

            # 从临时文件加载生成的网格
            mesh = o3d.io.read_triangle_mesh(temp_mesh_file)
            return mesh
        except Exception as e:
            print(f"Failed to generate mesh from point cloud: {e}")
            return None


    def save_mesh(self, mesh, file_path):
        """
        保存网格数据
        參數:
        mesh (o3d.geometry.TriangleMesh): 要保存的三角网格
        file_path (str): 保存文件的路径
        """
        try:
            o3d.io.write_triangle_mesh(file_path, mesh)
            print(f"Mesh saved to {file_path}")
        except Exception as e:
            print(f"Failed to save mesh: {e}")

    def update_point_cloud(self, pcd):
        """
        更新显示的点云
        參數:
        pcd (o3d.geometry.PointCloud): 要显示的点云
        """
        try:
            self._scene.scene.clear_geometry()
            self._scene.scene.add_geometry("PointCloud", pcd, self.material)
            #self._scene.setup_camera(60.0, pcd.get_axis_aligned_bounding_box(), pcd.get_center())
            self.point_cloud_loaded = True
            self.loaded_pcd = pcd
            self.loaded_mesh = None  # 更新状态，表示当前显示的是点云
        except Exception as e:
            print(f"Failed to update point cloud: {e}")

    def update_mesh(self, mesh):
        """
        更新显示的网格
        參數:
        mesh (o3d.geometry.TriangleMesh): 要显示的三角网格
        """
        try:
            self._scene.scene.clear_geometry()
            
            self._scene.scene.add_geometry("Mesh", mesh, self.material)
            
            if self.show_wireframe:
                lines = o3d.geometry.LineSet.create_from_triangle_mesh(mesh)
                lines.paint_uniform_color([0, 0, 0])  # 设置线框颜色为黑色
                self._scene.scene.add_geometry("Wireframe", lines, self.material)
            
            self.point_cloud_loaded = False  # 更新状态，表示当前显示的是网格
            self.loaded_pcd = None
            self.loaded_mesh = mesh
        except Exception as e:
            print(f"Failed to update mesh: {e}")

    def load_point_cloud(self, path):
        """
        加载点云或网格文件
        参数:
        path (str): 文件路径
        """
        try:
            # 尝试加载网格文件
            mesh = o3d.io.read_triangle_mesh(path)
            if mesh.has_triangles():
                # 存储加载的网格以便后续操作
                self.loaded_mesh = mesh

                # 移除当前几何对象（无论是点云还是网格）
                self._scene.scene.clear_geometry()

                self._scene.scene.add_geometry("Mesh", mesh, self.material)
                self._scene.setup_camera(60.0, mesh.get_axis_aligned_bounding_box(), mesh.get_center())
                    
                self.point_cloud_loaded = False  # 更新状态，表示当前显示的是网格
                self.loaded_pcd = None

                self.update_mesh(self.loaded_mesh)

                print("Mesh loaded successfully")

                self.undo_stack = []
                self.redo_stack = []

                return

            # 如果不是网格，尝试加载点云文件
            pcd = o3d.io.read_point_cloud(path)
            if pcd.has_points():
                # 存储加载的点云以便后续操作
                self.loaded_pcd = pcd

                # 移除当前几何对象（无论是点云还是网格）
                self._scene.scene.clear_geometry()

                self._scene.scene.add_geometry("PointCloud", pcd, self.material)
                self._scene.setup_camera(60.0, pcd.get_axis_aligned_bounding_box(), pcd.get_center())
                
                self.point_cloud_loaded = True
                self.loaded_mesh = None  # 重置当前的网格状态
                print("Point cloud loaded successfully")
                
                self.undo_stack = []
                self.redo_stack = []
                
                return

            print(f"Failed to load point cloud or mesh from {path}. Exiting.")
        except Exception as e:
            print(f"Failed to load point cloud or mesh: {e}")

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

    def _export_merged_point_cloud(self):
        """
        导出合并后的点云
        """
        
        if self.loaded_pcd is None and self.loaded_mesh is None:
            self._show_warning_dialog("No point cloud or mesh available for export.")
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
        if self.loaded_pcd is None and self.loaded_mesh is None:
            self._show_warning_dialog("No point cloud or mesh available for export.")
            return
        
        try:
            if self.loaded_pcd is not None:
                o3d.io.write_point_cloud(filename, self.loaded_pcd)
                print(f"Point cloud saved to {filename}")
            elif self.loaded_mesh is not None:
                o3d.io.write_triangle_mesh(filename, self.loaded_mesh)
                print(f"Mesh saved to {filename}")
        except Exception as e:
            self._show_warning_dialog(f"Failed to export merged point cloud: {e}")

    def close(self):
        gui.Application.instance.quit()


def main():
    gui.Application.instance.initialize()
    w = AppWindow(1024, 768)
    gui.Application.instance.run()

if __name__ == "__main__":
    main()
