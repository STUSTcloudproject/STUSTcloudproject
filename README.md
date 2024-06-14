# RealSense Data Processing System

## 簡介

此項目旨在提供一個基於 RealSense 的數據處理系統，包括數據錄製、數據處理和數據視圖顯示功能。<br>
數據錄製部分基於pyrealsense2，數據處理基於open3d，介面框架PyQt5。

## 目錄

- [安裝和配置](#安裝和配置)
- [使用說明](#使用說明)
- [詳細文檔](#詳細文檔)

## 安裝和配置

### 前置條件

請確保已安裝以下軟件：
- Python 3.10 <span style="color: rgba(255, 0, 0, 0.90); font-style: italic;">限定使用3.10</span>
- pip

### 安裝步驟

1. 克隆此存儲庫到本地：
    ```bash
    git clone https://github.com/STUSTcloudproject/MVC_gui.git
    ```

2. 進入項目目錄並安裝所需依賴：
    ```bash
    cd MVC_gui
    pip install -r requirements.txt
    ```

## 使用說明

1. 進入 `src` 資料夾：
    ```bash
    cd src
    ```
    
2. 運行主程序：
    ```bash
    python main.py
    ```

3. 使用 GUI 進行操作：
    - `Home`：查看應用說明
    - `Record`：錄製各種類型的數據，包括圖像和 .bag 文件與 .bag 文件回放
    - `RunSystem`：進行點雲數據處理，輸出 mesh 網格
    - `View`：查看各式模型，包括點雲數據、mesh網格等

## 詳細文檔

有關詳細的項目目錄結構和介紹，請參閱 [docs/directory_structure.md](docs/directory_structure.md)。
