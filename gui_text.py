import sys
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget
from PyQt5.QtGui import QColor
from PyQt5.QtCore import QSize, Qt
from MainQWidget import MainQWidget
from ButtonWidget import ButtonWidget

class MainInterface(QWidget):
    def __init__(self):
        # 初始化主界面
        super().__init__()
        
        self.main_layout_widget = None
        self.activity_bar = None
        self.main_splitter = None
        self.main_splitter_panel1 = None
        self.main_splitter_panel2 = None

        self.nested_widget = None
        self.start_bar = None
        self.nested_splitter = None
        self.nested_splitter_panel1 = None
        self.nested_splitter_panel2 = None

        self.activate_bar_width = 80
        self.start_bar_width = 60

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
        self.main_splitter = self.main_layout_widget.get_panel2()
        self.main_splitter_panel1 = self.main_splitter.get_panel1()
        self.main_splitter_panel2 = self.main_splitter.get_panel2()
        
        # 嵌套的MainQWidget實例，用於設置panel2的內容
        self.nested_widget = MainQWidget(
            self, 
            colors=("purple", "red", "orange"), 
            sizes=(self.start_bar_width, 0, 150), 
            orientations=(Qt.Vertical, Qt.Vertical, Qt.Horizontal), 
            fixed_panel='second'
        )
        
        self.start_bar = self.nested_widget.get_panel1()
        self.nested_splitter = self.nested_widget.get_panel2()
        self.nested_splitter_panel1 = self.nested_splitter.get_panel1()
        self.nested_splitter_panel2 = self.nested_splitter.get_panel2()

        # 將nested_widget設為panel2的內容
        self.main_splitter_panel2.clearAndAddWidget(self.nested_widget)

        # 設置佈局                                                                                                                                                                                                                                                                                                                                                                                                                                  
        layout = QVBoxLayout(self)
        self.setZeroMarginsAndSpacing(layout)
        layout.addWidget(self.main_layout_widget)
        self.setLayout(layout)

    def set_item(self):
        # 設置活動欄和開始欄的按鈕
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
            "name" : "Record", 
            "owner" : "activity_bar",
            "icon" : "None", 
            "color" : "transparent", 
            "size" : self.activate_bar_width, 
            "callback" : self.callback
        }
        
        self.set_activity_bar(activaty_bar_byttons)

        start_bar_byttons = {}
        start_bar_byttons["button1"] = {
            "name" : "Start", 
            "owner" : "start_bar",
            "icon" : "None", 
            "color" : "transparent", 
            "size" : self.start_bar_width, 
            "callback" : self.callback
        }
        
        self.set_start_bar(start_bar_byttons)


    def set_activity_bar(self, activaty_bar_byttons):
        # 設置活動欄的按鈕
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

    def set_start_bar(self, start_bar_byttons):
        # 設置開始欄的按鈕
        if self.start_bar is None:
            print("Start bar is None")
            return
        for key, value in start_bar_byttons.items():      
            self.start_bar.addToLayout(
                ButtonWidget(
                    value["name"],
                    value["owner"],
                    value["color"], 
                    value["icon"], 
                    value["callback"], 
                    value["size"], 
                    Qt.Horizontal
                )
            )

    def sizeHint(self):
        # 設置視窗大小
        return QSize(800, 600)
    
    def setZeroMarginsAndSpacing(self, layout):
        # 設置佈局的邊距和間距
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    def callback(self, info):
        # 按鈕的回調函數
        print("Button clicked")
        print(f"Button name: {info['name']}, Owner: {info['owner']}")

# 啟動應用程序
app = QApplication(sys.argv)
main_interface = MainInterface()
main_interface.show()
sys.exit(app.exec_())
