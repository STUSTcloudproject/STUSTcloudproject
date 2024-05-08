import sys
from PyQt5.QtWidgets import QApplication
from ApplicationModel import ApplicationModel
from ApplicationView import ApplicationView
from ApplicationController import ApplicationController

if __name__ == "__main__":
    app = QApplication(sys.argv)
    model = ApplicationModel()
    view = ApplicationView()
    controller = ApplicationController(model, view)
    view.show()
    sys.exit(app.exec_())
