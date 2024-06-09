from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette

class ConfigurableTree(QTreeWidget):
    def __init__(self, parent=None, callback=None, selectionMode='single'):
        """
        初始化 ConfigurableTree。

        參數:
        parent (QWidget, optional): 父級窗口。預設為 None。
        callback (callable, optional): 項目點擊的回調函數。預設為 None。
        selectionMode (str, optional): 選擇模式。預設為 'single'。
        """
        super().__init__(parent)
        self.setColumnCount(1)  # 設置列數為 1
        self.setHeaderHidden(True)  # 隱藏標題
        self.setIndentation(0)  # 設置縮進為 0
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 垂直滾動條總是隱藏
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 水平滾動條總是隱藏
        self.setStyleSheet("""
            QTreeWidget {
                background-color: transparent;
                border: none;
                color: white;
            }
            QTreeWidget::item {
                border-bottom: 1px solid #555;
            }
            QTreeWidget::item:selected {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
            }
        """)  # 設置樣式表

        self.callback = callback
        self.selectionMode = selectionMode
        self.setAttribute(Qt.WA_TranslucentBackground)  # 設置透明背景
        self.itemClicked.connect(self.handleItemClick)  # 連接項目點擊信號
        self.itemDoubleClicked.connect(self.toggleItemState)  # 連接項目雙擊信號

    def addGroup(self, group_name, data=None):
        """
        添加分組項目。

        參數:
        group_name (str): 分組名稱。
        data (any, optional): 分組相關的數據。預設為 None。

        回傳:
        QTreeWidgetItem: 創建的分組項目。
        """
        group = QTreeWidgetItem(self, [group_name])
        group.setExpanded(True)  # 展開分組
        if data is not None:
            group.setData(0, Qt.UserRole, data)  # 設置分組數據
        return group

    def addItem(self, parent, widget, data):
        """
        添加項目到指定的分組。

        參數:
        parent (QTreeWidgetItem): 父級分組項目。
        widget (QWidget): 要添加的小工具。
        data (any): 項目相關的數據。
        """
        item = QTreeWidgetItem(parent)
        self.setItemWidget(item, 0, widget)  # 設置項目的小工具
        item.setData(0, Qt.UserRole, data)  # 設置項目數據

    def handleItemClick(self, item, column):
        """
        處理項目點擊事件。

        參數:
        item (QTreeWidgetItem): 被點擊的項目。
        column (int): 被點擊的列。
        """
        custom_data = item.data(0, Qt.UserRole)
        if not isinstance(custom_data, dict) and self.callback:
            self._emit_button_info(self.callback, custom_data)  # 發送按鈕信息

    def toggleItemState(self, item, column):
        """
        切換項目狀態。

        參數:
        item (QTreeWidgetItem): 被雙擊的項目。
        column (int): 被雙擊的列。
        """
        custom_data = item.data(0, Qt.UserRole)
        if not isinstance(custom_data, dict):
            widget = self.itemWidget(item, 0)
            if self.selectionMode == 'single' and not widget.get_selected() and widget.get_group_name() == 'Required':
                self.setRequiredItemsSelection(False)  # 設置必需項目選擇狀態
            widget.toggle_selection()  # 切換選擇狀態

    def setRequiredItemsSelection(self, selected):
        """
        設置必需項目的選擇狀態。

        參數:
        selected (bool): 是否選擇。
        """
        iterator = QTreeWidgetItemIterator(self)
        while iterator.value():
            item = iterator.value()
            widget = self.itemWidget(item, 0)
            if widget and hasattr(widget, 'toggle_selection') and widget.get_group_name() == 'Required':
                widget.toggle_selection(selected)  # 切換選擇狀態
            iterator += 1

    def get_treeWidget_selected(self):
        """
        獲取選中的項目。

        回傳:
        dict: 包含選中項目名稱和選擇狀態的字典。
        """
        iterator = QTreeWidgetItemIterator(self)
        selected_items = {}
        while iterator.value():
            item = iterator.value()
            widget = self.itemWidget(item, 0)
            if widget and hasattr(widget, 'get_title') and hasattr(widget, 'get_selected'):
                selected_items[widget.get_title()] = widget.get_selected()  # 獲取項目選擇狀態
            iterator += 1
        return selected_items

    def _emit_button_info(self, callback, custom_data):
        """
        發送按鈕信息。

        參數:
        callback (callable): 回調函數。
        custom_data (any): 自定義數據。
        """
        info = {'name': custom_data, 'owner': "configurable_tree"}
        callback(info)  # 使用信息字典調用回調函數

    def update_visibility_by_mode(self, mode):
        """
        根據模式更新項目可見性。

        參數:
        mode (str): 模式。
        """
        iterator = QTreeWidgetItemIterator(self)
        while iterator.value():
            item = iterator.value()
            data = item.data(0, Qt.UserRole)
            if isinstance(data, dict) and "mode" in data:
                item.setHidden(data["mode"] != mode)  # 設置項目可見性
            iterator += 1
