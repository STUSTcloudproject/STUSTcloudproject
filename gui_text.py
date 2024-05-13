import sys
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget, QDialog
from PyQt5.QtGui import QColor
from PyQt5.QtCore import QSize, Qt
from MainQWidget import MainQWidget
from ButtonWidget import ButtonWidget
from SettingsWidget import SettingsWidget
from ConfigurableTree import ConfigurableTree
from config_manager import load_config, get_orientation
from Text_display_panel import TextDisplayPanel
from ConfirmDialog import ConfirmDialog

class MainInterface(QWidget):
    def __init__(self):
        # 初始化主界面
        super().__init__()
        self.config = load_config('config.json')

        self.activated = False
        self.current_mode = "Home"

        self.treeWidget = None

        self.main_layout_widget = None
        self.activity_bar = None
        self.main_splitter = None
        self.side_bar = None
        self.main_splitter_panel2 = None

        self.nested_widget = None
        self.start_bar = None
        self.nested_splitter = None
        self.display_panel = None
        self.nested_splitter_panel2 = None

        self.init_ui()
        self.init_item()

    def init_ui(self):
        # 主界面的配置，這裡直接使用tuple來傳遞顏色和尺寸

        self_color = self.config['colors']['main_background']
        main_colors = self.config['colors']['main_panel_backgrounds']
        main_sizes = self.config['sizes']['main_panel_sizes']
        main_orientations = [Qt.Horizontal if o == "Horizontal" else Qt.Vertical for o in self.config['ui_settings']['main_panel_orientations']]
        main_fixed_panel = self.config['ui_settings']['main_fixed_panel']

        nested_colors = self.config['colors']['nested_panel_backgrounds']
        nested_sizes = self.config['sizes']['nested_panel_sizes']
        nested_orientations = [Qt.Horizontal if o == "Horizontal" else Qt.Vertical for o in self.config['ui_settings']['nested_panel_orientations']]
        nested_fixed_panel = self.config['ui_settings']['nested_fixed_panel']

        self.main_layout_widget = MainQWidget(
            self,
            self_color=self_color,
            colors=main_colors,
            sizes=main_sizes,
            orientations=main_orientations,
            fixed_panel=main_fixed_panel
        )
        
        self.activity_bar = self.main_layout_widget.get_panel1()
        self.main_splitter = self.main_layout_widget.get_panel2()
        self.side_bar = self.main_splitter.get_panel1()
        self.main_splitter_panel2 = self.main_splitter.get_panel2()
        
        # 嵌套的MainQWidget實例，用於設置panel2的內容
        self.nested_widget = MainQWidget(
            self,
            self_color=self_color,
            colors=nested_colors,
            sizes=nested_sizes,
            orientations=nested_orientations,
            fixed_panel=nested_fixed_panel
        )
        
        self.start_bar = self.nested_widget.get_panel1()
        self.nested_splitter = self.nested_widget.get_panel2()
        self.display_panel = self.nested_splitter.get_panel1()
        self.nested_splitter_panel2 = self.nested_splitter.get_panel2()

        # 將nested_widget設為panel2的內容
        self.main_splitter_panel2.clearAndAddWidget(self.nested_widget)

        # 設置佈局                                                                                                                                                                                                                                                                                                                                                                                                                                  
        layout = QVBoxLayout(self)
        self.setZeroMarginsAndSpacing(layout)
        layout.addWidget(self.main_layout_widget)
        self.setLayout(layout)

    def init_item(self):
        # 設置按鈕欄和側邊欄的內容 
        self.set_activity_bar(self.config['buttons']['activity_bar'])
        self.set_side_bar(sidebar_settings=self.config['sidebar_settings'], mode="Home")
        self.set_start_bar(self.config['buttons']['start_bar']['Home'])
        #增加對display_panel的設置
        self.set_text_display_panel(self.get_text_display_panel(self.config["display_panel_text"]["Home"]))

    def set_side_bar(self, sidebar_settings=None, is_set=True, mode="Home"):
        # 設置側邊欄
        if self.side_bar is None:
            print(f"{self.side_bar} is None")
            return
        
        callback_function = None
        if sidebar_settings is not None and 'callback' in sidebar_settings:
            callback_function = getattr(self, sidebar_settings['callback'], None)

        single_modes = self.config['sidebar_settings']['selectionMode']['single']
        multiple_modes = self.config['sidebar_settings']['selectionMode']['multiple']
        if mode in single_modes:
            selectionMode = "single"
        elif mode in multiple_modes:
            selectionMode = "multiple"
        else:
            selectionMode = "single"
        
        self.treeWidget = ConfigurableTree(callback=callback_function, selectionMode=selectionMode)

        if is_set:
            categories = sidebar_settings["settings_item"][mode]
            for group_name, group_info in categories.items():
                extra_data = {
                    "description": ", ".join(group_info['description'])  # 将描述信息合并成一个字符串
                }
                group = self.treeWidget.addGroup(group_name, extra_data)
                for name, description in zip(group_info['name'], group_info['description']):
                    widget = SettingsWidget(name, description)
                    self.treeWidget.addItem(group, widget, name)
            
        self.side_bar.clearAndAddWidget(self.treeWidget)


    def set_button_bar(self, bar, buttons_info):
        # 通用方法設置按鈕欄
        if bar is None:
            print(f"{bar} is None")
            return
        bar.removeAllWidgets()
        for button in buttons_info:
            button_widget = ButtonWidget(
                name=button['name'],
                owner=button['owner'],
                color=button['color'],
                icon=button['icon'],
                callback=getattr(self, button['callback']),
                size=button['size']
            )
            bar.addToLayout(button_widget)

    def set_activity_bar(self, activity_bar_buttons):
        # 設置活動欄
        self.set_button_bar(self.activity_bar, activity_bar_buttons)

    def set_start_bar(self, start_bar_buttons):
        self.set_button_bar(self.start_bar, start_bar_buttons)

    def get_text_display_panel(self, display_panel_text):
        # 獲取TextDisplayPanel實例
        return TextDisplayPanel(
            title=display_panel_text['title'],
            content=display_panel_text['content'],
            background_color=display_panel_text['background_color'],
            font_color=display_panel_text['font_color'],
            title_font_size=display_panel_text['title_font_size'],
            content_font_size=display_panel_text['content_font_size']
        )

    def set_text_display_panel(self, display_panel):
        if self.display_panel is None:
            print(f"{self.display_panel} is None")
            return
        self.display_panel.clearAndAddWidget(display_panel)

    def get_treeWidget_selected(self):
        # 獲取樹狀結構的選擇狀態
        return self.treeWidget.get_treeWidget_selected()


    def create_detial_panel(self, mode, selected_items):
        # 创建详细设置面板
        print(f"Create detail panel for {mode} mode with selected items: {selected_items}")
        dialog = ConfirmDialog("Confirmation", selected_items, self)
        if dialog.exec_() == QDialog.Accepted:
            print("Confirmed:", dialog.get_selection())
            return True
        else:
            print("Cancelled")
            return False

    def sizeHint(self):
        # 設置視窗大小
        return QSize(1200, 800)
    
    def setZeroMarginsAndSpacing(self, layout):
        # 設置佈局的邊距和間距
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    def callback(self, info):
        # 按鈕的回調函數
        print(f"Button name: {info['name']}, Owner: {info['owner']}")
        
        if info["owner"] == "activity_bar":
            self.current_mode = info["name"]
            self.set_side_bar(sidebar_settings=self.config['sidebar_settings'], mode = info["name"])
            self.set_start_bar(self.config['buttons']['start_bar'][info["name"]])
            #增加對display_panel的設置
            self.set_text_display_panel(self.get_text_display_panel(self.config["display_panel_text"][info["name"]]))
        
        elif info["owner"] == "configurable_tree":
            self.set_text_display_panel(self.get_text_display_panel(self.config["display_panel_text"][info["name"]]))
        
        elif info["owner"] == "start_bar":
            if info["name"] == "Start":
                if self.activated == False:
                    #先檢查QTree裡面的內容並取得設定項目，再彈出詳細設定視窗
                    selected_items_dict = self.get_treeWidget_selected()
                    #如果selected_items_dict不為空，則彈出詳細設定視窗
                    if selected_items_dict:
                        if self.create_detial_panel(info["name"], selected_items_dict):
                            self.activated = True
                            # 把 selected_items_dict 傳送給 Controller
                            print(f"Send selected items to Controller:{self.current_mode} {selected_items_dict}")
                    else:
                        self.activated = True
                        print(f"Send selected items to Controller:{self.current_mode} {selected_items_dict}")
                        
            elif info["name"] == "Stop":
                self.activated = False
                pass
            elif info["name"] == "Record":
                pass
        #print(f"Current mode: {self.current_mode}")

# 啟動應用程序
app = QApplication(sys.argv)
main_interface = MainInterface()
main_interface.show()
sys.exit(app.exec_())
