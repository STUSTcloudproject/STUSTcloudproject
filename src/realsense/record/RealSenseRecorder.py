import pyrealsense2 as rs
import numpy as np
import cv2
import threading
from os import makedirs
from os.path import exists, join
import shutil
import json
from enum import IntEnum
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from point_cloud_manager import PointCloudManager, run_point_cloud_manager
import multiprocessing
import traceback
import ctypes

class Args:
    def __init__(self, output_folder, record_rosbag, record_imgs, playback_rosbag, calculate_overlap, overwrite, width=640, height=480, depth_fmt=rs.format.z16, color_fmt=rs.format.rgb8, fps=30):
        """
        初始化 Args 類別。

        參數:
        output_folder (str): 輸出文件夾。
        record_rosbag (bool): 是否錄製 rosbag 文件。
        record_imgs (bool): 是否錄製圖像。
        playback_rosbag (bool): 是否播放 rosbag 文件。
        calculate_overlap (bool): 是否計算重疊區域。
        overwrite (bool): 是否覆蓋現有文件。
        width (int, optional): 圖像寬度。預設為 640。
        height (int, optional): 圖像高度。預設為 480。
        depth_fmt (rs.format, optional): 深度格式。預設為 rs.format.z16。
        color_fmt (rs.format, optional): 顏色格式。預設為 rs.format.rgb8。
        fps (int, optional): 幀率。預設為 30。
        """
        self.output_folder = output_folder
        self.record_rosbag = record_rosbag
        self.record_imgs = record_imgs
        self.calculate_overlap = calculate_overlap
        self.playback_rosbag = playback_rosbag
        self.overwrite = overwrite
        self.width = width
        self.height = height
        self.depth_fmt = depth_fmt
        self.color_fmt = color_fmt
        self.fps = fps

class Preset(IntEnum):
    Custom = 0
    Default = 1
    Hand = 2
    HighAccuracy = 3
    HighDensity = 4
    MediumDensity = 5

class RealSenseRecorder:
    def __init__(self, args, callback=None):
        """
        初始化 RealSenseRecorder。

        參數:
        args (Args): 配置參數。
        callback (callable, optional): 回調函數。預設為 None。
        """
        self.args = args
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        self.path_output = args.output_folder
        self.path_depth = join(args.output_folder, "depth")
        self.path_color = join(args.output_folder, "color")
        self.path_bag = join(args.output_folder, "realsense.bag")
        self.is_running = False
        self.is_recording = False
        self.thread = None
        self.depth_image = None
        self.color_image = None
        self.bg_removed = None
        self.point_cloud_manager = None
        self.intrinsics_dict = None
        self.depth_image_shape = None
        self.shared_depth_image = None
        self.data_queue = multiprocessing.Queue()
        self.stop_event = multiprocessing.Event()

        if callback:
            self.callback = callback
        else:
            self.callback = None

        self.setup_folders()
        self.configure_streams(preview=True)

    def setup_folders(self):
        """
        設置輸出文件夾。
        """
        try:
            if self.args.record_imgs:
                self.make_clean_folder(self.path_output, self.args.overwrite)
                self.make_clean_folder(self.path_depth, self.args.overwrite)
                self.make_clean_folder(self.path_color, self.args.overwrite)
            if self.args.record_rosbag:
                self.handle_rosbag_file()
        except Exception as e:
            print(f"Error setting up folders: {e}")
            self.send_to_model("show_error", {"title": "Error setting up folders", "message": str(e)})

    def configure_streams(self, preview=False):
        """
        配置 RealSense 流。

        參數:
        preview (bool, optional): 是否僅配置預覽流。預設為 False。
        """
        try:
            if self.args.playback_rosbag:
                self.config.enable_device_from_file(self.path_bag, repeat_playback=True)
            else:
                self.config.enable_stream(rs.stream.depth, self.args.width, self.args.height, self.args.depth_fmt, self.args.fps)
                self.config.enable_stream(rs.stream.color, self.args.width, self.args.height, self.args.color_fmt, self.args.fps)
                if not preview and self.args.record_rosbag:
                    self.config.enable_record_to_file(self.path_bag)
        except Exception as e:
            print(f"Error configuring streams: {e}")
            self.send_to_model("show_error", {"title": "Error configuring streams", "message": str(e)})

    @staticmethod
    def make_clean_folder(path_folder, overwrite=True):
        """
        創建乾淨的文件夾。

        參數:
        path_folder (str): 文件夾路徑。
        overwrite (bool, optional): 是否覆蓋現有文件夾。預設為 True。
        """
        try:
            if not exists(path_folder):
                makedirs(path_folder)
            else:
                if overwrite:
                    shutil.rmtree(path_folder)
                    makedirs(path_folder)
                else:
                    exit()
        except Exception as e:
            print(f"Error making clean folder: {e}")
            raise

    def handle_rosbag_file(self, overwrite=True):
        """
        處理 rosbag 文件。

        參數:
        overwrite (bool, optional): 是否覆蓋現有文件。預設為 True。
        """
        try:
            if exists(self.path_bag):
                if not overwrite:
                    exit()
        except Exception as e:
            print(f"Error handling rosbag file: {e}")
            self.send_to_model("show_error", {"title": "Error handling rosbag file", "message": str(e)})

    @staticmethod
    def save_intrinsic_as_json(filename, frame):
        """
        保存相機內參到 JSON 文件。

        參數:
        filename (str): 文件名。
        frame (rs.frame): RealSense 幀。
        """
        try:
            intrinsics = frame.profile.as_video_stream_profile().intrinsics
            with open(filename, 'w') as outfile:
                json.dump(
                    {'width': intrinsics.width, 'height': intrinsics.height,
                     'intrinsic_matrix': [intrinsics.fx, 0, 0, 0, intrinsics.fy, 0, intrinsics.ppx, intrinsics.ppy, 1]},
                    outfile, indent=4)
        except Exception as e:
            print(f"Error saving intrinsic as JSON: {e}")
            raise

    def start_preview(self):
        """
        啟動預覽線程。
        """
        if not self.is_running:
            try:
                self.is_running = True
                self.thread = threading.Thread(target=self.preview)
                self.thread.start()
            except Exception as e:
                print(f"Error starting preview thread: {e}")
                self.send_to_model("show_error", {"title": "Error starting preview thread", "message": str(e)})

    def start_recording(self):
        """
        啟動錄製。
        """
        def recording_thread():
            try:
                if not self.args.playback_rosbag:
                    self.stop_pipeline()  # 停止當前管道以重新配置流
                    self.is_recording = True
                    self.configure_streams(preview=False)  # 重新配置流以進行錄製
                    self.start_pipeline()
            except Exception as e:
                print(f"Error starting recording: {e}")
                self.send_to_model("show_error", {"title": "Error starting recording", "message": str(e)})

        # 清除停止事件，確保錄製正常開始
        self.stop_event.clear()

        # 在單獨的線程中執行耗時操作
        threading.Thread(target=recording_thread).start()

    def stop_recording(self):
        """
        停止錄製。
        """
        try:
            self.is_recording = False
            self.stop_event.set()  # 設置停止事件
        except Exception as e:
            print(f"Error stopping recording: {e}")
            self.send_to_model("show_error", {"title": "Error stopping recording", "message": str(e)})

    def stop_pipeline(self):
        """
        停止管道。
        """
        try:
            if self.is_running:
                self.is_running = False
                try:
                    self.pipeline.stop()
                except RuntimeError as e:
                    print(f"Error stopping pipeline: {e}")
                    self.send_to_model("show_error", {"title": "Error stopping pipeline", "message": str(e)})
        except Exception as e:
            print(f"Error in stop_pipeline: {e}")
            self.send_to_model("show_error", {"title": "Error in stop_pipeline", "message": str(e)})

    def start_pipeline(self):
        """
        啟動管道。
        """
        try:
            self.is_running = True
            self.thread = threading.Thread(target=self.record)
            self.thread.start()
        except Exception as e:
            print(f"Error starting pipeline: {e}")
            self.send_to_model("show_error", {"title": "Error starting pipeline", "message": str(e)})

    def stop_preview(self):
        """
        停止預覽線程。
        """
        try:
            self.stop_pipeline()
        except Exception as e:
            print(f"Error stopping preview: {e}")
            self.send_to_model("show_error", {"title": "Error stopping preview", "message": str(e)})

    def preview(self):
        """
        預覽過程。
        """
        try:
            # 啟動管道並配置流
            profile = self.pipeline.start(self.config)
            depth_sensor = profile.get_device().first_depth_sensor()
            
            # 設置高精度預設選項（如果錄製 rosbag 或圖像）
            if self.args.record_rosbag or self.args.record_imgs:
                depth_sensor.set_option(rs.option.visual_preset, Preset.HighAccuracy)
            
            # 獲取深度比例並計算剪切距離（3 米）
            depth_scale = depth_sensor.get_depth_scale()
            clipping_distance = 3 / depth_scale
            
            # 對齊深度流和顏色流
            align = rs.align(rs.stream.color)

            # 如果需要計算重疊且正在播放 rosbag，初始化點雲管理器
            if self.args.calculate_overlap and self.args.playback_rosbag:
                aligned_frames = self.pipeline.wait_for_frames()
                aligned_depth_frame = aligned_frames.get_depth_frame()
                intrinsics = aligned_depth_frame.profile.as_video_stream_profile().intrinsics
                self.intrinsics_dict = {
                    'width': intrinsics.width,
                    'height': intrinsics.height,
                    'fx': intrinsics.fx,
                    'fy': intrinsics.fy,
                    'ppx': intrinsics.ppx,
                    'ppy': intrinsics.ppy
                }
                self.depth_image_shape = (intrinsics.height, intrinsics.width)

                self.shared_depth_image = multiprocessing.Array(ctypes.c_uint16, int(np.prod(self.depth_image_shape)))
                # 啟動 PointCloudManager 進程
                p = multiprocessing.Process(target=run_point_cloud_manager, args=(self.depth_image_shape, self.data_queue, self.shared_depth_image, self.stop_event, self.intrinsics_dict))
                p.start()

            while self.is_running:
                # 等待新的幀並對齊
                frames = self.pipeline.wait_for_frames()
                aligned_frames = align.process(frames)
                aligned_depth_frame = aligned_frames.get_depth_frame()
                color_frame = aligned_frames.get_color_frame()
                
                # 檢查是否獲取到有效的深度和顏色幀
                if not aligned_depth_frame or not color_frame:
                    continue
                
                # 將幀數據轉換為 numpy 數組
                self.depth_image = np.asanyarray(aligned_depth_frame.get_data())
                self.color_image = np.asanyarray(color_frame.get_data())

                # 如果需要計算重疊，將深度數據傳送到 PointCloudManager
                if self.args.calculate_overlap and self.args.playback_rosbag:
                    np.copyto(np.frombuffer(self.shared_depth_image.get_obj(), dtype=np.uint16).reshape(self.depth_image_shape), self.depth_image)
                    self.data_queue.put(True)

                # 移除背景
                self.bg_removed = self.remove_background(self.depth_image, self.color_image, clipping_distance)
                
                # 將深度圖像轉換為彩色映射
                self.depth_image = cv2.applyColorMap(
                    cv2.convertScaleAbs(self.depth_image, alpha=0.09), cv2.COLORMAP_JET)
                
                # 發送圖像數據到模型
                self.send_to_model("record_imgs", {"depth_image": self.depth_image, "color_image": self.bg_removed})
                
        except RuntimeError as e:
            print(f"Error during preview: {e}")
            self.send_to_model("show_error", {"title": "Error during preview", "message": str(e)})
        finally:
            if self.is_running:
                try:
                    self.pipeline.stop()
                    self.is_running = False
                    if self.args.calculate_overlap and self.args.playback_rosbag:
                        self.stop_event.set()  # 設置停止事件
                        p.join()
                except Exception as e:
                    print(f"Error stopping pipeline in preview: {e}")
                    self.send_to_model("show_error", {"title": "Error stopping pipeline in preview", "message": str(e)})

    def record(self):
        """
        錄製過程。
        """
        try:
            # 啟動管道並配置流
            profile = self.pipeline.start(self.config)
            depth_sensor = profile.get_device().first_depth_sensor()
            
            # 設置高精度預設選項（如果錄製 rosbag 或圖像）
            if self.args.record_rosbag or self.args.record_imgs:
                depth_sensor.set_option(rs.option.visual_preset, Preset.HighAccuracy)
            
            # 獲取深度比例並計算剪切距離（3 米）
            depth_scale = depth_sensor.get_depth_scale()
            clipping_distance = 3 / depth_scale
            
            # 對齊深度流和顏色流
            align = rs.align(rs.stream.color)

            # 如果需要計算重疊，初始化點雲管理器
            if self.args.calculate_overlap:
                # 獲取並保存內參
                aligned_frames = self.pipeline.wait_for_frames()
                aligned_depth_frame = aligned_frames.get_depth_frame()
                intrinsics = aligned_depth_frame.profile.as_video_stream_profile().intrinsics
                self.intrinsics_dict = {
                    'width': intrinsics.width,
                    'height': intrinsics.height,
                    'fx': intrinsics.fx,
                    'fy': intrinsics.fy,
                    'ppx': intrinsics.ppx,
                    'ppy': intrinsics.ppy
                }
                self.depth_image_shape = (intrinsics.height, intrinsics.width)
                
                self.shared_depth_image = multiprocessing.Array(ctypes.c_uint16, int(np.prod(self.depth_image_shape)))
                # 啟動 PointCloudManager 進程
                p = multiprocessing.Process(target=run_point_cloud_manager, args=(self.depth_image_shape, self.data_queue, self.shared_depth_image, self.stop_event, self.intrinsics_dict))
                p.start()

            frame_count = 0
            while self.is_running:
                try:
                    # 等待新的幀並對齊
                    frames = self.pipeline.wait_for_frames()
                    aligned_frames = align.process(frames)
                    aligned_depth_frame = aligned_frames.get_depth_frame()
                    color_frame = aligned_frames.get_color_frame()
                    
                    # 檢查是否獲取到有效的深度和顏色幀
                    if not aligned_depth_frame or not color_frame:
                        continue
                    
                    # 將幀數據轉換為 numpy 數組
                    self.depth_image = np.asanyarray(aligned_depth_frame.get_data())
                    self.color_image = np.asanyarray(color_frame.get_data())
                    
                    # 如果需要計算重疊，將深度數據傳送到 PointCloudManager
                    if self.args.calculate_overlap:
                        np.copyto(np.frombuffer(self.shared_depth_image.get_obj(), dtype=np.uint16).reshape(self.depth_image_shape), self.depth_image)
                        self.data_queue.put(True)

                    # 如果正在錄製，保存圖像
                    if self.is_recording and self.args.record_imgs:
                        if frame_count == 0:
                            self.save_intrinsic_as_json(join(self.path_output, "camera_intrinsic.json"), color_frame)
                        cv2.imwrite(f"{self.path_depth}/{frame_count:06d}.png", self.depth_image)
                        cv2.imwrite(f"{self.path_color}/{frame_count:06d}.jpg", self.color_image)
                        frame_count += 1

                    # 移除背景
                    self.bg_removed = self.remove_background(self.depth_image, self.color_image, clipping_distance)

                    # 將深度圖像轉換為彩色映射
                    self.depth_image = cv2.applyColorMap(
                        cv2.convertScaleAbs(self.depth_image, alpha=0.09), cv2.COLORMAP_JET)

                    # 發送圖像數據到模型
                    self.send_to_model("record_imgs", {"depth_image": self.depth_image, "color_image": self.bg_removed})
                    
                except RuntimeError as e:
                    tb = traceback.format_exc()
                    print(f"Error processing frames: {e}\n{tb}")
                    break  # 跳出循環，以便在 finally 中進行清理
        except RuntimeError as e:
            tb = traceback.format_exc()
            print(f"Error during recording: {e}\n{tb}")
            self.send_to_model("show_error", {"title": "Error during recording", "message": str(e)})
        finally:
            try:
                if self.is_running:
                    self.pipeline.stop()
                    self.is_running = False
                self.stop_event.set()  # 設置停止事件
                if self.args.calculate_overlap:
                    p.join()
            except Exception as e:
                print(f"Error stopping pipeline in record: {e}")
                self.send_to_model("show_error", {"title": "Error stopping pipeline in record", "message": str(e)})


    def recive_from_model(self, mode, data=None):
        """
        從模型接收消息。

        參數:
        mode (str): 模式。
        data (dict, optional): 附加數據。預設為 None。
        """
        try:
            if mode == "start_preview":
                self.start_preview()
            elif mode == "start_record":
                self.start_recording()
            elif mode == "stop_record":
                self.stop_recording()
                self.stop_preview()
        except Exception as e:
            print(f"Error receiving from model: {e}")
            self.send_to_model("show_error", {"title": "Error receiving from model", "message": str(e)})

    def send_to_model(self, mode, data):
        """
        發送消息到模型。

        參數:
        mode (str): 模式。
        data (dict): 附加數據。
        """
        if self.callback is not None:
            try:
                if mode == "record_imgs" or mode == "show_error":
                    self.callback(mode, data)
            except Exception as e:
                print(f"Error sending to model: {e}")
                if mode != "show_error":  # 防止遞歸調用
                    self.callback("show_error", {"title": "Error sending to model", "message": str(e)})

    @staticmethod
    def remove_background(depth_image, color_image, clipping_distance):
        """
        移除背景。

        參數:
        depth_image (np.ndarray): 深度圖像數組。
        color_image (np.ndarray): 顏色圖像數組。
        clipping_distance (float): 剪切距離。

        回傳:
        np.ndarray: 移除背景後的圖像。
        """
        try:
            grey_color = 153
            depth_image_3d = np.dstack((depth_image, depth_image, depth_image))
            return np.where((depth_image_3d > clipping_distance) | (depth_image_3d <= 0), grey_color, color_image)
        except Exception as e:
            print(f"Error removing background: {e}")
            raise

    @staticmethod
    def display_images(depth_image, bg_removed):
        """
        顯示圖像。

        參數:
        depth_image (np.ndarray): 深度圖像數組。
        bg_removed (np.ndarray): 移除背景後的圖像。
        """
        try:
            depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.09), cv2.COLORMAP_JET)
            images = np.hstack((bg_removed, depth_colormap))
            cv2.namedWindow('Align Example', cv2.WINDOW_NORMAL)
            cv2.imshow('Align Example', images)
            cv2.waitKey(1)
        except Exception as e:
            print(f"Error displaying images: {e}")
            raise
