from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt
import numpy as np

class ImagesDisplayPanel(QWidget):
    def __init__(self, image1_array=None, image2_array=None, parent=None):
        """
        初始化 ImagesDisplayPanel。

        參數:
        image1_array (np.ndarray, optional): 第一張顯示的圖像數組。預設為 None。
        image2_array (np.ndarray, optional): 第二張顯示的圖像數組。預設為 None。
        parent (QWidget, optional): 父級窗口。預設為 None。
        """
        super().__init__(parent)
        
        self.layout = QHBoxLayout(self)

        # 創建兩個 QLabel 用於顯示圖片
        self.image_label1 = QLabel(self)
        self.image_label2 = QLabel(self)

        # 設置 QLabel 的對齊方式，防止調整大小時圖像內容不一致
        self.image_label1.setAlignment(Qt.AlignCenter)
        self.image_label2.setAlignment(Qt.AlignCenter)

        # 添加 QLabel 到佈局中
        self.layout.addWidget(self.image_label1)
        self.layout.addWidget(self.image_label2)
        self.setLayout(self.layout)

        # 設置圖片
        self.set_image(self.image_label1, image1_array)
        self.set_image(self.image_label2, image2_array)

    def set_image(self, label, image_array):
        """
        設置 QLabel 的圖像。

        參數:
        label (QLabel): 要設置圖像的 QLabel。
        image_array (np.ndarray): 圖像數組。
        """
        if image_array is not None:
            if len(image_array.shape) == 3:
                height, width, channel = image_array.shape
                bytes_per_line = 3 * width
                q_image = QImage(image_array.data, width, height, bytes_per_line, QImage.Format_RGB888)
            elif len(image_array.shape) == 2:
                height, width = image_array.shape
                bytes_per_line = width
                q_image = QImage(image_array.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
            else:
                raise ValueError("Unsupported image array shape")
                
            pixmap = QPixmap.fromImage(q_image)
            label.setPixmap(pixmap)
            label.setScaledContents(True)
            label.setFixedSize(pixmap.width(), pixmap.height())
        else:
            label.setText("No image available")

    def update_images(self, image1_array, image2_array):
        """
        更新顯示的圖像。

        參數:
        image1_array (np.ndarray): 第一張顯示的圖像數組。
        image2_array (np.ndarray): 第二張顯示的圖像數組。
        """
        # 禁用窗口重繪
        self.setUpdatesEnabled(False)
        
        if self.image_label1 is not None:
            self.set_image(self.image_label1, image1_array)
        else:
            print("image_label1 is None")
        
        if self.image_label2 is not None:
            self.set_image(self.image_label2, image2_array)
        else:
            print("image_label2 is None")
        
        # 啟用窗口重繪
        self.setUpdatesEnabled(True)
        
        # 強制重繪窗口
        self.update()
