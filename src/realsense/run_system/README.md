# realsense/run_system 目錄

此目錄包含 RealSense Data Processing System 的數據處理相關代碼。以下是每個文件的簡要介紹：

```plaintext
realsense/run_system/
├── __init__.py                                     # 初始化模塊，使該目錄成為 Python 包
├── run_system.py                                   # 重建系統的主要運行模塊
├── make_fragments.py                               # 製作點雲片段的模塊
├── register_fragments.py                           # 註冊點雲片段的模塊
├── refine_registration.py                          # 細化配準的模塊
├── integrate_scene.py                              # 整合場景的模塊，處理 RGBD 圖像序列
├── slac.py                                         # SLAC 非剛性優化模塊
├── slac_integrate.py                               # SLAC 整合模塊，處理和整合非剛性優化後的數據
├── optimize_posegraph.py                           # 優化姿態圖的模塊
├── opencv_pose_estimation.py                       # 使用 OpenCV 進行姿態估計
├── color_map_optimization_for_..._system.py        # 用於優化重建系統的色彩地圖
├── data_loader.py                                  # 數據加載器，包含不同數據集的加載功能
├── initialize_config.py                            # 初始化配置的模塊
└── open3d_example.py                               # Open3D 的示例和實用工具
