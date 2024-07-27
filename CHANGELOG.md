# Changelog

## [Unreleased] - 2023-07-27
### Fixed
- 修正 run.bat
- 修正 remove_point_cloud_gui.py 匯出文件按鈕的名稱為 Export Point Cloud

### Improved
- 更新項目 README.md

## [0.2.2] - 2023-07-25
### Added
- 新增 run.bat 批次檔來支援在虛擬環境一鍵開啟。

### Improved
- 更新 directory_structure.md 目錄

### Fixed
- 修正 Model.py 中已刪除的功能(點雲即時可視化)，產生的 BUG

## [0.2.1] - 2023-07-22
### Improved
- 更新 config.json 裡關於文字面板裡 Home 模式的內容
- 更新目錄結構

### Fixed
- 修正 View 模式下，沒有選擇項目並按下開始時，並未跑出警示框的 BUG。
- 修正 remove_point_cloud_gui.py 裡 menubar 沒有匯出檔案的選項。

## [0.2.0] - 2023-07-22
### Added
- View 模式下新增以下功能
- 新增 Depth Stream 功能
- 新增 Registration 功能
- 新增 Point Cloud Remove 功能
- 新增 PointCloud Mesh  功能
- 新增 Visualization 功能
- 調整初始視窗與控件大小

### Improved
- 初始視窗大小從硬編碼改為在 config.json 設定

## [0.1.1] - 2023-06-14
### Added
- 新增README。
- 新增 CHANGELOG.md。
- 新增 gui.py 代碼註解。

### Improved
- 將所有代碼與執行的相關文件移動到 `src` 資料夾。

## [0.1.0] - 2023-06-08
### Added
- 新增所有代碼註解 (除了 gui.py )。

