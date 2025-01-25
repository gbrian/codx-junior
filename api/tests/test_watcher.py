import unittest
import time
import os

from api.codx.junior.project_watcher import ProjectWatcher

import logging;
logger = logging.getLogger(__name__)


class TestProjectWatcher(unittest.TestCase):
    def setUp(self):
        def callback(changes):
            self.changes = changes
        self.watcher = ProjectWatcher(
            callback=callback
        )
        self.project_path = "/tmp"
        self.temp_file = f"{self.project_path}/temp_test_file.txt"
        logger.info(f"Set test at {self.temp_file}")

    def tearDown(self):
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def test_start_and_stop_watching(self):
        self.changes = []
        self.watcher.watch_project(self.project_path)
        # Create a temporary file to trigger the callback
        with open(self.temp_file, "w") as f:
            f.write("test")

        time.sleep(1)
        logger.info(f"Check changes {self.changes}")
        # Assert that changes were detected
        self.assertIn(self.temp_file, self.changes)

        # Stop watching
        self.watcher.stop_watching(self.project_path)


if __name__ == "__main__":
    unittest.main()