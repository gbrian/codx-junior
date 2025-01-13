import unittest
import time
import os
from codx.junior.watcher import ProjectWatcher


class TestProjectWatcher(unittest.TestCase):
    def setUp(self):
        self.watcher = ProjectWatcher()
        self.temp_file = "temp_test_file.txt"

    def tearDown(self):
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def test_start_and_stop_watching(self):
        changes = []

        def callback(file_path):
            changes.append(file_path)

        # Start watching
        self.watcher.start_watching(".", callback)
        # Create a temporary file to trigger the callback
        with open(self.temp_file, "w") as f:
            f.write("test")
        time.sleep(1)
        # Assert that changes were detected
        self.assertIn(self.temp_file, changes)

        # Stop watching
        self.watcher.stop_watching(".")


if __name__ == "__main__":
    unittest.main()