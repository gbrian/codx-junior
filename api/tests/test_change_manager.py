import time
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from codx.junior.changes.change_manager import ChangeManager
from codx.junior.knowledge.knowledge_milvus import Knowledge
from codx.junior.mentions.mention_manager import MentionManager


class TestChangeManager(unittest.TestCase):

    def setUp(self):
        self.settings = MagicMock()
        self.event_manager = MagicMock()

        # Mock settings
        self.settings.is_valid_project.return_value = True
        self.settings.project_name = "TestProject"
        self.settings.watching = True

        # Create an instance of ChangeManager
        self.change_manager = ChangeManager(settings=self.settings, event_manager=self.event_manager)

    @patch.object(Knowledge, 'clean_deleted_documents')
    @patch.object(Knowledge, 'detect_changes')
    def test_check_project_changes_no_new_files(self, mock_detect_changes, mock_clean_deleted_documents):
        # Arrange
        mock_detect_changes.return_value = []  # No new files detected

        # Act
        result = self.change_manager.check_project_changes()

        # Assert
        self.assertFalse(result)

    @patch.object(Knowledge, 'clean_deleted_documents')
    @patch.object(Knowledge, 'detect_changes')
    def test_check_project_changes_with_new_files(self, mock_detect_changes, mock_clean_deleted_documents):
        # Arrange
        mock_detect_changes.return_value = ["new_file.py"]

        # Act
        result = self.change_manager.check_project_changes()

        # Assert
        self.assertTrue(result)

    @patch.object(Knowledge, 'clean_deleted_documents')
    @patch.object(Knowledge, 'detect_changes')
    @patch.object(Knowledge, 'reload_path')
    @patch.object(MentionManager, 'check_file_for_mentions', new_callable=AsyncMock)
    def test_process_project_changes_with_new_files(self, mock_check_file_for_mentions, mock_reload_path,
                                                    mock_detect_changes, mock_clean_deleted_documents):
        # Arrange
        mock_detect_changes.return_value = (["new_file.py"], None)
        mock_check_file_for_mentions.return_value = "processed"

        # Mock 'os.stat' to simulate file modification time
        with patch('os.stat') as mock_stat:
            mock_stat.return_value.st_mtime = time.time() - 10  # File modified 10 seconds ago

            # Act
            import asyncio
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.change_manager.process_project_changes())

        # Assert
        mock_check_file_for_mentions.assert_called_once_with(file_path="new_file.py")
        mock_reload_path.assert_called_once_with(path="new_file.py")
        self.event_manager.send_knowled_event.assert_called_once_with(type="loaded", file_path="new_file.py")


if __name__ == '__main__':
    unittest.main()
