import open3d as o3d
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering
from datetime import datetime
import platform
import threading
import multiprocessing
import logging
import sys
import time
import queue
import os

from .pipeline_model import pipeline_process, PipelineModel  # Import your pipeline_process and PipelineModel
from . import registration_ransac_icp as pcr_ransac
from . import registration_fast_icp as pcr_fast
from . import registration_point_to_point_icp as pcr_p2point
from . import registration_point_to_plane_icp as pcr_p2plane
from . import registration_colored_icp as pcr_colored
'''
from pipeline_model import pipeline_process, PipelineModel  # Import your pipeline_process and PipelineModel
import registration_ransac_icp as pcr_ransac
import registration_fast_icp as pcr_fast
import registration_point_to_point_icp as pcr_p2point
import registration_point_to_plane_icp as pcr_p2plane
import registration_colored_icp as pcr_colored'''

isMacOS = (platform.system() == "Darwin")

# 初始化 logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class OnlineRegistration:
    MENU_OPEN = 1
    MENU_QUIT = 3
    MENU_SHOW_SETTINGS = 11
    MENU_SHOW_PROCESS_CONTROLS = 12
    MENU_ABOUT = 21
    MENU_PIPELINE_START = 31
    MENU_PIPELINE_STOP = 32
    MENU_CAPTURE = 33
    MENU_START_CV = 34
    MENU_STOP_CV = 35
    MENU_REGISTRATION_START = 36
    MENU_REGISTRATION_STOP = 37
    MENU_START_RECORDING = 38
    MENU_STOP_RECORDING = 39
    MENU_CLEAR_SCENE = 40
    MENU_RESET_VIEW = 41
    MENU_TOGGLE_AUTO_REGISTRATION = 42

    def __init__(self, width, height):
        #儲存文件的原始位置
        self.original_dir_path = os.getcwd()
        print(f"Current directory: {self.original_dir_path}")
        self.pcds = []
        self.current_index = -1
        self.imported_filenames = []
        self.voxel_size = 0.05
        self.registration_mode = "RANSAC"
        self.ransac_distance_multiplier = 1.5
        self.ransac_max_iterations = 4000000
        self.ransac_max_validation = 500
        self.icp_distance_multiplier = 0.4
        self.current_pcd = None

        self.registration_captured = False
        self.is_auto_registration = False

        self.pipeline_running = False
        self.cv_running = False
        self.recording = False
        self.rgbd_video = None

        # 初始化进程间通信队列和管道
        self.start_queue = multiprocessing.Queue()
        self.save_queue = multiprocessing.Queue()
        self.complete_queue = multiprocessing.Queue()
        self.parent_conn, self.child_conn = multiprocessing.Pipe()

        self.pcd_folder_path = "pcd"
        self.captured_pcd_folder_path = "pcd\\captured_pcd"
        self.registration_pcd_folder_path = "pcd\\registration_pcd"
        
        self.pipeline_start_time = ""
        
        self.registration_thread = None

        self.pipeline_process = None
        self.registration_running = False  # 用于跟踪 Registration 是否正在运行

        self.registration_control_thread = None
        self.filename_counter = 1  # 用于生成唯一的文件名

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
        self.process_ctrls.visible = True
        self._settings_panel.visible = True

        self.refresh_view_on_mode_change = True

        self.window.set_on_close(self._on_window_close)

        gui.Application.instance.menubar.set_checked(OnlineRegistration.MENU_SHOW_SETTINGS, self.view_ctrls.visible)
        gui.Application.instance.menubar.set_checked(OnlineRegistration.MENU_SHOW_PROCESS_CONTROLS, self.process_ctrls.visible)
        
        self._update_process_menu()  # 初始化时更新 Process 菜单项

    def check_or_create_folder(self, folder_name):
        # 取得相對路徑
        full_path = os.path.join(os.getcwd(), folder_name)

        # 檢查是否存在目錄
        if os.path.exists(full_path) and os.path.isdir(full_path):
            print(f"The folder '{folder_name}' already exists at path: {full_path}")
        else:
            # 若不存在，創建資料夾
            os.makedirs(full_path)
            print(f"The folder '{folder_name}' does not exist, creating new folder at path: {full_path}")
        
        # 返回資料夾的完整路徑
        return full_path


    def _setup_menu_bar(self):
        if gui.Application.instance.menubar is None:
            if isMacOS:
                app_menu = gui.Menu()
                app_menu.add_item("About", OnlineRegistration.MENU_ABOUT)
                app_menu.add_separator()
                app_menu.add_item("Quit", OnlineRegistration.MENU_QUIT)
            file_menu = gui.Menu()
            file_menu.add_item("Open...", OnlineRegistration.MENU_OPEN)
            if not isMacOS:
                file_menu.add_separator()
                file_menu.add_item("Quit", OnlineRegistration.MENU_QUIT)
            settings_menu = gui.Menu()
            settings_menu.add_item("View Controls", OnlineRegistration.MENU_SHOW_SETTINGS)
            settings_menu.add_item("Process Controls", OnlineRegistration.MENU_SHOW_PROCESS_CONTROLS)

            scene_menu = gui.Menu()
            scene_menu.add_item("Clear Scene", OnlineRegistration.MENU_CLEAR_SCENE)
            scene_menu.add_item("Reset View", OnlineRegistration.MENU_RESET_VIEW)
            

            process_menu = gui.Menu()
            process_menu.add_item("Start Pipeline", OnlineRegistration.MENU_PIPELINE_START)
            process_menu.add_item("Stop Pipeline", OnlineRegistration.MENU_PIPELINE_STOP)
            process_menu.add_separator()
            process_menu.add_item("Auto Registration", OnlineRegistration.MENU_TOGGLE_AUTO_REGISTRATION)
            process_menu.add_item("Registration Start", OnlineRegistration.MENU_REGISTRATION_START)
            process_menu.add_item("Registration Stop", OnlineRegistration.MENU_REGISTRATION_STOP)
            process_menu.add_separator()
            process_menu.add_item("Capture", OnlineRegistration.MENU_CAPTURE)
            process_menu.add_item("Start CV", OnlineRegistration.MENU_START_CV)
            process_menu.add_item("Stop CV", OnlineRegistration.MENU_STOP_CV)
            process_menu.add_separator()
            process_menu.add_item("Start Recording", OnlineRegistration.MENU_START_RECORDING)
            process_menu.add_item("Stop Recording", OnlineRegistration.MENU_STOP_RECORDING)

            help_menu = gui.Menu()
            help_menu.add_item("About", OnlineRegistration.MENU_ABOUT)

            menu = gui.Menu()
            if isMacOS:
                menu.add_menu("Example", app_menu)
                menu.add_menu("File", file_menu)
                menu.add_menu("Settings", settings_menu)
                menu.add_menu("Scene", scene_menu)
                menu.add_menu("Process", process_menu)  # 添加 Process 菜单
            else:
                menu.add_menu("File", file_menu)
                menu.add_menu("Settings", settings_menu)
                menu.add_menu("Scene", scene_menu)
                menu.add_menu("Process", process_menu)  # 添加 Process 菜单
                menu.add_menu("Help", help_menu)
            gui.Application.instance.menubar = menu

        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_OPEN, self._on_menu_open)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_QUIT, self._on_menu_quit)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_SHOW_SETTINGS, self._on_menu_toggle_view_controls)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_SHOW_PROCESS_CONTROLS, self._on_menu_toggle_process_controls)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_ABOUT, self._on_menu_about)

        # Process menu items
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_PIPELINE_START, self._on_pipeline_start)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_PIPELINE_STOP, self._on_pipeline_stop)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_CAPTURE, self._on_capture)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_TOGGLE_AUTO_REGISTRATION, self._toggle_registration_mode)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_REGISTRATION_START, self._on_registration_start)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_REGISTRATION_STOP, self._on_registration_stop)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_START_CV, self._on_start_cv)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_STOP_CV, self._on_stop_cv)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_START_RECORDING, self._on_start_recording)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_STOP_RECORDING, self._on_stop_recording)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_CLEAR_SCENE, self._on_clear_scene)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_RESET_VIEW, self._on_reset_view)

    def _setup_settings_panel(self):
        em = self.window.theme.font_size
        self._settings_panel = gui.Vert(0, gui.Margins(0.25 * em, 0.25 * em, 0.25 * em, 0.25 * em))

        # View controls section
        self.view_ctrls = gui.CollapsableVert("View Controls", 0.25 * em, gui.Margins(em, 0, 0, 0))
        self._setup_view_controls()
        self._settings_panel.add_child(self.view_ctrls)

        # Process controls section
        self.process_ctrls = gui.CollapsableVert("Process Controls", 0.25 * em, gui.Margins(em, 0, 0, 0))
        self._setup_process_controls()
        self._settings_panel.add_child(self.process_ctrls)

        self.window.add_child(self._settings_panel)

    def _setup_view_controls(self):
        em = self.window.theme.font_size
        grid1 = gui.VGrid(2, 0.25 * em)
        
        # 添加 "BG Color" 標籤和顏色編輯器
        grid1.add_child(gui.Label("BG Color"))
        self._bg_color = gui.ColorEdit()
        self._bg_color.color_value = gui.Color(1, 1, 1)
        self._bg_color.set_on_value_changed(self._on_bg_color_changed)
        grid1.add_child(self._bg_color)

        # 將 grid1 添加到 view_ctrls
        self.view_ctrls.add_child(grid1)

    def _setup_process_controls(self):
        em = self.window.theme.font_size
        self.grid2 = gui.Vert(0.25 * em)  # 使用垂直布局
        
        # 創建一個水平佈局來放置 Status 標籤和狀態顯示
        status_row = gui.Horiz(0.25 * em)
        status_row.add_child(gui.Label("Status"))
        self._status_label = gui.Label("Idle")  # 初始狀態為 "Idle"
        status_row.add_child(self._status_label)

        # 將 Status 的水平佈局添加到垂直布局中
        self.grid2.add_child(status_row)

        # 更新狀態 Idle 綠色
        self.update_status("Idle", (0, 1, 0))

        # Depth Max Slider
        self.grid2.add_child(gui.Label("Depth Max"))
        self.depth_max_slider = gui.Slider(gui.Slider.DOUBLE)
        self.depth_max_slider.set_limits(0.1, 10.0)
        self.depth_max_slider.double_value = 3.0
        self.depth_max_slider.set_on_value_changed(self._on_depth_max_changed)
        self.grid2.add_child(self.depth_max_slider)

        # Depth Min Slider
        self.grid2.add_child(gui.Label("Depth Min"))
        self.depth_min_slider = gui.Slider(gui.Slider.DOUBLE)
        self.depth_min_slider.set_limits(0.1, 10.0)
        self.depth_min_slider.double_value = 0.1
        self.depth_min_slider.set_on_value_changed(self._on_depth_min_changed)
        self.grid2.add_child(self.depth_min_slider)

        # 添加 X Max Slider
        #self.grid2.add_child(gui.Label("X Max"))
        self.x_max_slider = gui.Slider(gui.Slider.DOUBLE)
        self.x_max_slider.set_limits(-5.0, 5.0)
        self.x_max_slider.double_value = 0.5  # 預設值，根據需要調整
        self.x_max_slider.set_on_value_changed(self._on_x_max_changed)
        self.grid2.add_child(self.x_max_slider)

        # 添加 X Min Slider
        #self.grid2.add_child(gui.Label("X Min"))
        self.x_min_slider = gui.Slider(gui.Slider.DOUBLE)
        self.x_min_slider.set_limits(-5.0, 5.0)
        self.x_min_slider.double_value = -0.5  # 預設值，根據需要調整
        self.x_min_slider.set_on_value_changed(self._on_x_min_changed)
        self.grid2.add_child(self.x_min_slider)

        self.x_min_slider.visible = False
        self.x_max_slider.visible = False

        # Voxel Size Slider
        self.grid2.add_child(gui.Label("Voxel Size"))
        self.voxel_size_slider = gui.Slider(gui.Slider.DOUBLE)
        self.voxel_size_slider.set_limits(0.001, 0.2)
        self.voxel_size_slider.double_value = 0.05
        self.voxel_size_slider.set_on_value_changed(self._on_voxel_size_changed)
        self.grid2.add_child(self.voxel_size_slider)

        # Registration Mode Combobox
        self.grid2.add_child(gui.Label("Registration Mode"))
        self.registration_mode_combobox = gui.Combobox()
        self.registration_mode_combobox.add_item("RANSAC")
        self.registration_mode_combobox.add_item("FAST")
        self.registration_mode_combobox.add_item("P2POINT")
        self.registration_mode_combobox.add_item("P2PLANE")
        self.registration_mode_combobox.add_item("COLORED")
        self.registration_mode_combobox.selected_text = "RANSAC"
        self.registration_mode_combobox.set_on_selection_changed(self._on_registration_mode_changed)
        self.grid2.add_child(self.registration_mode_combobox)

        # Create a layout for RANSAC-related controls
        self.ransac_layout = gui.Vert(0.25 * em)

        # Add some padding or indentation to give a visual sense of hierarchy
        ransac_inner_layout = gui.Vert(0.5 * em, gui.Margins(2 * em, 0, 0, 0))  # Indent to show sub-item

        # RANSAC Distance Threshold
        ransac_inner_layout.add_child(gui.Label("RANSAC Distance Threshold"))
        self.ransac_distance_slider = gui.Slider(gui.Slider.DOUBLE)
        self.ransac_distance_slider.set_limits(1.0, 5.0)
        self.ransac_distance_slider.double_value = 1.5
        self.ransac_distance_slider.set_on_value_changed(self._on_ransac_distance_changed)
        ransac_inner_layout.add_child(self.ransac_distance_slider)

        # RANSAC Max Iterations
        ransac_inner_layout.add_child(gui.Label("RANSAC Max Iterations"))
        self.ransac_iterations_slider = gui.Slider(gui.Slider.INT)
        self.ransac_iterations_slider.set_limits(100000, 5000000)
        self.ransac_iterations_slider.int_value = 4000000
        self.ransac_iterations_slider.set_on_value_changed(self._on_ransac_iterations_changed)
        ransac_inner_layout.add_child(self.ransac_iterations_slider)

        # RANSAC Max Validation
        self.ransac_layout.add_child(gui.Label("RANSAC Max Validation"))
        self.ransac_max_validation_slider = gui.Slider(gui.Slider.INT)
        self.ransac_max_validation_slider.set_limits(100, 10000)  # 设置 RANSAC 验证次数的范围
        self.ransac_max_validation_slider.int_value = 500  # 设置默认值
        self.ransac_max_validation_slider.set_on_value_changed(self._on_ransac_max_validation_changed)
        self.ransac_layout.add_child(self.ransac_max_validation_slider)

        # ICP Threshold
        ransac_inner_layout.add_child(gui.Label("ICP Distance Threshold"))
        self.icp_threshold_slider = gui.Slider(gui.Slider.DOUBLE)
        self.icp_threshold_slider.set_limits(0.1, 1.0)
        self.icp_threshold_slider.double_value = 0.4
        self.icp_threshold_slider.set_on_value_changed(self._on_icp_threshold_changed)
        ransac_inner_layout.add_child(self.icp_threshold_slider)

        # Add the inner layout to the RANSAC layout
        self.ransac_layout.add_child(ransac_inner_layout)

        # Initially, add the RANSAC layout to grid
        self.grid2.add_child(self.ransac_layout)

        self.process_ctrls.add_child(self.grid2)
        self.window.add_child(self.process_ctrls)

    
    def update_status(self, new_status, color=(1, 1, 1)):
        """
        更新 Status 標籤的內容和顏色。
        
        參數：
        new_status (str): 新的狀態文字。
        color (tuple): 一個 RGB 三元組，用來設定狀態文字的顏色，預設為黑色。
        """
        self._status_label.text = new_status
        self._status_label.text_color = gui.Color(color[0], color[1], color[2])  # 更新文字顏色
        self.window.set_needs_layout()  # 讓介面更新以顯示新的狀態

    def _toggle_registration_mode(self):
        """
        切換配準模式（手動或自動）。
        """
        self.is_auto_registration = not self.is_auto_registration
        mode = "Auto" if self.is_auto_registration else "Manual"
        print(f"Registration mode switched to: {mode}")

        # 更新菜單項的狀態顯示
        gui.Application.instance.menubar.set_checked(OnlineRegistration.MENU_TOGGLE_AUTO_REGISTRATION, self.is_auto_registration)

        self._update_process_menu()


    def get_status(self):
        """
        獲取當前的 Status 標籤文字和顏色。
        
        返回：
        tuple: 包含當前狀態標籤的文字內容和顏色 (文字內容, (R, G, B))
        """
        # 提取當前文字和顏色
        status_text = self._status_label.text
        status_color = (self._status_label.text_color.red, 
                        self._status_label.text_color.green, 
                        self._status_label.text_color.blue)
        
        return status_text, status_color

    def _on_clear_scene(self):
        """
        清除場景中的所有幾何對象，並重置應用的內部狀態。
        """
        try:
            # 清除場景中的所有幾何對象
            self._scene.scene.clear_geometry()
            print("Scene cleared.")

            # 重置與場景相關的內部變量
            self.current_pcd = None  # 當前點雲設置為None
            print("Internal state reset.")

        except Exception as e:
            print(f"Error while clearing scene: {e}")

    def _on_reset_view(self):

        if self.current_pcd is not None:
            self._scene.setup_camera(60.0, self.current_pcd.get_axis_aligned_bounding_box(), self.current_pcd.get_center())
        else:
            print("No point cloud loaded. Cannot reset view.")
        
    def _on_depth_max_changed(self, value):
        if self.pipeline_running:
            # 向子进程发送新的深度阈值
            self.parent_conn.send(("SET_DEPTH_MAX", value))
            #log.info(f"Depth max updated to {value}")
        else:
            log.warning("Pipeline is not running. Cannot update depth max.")

    def _on_depth_min_changed(self, value):
        if self.pipeline_running:
            # 向子进程发送新的最小深度值
            self.parent_conn.send(("SET_DEPTH_MIN", value))
            log.info(f"Depth min updated to {value}")
        else:
            log.warning("Pipeline is not running. Cannot update depth min.")

    def _on_x_max_changed(self, value):
        if self.pipeline_running:
            # 向子进程发送新的 X 最大值
            self.parent_conn.send(("SET_X_MAX", value))
            log.info(f"X max updated to {value}")
        else:
            log.warning("Pipeline is not running. Cannot update X max.")

    def _on_x_min_changed(self, value):
        if self.pipeline_running:
            # 向子进程发送新的 X 最小值
            self.parent_conn.send(("SET_X_MIN", value))
            log.info(f"X min updated to {value}")
        else:
            log.warning("Pipeline is not running. Cannot update X min.")

    def _on_voxel_size_changed(self, value):
        """当 voxel size 滑块值变化时触发"""
        if not self.registration_running:
            self.voxel_size = value
            log.info(f"Voxel size updated to {value}")
        else:
            log.warning("Cannot change voxel size while registration is running.")

    def _on_registration_mode_changed(self, text, index):
        """
        当用户在 Registration Quality 下拉框中选择不同的值时触发。
        参数：
            text (str): 选中的文本
            index (int): 选中的索引
        """
        try:
            log.info(f"Combobox selection changed to: {text} (index {index})")
            
            # 更新类属性，供其他部分访问
            self.registration_mode = text  # 更新 registration_mode 属性
            
            # 打印当前选择，调试用
            log.info(f"Updated registration quality to: {self.registration_mode}")
            
            self._update_process_menu()

        except Exception as e:
            log.error(f"Error handling registration quality change: {e}")

    def _on_ransac_distance_changed(self, value):
        # 更新RANSAC配准中的距离阈值倍数
        self.ransac_distance_multiplier = value

    def _on_ransac_iterations_changed(self, value):
        # 更新RANSAC的最大迭代次数
        self.ransac_max_iterations = value

    def _on_ransac_max_validation_changed(self, value):
        self.ransac_max_validation = int(value)
        print(f"RANSAC Max Validation set to {self.ransac_max_validation}")

    def _on_icp_threshold_changed(self, value):
        # 更新ICP配准中的距离阈值倍数
        self.icp_distance_multiplier = value

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
        #把目前位置改為self.original_dir_path
        os.chdir(self.original_dir_path)

    def _on_menu_quit(self):
        self._on_stop_cv()  # 确保在退出时停止 CV
        self._on_pipeline_stop()  # 确保在退出时停止 Pipeline
        gui.Application.instance.quit()

    def _on_menu_toggle_view_controls(self):
        self.view_ctrls.visible = not self.view_ctrls.visible
        self._update_settings_panel_visibility()

    def _on_menu_toggle_process_controls(self):
        self.process_ctrls.visible = not self.process_ctrls.visible
        self._update_settings_panel_visibility()
        

    def _update_settings_panel_visibility(self):
        self._settings_panel.visible = self.view_ctrls.visible or self.process_ctrls.visible
        gui.Application.instance.menubar.set_checked(OnlineRegistration.MENU_SHOW_SETTINGS, self.view_ctrls.visible)
        gui.Application.instance.menubar.set_checked(OnlineRegistration.MENU_SHOW_PROCESS_CONTROLS, self.process_ctrls.visible)
        self.window.set_needs_layout()


    def _on_menu_about(self):
        pass

    def _on_bg_color_changed(self, color):
        self._scene.scene.set_background([color.red, color.green, color.blue, color.alpha])

    def _on_key_event(self, event):
        if event.type == gui.KeyEvent.Type.DOWN:
            if event.key == gui.KeyName.N:
                pass  # 保留方法，但不处理任何按键事件

    def load_point_cloud(self, filename):
        try:
            pcd = o3d.io.read_point_cloud(filename)
            if pcd:
                self._scene.scene.clear_geometry()
                self._scene.scene.add_geometry("Point Cloud", pcd, self.material)
                self.current_pcd = pcd
                #self._scene.setup_camera(60.0, pcd.get_axis_aligned_bounding_box(), pcd.get_center())
                print(f"Loaded point cloud from {filename}")
                return "success"
            else:
                print(f"Failed to load point cloud from {filename}")
                return "failed"

        except Exception as e:
            print(f"An error occurred: {e}")
            return "failed"
        
    def load_pcd(self, pcd):
        try:
            if pcd:
                self._scene.scene.clear_geometry()
                self._scene.scene.add_geometry("Point Cloud", pcd, self.material)
                self.current_pcd = pcd
            else:
                print(f"Failed to load point cloud")
        
        except Exception as e:
            print(f"An error occurred: {e}")

    def _on_pipeline_start(self):
        """處理啟動 pipeline 的邏輯，這裡改為等待使用者的選擇後才執行 pipeline。"""
        if not self.pipeline_running:
            # 顯示選項對話框
            self._show_pipeline_options_dialog()

    def _show_pipeline_options_dialog(self):
        """顯示一個對話框，讓使用者選擇 'Use camera' 或 'Use .bag'。"""
        em = self.window.theme.font_size
        dlg = gui.Dialog("Pipeline Options")

        layout = gui.Vert(0.25 * em, gui.Margins(0.5 * em, 0.5 * em, 0.5 * em, 0.5 * em))

        # 添加第一個選項 'Use camera'
        self.use_camera_checkbox = gui.Checkbox("Use camera")
        self.use_camera_checkbox.checked = True  # 預設使用相機
        layout.add_child(self.use_camera_checkbox)

        # 添加第二個選項 'Use .bag'
        self.use_bag_checkbox = gui.Checkbox("Use .bag")
        layout.add_child(self.use_bag_checkbox)

        # 讓這兩個選項互斥
        self.use_camera_checkbox.set_on_checked(self._on_use_camera_checked)
        self.use_bag_checkbox.set_on_checked(self._on_use_bag_checked)

        # 添加確認和取消按鈕
        h = gui.Horiz(0.25 * em)
        h.add_stretch()

        confirm_btn = gui.Button("Confirm")
        confirm_btn.set_on_clicked(self._on_pipeline_options_confirmed)  # 確認後的處理函數
        h.add_child(confirm_btn)

        cancel_btn = gui.Button("Cancel")
        cancel_btn.set_on_clicked(self.window.close_dialog)
        h.add_child(cancel_btn)

        h.add_stretch()
        layout.add_child(h)

        dlg.add_child(layout)
        self.window.show_dialog(dlg)

    def _on_use_camera_checked(self, checked):
        """當 'Use camera' 被選中時，取消選中 'Use .bag'"""
        if checked:
            self.use_bag_checkbox.checked = False

    def _on_use_bag_checked(self, checked):
        """當 'Use .bag' 被選中時，取消選中 'Use camera'"""
        if checked:
            self.use_camera_checkbox.checked = False

    def _on_pipeline_options_confirmed(self):
        """當使用者確認選項後，處理選擇並啟動 pipeline。"""
        use_camera = self.use_camera_checkbox.checked
        use_bag = self.use_bag_checkbox.checked

        # 關閉選項對話框
        self.window.close_dialog()

        # 如果選擇使用 .bag，則顯示文件選擇對話框
        if use_bag:
            dlg = gui.FileDialog(gui.FileDialog.OPEN, "Choose .bag file", self.window.theme)
            dlg.add_filter(".bag", "ROS Bag files (.bag)")
            dlg.add_filter("", "All files")
            dlg.set_on_cancel(self._on_file_dialog_cancel)
            dlg.set_on_done(self._on_bag_file_selected)
            self.window.show_dialog(dlg)
        else:
            # 如果選擇了相機，則直接啟動 pipeline 並傳入 None 作為 rgbd_video
            self._start_pipeline(rgbd_video=None)

    def _on_bag_file_selected(self, filename):
        """當使用者選擇了 .bag 文件後，啟動 pipeline。"""
        rgbd_video = filename  # 獲取選中的 .bag 文件路徑
        self.window.close_dialog()

        # 啟動 pipeline，傳入 .bag 文件路徑作為參數
        self._start_pipeline(rgbd_video=rgbd_video)

    def _start_pipeline(self, rgbd_video):
        """實際啟動 pipeline 的邏輯。"""
        try:
            self.pipeline_start_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

            self.start_queue = multiprocessing.Queue()
            self.save_queue = multiprocessing.Queue()
            self.complete_queue = multiprocessing.Queue()
            self.parent_conn, self.child_conn = multiprocessing.Pipe()
            
            # 启动 pipeline 进程，传入 rgbd_video（可能是 None 或 .bag 文件路径）
            self.pipeline_process = multiprocessing.Process(
                target=pipeline_process, 
                args=(self.start_queue, self.save_queue, self.complete_queue, self.child_conn, rgbd_video, self.pipeline_start_time)
            )
            self.pipeline_process.daemon = True
            self.pipeline_process.start()

            # 等待 pipeline 启动完成
            is_started = self.start_queue.get(timeout=10)
            if is_started == "START":
                self.pipeline_running = True
                print("Pipeline started successfully.")
            elif is_started == "ERROR":
                self._show_warning_dialog("Failed to start pipeline: No device connected or other error.")
                self.pipeline_process.join()
        except queue.Empty:
            self._show_warning_dialog("Pipeline start timed out.")
            self.pipeline_running = False
        except Exception as e:
            self._show_warning_dialog(f"An error occurred while starting the pipeline: {e}")
            if self.pipeline_process.is_alive():
                self.pipeline_process.terminate()
                self.pipeline_process.join()
            self.pipeline_running = False

        self._update_process_menu()


    def _on_pipeline_stop(self):
        """处理停止 pipeline 的逻辑"""
        if self.cv_running:
            self._on_stop_cv()  # 先关闭 CV
        if self.registration_running:
            self._on_registration_stop()  # 先关闭 Registration
        if self.pipeline_running:
            self.save_queue.put('STOP')
            self.pipeline_process.join()
            self.pipeline_running = False
            print("Pipeline stopped.")

        self._update_process_menu()


    def _on_capture(self):
        if not self.registration_running:
            start_time = time.time()
            complete_message = self.capture_point_cloud()

            if complete_message == "SAVED":
                if self.load_point_cloud(f"{self.captured_pcd_folder_path}\\{self.pipeline_start_time}\\output.ply") == "success":
                    # 计算时间差
                    end_time = time.time()
                    total_time = end_time - start_time
                    print(f"Total capture time: {total_time:.6f} seconds")
        else:
            print("Registration is already in progress.")
            self.registration_captured = True

    def capture_point_cloud(self, filename="output.ply"):
        """处理捕获点云的逻辑"""
        current_status, current_color = self.get_status()  # 保存當前狀態和顏色
        self.update_status("Capturing Point Cloud", (1, 0.65, 0))  # 更新狀態為捕捉中
        
        try:
            if self.pipeline_running:
                self.save_queue.put(filename)  # 发送保存指令
                return_value = self.complete_queue.get()  # 等待保存完成
                return return_value
        finally:
            # 無論捕捉是否成功，最後都恢復之前的狀態和顏色
            self.update_status(current_status, current_color)


    def _on_registration_start(self):
        """使用线程处理启动 Registration 的逻辑"""
        if not self.registration_running and self.pipeline_running:
            # 通知主进程开始录制
            #self._on_start_recording()
            #print("Starting recording...")

            # 设置配准状态为运行中
            self.registration_running = True
            print("Registration started using threads.")
            self.update_status("Registration Started", (0, 0, 1))
            self.registration_thread = threading.Thread(target=self.registration)
            self.registration_thread.start()
            
        self._update_process_menu()

    def _on_registration_stop(self):
        """处理关闭 Registration 的逻辑"""
        if self.registration_running:
            self.registration_running = False
            self.registration_captured = True
            self.registration_thread.join()
            print("Registration stopped.")
            self.update_status("Idle", (0, 1, 0))
            # 通知主进程停止录制
            #self._on_stop_recording()
            #print("Recording stopped.")

        self._update_process_menu()

    def _on_start_cv(self):
        """处理开启 CV 的逻辑"""
        if not self.cv_running and self.pipeline_running:
            self.parent_conn.send("START_CV")
            self.cv_running = True
            print("CV started.")
        self._update_process_menu()

    def _on_stop_cv(self):
        """处理关闭 CV 的逻辑"""
        if self.cv_running:
            self.parent_conn.send("STOP_CV")
            self.cv_running = False
            print("CV stopped.")
        self._update_process_menu()

    def _on_start_recording(self):
        """处理开启录制的逻辑"""
        if not self.recording and self.pipeline_running:
            self.parent_conn.send("START_RECORDING")
            self.recording = True
            print("Recording started.")
        self._update_process_menu()
        
    def _on_stop_recording(self):
        """处理关闭录制的逻辑"""
        if self.recording:
            self.parent_conn.send("STOP_RECORDING")
            self.recording = False
            print("Recording stopped.")
            self._on_pipeline_stop()
        self._update_process_menu()

    def _update_process_menu(self):
        """根据 pipeline、CV 和 Registration 的状态更新 Process 菜单的状态"""
        gui.Application.instance.menubar.set_enabled(OnlineRegistration.MENU_PIPELINE_START, not self.pipeline_running)
        gui.Application.instance.menubar.set_enabled(OnlineRegistration.MENU_PIPELINE_STOP, self.pipeline_running)

        # 如果 registration 正在运行，禁用 capture；否则根据 pipeline 状态启用/禁用 capture
        gui.Application.instance.menubar.set_enabled(OnlineRegistration.MENU_CAPTURE, self.pipeline_running)

        # 根据 Registration 的状态启用/禁用菜单项
        gui.Application.instance.menubar.set_enabled(OnlineRegistration.MENU_TOGGLE_AUTO_REGISTRATION, self.pipeline_running)
        gui.Application.instance.menubar.set_enabled(OnlineRegistration.MENU_REGISTRATION_START, self.pipeline_running and not self.registration_running)
        gui.Application.instance.menubar.set_enabled(OnlineRegistration.MENU_REGISTRATION_STOP, self.registration_running)

        # 根据 CV 的状态启用/禁用菜单项
        gui.Application.instance.menubar.set_enabled(OnlineRegistration.MENU_START_CV, self.pipeline_running and not self.cv_running)
        gui.Application.instance.menubar.set_enabled(OnlineRegistration.MENU_STOP_CV, self.cv_running)

        # 根据 Recording 的状态启用/禁用菜单项
        gui.Application.instance.menubar.set_enabled(
            OnlineRegistration.MENU_START_RECORDING, 
            self.pipeline_running and not self.recording and not self.registration_running
        )
        gui.Application.instance.menubar.set_enabled(
            OnlineRegistration.MENU_STOP_RECORDING, 
            self.recording and not self.registration_running
        )

        self.depth_max_slider.enabled = self.pipeline_running
        self.depth_min_slider.enabled = self.pipeline_running
        self.x_max_slider.enabled = self.pipeline_running
        self.x_min_slider.enabled = self.pipeline_running

        if self.registration_mode == "RANSAC":
            self.ransac_layout.visible = True
        else:
            self.ransac_layout.visible = False

        self.window.set_needs_layout()

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

      
    def registration(self):
        self.filename_counter = 1
        voxel_size = self.voxel_size
        target = None
        source = None

        #顯示當前目錄位置
        print(f"Current directory: {os.getcwd()}")
        try:
            print("Registration started.")
            start_time = time.time()

            registration_start_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            merged_pcd_path = self.check_or_create_folder(f"{self.registration_pcd_folder_path}\\{registration_start_time}")

            if self.current_pcd == None:
                print("No point cloud loaded. Capturing point cloud as target.")
                if self.capture_point_cloud(f"pc{self.filename_counter}.ply") != "SAVED":
                    print("Failed to capture point cloud.")
                    return
                print(f"captured target: {time.time() - start_time:.6f} seconds")
                target = o3d.io.read_point_cloud(f"{self.captured_pcd_folder_path}\\{self.pipeline_start_time}\\pc{self.filename_counter}.ply")
            else:
                print("Using current point cloud as target.")
                target = self.current_pcd
                o3d.io.write_point_cloud(f"{self.captured_pcd_folder_path}\\{self.pipeline_start_time}\\pc{self.filename_counter}.ply", target)

            self.filename_counter += 1

            while self.registration_running:
                try:
                    print("start capturing source")
                    capture_source_time = time.time()
                    if self.capture_point_cloud(f"pc{self.filename_counter}.ply") != "SAVED":
                        break
                    print(f"captured source: {time.time() - capture_source_time:.6f} seconds")
                    
                    source = o3d.io.read_point_cloud(f"{self.captured_pcd_folder_path}\\{self.pipeline_start_time}\\pc{self.filename_counter}.ply")
                    self.filename_counter += 1

                    print("registering and merging")
                    register_and_merge_start = time.time()

                    args = {
                        "voxel_size": voxel_size,
                        "ransac_distance_multiplier": self.ransac_distance_multiplier,
                        "ransac_max_iterations": self.ransac_max_iterations,
                        "ransac_max_validation": self.ransac_max_validation,
                        "icp_distance_multiplier": self.icp_distance_multiplier
                    }
                    self.update_status("Registering...", (1, 0, 0))
                    target = register_and_merge(target, source, self.registration_mode, args)
                    
                    print(f"registered and merged: {time.time() - register_and_merge_start:.6f} seconds")
                    if target is None:
                            raise RuntimeError("Failed to merge point clouds.")
                    
                    o3d.io.write_point_cloud(f"{merged_pcd_path}\\merged_{int(time.time())}.ply", target)
                    self.load_pcd(target)
                    source = None
                    self.registration_captured = False
                    if not self.is_auto_registration:
                        self.update_status("Waiting for user to press Capture", (1, 1, 0))
                        while not self.registration_captured and not self.is_auto_registration:
                            time.sleep(0.2)
                        

                except Exception as e:
                        error_message = f"Error during processing: {e}"
                        print(error_message)
        
        except Exception as e:
            error_message = f"Error during processing: {e}"
            print(error_message)
        
        finally:
            print("registration done")
            print(f"Total registration time: {time.time() - start_time:.6f} seconds")

    def _on_window_close(self):
        # 停止任何正在執行的 CV
        if self.cv_running:
            self._on_stop_cv()

        # 停止任何正在執行的 Registration
        if self.registration_running:
            self._on_registration_stop()

        # 停止 Pipeline
        if self.pipeline_running:
            self._on_pipeline_stop()

        # 如果有任何執行緒或子程序需要強制終止，請在此處處理

        # 返回 True 以允許視窗關閉
        return True


def register_and_merge(target, source, registration_mode, args):
    """
    对 source 和 target 进行配准和合并操作，并对结果进行降采样。
    """
    if target is None or source is None:
        print("Target or Source is not set. Please set both before registration.")
        return None

    start_time = time.time()

    try:
        print("Starting registration...")

        # 执行配准
        if registration_mode == "RANSAC":
            result_icp = pcr_ransac.perform_registration(source, target, voxel_size=args["voxel_size"], 
                                                         ransac_distance_multiplier=args["ransac_distance_multiplier"],
                                                         ransac_max_iterations=args["ransac_max_iterations"],
                                                         ransac_max_validation=args["ransac_max_validation"],
                                                         icp_distance_multiplier=args["icp_distance_multiplier"])
        elif registration_mode == "FAST":
            result_icp = pcr_fast.perform_fast_registration(source, target, voxel_size=args["voxel_size"])
        elif registration_mode == "P2POINT":
            result_icp = pcr_p2point.point_to_point_icp(source, target, voxel_size=args["voxel_size"])
        elif registration_mode == "P2PLANE":
            result_icp = pcr_p2plane.point_to_plane_icp(source, target, voxel_size=args["voxel_size"])
        elif registration_mode == "COLORED":
            result_icp = pcr_colored.colored_icp(source, target, voxel_size=args["voxel_size"])
        # 应用配准变换到 source
        source.transform(result_icp.transformation)
        print("Applied transformation to source.")

        # 合并 target 和 source
        merged_cloud = target + source
        print("Merged target and source point clouds.")

        # 对合并后的点云进行降采样
        downsampled_cloud = merged_cloud.voxel_down_sample(args["voxel_size"])
        print("Downsampled the merged point cloud.")

        return downsampled_cloud

    except Exception as e:
        print(f"Error during registration and merging: {e}")
        return None

    finally:
        end_time = time.time()
        duration = end_time - start_time
        print(f"Registration and merging took {duration:.2f} seconds.")

'''

舊版 pipeline_process

def pipeline_process(start_queue, save_queue, complete_queue, conn, rgbd_video, pipeline_start_time):
    """子进程运行的函数，负责执行 PipelineModel 的操作"""
    try:
        model = PipelineModel(pipeline_start_time, camera_config_file=None, rgbd_video=rgbd_video)
    except RuntimeError as e:
        start_queue.put("ERROR")
        print(f"Pipeline process failed to start: {e}")
        return
    
    # 启动捕获引擎并等待其启动成功
    model.start_capture_engine()
    model.capture_started_event.wait()  # 等待捕获引擎成功启动并捕获到第一帧数据

    while model._get_current_point_cloud() is None:
        time.sleep(0.1)
        
    start_queue.put("START")

    while True:
        # 检查是否有来自主进程的命令
        if conn.poll():
            command = conn.recv()
            print(f"Received command: {command}")
            if isinstance(command, tuple):
                if command[0] == "SET_DEPTH_MAX":
                    depth_max_value = command[1]
                    model.set_depth_max(depth_max_value)
                    print(f"Depth max updated to {depth_max_value} in PipelineModel.")
                elif command[0] == "SET_DEPTH_MIN":
                    depth_min_value = command[1]
                    model.set_depth_min(depth_min_value)
                    print(f"Depth min updated to {depth_min_value} in PipelineModel.")
                elif command[0] == "SET_X_MAX":
                    x_max_value = command[1]
                    model.set_x_max(x_max_value)
                    print(f"X max updated to {x_max_value} in PipelineModel.")
                elif command[0] == "SET_X_MIN":
                    x_min_value = command[1]
                    model.set_x_min(x_min_value)
                    print(f"X min updated to {x_min_value} in PipelineModel.")
            else:
                if command == "START_CV":
                    model.show_depth_image()
                elif command == "STOP_CV":
                    model.stop_depth_image()
                elif command == "START_RECORDING":
                    model.start_recording()
                elif command == "STOP_RECORDING":
                    model.stop_recording()
                    break  # 如果需要在停止录制后退出子进程，可以保留这行，否则可以去掉

        # 检查保存队列
        if not save_queue.empty():
            save_path = save_queue.get()
            if save_path == 'STOP':
                break
            if save_path.lower().endswith('.ply'):
                model.save_point_cloud(save_path)
                complete_queue.put("SAVED")
            else:
                print(f"Invalid save path: {save_path}")

    model.close()

'''


def pipeline_process(start_queue, save_queue, complete_queue, conn, rgbd_video, pipeline_start_time):
    import os
    import time
    import cv2
    import psutil

    parent_pid = os.getppid()

    try:
        model = PipelineModel(pipeline_start_time, camera_config_file=None, rgbd_video=rgbd_video)
    except RuntimeError as e:
        start_queue.put("ERROR")
        print(f"Pipeline process failed to start: {e}")
        return

    # 启动捕获引擎并等待其启动成功
    model.start_capture_engine()
    model.capture_started_event.wait()

    while model._get_current_point_cloud() is None:
        time.sleep(0.1)

    start_queue.put("START")

    while True:
        # 检查父进程是否仍然存在
        if not psutil.pid_exists(parent_pid):
            print("Parent process has terminated. Exiting child process.")
            break

        # 尝试从管道接收数据
        try:
            if conn.poll():
                command = conn.recv()
                #print(f"Received command: {command}")
                if isinstance(command, tuple):
                    if command[0] == "SET_DEPTH_MAX":
                        depth_max_value = command[1]
                        model.set_depth_max(depth_max_value)
                    elif command[0] == "SET_DEPTH_MIN":
                        depth_min_value = command[1]
                        model.set_depth_min(depth_min_value)
                    elif command[0] == "SET_X_MAX":
                        x_max_value = command[1]
                        model.set_x_max(x_max_value)
                    elif command[0] == "SET_X_MIN":
                        x_min_value = command[1]
                        model.set_x_min(x_min_value)
                else:
                    if command == "START_CV":
                        model.show_depth_image()
                    elif command == "STOP_CV":
                        model.stop_depth_image()
                    elif command == "START_RECORDING":
                        model.start_recording()
                    elif command == "STOP_RECORDING":
                        model.stop_recording()

        except (EOFError, BrokenPipeError):
            # 如果连接断开，等待一段时间再重试，而不是立即退出
            print("Connection to parent process lost. Waiting to reconnect...")
            time.sleep(1)
            continue  # 重新开始循环，检查父进程是否存在

        # 检查保存队列
        if not save_queue.empty():
            save_path = save_queue.get()
            if save_path == 'STOP':
                break
            if save_path.lower().endswith('.ply'):
                model.save_point_cloud(save_path)
                complete_queue.put("SAVED")
            else:
                print(f"Invalid save path: {save_path}")

    # 在退出前关闭 OpenCV 窗口
    model.close()
    cv2.destroyAllWindows()
    print("Child process exited gracefully.")


    

def main():
    gui.Application.instance.initialize()
    w = OnlineRegistration(1600, 900)
    gui.Application.instance.run()

if __name__ == "__main__":
    print("Starting Open3D Online Processing PC Visualizer")
    sys.stdout.flush()
    main()
