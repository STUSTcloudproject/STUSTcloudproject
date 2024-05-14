from PyQt5.QtWidgets import QMessageBox, QApplication
from PyQt5.QtGui import QColor

class ErrorDialog(QMessageBox):
    def __init__(self, parent=None, title="Error", message="An error has occurred.", background_color="#FF0000"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setIcon(QMessageBox.Warning)
        self.setStandardButtons(QMessageBox.Ok)
        self.setText(message)
        self.set_background_color(background_color)

    def set_background_color(self, color):
        self.setStyleSheet(f"""
            QMessageBox {{
                background-color: {color};
                color: white;
            }}
            QMessageBox QLabel {{
                color: white;
            }}
        """)

# Example usage
if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    dialog = ErrorDialog(title="Validation Error", message="An error occurred during validation.", background_color="#1E1E1E")
    dialog.show()
    app.exec_()
