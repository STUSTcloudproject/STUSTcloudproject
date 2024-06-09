# realsense.py

# 從 realsense.record 模組匯入類別和函式
from realsense.record import Args, Preset, RealSenseRecorder, get_profiles

# 從 realsense.run_system 模組匯入類別
from realsense.run_system import Args_run_system, ReconstructionSystem

# 從 realsense.view 模組匯入類別
from realsense.view import ViewSystem

"""
realsense 模組

該模組整合了 RealSenseRecorder 和 realsense_helper 的功能。
"""

# 註解說明:
# Args: 用於記錄器的參數類別
# Preset: 用於設定預設參數的類別
# RealSenseRecorder: 主要的 RealSense 記錄器類別
# get_profiles: 獲取 RealSense 配置文件的函式

# Args_run_system: 用於運行系統的參數類別
# ReconstructionSystem: 重建系統類別

# ViewSystem: 視圖系統類別

# 該模組將這些功能整合在一起，提供了一個統一的接口來使用 RealSense record、run_system 和 view 系統。
