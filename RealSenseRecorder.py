import pyrealsense2 as rs
import numpy as np
import cv2
import argparse
from os import makedirs
from os.path import exists, join, abspath
import shutil
import json
from enum import IntEnum
import sys
import threading

class Args:
    def __init__(self, output_folder, record_rosbag, record_imgs, playback_rosbag, overwrite, width, height, depth_fmt, color_fmt, fps):
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
        self.thread = None
        self.depth_image = None
        self.color_image = None
        self.bg_removed = None

        if callback:
            self.callback = callback
            print("Callback function provided")
        else:
            self.callback = None
            print("No callback function provided")

        self.setup_folders()
        self.configure_streams()

    def setup_folders(self):
        if self.args.record_imgs:
            self.make_clean_folder(self.path_output, self.args.overwrite)
            self.make_clean_folder(self.path_depth, self.args.overwrite)
            self.make_clean_folder(self.path_color, self.args.overwrite)
        if self.args.record_rosbag:
            self.handle_rosbag_file()

    def configure_streams(self):
        if self.args.record_imgs or self.args.record_rosbag:
            print(f'Using the default profiles: \n  width : {self.args.width}, height : {self.args.height} depth_fmt : {self.args.depth_fmt} color_fmt : {self.args.color_fmt} fps : {self.args.fps}')
            self.config.enable_stream(rs.stream.depth, self.args.width, self.args.height, self.args.depth_fmt, self.args.fps)
            self.config.enable_stream(rs.stream.color, self.args.width, self.args.height, self.args.color_fmt, self.args.fps)
            if self.args.record_rosbag:
                self.config.enable_record_to_file(self.path_bag)
        if self.args.playback_rosbag:
            self.config.enable_device_from_file(self.path_bag, repeat_playback=True)

    @staticmethod
    def make_clean_folder(path_folder, overwrite=True):
        if not exists(path_folder):
            makedirs(path_folder)
        else:
            if overwrite:
                shutil.rmtree(path_folder)
                makedirs(path_folder)
            else:
                exit()

    def handle_rosbag_file(self, overwrite=True):
        if exists(self.path_bag):
            if overwrite == False:
                exit()

    @staticmethod
    def save_intrinsic_as_json(filename, frame):
        intrinsics = frame.profile.as_video_stream_profile().intrinsics
        with open(filename, 'w') as outfile:
            json.dump(
                {'width': intrinsics.width, 'height': intrinsics.height,
                 'intrinsic_matrix': [intrinsics.fx, 0, 0, 0, intrinsics.fy, 0, intrinsics.ppx, intrinsics.ppy, 1]},
                outfile, indent=4)

    def start_record(self):
        """启动录制线程"""
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self.record)
            self.thread.start()

    def stop_record(self):
        """停止录制线程"""
        if self.is_running:
            self.is_running = False
            self.thread.join()

    def record(self):
        profile = self.pipeline.start(self.config)
        depth_sensor = profile.get_device().first_depth_sensor()
        if self.args.record_rosbag or self.args.record_imgs:
            depth_sensor.set_option(rs.option.visual_preset, Preset.HighAccuracy)
        depth_scale = depth_sensor.get_depth_scale()
        clipping_distance = 3 / depth_scale  # 3 meters
        align = rs.align(rs.stream.color)
        frame_count = 0
        try:
            while self.is_running:  # Use self.is_running instead of True for controlled exit
                frames = self.pipeline.wait_for_frames()
                aligned_frames = align.process(frames)
                aligned_depth_frame = aligned_frames.get_depth_frame()
                color_frame = aligned_frames.get_color_frame()
                if not aligned_depth_frame or not color_frame:
                    continue
                self.depth_image = np.asanyarray(aligned_depth_frame.get_data())
                self.color_image = np.asanyarray(color_frame.get_data())
                if self.args.record_imgs:
                    if frame_count == 0:
                        self.save_intrinsic_as_json(join(self.path_output, "camera_intrinsic.json"), color_frame)
                    cv2.imwrite(f"{self.path_depth}/{frame_count:06d}.png", self.depth_image)
                    cv2.imwrite(f"{self.path_color}/{frame_count:06d}.jpg", self.color_image)
                    print(f"Saved color + depth image {frame_count:06d}")
                    frame_count += 1
                self.bg_removed = self.remove_background(self.depth_image, self.color_image, clipping_distance)
                #self.display_images(self.depth_image, self.bg_removed)
                self.send_to_model("record_imgs", {"depth_image": self.depth_image, "color_image": self.bg_removed})
                if cv2.waitKey(1) == 27:
                    cv2.destroyAllWindows()
                    break
        finally:
            self.pipeline.stop()
            self.is_running = False

    def recive_from_model(self, mode, data=None):
        if mode == "start_record":
            self.start_record()
        if mode == "stop_record":
            self.stop_record()

    def send_to_model(self, mode, data):
        if self.callback:
            if mode == "record_imgs":
                self.callback(mode, data)

    @staticmethod
    def remove_background(depth_image, color_image, clipping_distance):
        grey_color = 153
        depth_image_3d = np.dstack((depth_image, depth_image, depth_image))
        return np.where((depth_image_3d > clipping_distance) | (depth_image_3d <= 0), grey_color, color_image)

    @staticmethod
    def display_images(depth_image, bg_removed):
        depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.09), cv2.COLORMAP_JET)
        images = np.hstack((bg_removed, depth_colormap))
        cv2.namedWindow('Recorder Realsense', cv2.WINDOW_AUTOSIZE)
        cv2.imshow('Recorder Realsense', images)

if __name__ == "__main__":
    args = Args(
    output_folder='E:\\O3d_cuda\\Open3D\\examples\\python\\reconstruction_system\\sensors\\bag',
    record_rosbag=True,
    record_imgs=False,
    playback_rosbag=False,
    overwrite=True,
    width=640,
    height=480,
    depth_fmt=rs.format.z16,
    color_fmt=rs.format.rgb8,
    fps=30
    )
    recorder = RealSenseRecorder(args)
    recorder.start_record()  # Start recording in a new thread
    