from Camera import Camera
from DataProcessor import DataProcessor
from Visualizer import Visualizer

class ApplicationModel:
    def __init__(self):
        self.camera = None
        self.processor = None
        self.visualizer = None

    def start_camera(self, settings):
        self.camera = Camera(settings)
        return self.camera.run()

    def process_data(self, data):
        self.processor = DataProcessor(data)
        return self.processor.process()

    def visualize_data(self):
        if self.processor:
            self.visualizer = Visualizer(self.processor.data)
            return self.visualizer.visualize()
        else:
            return "No data to visualize"