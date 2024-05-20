import sys
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QTextEdit, QComboBox, QLineEdit, QMessageBox
from PyQt5.QtCore import Qt
import os

class ConfirmDialog(QDialog):
    def __init__(self, title, selection, callback=None, parent=None, select_type='folder', enable_realsense_check=False):
        super().__init__(parent)
        self.setWindowTitle(title)

        self.callback = callback
        self.selection = selection
        self.select_type = select_type  # 'folder' or 'file'
        self.enable_realsense_check = enable_realsense_check  # 是否启用 Realsense 检查
        
        self.realsense_checked = not enable_realsense_check  # 初始状态，如果不启用则默认通过
        self.path_selected = False  # 是否已选择路径
        self.selected_path = ''  # 存储选择的路径

        self.matched_depth_profiles = []  # 存储匹配的深度配置文件
        self.selected_color_profiles = []  # 存储选中的颜色配置文件

        self.initUI()
    
    def initUI(self):
        font_style = "font-family: 'Consolas', 'Courier New', 'Lucida Console', monospace;"

        layout = QVBoxLayout()

        # 标题
        self.title_label = QLabel("Confirm Your Selection")
        self.title_label.setStyleSheet(f"font-size: 18pt; font-weight: bold; color: white; {font_style}")
        layout.addWidget(self.title_label)

        # 显示选择项
        self.selection_text = QTextEdit()
        self.selection_text.setReadOnly(True)
        self.selection_text.setStyleSheet(f"background-color: #1E1E1E; color: #DCDCDC; font-size: 12pt; {font_style}")
        selection_content = "\n".join(f"{key}: {value}" for key, value in self.selection.items())
        self.selection_text.setText(selection_content)
        layout.addWidget(self.selection_text)

        # Check Realsense 按钮和组合框（根据 enable_realsense_check 显示）
        if self.enable_realsense_check:
            self.check_realsense_button = QPushButton("Check Realsense")
            self.check_realsense_button.setStyleSheet(f"background-color: #333; color: white; font-weight: bold; padding: 5px; {font_style}")
            self.check_realsense_button.clicked.connect(self.check_realsense_profiles)
            layout.addWidget(self.check_realsense_button)

            self.realsense_combobox = QComboBox()
            self.realsense_combobox.setStyleSheet(f"background-color: #1E1E1E; color: #DCDCDC; font-size: 12pt; {font_style}")
            layout.addWidget(self.realsense_combobox)

        # 手动输入路径和验证按钮
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Enter the path manually")
        self.path_input.setStyleSheet(f"background-color: #1E1E1E; color: #DCDCDC; font-size: 12pt; {font_style}")
        layout.addWidget(self.path_input)

        self.verify_button = QPushButton("Verify Path")
        self.verify_button.setStyleSheet(f"background-color: #333; color: white; font-weight: bold; padding: 5px; {font_style}")
        self.verify_button.clicked.connect(self.verify_path)
        layout.addWidget(self.verify_button)

        self.selected_path_label = QLabel("Selected Path: None")
        self.selected_path_label.setStyleSheet(f"color: #DCDCDC; font-size: 12pt; {font_style}")
        layout.addWidget(self.selected_path_label)

        # 按钮布局
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("Confirm")
        self.ok_button.setStyleSheet(f"background-color: #333; color: white; font-weight: bold; padding: 5px; {font_style}")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setEnabled(False)  # 初始禁用

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet(f"background-color: #333; color: white; font-weight: bold; padding: 5px; {font_style}")
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.setStyleSheet(f"background-color: #1E1E1E; border: none; {font_style}")

    def check_realsense_profiles(self):
        if self.callback:
            self.matched_depth_profiles, self.selected_color_profiles = self.callback({"name": "check_realsense", "owner": "confirm_dialog"})
            if (isinstance(self.matched_depth_profiles, list) and self.matched_depth_profiles and
                isinstance(self.selected_color_profiles, list) and self.selected_color_profiles):
                profiles_str = [self.format_profile(profile) for profile in self.matched_depth_profiles]
                self.realsense_combobox.clear()
                self.realsense_combobox.addItems(profiles_str)
                self.realsense_checked = True
            else:
                self.realsense_combobox.clear()
                self.realsense_checked = False
            self.update_ok_button_state()

    def format_profile(self, profile):
        # profile 是一个元组，我们需要将其转换为所需的格式
        width = profile[0]
        height = profile[1]
        fps = profile[2]
        return f"width={width}, height={height}, fps={fps}"

    def verify_path(self):
        path = self.path_input.text()
        if self.select_type == 'folder':
            path_status = self.callback({"name": "check_dir", "owner": "confirm_dialog", "data": path})

            if path_status == "NotExist":
                self.selected_path_label.setText("Selected Path: Invalid Folder")
                self.path_selected = False
                self.selected_path = ''
            elif path_status == "Empty":
                if self.enable_realsense_check:
                    self.selected_path_label.setText(f"Selected Path: {path}")
                    self.path_selected = True
                    self.selected_path = path
                else:
                    self.selected_path_label.setText("Selected Path: No realsense.bag Found")
                    self.path_selected = False
                    self.selected_path = ''
            elif path_status in ["ContainsRealsenseBag", "ContainsOtherFiles"]:
                if self.enable_realsense_check:
                    result = self.show_overwrite_dialog()
                    if result == QMessageBox.Yes:  # 替換這裡為對話框邏輯
                        self.selected_path_label.setText(f"Selected Path: {path}")
                        self.path_selected = True
                        self.selected_path = path
                    else:
                        self.selected_path_label.setText("Selected Path: Contains Other Files")
                        self.path_selected = False
                        self.selected_path = ''
                else:
                    if path_status == "ContainsRealsenseBag":
                        self.selected_path_label.setText(f"Selected Path: {path}")
                        self.path_selected = True
                        self.selected_path = path
                    else:
                        self.selected_path_label.setText("Selected Path: No realsense.bag Found")
                        self.path_selected = False
                        self.selected_path = ''                     
        else:
            if self.callback({"name": "check_file", "owner": "confirm_dialog", "data": path}):
                self.selected_path_label.setText(f"Selected Path: {path}")
                self.path_selected = True
                self.selected_path = path
            else:
                self.selected_path_label.setText("Selected Path: Invalid File")
                self.path_selected = False
                self.selected_path = ''
        self.update_ok_button_state()

    def show_overwrite_dialog(self):
        dialog = QMessageBox()
        dialog.setIcon(QMessageBox.Warning)
        dialog.setWindowTitle("Confirm Overwrite")
        dialog.setText("The directory contains files. Do you want to overwrite?")
        dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dialog.setDefaultButton(QMessageBox.No)
        return dialog.exec_()

    def update_ok_button_state(self):
        if self.realsense_checked and self.path_selected:
            self.ok_button.setEnabled(True)
        else:
            self.ok_button.setEnabled(False)

    def get_selection(self):
        return self.selection

    def get_selected_path(self):
        return self.selected_path

    def get_realsense_selection(self):
        if self.enable_realsense_check:
            selected_text = self.realsense_combobox.currentText()
            # 在 matched_depth_profiles 和 selected_color_profiles 中找到与 selected_text 匹配的配置文件
            selected_profiles = []
            for dp in self.matched_depth_profiles:
                if self.format_profile(dp) == selected_text:
                    selected_profiles.append(dp)
                    for cp in self.selected_color_profiles:
                        if (cp[0], cp[1], cp[2]) == (dp[0], dp[1], dp[2]):
                            selected_profiles.append(cp)
                            break
            return selected_profiles
        return None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    def dummy_callback(mode, selected_items_dict=None):
        if mode == "get_realsense_profiles":
            depth_profiles = [
                (1024, 768, 30, "format.z16"),
                (1024, 480, 30, "format.z16"),
                (640, 480, 30, "format.z16"),
                (320, 240, 30, "format.z16")
            ]
            color_profiles = [
                (640, 480, 30, "format.rgb8"),
                (640, 480, 30, "format.y16"),
                (640, 480, 30, "format.y8"),
                (640, 480, 30, "format.bgra8"),
                (640, 480, 30, "format.rgba8"),
                (640, 480, 30, "format.bgr8"),
                (640, 480, 30, "format.yuyv")
            ]
            return depth_profiles, color_profiles
        return None
    
    dialog = ConfirmDialog("Confirmation", {"Item 1": "Value 1", "Item 2": "Value 2"}, callback=dummy_callback, select_type='folder', enable_realsense_check=True)
    result = dialog.exec_()
    if result == QDialog.Accepted:
        print("Confirmed:", dialog.get_selection())
        print("Selected Path:", dialog.get_selected_path())
        print("Realsense Selection:", dialog.get_realsense_selection())
    else:
        print("Cancelled")
    app.quit()  # 显式调用退出
