# src 目錄

此目錄包含此應用的所有源代碼與相關檔案。以下是每個子目錄和文件的簡要介紹：

## 目錄結構

```plaintext
src/
├── custom_widgets/                        # 各種自定義小部件，用於增強 GUI 的功能和用戶體驗
├── icon/                                  # 應用程序中使用的圖標文件
├── realsense/                             # 與 RealSense 相機和數據處理相關的模塊
├── config.json                            # 應用程序的配置文件
├── config_manager.py                      # 配置管理模塊，負責加載和解析配置文件
├── Controller.py                          # 控制器模塊，實現 MVC 模式中的控制器邏輯
├── gui.py                                 # 圖形用戶界面模塊，負責創建和管理 GUI
├── main.py                                # 主程序入口點
├── Model.py                               # 模型模塊，實現 MVC 模式中的模型邏輯
├── realsense.json                         # RealSense 設置的配置文件
├── realsense.py                           # RealSense 記錄和處理的主模塊
├── tool.py                                # 工具模塊，提供輔助功能
└── View.py                                # 視圖模塊，實現 MVC 模式中的視圖邏輯
