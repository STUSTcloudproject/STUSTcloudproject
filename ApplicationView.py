from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, QStackedWidget
import sys

class ApplicationView(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Multi-Mode GUI Application')
        self.setGeometry(100, 100, 800, 600)
        self.widgets = QStackedWidget()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Buttons for mode selection
        self.mode1_button = QPushButton('Mode 1: Recording Settings')
        self.mode2_button = QPushButton('Mode 2: Process Data')
        self.mode3_button = QPushButton('Mode 3: Visualization')

        layout.addWidget(self.mode1_button)
        layout.addWidget(self.mode2_button)
        layout.addWidget(self.mode3_button)

        main_widget = QWidget()
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

        self.message_label = QLabel("Status: Ready", self)
        layout.addWidget(self.message_label)

    def connect_events(self, controller):
        self.mode1_button.clicked.connect(lambda: controller.handle_mode(1))
        self.mode2_button.clicked.connect(lambda: controller.handle_mode(2))
        self.mode3_button.clicked.connect(lambda: controller.handle_mode(3))

    def display_message(self, message):
        self.message_label.setText(f"Status: {message}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    view = ApplicationView()
    view.show()
    sys.exit(app.exec_())