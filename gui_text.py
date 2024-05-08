import sys
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtCore import QSize, Qt
from MainQWidget import MainQWidget

class MainInterface(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.main_layout_widget = MainQWidget(self,
                                              panel1_color=QColor("blue"), 
                                              panel1_pixel=70,
                                              splitter_orientation=Qt.Horizontal,
                                              layout_orientation=Qt.Horizontal, 
                                              fixed_panel='first', 
                                              initial_sizes=(200, 600))
        self.main_layout_widget.get_panel2().setPanel2Content(MainQWidget(self,
                                                                          panel1_color=QColor("blue"), 
                                                                          panel1_pixel=50,
                                                                          splitter_orientation=Qt.Vertical,
                                                                          layout_orientation=Qt.Vertical, 
                                                                          fixed_panel='second', 
                                                                          initial_sizes=(0, 150)
                                                                          ))
        layout = QVBoxLayout(self)
        self.setZeroMarginsAndSpacing(layout)
        layout.addWidget(self.main_layout_widget)
        #self.main_layout.setPanel
        self.setLayout(layout)
        
    def sizeHint(self):
        return QSize(800, 600)
    
    def setZeroMarginsAndSpacing(self, layout):
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

# Running the application
app = QApplication(sys.argv)
main_interface = MainInterface()
main_interface.show()
sys.exit(app.exec_())
