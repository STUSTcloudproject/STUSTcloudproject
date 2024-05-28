import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import o3d_gui

class ViewSystem:
    def __init__(self, callback=None):
        self.callback = callback

    def run(self):
        try:
            print("\n\nView System is running\n\n")
            o3d_gui.run()
        except Exception as e:
            print(f"Error starting run: {e}")
            self.send_to_model("show_error", {"title": "Error starting run", "message": str(e)})

    def receive_from_model(self, mode, data=None):
        try:
            if mode == "start_view_system":
                self.run()
        except Exception as e:
            print(f"Error receiving from model: {e}")
            self.send_to_model("show_error", {"title": "Error receiving from model", "message": str(e)})

    def send_to_model(self, mode, data=None):
        if self.callback is not None:
            try:
                if mode == "show_error":
                    self.callback(mode, data)
                elif mode == "terminal_print":
                    self.callback(mode, data)
            except Exception as e:
                print(f"Error sending to model: {e}")
                if mode != "show_error":
                    self.callback("show_error", {"title": "Error sending to model", "message": str(e)})

# Usage Example
if __name__ == "__main__":
    system = ViewSystem()
    system.run()
