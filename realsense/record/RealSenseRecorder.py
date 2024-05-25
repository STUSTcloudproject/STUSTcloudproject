import pyrealsense2 as rs
import numpy as np
import cv2
import threading
from os import makedirs
from os.path import exists, join
import shutil
import json
from enum import IntEnum

class Args:
    def __init__(self, output_folder, record_rosbag, record_imgs, playback_rosbag, overwrite, width=640, height=480, depth_fmt=rs.format.z16, color_fmt=rs.format.rgb8, fps=30):
        self.output_folder = output_folder
        self.record_rosbag = record_rosbag
        self.record_imgs = record_imgs
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

        if callback:
            self.callback = callback
        else:
            self.callback = None

        self.setup_folders()
        self.configure_streams(preview=True)

    def setup_folders(self):
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
        try:
            if exists(self.path_bag):
                if not overwrite:
                    exit()
        except Exception as e:
            print(f"Error handling rosbag file: {e}")
            self.send_to_model("show_error", {"title": "Error handling rosbag file", "message": str(e)})

    @staticmethod
    def save_intrinsic_as_json(filename, frame):
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
        """启动预览线程"""
        if not self.is_running:
            try:
                self.is_running = True
                self.thread = threading.Thread(target=self.preview)
                self.thread.start()
            except Exception as e:
                print(f"Error starting preview thread: {e}")
                self.send_to_model("show_error", {"title": "Error starting preview thread", "message": str(e)})

    def start_recording(self):
        """启动录制"""
        try:
            if not self.args.playback_rosbag:
                if self.is_running:
                    self.stop_pipeline()  # Stop the current pipeline before reconfiguring streams
                self.is_recording = True
                self.configure_streams(preview=False)  # Reconfigure streams for recording
                self.start_pipeline()
        except Exception as e:
            print(f"Error starting recording: {e}")
            self.send_to_model("show_error", {"title": "Error starting recording", "message": str(e)})

    def stop_recording(self):
        """停止录制"""
        try:
            self.is_recording = False
        except Exception as e:
            print(f"Error stopping recording: {e}")
            self.send_to_model("show_error", {"title": "Error stopping recording", "message": str(e)})

    def stop_pipeline(self):
        """停止管道"""
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
        """启动管道"""
        try:
            self.is_running = True
            self.thread = threading.Thread(target=self.record)
            self.thread.start()
        except Exception as e:
            print(f"Error starting pipeline: {e}")
            self.send_to_model("show_error", {"title": "Error starting pipeline", "message": str(e)})

    def stop_preview(self):
        """停止预览线程"""
        try:
            self.stop_pipeline()
        except Exception as e:
            print(f"Error stopping preview: {e}")
            self.send_to_model("show_error", {"title": "Error stopping preview", "message": str(e)})

    def preview(self):
        try:
            profile = self.pipeline.start(self.config)
            depth_sensor = profile.get_device().first_depth_sensor()
            if self.args.record_rosbag or self.args.record_imgs:
                depth_sensor.set_option(rs.option.visual_preset, Preset.HighAccuracy)
            depth_scale = depth_sensor.get_depth_scale()
            clipping_distance = 3 / depth_scale  # 3 meters
            align = rs.align(rs.stream.color)
            while self.is_running:
                frames = self.pipeline.wait_for_frames()
                aligned_frames = align.process(frames)
                aligned_depth_frame = aligned_frames.get_depth_frame()
                color_frame = aligned_frames.get_color_frame()
                if not aligned_depth_frame or not color_frame:
                    continue
                self.depth_image = np.asanyarray(aligned_depth_frame.get_data())
                self.color_image = np.asanyarray(color_frame.get_data())
                self.bg_removed = self.remove_background(self.depth_image, self.color_image, clipping_distance)
                
                self.depth_image = cv2.applyColorMap(
                    cv2.convertScaleAbs(self.depth_image, alpha=0.09), cv2.COLORMAP_JET)
                
                self.send_to_model("record_imgs", {"depth_image": self.depth_image, "color_image": self.bg_removed})
                if cv2.waitKey(1) == 27:
                    cv2.destroyAllWindows()
                    break
        except RuntimeError as e:
            print(f"Error during preview: {e}")
            self.send_to_model("show_error", {"title": "Error during preview", "message": str(e)})
        finally:
            if self.is_running:
                try:
                    self.pipeline.stop()
                    self.is_running = False
                except Exception as e:
                    print(f"Error stopping pipeline in preview: {e}")
                    self.send_to_model("show_error", {"title": "Error stopping pipeline in preview", "message": str(e)})

    def record(self):
        try:
            profile = self.pipeline.start(self.config)
            depth_sensor = profile.get_device().first_depth_sensor()
            if self.args.record_rosbag or self.args.record_imgs:
                depth_sensor.set_option(rs.option.visual_preset, Preset.HighAccuracy)
            depth_scale = depth_sensor.get_depth_scale()
            clipping_distance = 3 / depth_scale  # 3 meters
            align = rs.align(rs.stream.color)
            frame_count = 0
            while self.is_running:
                frames = self.pipeline.wait_for_frames()
                aligned_frames = align.process(frames)
                aligned_depth_frame = aligned_frames.get_depth_frame()
                color_frame = aligned_frames.get_color_frame()
                if not aligned_depth_frame or not color_frame:
                    continue
                self.depth_image = np.asanyarray(aligned_depth_frame.get_data())
                self.color_image = np.asanyarray(color_frame.get_data())
                if self.is_recording and self.args.record_imgs:
                    if frame_count == 0:
                        self.save_intrinsic_as_json(join(self.path_output, "camera_intrinsic.json"), color_frame)
                    cv2.imwrite(f"{self.path_depth}/{frame_count:06d}.png", self.depth_image)
                    cv2.imwrite(f"{self.path_color}/{frame_count:06d}.jpg", self.color_image)
                    frame_count += 1
                self.bg_removed = self.remove_background(self.depth_image, self.color_image, clipping_distance)
                
                self.depth_image = cv2.applyColorMap(
                    cv2.convertScaleAbs(self.depth_image, alpha=0.09), cv2.COLORMAP_JET)
                
                self.send_to_model("record_imgs", {"depth_image": self.depth_image, "color_image": self.bg_removed})
                if cv2.waitKey(1) == 27:
                    cv2.destroyAllWindows()
                    break
        except RuntimeError as e:
            print(f"Error during recording: {e}")
            self.send_to_model("show_error", {"title": "Error during recording", "message": str(e)})
        finally:
            try:
                if self.is_running:
                    self.pipeline.stop()
                    self.is_running = False
            except Exception as e:
                print(f"Error stopping pipeline in record: {e}")
                self.send_to_model("show_error", {"title": "Error stopping pipeline in record", "message": str(e)})

    def recive_from_model(self, mode, data=None):
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
        if self.callback is not None:
            try:
                if mode == "record_imgs":
                    self.callback(mode, data)
                elif mode == "show_error":
                    self.callback(mode, data)
            except Exception as e:
                print(f"Error sending to model: {e}")
                if mode != "show_error":  # 防止遞歸調用
                    self.callback("show_error", {"title": "Error sending to model", "message": str(e)})

    @staticmethod
    def remove_background(depth_image, color_image, clipping_distance):
        try:
            grey_color = 153
            depth_image_3d = np.dstack((depth_image, depth_image, depth_image))
            return np.where((depth_image_3d > clipping_distance) | (depth_image_3d <= 0), grey_color, color_image)
        except Exception as e:
            print(f"Error removing background: {e}")
            raise

    @staticmethod
    def display_images(depth_image, bg_removed):
        try:
            depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.09), cv2.COLORMAP_JET)
            images = np.hstack((bg_removed, depth_colormap))
            cv2.namedWindow('Align Example', cv2.WINDOW_NORMAL)
            cv2.imshow('Align Example', images)
            cv2.waitKey(1)
        except Exception as e:
            print(f"Error displaying images: {e}")
            raise
