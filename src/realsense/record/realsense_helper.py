# ----------------------------------------------------------------------------
# -                        Open3D: www.open3d.org                            -
# ----------------------------------------------------------------------------
# Copyright (c) 2018-2023 www.open3d.org
# SPDX-License-Identifier: MIT
# ----------------------------------------------------------------------------

# examples/python/reconstruction_system/sensors/realsense_helper.py

# pyrealsense2 是必需的。
# 請參見 https://github.com/IntelRealSense/librealsense/tree/master/wrappers/python 中的說明
import pyrealsense2 as rs

def get_profiles():
    """
    獲取所有已連接的 RealSense 設備的顏色和深度配置文件。

    回傳:
    tuple: 包含顏色配置文件列表和深度配置文件列表的元組。
    """
    ctx = rs.context()
    devices = ctx.query_devices()  # 查詢所有已連接的 RealSense 設備

    color_profiles = []
    depth_profiles = []
    for device in devices:
        name = device.get_info(rs.camera_info.name)
        serial = device.get_info(rs.camera_info.serial_number)
        for sensor in device.query_sensors():
            for stream_profile in sensor.get_stream_profiles():
                stream_type = str(stream_profile.stream_type())  # 獲取流類型

                if stream_type in ['stream.color', 'stream.depth']:
                    v_profile = stream_profile.as_video_stream_profile()
                    fmt = stream_profile.format()
                    w, h = v_profile.width(), v_profile.height()
                    fps = v_profile.fps()

                    video_type = stream_type.split('.')[-1]
                    if video_type == 'color':
                        color_profiles.append((w, h, fps, fmt))  # 添加顏色配置文件
                    else:
                        depth_profiles.append((w, h, fps, fmt))  # 添加深度配置文件

    return color_profiles, depth_profiles

if __name__ == "__main__":
    color_profiles, depth_profiles = get_profiles()
    print("Color profiles:")
    print(color_profiles)
    print("Depth profiles:")
    print(depth_profiles)
