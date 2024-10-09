import threading
import time
import open3d as o3d
from datetime import datetime
import logging
import numpy as np
import cv2
import os
import multiprocessing

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class PipelineModel:

    def __init__(self, pipeline_start_time, camera_config_file=None, rgbd_video=None, device=None):
        self.rgbd_video = rgbd_video

        if device:
            self.device = device.lower()
        else:
            self.device = 'cuda:0' if o3d.core.cuda.is_available() else 'cpu:0'
        self.o3d_device = o3d.core.Device(self.device)

        self.video = None
        self.camera = None
        self.rgbd_frame = None
        self.positions = None
        self.colors = None
        self.pcd_frame = None
        self.flag_running = False
        self.show_depth_flag = False
        self.depth_thread = None
        self.recording = False
        self.pipeline_start_time = pipeline_start_time
        self.captured_pcd_folder_path = self.check_or_create_folder(f"pcd\\captured_pcd\\{pipeline_start_time}") 
        self.filename = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.bag"

        self.capture_started_event = threading.Event()

        try:
            if rgbd_video:
                log.info(f"Attempting to open .bag file: {rgbd_video}")
                
                if not os.path.exists(rgbd_video):
                    raise FileNotFoundError(f"Provided .bag file does not exist: {rgbd_video}")

                self.video = o3d.t.io.RGBDVideoReader.create(rgbd_video)
                if not self.video.is_opened():
                    raise RuntimeError(f"Failed to open .bag file: {rgbd_video}")
                
                self.rgbd_metadata = self.video.metadata
                self.status_message = f"Video {rgbd_video} opened successfully."
                log.info(self.status_message)

            else:
                log.info("Initializing RealSense camera...")
                self.camera = o3d.t.io.RealSenseSensor()

                if camera_config_file:
                    log.info(f"Using camera config file: {camera_config_file}")
                    with open(camera_config_file) as ccf:
                        self.camera.init_sensor(o3d.t.io.RealSenseSensorConfig(json.load(ccf)),
                                                filename=self.filename)
                else:
                    log.info(f"No camera config file provided, initializing with default settings.")
                    self.camera.init_sensor(filename=self.filename)
                
                self.camera.start_capture(start_record=False)
                self.rgbd_metadata = self.camera.get_metadata()
                self.status_message = f"Camera {self.rgbd_metadata.serial_number} initialized successfully."
                log.info(self.status_message)

            log.info(self.rgbd_metadata)

            self.extrinsics = o3d.core.Tensor.eye(4, dtype=o3d.core.Dtype.Float32, device=self.o3d_device)
            self.intrinsic_matrix = o3d.core.Tensor(
                self.rgbd_metadata.intrinsics.intrinsic_matrix,
                dtype=o3d.core.Dtype.Float32,
                device=self.o3d_device
            )
            self.depth_max = 3.0
            self.depth_min = 0.1 
            self.x_min = -0.5
            self.x_max = 0.5
            self.pcd_stride = 2

            self.start_capture_engine()

        except Exception as e:
            log.error(f"Failed to initialize camera or load .bag file: {e}")
            self.camera = None
            self.status_message = "Failed to initialize RealSense camera or load .bag file."
            print(self.status_message)
            raise

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


    def set_depth_max(self, depth_max):
        if depth_max > 0:
            self.depth_max = depth_max
            #log.info(f"Depth max set to {self.depth_max}")
        else:
            #log.error("Depth max must be a positive value.")
            pass

    def set_depth_min(self, depth_min):
        if depth_min >= 0:
            self.depth_min = depth_min
            #log.info(f"Depth min set to {self.depth_min}")
        else:
            #log.error("Depth min must be a non-negative value.")
            pass

    def set_x_min(self, x_min):
        self.x_min = x_min
        #logging.info(f"X min set to {self.x_min}")

    def set_x_max(self, x_max):
        self.x_max = x_max
        #logging.info(f"X max set to {self.x_max}")


    def get_depth_max(self):

        return self.depth_max
    
    def get_depth_min(self):
        return self.depth_min

    def rotate_pcd_180_x(self):
        """Rotate the point cloud along the X axis by 180 degrees."""
        R = np.eye(3, dtype=np.float32)
        R[1, 1], R[1, 2] = -1, 0
        R[2, 1], R[2, 2] = 0, -1
        
        if self.pcd_frame.point.positions.dtype != o3d.core.Dtype.Float32:
            self.pcd_frame.point.positions = self.pcd_frame.point.positions.to(o3d.core.Dtype.Float32)
        
        self.pcd_frame.point.positions = self.pcd_frame.point.positions @ R.T

    def capture_point_cloud(self):
        if self.rgbd_frame is not None:
            self.rgbd_frame = self.rgbd_frame.to(self.o3d_device)
            
            depth_image = self.rgbd_frame.depth
            depth_array = np.asarray(depth_image.to_legacy())
            depth_scale = self.rgbd_metadata.depth_scale
            depth_in_meters = depth_array / depth_scale
            print(f"depth_scale: {depth_scale}")

            mask = (depth_in_meters < self.depth_min) | (depth_in_meters > self.depth_max)

            depth_array[mask] = 0

            depth_array_uint16 = depth_array.astype(np.uint16)
            depth_image_filtered = o3d.t.geometry.Image(o3d.core.Tensor(depth_array_uint16, dtype=o3d.core.Dtype.UInt16))
            self.rgbd_frame.depth = depth_image_filtered

            self.pcd_frame = o3d.t.geometry.PointCloud.create_from_rgbd_image(
                self.rgbd_frame, self.intrinsic_matrix, self.extrinsics,
                self.rgbd_metadata.depth_scale, self.depth_max, self.pcd_stride, False)

            if not self.pcd_frame.is_empty():
                self.rotate_pcd_180_x()
                self.positions = self.pcd_frame.cpu().point.positions.numpy()
                self.colors = self.pcd_frame.cpu().point.colors.numpy()
                return self.positions, self.colors
            else:
                log.warning("Point cloud is empty.")
                return None, None
        return None, None


    def create_point_cloud(self):
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
        if self.rgbd_frame is not None:
            try:
                depth_image = self.rgbd_frame.depth.to_legacy()
                color_image = self.rgbd_frame.color.to_legacy()
                
                depth_array = np.asarray(depth_image)
                color_array = np.asarray(color_image)
                
                depth_in_meters = depth_array / self.rgbd_metadata.depth_scale
                
                mask = (depth_in_meters < self.depth_min) | (depth_in_meters > self.depth_max)

                # Check the shape of color_array before applying mask
                if len(color_array.shape) == 3:
                    color_array[mask, :] = [0, 0, 0]
                else:
                    # Handle the case where color_array is 2D
                    color_array[mask] = 0

                # Validate depth_array before normalization
                if depth_array is None or not depth_array.size:
                    #log.error("Depth array is None or empty.")
                    return None, None
                
                if np.isnan(depth_array).any() or np.isinf(depth_array).any():
                    log.error("Depth array contains NaN or Inf values.")
                    return None, None

                # Normalize the depth array and validate
                depth_array_normalized = cv2.normalize(depth_array, None, 0, 255, cv2.NORM_MINMAX)

                if depth_array_normalized is None:
                    log.error("cv2.normalize returned None.")
                    return None, None

                depth_array_normalized = np.uint8(depth_array_normalized)

                color_array_bgr = cv2.cvtColor(color_array, cv2.COLOR_RGB2BGR)

                return depth_array_normalized, color_array_bgr

            except Exception as e:
                log.error(f"Error processing depth and color images: {e}", exc_info=True)
                return None, None
        else:
            log.error("RGBD frame is None.")
            return None, None


    def _show_depth_image_internal(self):

        try:
            while self.show_depth_flag:
                depth_image, color_image = self.get_depth_and_color_image()
                if depth_image is not None and color_image is not None:
                    scale_percent = 50
                    width_depth = int(depth_image.shape[1] * scale_percent / 100)
                    height_depth = int(depth_image.shape[0] * scale_percent / 100)
                    dim_depth = (width_depth, height_depth)
                    
                    width_color = int(color_image.shape[1] * scale_percent / 100)
                    height_color = int(color_image.shape[0] * scale_percent / 100)
                    dim_color = (width_color, height_color)

                    resized_depth_image = cv2.resize(depth_image, dim_depth, interpolation=cv2.INTER_AREA)
                    resized_color_image = cv2.resize(color_image, dim_color, interpolation=cv2.INTER_AREA)

                    depth_colormap = cv2.applyColorMap(resized_depth_image, cv2.COLORMAP_JET)

                    combined_image = np.hstack((depth_colormap, resized_color_image))

                    cv2.imshow('Depth and Color Image', combined_image)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        self.show_depth_flag = False
                        break
        except Exception as e:
            print(f"Error displaying depth and color image: {e}")
        finally:
            cv2.destroyAllWindows()


    def show_depth_image(self):
        if not self.show_depth_flag:
            self.show_depth_flag = True
            self.depth_thread = threading.Thread(target=self._show_depth_image_internal)
            self.depth_thread.start()

    def stop_depth_image(self):
        self.show_depth_flag = False
        if self.depth_thread and self.depth_thread.is_alive():
            self.depth_thread.join()
        cv2.destroyAllWindows()


    def background_capture(self):
        self.capture_started_event.set()
        while self.flag_running:
            if self.video:
                try:
                    if self.video.is_eof():
                        log.info("EOF reached, restarting video from the beginning.")
                        self.video.close()
                        del self.video
                        self.video = o3d.t.io.RGBDVideoReader.create(self.rgbd_video)
                    
                    self.rgbd_frame = self.video.next_frame()
                    
                    if self.rgbd_frame is None or self.rgbd_frame.depth is None or self.rgbd_frame.color is None:
                        log.error("Captured RGBD frame is None or contains invalid depth/color data.")
                        continue

                except Exception as e:
                    log.error(f"Error capturing frame: {e}")
                    continue
            else:
                try:
                    self.rgbd_frame = self.camera.capture_frame(wait=True, align_depth_to_color=True)
                    if self.rgbd_frame is None or self.rgbd_frame.depth is None or self.rgbd_frame.color is None:
                        log.error("Captured RGBD frame is None or contains invalid depth/color data.")
                        continue

                except Exception as e:
                    log.error(f"Error capturing frame from camera: {e}")
                    continue

    def start_capture_engine(self):
        if not self.flag_running:
            self.flag_running = True
            log.info("Starting the capture engine...")
            self.capture_thread = threading.Thread(target=self.background_capture)
            self.capture_thread.daemon = True
            self.capture_thread.start()

    def stop_capture_engine(self):
        if self.flag_running:
            self.flag_running = False
            self.capture_thread.join()

    def _get_current_point_cloud(self):
        return self.create_point_cloud()

    
    def save_point_cloud(self, ply_path="output.ply"):

        point_cloud = self._get_current_point_cloud()

        if point_cloud is not None:
            o3d.io.write_point_cloud(f"{self.captured_pcd_folder_path}\\{ply_path}", point_cloud)
            log.info(f"Point cloud data saved to {ply_path}")

    def start_recording(self):
        if self.camera and not self.recording:
            log.info(f"Starting recording to {self.filename}...")
            self.camera.resume_record()
            self.recording = True
            log.info(f"Recording started.")

    def stop_recording(self):
        if self.camera and self.recording:
            log.info(f"Stopping recording to {self.filename}...")
            self.camera.pause_record()
            self.recording = False
            log.info(f"Recording stopped.")
            #self.close()



    def close(self):
        self.stop_depth_image()
        self.stop_capture_engine()
        if self.camera:
            if self.recording:
                self.stop_recording()
            log.info("Stopping camera capture...")
            self.camera.stop_capture()
            log.info("Camera capture stopped.")
        elif self.video:
            self.video.close()



def pipeline_process(start_queue, save_queue, complete_queue, rgbd_video, pipeline_start_time):
    try:
        model = PipelineModel(pipeline_start_time, camera_config_file=None, rgbd_video=rgbd_video)
    except RuntimeError:
        start_queue.put("ERROR")
        return

    # 启动捕获引擎并等待其启动成功
    model.start_capture_engine()
    model.capture_started_event.wait()

    while model._get_current_point_cloud() is None:
        time.sleep(0.1)
        
    start_queue.put("START")

    while True:
        save_path = save_queue.get()
        if save_path == 'STOP':
            log.info("Shutting down pipeline...")
            model.close()
            break
        elif save_path == "SHOW_CV":
            model.show_depth_image()
        elif save_path == "HIDE_CV":
            model.stop_depth_image()
        elif save_path == "START_RECORDING":
            model.start_recording()
        elif save_path == "STOP_RECORDING":
            model.stop_recording()
            break
        elif save_path.lower().endswith('.ply'):
            model.save_point_cloud(save_path)
            complete_queue.put("SAVED")
        else:
            print(f"Invalid save path: {save_path}")

if __name__ == "__main__":
    start_queue = multiprocessing.Queue()
    save_queue = multiprocessing.Queue()
    complete_queue = multiprocessing.Queue()

    mode = input("Please select mode: \n1. Use camera\n2. Use .bag file\nEnter '1' or '2': ").strip()

    camera_config_file = None
    rgbd_video = None

    if mode == '1':
        print("You selected to use the camera.")
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

    pipeline_start_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    process = multiprocessing.Process(
        target=pipeline_process, 
        args=(start_queue, save_queue, complete_queue, rgbd_video, pipeline_start_time)
    )
    process.start()

    is_started = start_queue.get()
    print(f"Pipeline process started: {is_started}")
    
    if is_started == "START":
        try:
            while True:
                command = input("Enter command (capture, show_cv, hide_cv, start_recording, stop_recording, quit): ").strip().lower()

                if command == 'capture':
                    start_time = time.time()
                    ply_path = "output.ply"
                    save_queue.put(ply_path)

                    complete_message = complete_queue.get()
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
            save_queue.put('STOP')
            process.join()
    else:
        print("Pipeline model did not start.")
