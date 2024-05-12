from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette

class ConfigurableTree(QTreeWidget):
    def __init__(self, parent=None, callback=None, selectionMode='single'):
        super().__init__(parent)
        self.setColumnCount(1)
        self.setHeaderHidden(True)
        self.setIndentation(0)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
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
        """)
        self.callback = callback
        self.selectionMode = selectionMode
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.itemClicked.connect(self.handleItemClick)
        self.itemDoubleClicked.connect(self.toggleItemState)

    def addGroup(self, group_name, data=None):
        group = QTreeWidgetItem(self, [group_name])
        group.setExpanded(True)
        if data is not None:
            group.setData(0, Qt.UserRole, data)
        return group

    def addItem(self, parent, widget, data):
        item = QTreeWidgetItem(parent)
        self.setItemWidget(item, 0, widget)
        # Store additional data in the item for retrieval
        item.setData(0, Qt.UserRole, data)

    def handleItemClick(self, item, column):
        # 处理单击事件的方法
        custom_data = item.data(0, Qt.UserRole)
        if self.callback:
            self._emit_button_info(self.callback, custom_data)

    def toggleItemState(self, item, column):
        # Retrieve stored data from the item
        custom_data = item.data(0, Qt.UserRole)
        widget = self.itemWidget(item, 0)
        print(f"Double-clicked on item: {custom_data}")
        if self.selectionMode == 'single' and widget.get_selected() is False:
            self.setAllItemsSelection(False)
        widget.toggle_selection()

    def setAllItemsSelection(self, selected):
        """遍历所有 items 并设置其 widget 的选中状态"""
        iterator = QTreeWidgetItemIterator(self)
        while iterator.value():
            item = iterator.value()
            widget = self.itemWidget(item, 0)
            if widget and hasattr(widget, 'toggle_selection'):
                widget.toggle_selection(selected)
            iterator += 1

    def _emit_button_info(self, callback, custom_data):
        # 發送按鈕信息
        info = {'name': custom_data, 'owner': "configurable_tree"}
        callback(info)  # Call the callback with the info dictionary

