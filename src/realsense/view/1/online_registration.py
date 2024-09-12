import open3d as o3d
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering
import platform
import threading
import multiprocessing
import logging
import sys
import time
import queue
import os

from pipeline_model import pipeline_process, PipelineModel  # Import your pipeline_process and PipelineModel
import point_cloud_registration as pcr

isMacOS = (platform.system() == "Darwin")

# 初始化 logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class OnlineRegistration:
    MENU_OPEN = 1
    MENU_QUIT = 3
    MENU_SHOW_SETTINGS = 11
    MENU_ABOUT = 21
    MENU_PIPELINE_START = 31
    MENU_PIPELINE_STOP = 32
    MENU_CAPTURE = 33
    MENU_START_CV = 34
    MENU_STOP_CV = 35
    MENU_REGISTRATION_START = 36
    MENU_REGISTRATION_STOP = 37

    def __init__(self, width, height):
        self.pcds = []
        self.current_index = -1
        self.imported_filenames = []

        self.pipeline_running = False
        self.cv_running = False

        # 初始化进程间通信队列和管道
        self.start_queue = multiprocessing.Queue()
        self.save_queue = multiprocessing.Queue()
        self.complete_queue = multiprocessing.Queue()
        self.parent_conn, self.child_conn = multiprocessing.Pipe()

        self.filename_queue = queue.Queue()
        self.output_queue = queue.Queue()
        self.status_queue = queue.Queue()
        self.error_queue = queue.Queue()
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
        self._settings_panel.visible = True

        self.refresh_view_on_mode_change = True

        gui.Application.instance.menubar.set_checked(OnlineRegistration.MENU_SHOW_SETTINGS, self.view_ctrls.visible)

        self._update_process_menu()  # 初始化时更新 Process 菜单项

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

            process_menu = gui.Menu()
            process_menu.add_item("Start Pipeline", OnlineRegistration.MENU_PIPELINE_START)
            process_menu.add_item("Stop Pipeline", OnlineRegistration.MENU_PIPELINE_STOP)
            process_menu.add_separator()
            process_menu.add_item("Registration Start", OnlineRegistration.MENU_REGISTRATION_START)
            process_menu.add_item("Registration Stop", OnlineRegistration.MENU_REGISTRATION_STOP)
            process_menu.add_separator()
            process_menu.add_item("Capture", OnlineRegistration.MENU_CAPTURE)
            process_menu.add_item("Start CV", OnlineRegistration.MENU_START_CV)
            process_menu.add_item("Stop CV", OnlineRegistration.MENU_STOP_CV)

            help_menu = gui.Menu()
            help_menu.add_item("About", OnlineRegistration.MENU_ABOUT)

            menu = gui.Menu()
            if isMacOS:
                menu.add_menu("Example", app_menu)
                menu.add_menu("File", file_menu)
                menu.add_menu("Settings", settings_menu)
                menu.add_menu("Process", process_menu)  # 添加 Process 菜单
            else:
                menu.add_menu("File", file_menu)
                menu.add_menu("Settings", settings_menu)
                menu.add_menu("Process", process_menu)  # 添加 Process 菜单
                menu.add_menu("Help", help_menu)
            gui.Application.instance.menubar = menu

        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_OPEN, self._on_menu_open)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_QUIT, self._on_menu_quit)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_SHOW_SETTINGS, self._on_menu_toggle_view_controls)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_ABOUT, self._on_menu_about)

        # Process menu items
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_PIPELINE_START, self._on_pipeline_start)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_PIPELINE_STOP, self._on_pipeline_stop)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_CAPTURE, self._on_capture)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_REGISTRATION_START, self._on_registration_start)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_REGISTRATION_STOP, self._on_registration_stop)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_START_CV, self._on_start_cv)
        self.window.set_on_menu_item_activated(OnlineRegistration.MENU_STOP_CV, self._on_stop_cv)

    def _setup_settings_panel(self):
        em = self.window.theme.font_size
        self._settings_panel = gui.Vert(0, gui.Margins(0.25 * em, 0.25 * em, 0.25 * em, 0.25 * em))

        self.view_ctrls = gui.CollapsableVert("View controls", 0.25 * em, gui.Margins(em, 0, 0, 0))
        self._setup_view_controls()
        self._settings_panel.add_child(self.view_ctrls)

        self.window.add_child(self._settings_panel)

    def _setup_view_controls(self):
        em = self.window.theme.font_size
        grid1 = gui.VGrid(2, 0.25 * em)
        
        grid1.add_child(gui.Label("BG Color"))
        self._bg_color = gui.ColorEdit()
        self._bg_color.color_value = gui.Color(1, 1, 1)
        self._bg_color.set_on_value_changed(self._on_bg_color_changed)
        grid1.add_child(self._bg_color)

        self.view_ctrls.add_child(grid1)

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
        self._on_stop_cv()  # 确保在退出时停止 CV
        self._on_pipeline_stop()  # 确保在退出时停止 Pipeline
        gui.Application.instance.quit()

    def _on_menu_toggle_view_controls(self):
        self.view_ctrls.visible = not self.view_ctrls.visible
        self._update_settings_panel_visibility()

    def _update_settings_panel_visibility(self):
        self._settings_panel.visible = self.view_ctrls.visible
        gui.Application.instance.menubar.set_checked(OnlineRegistration.MENU_SHOW_SETTINGS, self.view_ctrls.visible)
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
            else:
                print(f"Failed to load point cloud")
        
        except Exception as e:
            print(f"An error occurred: {e}")

    def _on_pipeline_start(self):
        """处理启动 pipeline 的逻辑"""
        if not self.pipeline_running:
            try:
                self.pipeline_process = multiprocessing.Process(
                    target=pipeline_process, 
                    args=(self.start_queue, self.save_queue, self.complete_queue, self.child_conn)
                )
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
        start_time = time.time()
        complete_message = self.capture_point_cloud()

        if complete_message == "SAVED":
            if self.load_point_cloud("output.ply") == "success":
                # 计算时间差
                end_time = time.time()
                total_time = end_time - start_time
                print(f"Total capture time: {total_time:.6f} seconds")

    def capture_point_cloud(self, filename = "output.ply"):
        """处理捕获点云的逻辑"""
        if self.pipeline_running:
            self.save_queue.put(filename)  # 发送保存指令

            return self.complete_queue.get()  # 等待保存完成

    def _on_registration_start(self):
        """使用线程处理启动 Registration 的逻辑"""
        if not self.registration_running and self.pipeline_running:
            # 设置配准状态为运行中
            self.registration_running = True
            print("Registration started using threads.")
            
            self.registration_thread = threading.Thread(target=self.registration)
            self.registration_thread.start()
            
        self._update_process_menu()

    def _on_registration_stop(self):
        """处理关闭 Registration 的逻辑"""
        if self.registration_running:
            self.registration_running = False
            self.registration_thread.join()
            print("Registration stopped.")

        self._update_process_menu()

    def registration_process(self, filename_queue, output_queue, status_queue, error_queue):
        """
        持续进行点云配准的线程函数。

        :param filename_queue: 用于接收文件名的队列
        :param output_queue: 用于输出合并点云的队列
        :param status_queue: 用于传达状态的队列
        :param error_queue: 用于传达错误信息的队列
        """
        try:
            # 初始化 target 和 source 为 None
            target = None
            source = None
            voxel_size = 0.03  # 设置体素大小用于降采样

            # 从 filename_queue 中读取第一个文件作为 target
            first_filename = filename_queue.get()
            if first_filename == "STOP":
                return

            print(f"Loading first point cloud from {first_filename} as target...")
            target = o3d.io.read_point_cloud(first_filename)  # 读取点云文件
            print(f"target's point count: {len(target.points)}")
            if target is None:
                raise ValueError(f"Failed to load point cloud: {first_filename}")

            while self.registration_running:
                try:
                    # 从 filename_queue 获取文件名
                    next_filename = filename_queue.get()
                    if next_filename == "STOP":
                        print("Received STOP signal. Exiting thread...")
                        status_queue.put("STOPPED")
                        return

                    print(f"Loading next point cloud from {next_filename} as source...")
                    source = o3d.io.read_point_cloud(next_filename)
                    print(f"source's point count: {len(source.points)}")
                    if source is None:
                        raise ValueError(f"Failed to load point cloud: {next_filename}")
    
                    # 执行配准和合并
                    merged_cloud = register_and_merge(target, source, voxel_size)
                    if merged_cloud is None:
                        raise RuntimeError("Failed to merge point clouds.")

                    # 更新 target 为合并后的点云，source 置为 None
                    target = merged_cloud
                    source = None

                    # 将合并后的点云保存并传递文件名到 output_queue
                    output_filename = f"merged_{int(time.time())}.ply"
                    o3d.io.write_point_cloud(output_filename, merged_cloud)
                    print(f"Merged point count: {len(merged_cloud.points)}")
                    output_queue.put(output_filename)  # 向主线程传递合并后的文件名

                    print(f"Merged cloud saved to {output_filename}")

                except Exception as e:
                    error_message = f"Error during processing: {e}"
                    print(error_message)
                    error_queue.put(error_message)  # 将错误信息传递到 error_queue

        finally:
            print("Registration thread has been terminated.")
            status_queue.put("TERMINATED")

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

    def _update_process_menu(self):
        """根据 pipeline、CV 和 Registration 的状态更新 Process 菜单的状态"""
        gui.Application.instance.menubar.set_enabled(OnlineRegistration.MENU_PIPELINE_START, not self.pipeline_running)
        gui.Application.instance.menubar.set_enabled(OnlineRegistration.MENU_PIPELINE_STOP, self.pipeline_running)
        
        # 如果 registration 正在运行，禁用 capture；否则根据 pipeline 状态启用/禁用 capture
        gui.Application.instance.menubar.set_enabled(OnlineRegistration.MENU_CAPTURE, self.pipeline_running and not self.registration_running)

        # 根据 Registration 的状态启用/禁用菜单项
        gui.Application.instance.menubar.set_enabled(OnlineRegistration.MENU_REGISTRATION_START, self.pipeline_running and not self.registration_running)
        gui.Application.instance.menubar.set_enabled(OnlineRegistration.MENU_REGISTRATION_STOP, self.registration_running)

        # 根据 CV 的状态启用/禁用菜单项
        gui.Application.instance.menubar.set_enabled(OnlineRegistration.MENU_START_CV, self.pipeline_running and not self.cv_running)
        gui.Application.instance.menubar.set_enabled(OnlineRegistration.MENU_STOP_CV, self.cv_running)

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
        voxel_size = 0.05
        target = None
        source = None

        try:
            print("Registration started.")
            start_time = time.time()
            if self.capture_point_cloud(f"pc{self.filename_counter}.ply") != "SAVED":
                print("Failed to capture point cloud.")
                return
            print(f"captured target: {time.time() - start_time:.6f} seconds")
            target = o3d.io.read_point_cloud(f"pc{self.filename_counter}.ply")
            self.filename_counter += 1

            while self.registration_running:
                try:
                    print("start capturing source")
                    capture_source_time = time.time()
                    if self.capture_point_cloud(f"pc{self.filename_counter}.ply") != "SAVED":
                        break
                    print(f"captured source: {time.time() - capture_source_time:.6f} seconds")
                    
                    source = o3d.io.read_point_cloud(f"pc{self.filename_counter}.ply")
                    self.filename_counter += 1

                    print("registering and merging")
                    register_and_merge_start = time.time()
                    target = register_and_merge(target, source, voxel_size)
                    print(f"registered and merged: {time.time() - register_and_merge_start:.6f} seconds")
                    if target is None:
                            raise RuntimeError("Failed to merge point clouds.")
                    
                    o3d.io.write_point_cloud(f"merged_{int(time.time())}.ply", target)
                    self.load_pcd(target)
                    source = None

                except Exception as e:
                        error_message = f"Error during processing: {e}"
                        print(error_message)
        
        except Exception as e:
            error_message = f"Error during processing: {e}"
            print(error_message)
        
        finally:
            print("registration done")
            print(f"Total registration time: {time.time() - start_time:.6f} seconds")

    def register_and_merge(target, source, voxel_size):
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
            result_icp = pcr.perform_registration(source, target, voxel_size=voxel_size)

            # 应用配准变换到 source
            source.transform(result_icp.transformation)
            print("Applied transformation to source.")

            # 合并 target 和 source
            merged_cloud = target + source
            print("Merged target and source point clouds.")

            # 对合并后的点云进行降采样
            downsampled_cloud = merged_cloud.voxel_down_sample(voxel_size)
            print("Downsampled the merged point cloud.")

            return downsampled_cloud

        except Exception as e:
            print(f"Error during registration and merging: {e}")
            return None

        finally:
            end_time = time.time()
            duration = end_time - start_time
            print(f"Registration and merging took {duration:.2f} seconds.") 


def pipeline_process(start_queue, save_queue, complete_queue, conn):
    """子进程运行的函数，负责执行PipelineModel的操作"""
    try:
        model = PipelineModel(camera_config_file=None, rgbd_video=None)
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
        if conn.poll():  # 检查是否有来自主进程的命令
            command = conn.recv()
            if command == "START_CV":
                model.show_depth_image()
            elif command == "STOP_CV":
                model.stop_depth_image()

        if not save_queue.empty():
            save_path = save_queue.get()  # 等待从主进程接收保存指令
            if save_path == 'STOP':
                break
            model.save_point_cloud(save_path)
            complete_queue.put("SAVED")  # 通知主进程保存完成

    model.close()

def register_and_merge(target, source, voxel_size):
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
        result_icp = pcr.perform_registration(source, target, voxel_size=voxel_size)

        # 应用配准变换到 source
        source.transform(result_icp.transformation)
        print("Applied transformation to source.")

        # 合并 target 和 source
        merged_cloud = target + source
        print("Merged target and source point clouds.")

        # 对合并后的点云进行降采样
        downsampled_cloud = merged_cloud.voxel_down_sample(voxel_size)
        print("Downsampled the merged point cloud.")

        return downsampled_cloud

    except Exception as e:
        print(f"Error during registration and merging: {e}")
        return None

    finally:
        end_time = time.time()
        duration = end_time - start_time
        print(f"Registration and merging took {duration:.2f} seconds.")


    

def main():
    gui.Application.instance.initialize()
    w = OnlineRegistration(1024, 768)
    gui.Application.instance.run()

if __name__ == "__main__":
    print("Starting Open3D Online Processing PC Visualizer")
    sys.stdout.flush()
    main()
