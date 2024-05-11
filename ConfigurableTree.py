from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette

class ConfigurableTree(QTreeWidget):
    def __init__(self, parent=None):
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
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.itemDoubleClicked.connect(self.toggleItemState)

    def addGroup(self, group_name):
        group = QTreeWidgetItem(self, [group_name])
        group.setExpanded(True)
        return group

    def addItem(self, parent, widget, data):
        item = QTreeWidgetItem(parent)
        self.setItemWidget(item, 0, widget)
        # Store additional data in the item for retrieval
        item.setData(0, Qt.UserRole, data)

    def toggleItemState(self, item, column):
        # Retrieve stored data from the item
        custom_data = item.data(0, Qt.UserRole)
        print(f"Double-clicked on item: {custom_data}")

