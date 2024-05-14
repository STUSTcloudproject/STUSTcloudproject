import json
from PyQt5.QtCore import Qt

def load_config(filename):
    """Load and return configuration data from a JSON file."""
    with open(filename, 'r', encoding='utf-8') as file:  # 指定使用 UTF-8 编码读取
        return json.load(file)

def get_orientation(orientation_str):
    """Convert orientation from string to Qt orientation."""
    return {
        'Horizontal': Qt.Horizontal,
        'Vertical': Qt.Vertical
    }.get(orientation_str, Qt.Horizontal)  # Default to Horizontal if not found
