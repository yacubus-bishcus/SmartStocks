import os
import sys
import pkg_resources

class StockInput:
    def __init__(self, filename, debug=False):
        self.filename = filename
        self.debug = debug

    def __del(self):
        pass

    def read_txt_file(self):
        data = []
        filepath = pkg_resources.resource_filename('StockApp.user_input', self.filename)
        if os.path.exists(filepath):
            with open(filepath, 'r') as file:
                for line in file:
                    # Remove newline characters and any leading/trailing whitespaces
                    line = line.strip()
                    data.append(line)
        else:
            print(f"The file '{self.filename}' does not exist. Please check spelling and retry.")
            sys.exit(0)
        return data
