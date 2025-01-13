import unittest
from unittest.mock import MagicMock
from project_watcher import ProjectWatcher

class TestProjectWatcher(unittest.TestCase):
    def setUp(self):
        self.project_watcher = ProjectWatcher()
        self.mock_callback = MagicMock()

    def test_start_and_stop_watching(self):
        project_path = '/shared/codx-junior/api/codx/junior'
        self.project_watcher.start_watching(project_path, self.mock_callback)

        # Simulate a file change
        self.mock_callback.assert_not_called()

        # Stop watching
        self.project_watcher.stop_watching()
        self.assertIsNone(self.project_watcher.observer)

if __name__ == '__main__':
    unittest.main()