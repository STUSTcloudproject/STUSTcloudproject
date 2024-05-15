from Controller import Controller
from Model import Model
from View import View
import pythoncom

if __name__ == "__main__":
    # Initialize COM
    pythoncom.CoInitialize()
    try:
        model = Model()
        view = View()  # The controller will set the callback
        controller = Controller(model, view)
        controller.run()
    finally:
        # Uninitialize COM
        pythoncom.CoUninitialize()
