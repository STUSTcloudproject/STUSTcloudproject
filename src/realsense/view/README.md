# view 目錄

此目錄包含與視圖相關的所有模塊。以下是每個文件的簡要介紹：

## 目錄結構

```plaintext
view/
├── __init__.py        # 初始化文件，定義包的結構
├── view.py            # 包含 ViewSystem 類別，用於管理視圖系統
├── online_processing.py                # Depth Stream**: 獲取和保存深度圖像，並使用 Open3d 可視化深度數據
├── online_processing_pc_vis.py         # Open3d 可視化深度數據的邏輯
├── registration_manual_automatic.py    # 匯入並配準多個點雲數據，合併為一個點雲
├── remove_point_cloud_gui.py           # 使用 Eraser 和 Bounding Box 模式選擇並刪除或著色點雲數據
├── PointCloud_Mesh_Editor.py           # 對點雲進行降採樣，生成 Mesh 或將 Mesh 取樣為點雲
├── visualization.py                    # 匯入點雲數據並進行可視化操作
└── README.md

