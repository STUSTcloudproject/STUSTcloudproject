from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt5.QtGui import QPixmap, QImage
import numpy as np

class ImagesDisplayPanel(QWidget):
    def __init__(self, image1_array=None, image2_array=None, parent=None):
        super().__init__(parent)
        
        self.layout = QHBoxLayout(self)

        # 创建两个 QLabel 用于显示图片
        self.image_label1 = QLabel(self)
        self.image_label2 = QLabel(self)

        # 添加 QLabel 到布局中
        self.layout.addWidget(self.image_label1)
        self.layout.addWidget(self.image_label2)
        self.setLayout(self.layout)

        # 设置图片
        self.set_image(self.image_label1, image1_array)
        self.set_image(self.image_label2, image2_array)

    def set_image(self, label, image_array):
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
        if self.image_label1 is not None:
            self.set_image(self.image_label1, image1_array)
        else:
            print("image_label1 is None")
        
        if self.image_label2 is not None:
            self.set_image(self.image_label2, image2_array)
        else:
            print("image_label2 is None")
