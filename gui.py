import sys
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget, QDialog
from PyQt5.QtGui import QColor
from PyQt5.QtCore import QSize, Qt
import widgets as w
from config_manager import load_config
class MainInterface(QWidget):
    def __init__(self, callback_to_view=None):
        # 初始化主界面
        super().__init__()
        self.config = load_config('config.json')
        
        if callback_to_view is None:
            print("Callback is None in MainInterface constructor.")
        else:
            print("Callback is set in MainInterface constructor.")
        self.callback_to_view = callback_to_view
        
        self.activated = False
        self.current_mode = "Home"

        self.treeWidget = None
        self.terminal_widget = None

        self.main_layout_widget = None
        self.activity_bar = None
        self.main_splitter = None
        self.sider_bar = None
        self.main_splitter_panel2 = None

        self.nested_widget = None
        self.start_bar = None
        self.nested_splitter = None
        self.display_panel = None
        self.terminal_panel = None

        self.text_display_panels = {}
        self.images_display_panel = None

        self.init_ui()
        self.init_item()

    def set_callback_to_View(self, callback):
        self.callback_to_view = callback

    def init_ui(self):
        # 主界面的配置，這裡直接使用tuple來傳遞顏色和尺寸
        ui_config = self.config['ui']
        self_color = ui_config['colors']['main_background']
        main_colors = ui_config['colors']['panels']['main']
        main_sizes = ui_config['sizes']['panels']['main']
        main_orientations = [Qt.Horizontal if o == "Horizontal" else Qt.Vertical for o in ui_config['settings']['orientations']['main']]
        main_fixed_panel = ui_config['settings']['fixed_panel']['main']

        nested_colors = ui_config['colors']['panels']['nested']
        nested_sizes = ui_config['sizes']['panels']['nested']
        nested_orientations = [Qt.Horizontal if o == "Horizontal" else Qt.Vertical for o in ui_config['settings']['orientations']['nested']]
        nested_fixed_panel = ui_config['settings']['fixed_panel']['nested']

        self.main_layout_widget = w.MainQWidget(
            self,
            self_color=self_color,
            colors=main_colors,
            sizes=main_sizes,
            orientations=main_orientations,
            fixed_panel=main_fixed_panel
        )
        
        self.activity_bar = self.main_layout_widget.get_panel1()
        self.main_splitter = self.main_layout_widget.get_panel2()
        self.sider_bar = self.main_splitter.get_panel1()
        self.main_splitter_panel2 = self.main_splitter.get_panel2()
        
        # 嵌套的MainQWidget實例，用於設置panel2的內容
        self.nested_widget = w.MainQWidget(
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
        self.terminal_panel = self.nested_splitter.get_panel2()

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
        self.set_sider_bar(mode="init")
        self.set_start_bar(self.config['buttons']['start_bar']['Home'])
        #增加對display_panel的設置
        self.initialize_display_panels()
        # 設置terminal
        self.set_terminal(self.config['terminal'])

    def initialize_display_panels(self):
        # 初始化所有显示面板
        self.create_images_display_panel()
        self.set_text_display_panel("Home")

    def create_images_display_panel(self):
        self.images_display_panel = w.ImagesDisplayPanel(
            image1_array=None, 
            image2_array=None,
            parent=self.display_panel
            )
        self.display_panel.addToLayout(self.images_display_panel)
        self.images_display_panel.setVisible(False)
        print("Images display panel has been created.")

    def get_or_create_text_display_panel(self, mode):
        if mode not in self.text_display_panels:
            display_panel = self.get_text_display_panel(self.config["display_text"][mode])
            self.display_panel.addToLayout(display_panel)
            self.text_display_panels[mode] = display_panel
            display_panel.setVisible(False)
        return self.text_display_panels[mode]
        
    def set_terminal(self, terminal_settings):
        # 設置終端
        if self.terminal_panel is None:
            print(f"{self.terminal_panel} is None")
            return
        
        welcome_message = terminal_settings['welcome_message']
        font_size = terminal_settings['font_size']
        background_color = terminal_settings['background_color']

        self.terminal_widget = w.TerminalWidget(
            welcome_message=welcome_message, 
            font_size=font_size, 
            background_color=background_color,
            parent=self.terminal_panel
            )

        self.terminal_panel.clearAndAddWidget(self.terminal_widget)

    def set_terminal_message(self, sender, message):
        # 設置終端信息
        if self.terminal_widget is None:
            print(f"{self.terminal_widget} is None")
            return
        self.terminal_widget.post_message(sender, message)
    
    def show_error(self, errorDialog_settings, title, message):
        background_color = errorDialog_settings["background_color"]
        error_dialog = w.ErrorDialog(self, title=title, message=message, background_color=background_color)
        error_dialog.exec_()  # Show the dialog modally

    def set_sider_bar(self, mode="Home"):
        if self.sider_bar is None:
            print(f"{self.sider_bar} is None")
            return
        
        sidebar_config = self.config['sidebar']
        config_settings = sidebar_config['settings']
        config_callback = sidebar_config['callback']
        config_single_modes = self.config['sidebar']['selection_mode']['single']
        config_multiple_modes = self.config['sidebar']['selection_mode']['multiple']

        callback_function = None
        if config_settings is not None and 'callback' in sidebar_config:
            callback_function = getattr(self, config_callback, None)

        if mode in config_single_modes:
            selection_mode = "single"
        elif mode in config_multiple_modes:
            selection_mode = "multiple"
        else:
            selection_mode = "single"
        
        if mode == "init":
            self.treeWidget = w.ConfigurableTree(
                callback=callback_function, 
                selectionMode=selection_mode,
                parent=self.sider_bar
            )
            for mode_key, mode_settings in config_settings.items():
                for group_name, group_info in mode_settings.items():
                    extra_data = {
                        "description": ", ".join(group_info['description']),
                        "mode": mode_key
                    }
                    group = self.treeWidget.addGroup(group_name, extra_data)
                    for name, description in zip(group_info['name'], group_info['description']):
                        widget = w.SettingsWidget(name, description, parent=self.treeWidget)
                        self.treeWidget.addItem(group, widget, name)
            
            self.sider_bar.addToLayout(self.treeWidget)
            self.treeWidget.update_visibility_by_mode("Home")
        else:
            self.treeWidget.update_visibility_by_mode(mode)

        if mode in config_single_modes:
            self.treeWidget.selectionMode = "single"
        elif mode in config_multiple_modes:
            self.treeWidget.selectionMode = "multiple"

    def set_button_bar(self, bar, buttons_info):
        # 通用方法設置按鈕欄
        if bar is None:
            print(f"{bar} is None")
            return
        bar.removeAllWidgets()
        for button in buttons_info:
            button_widget = w.ButtonWidget(
                name=button['name'],
                owner=button['owner'],
                color=button['color'],
                icon=button['icon'],
                callback=getattr(self, button['callback']),
                size=button['size'],
                parent=bar
            )
            bar.addToLayout(button_widget)

    def set_activity_bar(self, activity_bar_buttons):
        # 設置活動欄
        self.set_button_bar(self.activity_bar, activity_bar_buttons)

    def set_start_bar(self, start_bar_buttons):
        self.set_button_bar(self.start_bar, start_bar_buttons)

    def get_text_display_panel(self, display_panel_text):
        # 獲取TextDisplayPanel實例
        return w.TextDisplayPanel(
            title=display_panel_text['title'],
            content=display_panel_text['content'],
            background_color=display_panel_text['background_color'],
            font_color=display_panel_text['font_color'],
            title_font_size=display_panel_text['title_font_size'],
            content_font_size=display_panel_text['content_font_size']
        )

    def set_text_display_panel(self, mode):
        if self.display_panel is None:
            print("display_panel is None")
            return

        text_display_panel = self.get_or_create_text_display_panel(mode)

        print("Set text display panel")

        self.images_display_panel.setVisible(False)

        for panel in self.text_display_panels.values():
            panel.setVisible(False)

        text_display_panel.setVisible(True)

    def set_images_display_panel(self):
        if self.display_panel is None:
            print("display_panel is None")
            return

        print("Set images display panel")

        for panel in self.text_display_panels.values():
            panel.setVisible(False)

        self.images_display_panel.setVisible(True)

    def get_treeWidget_selected(self):
        all_items = self.treeWidget.get_treeWidget_selected()
        if all_items is None:
            return {}
        else:
            current_mode_items = self.get_current_mode_items(all_items)

        return current_mode_items

    def get_current_mode_items(self, all_items):
        current_mode_items = {}
        
        current_mode = self.current_mode

        mode_settings = self.config['sidebar']['settings'].get(current_mode, {})
        
        required_items = mode_settings.get('Required', {}).get('name', [])
        optional_items = mode_settings.get('Optional', {}).get('name', [])

        all_mode_items = required_items + optional_items

        for item_name in all_mode_items:
            if item_name in all_items:
                current_mode_items[item_name] = all_items[item_name]

        return current_mode_items
        

    def create_detail_panel(self, mode, selected_items):
        # 创建详细设置面板
        print(f"Create detail panel for {mode} mode with selected items: {selected_items}")

        dialog = None
        if mode == "Record":
            #如果selected_items裡面，Playback rosbag的Value為True，則顯示錯誤信息
            if selected_items["Playback rosbag"]:
                dialog = w.ConfirmDialog("Confirmation", selected_items, callback=self.callback, select_type="folder", enable_realsense_check=False, parent=self)
            else:
                dialog = w.ConfirmDialog("Confirmation", selected_items, callback=self.callback, select_type="folder", enable_realsense_check=True, parent=self)
        elif mode == "RunSystem":
            dialog = w.ConfirmDialog("Confirmation", selected_items, callback=self.callback, select_type="File", enable_realsense_check=False, parent=self)
        
        if dialog is not None:
            if dialog.exec_() == QDialog.Accepted:
                print("Confirmed:", dialog.get_selection())
                return True, dialog.get_selected_path(), dialog.get_realsense_selection()
            else:
                print("Cancelled")
        return False, None, None

    def callback(self, info):
        # 按鈕的回調函數
        print(f"Button name: {info['name']}, Owner: {info['owner']}")

        owner = info["owner"]
        name = info["name"]
        if "data" in info:
            data = info["data"]
        else:
            data = None

        if owner == "activity_bar":
            self.handle_activity_bar_callback(name)
        elif owner == "configurable_tree":
            self.handle_configurable_tree_callback(name)
        elif owner == "start_bar":
            self.handle_start_bar_callback(name)
        elif owner == "confirm_dialog":
            return self.handel_confirm_dialog_callback(name, data)

    def get_gui_callback(self):
        return self.recive_form_view

    def handle_activity_bar_callback(self, name):
        self.set_terminal_message("activity_bar", f"{name} button clicked.")
        self.set_sider_bar(mode=name)
        self.set_start_bar(self.config['buttons']['start_bar'][name])
        self.set_text_display_panel(name)
        self.current_mode = name

    def handle_configurable_tree_callback(self, name):
        self.set_text_display_panel(name)

    def handle_start_bar_callback(self, name):
        self.set_terminal_message("start_bar", f"{name} button clicked.")

        if name == "start":
            self.handle_start_button()
        elif name == "stop":
            self.handle_stop_button()
        elif name == "secord":
            pass

    def handle_start_button(self):
        if not self.activated:
            selected_items_dict = self.get_treeWidget_selected()
            print(f"Selected items: {selected_items_dict}") 

            if selected_items_dict:
                if not self.check_selected_items(selected_items_dict):
                    return

                success, selected_path, realsense_selection = self.create_detail_panel(self.current_mode, selected_items_dict)
                if success:                  
                    self.set_terminal_message("start_bar", f"Send selected items to Controller: {self.current_mode} {selected_items_dict}")
                    self.set_terminal_message("start_bar", f"Selected Path: {selected_path}, Realsense Selection: {realsense_selection}")
                    self.send_to_view("send_selected_items", selected_items_dict=selected_items_dict, realsense_selection=realsense_selection, selected_path=selected_path)
                    self.set_images_display_panel()
                    self.activated = True
            else:
                self.activated = True
                
                self.set_terminal_message("start_bar", f"Send selected items to Controller: {self.current_mode} {selected_items_dict}")
                self.send_to_view("send_selected_items", selected_items_dict)
        else:
            self.set_terminal_message("start_bar", "ERROR! The system is already running.")
            self.show_error(self.config['error_dialog'], "Error", "The system is already running.")

    def handle_stop_button(self):
        if self.activated:
            self.set_terminal_message("start_bar", "Stop the system.")
            self.send_to_view("stop_record")
            self.activated = False

    def check_selected_items(self, selected_items_dict):
        required_item = self.config["sidebar"]["settings"][self.current_mode]["Required"]["name"]
        
        #如果selected_items_dict裡面key為required_item的value皆為False，則顯示錯誤信息
        if all([selected_items_dict[key] == False for key in required_item]):
            self.set_terminal_message("start_bar", "ERROR! Required items are not selected.")
            self.show_error(self.config['error_dialog'], "Error", "Required items are not selected.")
            return False
        
        return True
    
    def handel_confirm_dialog_callback(self, name, data):
        if name == "check_realsense":
            return self.send_to_view("get_realsense_profiles")
        elif name == "check_dir":
            return self.send_to_view("check_dir", data=data)
        elif name == "check_file":
            return self.send_to_view("check_file", data=data)

    def send_to_view(self, mode, selected_items_dict = None, realsense_selection=None, selected_path=None, data=None):
        if self.callback_to_view is None:
            print("No callback function is set.")
            return
        
        if mode == "send_selected_items":
            self.callback_to_view(
                "start_record", 
                selected_items_dict=selected_items_dict, 
                realsense_selection=realsense_selection, 
                selected_path=selected_path,
                data=data
                )
            
        elif mode == "get_realsense_profiles":
            return self.callback_to_view("get_realsense_profiles")
        elif mode == "check_dir":
            return self.callback_to_view("check_dir", data=data)
        elif mode == "check_file":
            return self.callback_to_view("check_file", data=data)
        
        elif mode == "stop_record":
            self.callback_to_view("stop_record")

    def recive_form_view(self, mode, data):
        if mode == "record_imgs":
            self.update_image_display_panel(data['depth_image'], data['color_image'])

    def update_image_display_panel(self, image1_array, image2_array):
        if self.images_display_panel is not None:
            self.images_display_panel.update_images(image1_array, image2_array)
        else:
            print("Images display panel is None")

    def sizeHint(self):
        # 設置視窗大小
        return QSize(1200, 800)
    
    def setZeroMarginsAndSpacing(self, layout):
        # 設置佈局的邊距和間距
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

if __name__ == "__main__":
    # 啟動應用程序
    app = QApplication(sys.argv)
    main_interface = MainInterface()
    main_interface.show()
    sys.exit(app.exec_())
