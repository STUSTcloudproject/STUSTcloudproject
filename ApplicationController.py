class ApplicationController:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.view.connect_events(self)

    def handle_mode(self, mode):
        if mode == 1:
            settings = {'resolution': '1080p', 'fps': 30}  # Mock settings
            message = self.model.start_camera(settings)
            self.view.display_message(message)
        elif mode == 2:
            data = "sample_video_data"  # Mock data
            message = self.model.process_data(data)
            self.view.display_message(message)
        elif mode == 3:
            message = self.model.visualize_data()
            self.view.display_message(message)