class DataProcessor:
    def __init__(self, data):
        self.data = data

    def process(self):
        return "Data processed: {}".format(self.data)