import json
from PyQt5.QtCore import Qt

def load_config(filename):
    """
    從 JSON 文件加載並返回配置數據。

    參數:
    filename (str): 要加載的 JSON 文件的名稱。

    回傳:
    dict: 包含配置數據的字典。
    """
    with open(filename, 'r', encoding='utf-8') as file:  # 指定使用 UTF-8 編碼讀取
        return json.load(file)

def get_orientation(orientation_str):
    """
    將方向從字符串轉換為 Qt 的方向。

    參數:
    orientation_str (str): 表示方向的字符串 ("Horizontal" 或 "Vertical")。

    回傳:
    Qt.Orientation: 對應的 Qt 方向常數，默認為 Qt.Horizontal。
    """
    return {
        'Horizontal': Qt.Horizontal,
        'Vertical': Qt.Vertical
    }.get(orientation_str, Qt.Horizontal)  # 如果未找到，默認為 Horizontal
