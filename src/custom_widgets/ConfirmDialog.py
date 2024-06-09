import sys
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QTextEdit, QComboBox, QLineEdit, QMessageBox
from PyQt5.QtCore import Qt
import os

class ConfirmDialog(QDialog):
    def __init__(self, title, selection, callback=None, parent=None, select_type='folder', enable_realsense_check=False):
        """
        初始化 ConfirmDialog。

        參數:
        title (str): 對話框標題。
        selection (dict): 顯示在對話框中的選擇項。
        callback (callable, optional): 用於回調的函式。預設為 None。
        parent (QWidget, optional): 父級窗口。預設為 None。
        select_type (str, optional): 選擇類型，'folder' 或 'file'。預設為 'folder'。
        enable_realsense_check (bool, optional): 是否啟用 Realsense 檢查。預設為 False。
        """
        super().__init__(parent)
        self.setWindowTitle(title)

        self.callback = callback
        self.selection = selection
        self.select_type = select_type  # 'folder' 或 'file'
        self.enable_realsense_check = enable_realsense_check  # 是否啟用 Realsense 檢查
        
        self.realsense_checked = not enable_realsense_check  # 初始狀態，如果不啟用則默認通過
        self.path_selected = False  # 是否已選擇路徑
        self.selected_path = ''  # 存儲選擇的路徑

        self.matched_depth_profiles = []  # 存儲匹配的深度配置文件
        self.selected_color_profiles = []  # 存儲選中的顏色配置文件

        self.initUI()
    
    def initUI(self):
        """
        初始化用戶界面。
        """
        font_style = "font-family: 'Consolas', 'Courier New', 'Lucida Console', monospace;"

        layout = QVBoxLayout()

        # 標題
        self.title_label = QLabel("Confirm Your Selection")
        self.title_label.setStyleSheet(f"font-size: 18pt; font-weight: bold; color: white; {font_style}")
        layout.addWidget(self.title_label)

        # 顯示選擇項
        self.selection_text = QTextEdit()
        self.selection_text.setReadOnly(True)
        self.selection_text.setStyleSheet(f"background-color: #1E1E1E; color: #DCDCDC; font-size: 12pt; {font_style}")
        selection_content = "\n".join(f"{key}: {value}" for key, value in self.selection.items())
        self.selection_text.setText(selection_content)
        layout.addWidget(self.selection_text)

        # 檢查 Realsense 按鈕和組合框（根據 enable_realsense_check 顯示）
        if self.enable_realsense_check:
            self.check_realsense_button = QPushButton("Check Realsense")
            self.check_realsense_button.setStyleSheet(f"background-color: #333; color: white; font-weight: bold; padding: 5px; {font_style}")
            self.check_realsense_button.clicked.connect(self.check_realsense_profiles)
            layout.addWidget(self.check_realsense_button)

            self.realsense_combobox = QComboBox()
            self.realsense_combobox.setStyleSheet(f"background-color: #1E1E1E; color: #DCDCDC; font-size: 12pt; {font_style}")
            layout.addWidget(self.realsense_combobox)

        # 手動輸入路徑和驗證按鈕
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

        # 按鈕佈局
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
        """
        回調 callback 來檢查 Realsense 配置文件。
        """
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
        """
        格式化配置文件。

        參數:
        profile (tuple): 配置文件元組。

        回傳:
        str: 格式化的配置文件字符串。
        """
        width, height, fps = profile[:3]
        return f"width={width}, height={height}, fps={fps}"

    def verify_path(self):
        """
        驗證輸入的路徑，會回調 callback 來獲取結果。
        """
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
        """
        顯示覆蓋確認對話框。

        回傳:
        int: 對話框返回值。
        """
        dialog = QMessageBox()
        dialog.setIcon(QMessageBox.Warning)
        dialog.setWindowTitle("Confirm Overwrite")
        dialog.setText("The directory contains files. Do you want to overwrite?")
        dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dialog.setDefaultButton(QMessageBox.No)
        return dialog.exec_()

    def update_ok_button_state(self):
        """
        更新確認按鈕的狀態。
        """
        self.ok_button.setEnabled(self.realsense_checked and self.path_selected)

    def get_selection(self):
        """
        獲取選擇項。

        回傳:
        dict: 選擇項字典。
        """
        return self.selection

    def get_selected_path(self):
        """
        獲取選擇的路徑。

        回傳:
        str: 選擇的路徑。
        """
        return self.selected_path

    def get_realsense_selection(self):
        """
        獲取 Realsense 選擇項。

        回傳:
        list: 選擇的 Realsense 配置文件列表。
        """
        if self.enable_realsense_check:
            selected_text = self.realsense_combobox.currentText()
            # 在 matched_depth_profiles 和 selected_color_profiles 中找到與 selected_text 匹配的配置文件
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
    
    def dummy_callback(params):
        if params["name"] == "check_realsense":
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
        elif params["name"] == "check_dir":
            if params["data"] == "/valid/path":
                return "ContainsRealsenseBag"
            else:
                return "NotExist"
        elif params["name"] == "check_file":
            if params["data"] == "/valid/file":
                return True
            else:
                return False
        return None
    
    dialog = ConfirmDialog("Confirmation", {"Item 1": "Value 1", "Item 2": "Value 2"}, callback=dummy_callback, select_type='folder', enable_realsense_check=True)
    result = dialog.exec_()
    if result == QDialog.Accepted:
        print("Confirmed:", dialog.get_selection())
        print("Selected Path:", dialog.get_selected_path())
        print("Realsense Selection:", dialog.get_realsense_selection())
    else:
        print("Cancelled")
    app.quit()  # 顯式調用退出
