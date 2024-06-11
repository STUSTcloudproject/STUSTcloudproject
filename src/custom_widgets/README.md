# custom_widgets 目錄

此目錄包含各種自定義小部件，用於增強 GUI 的功能和用戶體驗。每個小部件都是一個獨立的模塊，可以在應用中單獨使用或組合使用。

## 目錄結構

```plaintext
custom_widgets/
├── __init__.py
├── MainQWidget.py              # 主要的 QWidget 小部件，作為應用程序的主窗口
├── ButtonWidget.py             # 自定義按鈕小部件，支持設置圖標、顏色和回調函數
├── SettingsWidget.py           # 設置小部件，用於顯示和調整應用程序的設置選項
├── ConfigurableTree.py         # 可配置的樹狀結構小部件，用於顯示和操作層級化數據
├── Text_display_panel.py       # 文本顯示面板，用於顯示富文本內容
├── ImagesDisplayPanel.py       # 圖像顯示面板，用於顯示兩張圖像並支持圖像更新
├── ConfirmDialog.py            # 確認對話框，用於顯示確認消息並接受用戶輸入
├── TerminalWidget.py           # 終端小部件，用於模擬終端輸入輸出
├── ErrorDialog.py              # 錯誤對話框，用於顯示錯誤消息
├── ContentSplitterWidget.py    # 內容分割小部件，支持水平方向和垂直方向的內容分割
├── ColoredWidget.py            # 帶顏色的小部件，用於設置背景顏色和顯示內容
└── README.md
