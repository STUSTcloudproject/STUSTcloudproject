import threading
import time
import open3d as o3d
from datetime import datetime
import logging
import numpy as np
import cv2  # 导入OpenCV
import os
import multiprocessing

# 初始化 logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class PipelineModel:
    """控制I/O（相機、視頻文件、錄製、保存幀）。"""

    def __init__(self, camera_config_file=None, rgbd_video=None, device=None):
        """初始化 PipelineModel，包括相机或 .bag 文件"""
        self.rgbd_video = rgbd_video

        # 设备初始化
        if device:
            self.device = device.lower()
        else:
            self.device = 'cuda:0' if o3d.core.cuda.is_available() else 'cpu:0'
        self.o3d_device = o3d.core.Device(self.device)

        # 各种状态变量初始化
        self.video = None
        self.camera = None
        self.rgbd_frame = None
        self.positions = None
        self.colors = None
        self.pcd_frame = None
        self.flag_running = False  # 用于控制持续捕获的开关
        self.show_depth_flag = False  # 控制深度图像显示的标志
        self.depth_thread = None  # 深度图像线程
        self.recording = False  # 控制录制的标志

        # 设置保存的文件名
        self.filename = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.bag"

        # 事件，用于通知捕获已经开始
        self.capture_started_event = threading.Event()

        try:
            # 如果是 .bag 文件，尝试加载 .bag 文件
            if rgbd_video:
                log.info(f"Attempting to open .bag file: {rgbd_video}")
                
                # 确保文件存在
                if not os.path.exists(rgbd_video):
                    raise FileNotFoundError(f"Provided .bag file does not exist: {rgbd_video}")

                # 尝试打开 .bag 文件
                self.video = o3d.t.io.RGBDVideoReader.create(rgbd_video)
                if not self.video.is_opened():
                    raise RuntimeError(f"Failed to open .bag file: {rgbd_video}")
                
                # 获取视频元数据
                self.rgbd_metadata = self.video.metadata
                self.status_message = f"Video {rgbd_video} opened successfully."
                log.info(self.status_message)

            else:
                # 启动相机捕获
                log.info("Initializing RealSense camera...")
                self.camera = o3d.t.io.RealSenseSensor()

                if camera_config_file:
                    log.info(f"Using camera config file: {camera_config_file}")
                    # 加载相机配置文件
                    with open(camera_config_file) as ccf:
                        self.camera.init_sensor(o3d.t.io.RealSenseSensorConfig(json.load(ccf)),
                                                filename=self.filename)
                else:
                    log.info(f"No camera config file provided, initializing with default settings.")
                    self.camera.init_sensor(filename=self.filename)
                
                self.camera.start_capture(start_record=False)  # 启动相机但不开始录制
                self.rgbd_metadata = self.camera.get_metadata()
                self.status_message = f"Camera {self.rgbd_metadata.serial_number} initialized successfully."
                log.info(self.status_message)

            # 打印相机或 .bag 文件的元数据
            log.info(self.rgbd_metadata)

            # 初始化 RGBD 到 PCD 的转换参数
            self.extrinsics = o3d.core.Tensor.eye(4, dtype=o3d.core.Dtype.Float32, device=self.o3d_device)
            self.intrinsic_matrix = o3d.core.Tensor(
                self.rgbd_metadata.intrinsics.intrinsic_matrix,
                dtype=o3d.core.Dtype.Float32,
                device=self.o3d_device
            )
            self.depth_max = 3.0  # 最大深度
            self.pcd_stride = 2  # 下采样点云，可能会提高帧率

            # 启动数据捕获引擎
            self.start_capture_engine()

        except Exception as e:
            log.error(f"Failed to initialize camera or load .bag file: {e}")
            self.camera = None  # 确保在错误情况下，相机对象被清除
            self.status_message = "Failed to initialize RealSense camera or load .bag file."
            print(self.status_message)
            raise

    def rotate_pcd_180_x(self):
        """Rotate the point cloud along the X axis by 180 degrees."""
        R = np.eye(3, dtype=np.float32)  # 確保旋轉矩陣是 Float32
        R[1, 1], R[1, 2] = -1, 0
        R[2, 1], R[2, 2] = 0, -1
        
        # 如果位置不是 Float32，將其轉換為 Float32
        if self.pcd_frame.point.positions.dtype != o3d.core.Dtype.Float32:
            self.pcd_frame.point.positions = self.pcd_frame.point.positions.to(o3d.core.Dtype.Float32)
        
        self.pcd_frame.point.positions = self.pcd_frame.point.positions @ R.T

    def capture_point_cloud(self):
        """處理並獲取當前幀的點雲數據"""
        if self.rgbd_frame is not None:
            self.rgbd_frame = self.rgbd_frame.to(self.o3d_device)
            self.pcd_frame = o3d.t.geometry.PointCloud.create_from_rgbd_image(
                self.rgbd_frame, self.intrinsic_matrix, self.extrinsics,
                self.rgbd_metadata.depth_scale, self.depth_max, self.pcd_stride, False)
            
            if not self.pcd_frame.is_empty():
                self.rotate_pcd_180_x()
                self.positions = self.pcd_frame.cpu().point.positions.numpy()
                self.colors = self.pcd_frame.cpu().point.colors.numpy()
                return self.positions, self.colors
            else:
                log.warning("當前幀沒有有效的深度數據")
                return None, None
        return None, None

    def create_point_cloud(self):
        """根據捕獲的點雲數據創建 Open3D PointCloud 對象"""
        positions, colors = self.capture_point_cloud()

        if positions is not None and colors is not None:
            if colors.dtype == np.uint8:
                colors_normalized = colors.astype(np.float32) / 255.0
            else:
                colors_normalized = np.clip(colors, 0, 1)

            point_cloud = o3d.geometry.PointCloud()
            point_cloud.points = o3d.utility.Vector3dVector(positions)
            point_cloud.colors = o3d.utility.Vector3dVector(colors_normalized)

            return point_cloud
        return None

    def get_depth_and_color_image(self):
        """获取当前帧的深度图像和颜色图像并返回适合显示的格式和分辨率"""
        if self.rgbd_frame is not None:
            try:

                # 檢查深度和顏色圖像是否為 None
                if self.rgbd_frame.depth is None:
                    log.error("Depth image is None.")
                    return None, None
                if self.rgbd_frame.color is None:
                    log.error("Color image is None.")
                    return None, None

                depth_image = self.rgbd_frame.depth.to_legacy()
                color_image = self.rgbd_frame.color.to_legacy()

                # 將 Open3D 的圖像對象轉換為 NumPy 數組
                depth_array = np.asarray(depth_image)
                color_array = np.asarray(color_image)

                # 確保轉換後的深度和顏色圖像不是 None
                if depth_array is None or depth_array.size == 0:
                    return None, None
                if color_array is None or color_array.size == 0:
                    return None, None

                # 归一化深度图，使其可以显示
                depth_array_normalized = cv2.normalize(depth_array, None, 0, 255, cv2.NORM_MINMAX)
                depth_array_normalized = np.uint8(depth_array_normalized)

                # 将颜色图像从 RGB 转换为 BGR
                color_array_bgr = cv2.cvtColor(color_array, cv2.COLOR_RGB2BGR)

                return depth_array_normalized, color_array_bgr

            except Exception as e:
                log.error(f"Error processing depth and color images: {e}", exc_info=True)
                return None, None
        else:
            log.error("RGBD frame is None.")
            return None, None


    def _show_depth_image_internal(self):
        """内部方法，在线程中显示深度图像和颜色图像"""
        try:
            while self.show_depth_flag:
                depth_image, color_image = self.get_depth_and_color_image()
                if depth_image is not None and color_image is not None:
                    # 缩小图像尺寸，例如缩小为原来的 50%
                    scale_percent = 50  # 缩小比例
                    width_depth = int(depth_image.shape[1] * scale_percent / 100)
                    height_depth = int(depth_image.shape[0] * scale_percent / 100)
                    dim_depth = (width_depth, height_depth)
                    
                    width_color = int(color_image.shape[1] * scale_percent / 100)
                    height_color = int(color_image.shape[0] * scale_percent / 100)
                    dim_color = (width_color, height_color)

                    # 使用 cv2.resize 缩小图像
                    resized_depth_image = cv2.resize(depth_image, dim_depth, interpolation=cv2.INTER_AREA)
                    resized_color_image = cv2.resize(color_image, dim_color, interpolation=cv2.INTER_AREA)

                    # 将深度图像转换为彩色映射
                    depth_colormap = cv2.applyColorMap(resized_depth_image, cv2.COLORMAP_JET)

                    # 水平拼接深度图像和颜色图像
                    combined_image = np.hstack((depth_colormap, resized_color_image))

                    # 显示拼接后的图像
                    cv2.imshow('Depth and Color Image', combined_image)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        self.show_depth_flag = False  # 允许通过按 'q' 键退出
                        break
        except Exception as e:
            print(f"Error displaying depth and color image: {e}")
        finally:
            cv2.destroyAllWindows()

    def show_depth_image(self):
        """显示深度图像"""
        if not self.show_depth_flag:
            self.show_depth_flag = True
            self.depth_thread = threading.Thread(target=self._show_depth_image_internal)
            self.depth_thread.start()

    def stop_depth_image(self):
        """停止显示深度图像"""
        self.show_depth_flag = False
        if self.depth_thread and self.depth_thread.is_alive():
            self.depth_thread.join()
        cv2.destroyAllWindows()


    def background_capture(self):
        """持续从相机或视频文件捕获数据"""
        self.capture_started_event.set()  # 通知捕获已经开始
        while self.flag_running:
            if self.video:  # 使用 .bag 文件
                try:
                    if self.video.is_eof():  # 检查是否到达 EOF
                        log.info("EOF reached, restarting video from the beginning.")
                        # 关闭并重新创建 RGBDVideoReader 对象
                        self.video.close()  # 关闭当前文件
                        del self.video  # 销毁当前对象
                        #time.sleep(0.1)  # 给系统一个短暂的时间来释放资源
                        # 使用保存的路径重新打开 .bag 文件
                        self.video = o3d.t.io.RGBDVideoReader.create(self.rgbd_video)
                    
                    # 捕获下一帧
                    self.rgbd_frame = self.video.next_frame()
                    
                    # 檢查 RGBD 幀是否為 None 或無效
                    if self.rgbd_frame is None or self.rgbd_frame.depth is None or self.rgbd_frame.color is None:
                        log.error("Captured RGBD frame is None or contains invalid depth/color data.")
                        continue  # 跳過此幀

                except Exception as e:
                    log.error(f"Error capturing frame: {e}")
                    continue
            else:  # 使用相机
                try:
                    self.rgbd_frame = self.camera.capture_frame(wait=True, align_depth_to_color=True)
                    # 同样添加类似的 None 检查
                    if self.rgbd_frame is None or self.rgbd_frame.depth is None or self.rgbd_frame.color is None:
                        log.error("Captured RGBD frame is None or contains invalid depth/color data.")
                        continue  # 跳過此幀

                except Exception as e:
                    log.error(f"Error capturing frame from camera: {e}")
                    continue

    def start_capture_engine(self):
        """启动数据获取引擎"""
        if not self.flag_running:
            self.flag_running = True
            log.info("Starting the capture engine...")
            self.capture_thread = threading.Thread(target=self.background_capture)
            self.capture_thread.daemon = True  # 设置为守护线程
            self.capture_thread.start()

    def stop_capture_engine(self):
        """停止數據獲取引擎"""
        if self.flag_running:
            self.flag_running = False
            self.capture_thread.join()

    def _get_current_point_cloud(self):
        """返回最新的點雲數據，並可選擇保存為 PLY 文件"""
        return self.create_point_cloud()

    
    def save_point_cloud(self, ply_path="output.ply"):
        """保存最新的點雲數據為 PLY 文件"""
        point_cloud = self._get_current_point_cloud()

        if point_cloud is not None:
            o3d.io.write_point_cloud(ply_path, point_cloud)
            log.info(f"Point cloud data saved to {ply_path}")

    def start_recording(self):
        """开始录制 .bag 文件"""
        if self.camera and not self.recording:
            log.info(f"Starting recording to {self.filename}...")
            self.camera.resume_record()  # 开始录制
            self.recording = True
            log.info(f"Recording started.")

    def stop_recording(self):
        """停止录制 .bag 文件，但不停止捕获"""
        if self.camera and self.recording:
            log.info(f"Stopping recording to {self.filename}...")
            self.camera.pause_record()  # 暂停录制，但不停止捕获
            self.recording = False
            log.info(f"Recording stopped.")
            self.close()



    def close(self):
        """关闭模型并释放资源"""
        self.stop_depth_image()
        self.stop_capture_engine()
        if self.camera:
            if self.recording:
                self.stop_recording()
            log.info("Stopping camera capture...")
            self.camera.stop_capture()  # 仅在关闭程序时停止相机捕获
            log.info("Camera capture stopped.")
        elif self.video:
            self.video.close()



def pipeline_process(start_queue, save_queue, complete_queue, rgbd_video):
    """子进程运行的函数，负责执行PipelineModel的操作"""
    try:
        model = PipelineModel(camera_config_file=None, rgbd_video=rgbd_video)
    except RuntimeError:
        start_queue.put("ERROR")  # 向主进程发送错误状态
        return

    # 启动捕获引擎并等待其启动成功
    model.start_capture_engine()
    model.capture_started_event.wait()  # 等待捕获引擎成功启动并捕获到第一帧数据

    while model._get_current_point_cloud() is None:
        time.sleep(0.1)
        
    start_queue.put("START")

    while True:
        save_path = save_queue.get()  # 等待从主进程接收保存指令
        if save_path == 'STOP':
            log.info("Shutting down pipeline...")
            model.close()  # 顯式關閉 pipeline
            break
        elif save_path == "SHOW_CV":
            model.show_depth_image()
        elif save_path == "HIDE_CV":
            model.stop_depth_image()
        elif save_path == "START_RECORDING":
            model.start_recording()  # 开启录制
        elif save_path == "STOP_RECORDING":
            model.stop_recording()  # 停止录制
            break
        elif save_path.lower().endswith('.ply'):
            model.save_point_cloud(save_path)
            complete_queue.put("SAVED")  # 通知主进程保存完成
        else:
            print(f"Invalid save path: {save_path}")

if __name__ == "__main__":
    start_queue = multiprocessing.Queue()
    save_queue = multiprocessing.Queue()  # Queue for sending save commands
    complete_queue = multiprocessing.Queue()  # Queue for receiving save completion notifications

    # Ask the user whether to use the camera or .bag file
    mode = input("Please select mode: \n1. Use camera\n2. Use .bag file\nEnter '1' or '2': ").strip()

    camera_config_file = None  # Default is no camera configuration file
    rgbd_video = None  # Default is no .bag file

    if mode == '1':
        print("You selected to use the camera.")
        # Optionally ask if the user wants to use a specific camera config file
        use_camera_config = input("Do you want to use a camera config file? (y/n): ").strip().lower()
        if use_camera_config == 'y':
            camera_config_file = input("Please enter the path to the camera config file: ").strip()
            if not os.path.exists(camera_config_file):
                print(f"Camera config file {camera_config_file} does not exist.")
                exit(1)
    elif mode == '2':
        rgbd_video = input("Please enter the path to the .bag file: ").strip()
        if not os.path.exists(rgbd_video):
            print(f".bag file {rgbd_video} does not exist.")
            exit(1)
        print(f"You selected to use the .bag file: {rgbd_video}")
    else:
        print("Invalid choice, please enter '1' or '2'.")
        exit(1)

    # Start the subprocess
    process = multiprocessing.Process(target=pipeline_process, args=(start_queue, save_queue, complete_queue, rgbd_video))
    process.start()

    # Wait for the subprocess to start
    is_started = start_queue.get()
    print(f"Pipeline process started: {is_started}")
    
    if is_started == "START":
        try:
            while True:
                command = input("Enter command (capture, show_cv, hide_cv, start_recording, stop_recording, quit): ").strip().lower()

                if command == 'capture':
                    start_time = time.time()
                    ply_path = "output.ply"
                    save_queue.put(ply_path)  # Send save command

                    complete_message = complete_queue.get()  # Wait for save completion
                    if complete_message == "SAVED":
                        end_time = time.time()
                        print(f"Capture and update time: {end_time - start_time:.6f} seconds")

                elif command == 'show_cv':
                    save_queue.put("SHOW_CV")

                elif command == 'hide_cv':
                    save_queue.put("HIDE_CV")
                
                elif command == 'start_recording':
                    save_queue.put("START_RECORDING")

                elif command == 'stop_recording':
                    save_queue.put("STOP_RECORDING")
                    break

                elif command == 'quit':
                    break

                else:
                    print("Invalid command. Available commands: capture, show_cv, hide_cv, start_recording, stop_recording, quit")

        finally:
            save_queue.put('STOP')  # Send stop signal to the subprocess
            process.join()  # Wait for subprocess to end
    else:
        print("Pipeline model did not start.")
