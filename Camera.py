class Camera:
    def __init__(self, settings):
        self.settings = settings

    def run(self):
        return "Camera running with settings: {}".format(self.settings)