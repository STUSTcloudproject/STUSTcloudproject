# 項目目錄結構和介紹

## 目錄結構

```plaintext
your_repository/
├── bag/                         # 存儲 RealSense 錄製數據的目錄
├── custom_widgets/              # 自定義小部件
│   ├── MainQWidget.py
│   ├── ButtonWidget.py
│   ├── SettingsWidget.py
│   ├── ConfigurableTree.py
│   ├── Text_display_panel.py
│   ├── ImagesDisplayPanel.py
│   ├── ConfirmDialog.py
│   ├── TerminalWidget.py
│   ├── ErrorDialog.py
│   ├── ContentSplitterWidget.py
│   └── ColoredWidget.py
├── icon/                        # 存放圖標文件的目錄
├── realsense/                   # RealSense 相關功能
│   ├── __init__.py
│   ├── record/
│   │   ├── __init__.py
│   │   ├── RealSenseRecorder.py
│   │   └── realsense_helper.py
│   ├── run_system/
│   │   ├── __init__.py
│   │   └── run_system.py
│   └── view/
│       ├── __init__.py
│       └── view.py
├── __pycache__/                 # 編譯後的 Python 文件
├── config.json                  # 配置文件
├── config_manager.py            # 配置管理模組
├── Controller.py                # 控制器模組
├── gui.py                       # 圖形用戶界面模組
├── main.py                      # 主程序入口
├── Model.py                     # 模型模組
├── realsense.json               # RealSense 配置文件
├── realsense.py                 # 整合 RealSense 相關功能
├── tool.py                      # 工具函數
└── View.py                      # 視圖模組
