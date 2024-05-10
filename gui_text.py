import sys
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget
from PyQt5.QtGui import QColor
from PyQt5.QtCore import QSize, Qt
from MainQWidget import MainQWidget
from ButtonWidget import ButtonWidget

class MainInterface(QWidget):
    def __init__(self):
        super().__init__()  
        self.activate_bar_width = 80
        self.activity_bar = None
        self.start_button_bar = 60
        self.init_ui()
        self.set_item()

    def init_ui(self):

        # 主界面的配置，這裡直接使用tuple來傳遞顏色和尺寸
        self.main_layout_widget = MainQWidget(
            self, 
            colors=("blue", "green", "yellow"), 
            sizes=(self.activate_bar_width, 200, 600), 
            orientations=(Qt.Horizontal, Qt.Horizontal, Qt.Vertical), 
            fixed_panel='first'
        )
        
        self.activity_bar = self.main_layout_widget.get_panel1()

        # 嵌套的MainQWidget實例，用於設置panel2的內容
        self.nested_widget = MainQWidget(
            self, 
            colors=("purple", "red", "orange"), 
            sizes=(self.start_button_bar, 0, 150), 
            orientations=(Qt.Vertical, Qt.Vertical, Qt.Horizontal), 
            fixed_panel='second'
        )
        
        # 將nested_widget設為panel2的內容
        self.main_layout_widget.set_panel2_Content(2, self.nested_widget)

        # 設置佈局                                                                                                                                                                                                                                                                                                                                                                                                                                  
        layout = QVBoxLayout(self)
        self.setZeroMarginsAndSpacing(layout)
        layout.addWidget(self.main_layout_widget)
        self.setLayout(layout)

    def set_item(self):
        activaty_bar_byttons = {}
        activaty_bar_byttons["button1"] = {
            "name" : "Home", 
            "owner" : "activity_bar",
            "icon" : "None", 
            "color" : "transparent", 
            "size" : self.activate_bar_width, 
            "callback" : self.callback
        }
        activaty_bar_byttons["button2"] = {
            "name" : "record", 
            "owner" : "activity_bar",
            "icon" : "None", 
            "color" : "transparent", 
            "size" : self.activate_bar_width, 
            "callback" : self.callback
        }
        self.set_activity_bar(activaty_bar_byttons)

    def set_activity_bar(self, activaty_bar_byttons):
        if self.activity_bar is None:
            print("Activity bar is None")
            return
        for key, value in activaty_bar_byttons.items():      
            self.activity_bar.addToLayout(
                ButtonWidget(
                    value["name"],
                    value["owner"],
                    value["color"], 
                    value["icon"], 
                    value["callback"], 
                    value["size"], 
                    Qt.Vertical
                )
            )

    #def set_MainQWidget(self, widget):

    def sizeHint(self):
        return QSize(800, 600)
    
    def setZeroMarginsAndSpacing(self, layout):
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    def callback(self, info):
        """Process button click information."""
        print("Button clicked")
        print(f"Button name: {info['name']}, Owner: {info['owner']}")

# Running the application
app = QApplication(sys.argv)
main_interface = MainInterface()
main_interface.show()
sys.exit(app.exec_())
