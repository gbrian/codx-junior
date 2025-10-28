import unittest
from unittest.mock import patch, MagicMock
from codx.junior.changes.watch_project_file_changes import WatchProjectFileChanges, get_common_path_and_merged_ignores

# TESTS
class TestWatchProjectFileChanges(unittest.TestCase):
    def setUp(self):
        self.watcher = WatchProjectFileChanges()

    @patch('codx.junior.project.project_discover.find_all_projects')
    def test_grouping_projects(self, mock_find_all_projects):
        mock_find_all_projects.return_value = {
            'project1': MagicMock(project_path='/path/to/project1', knowledge_file_ignore=['ignore1']),
            'project2': MagicMock(project_path='/path/to/project2', knowledge_file_ignore=['ignore2']),
            'project3': MagicMock(project_path='/path/to/project1/subproject', knowledge_file_ignore=['ignore3']),
        }
        project_groups = list(get_common_path_and_merged_ignores(mock_find_all_projects().values()))
        self.assertEqual(len(project_groups), 2)
        self.assertIn('/path/to/project1', [group[0] for group in project_groups])
        self.assertIn('/path/to/project2', [group[0] for group in project_groups])
        for path, ignores in project_groups:
            if path == '/path/to/project1':
                self.assertEqual(ignores, {'ignore1', 'ignore3'})
            elif path == '/path/to/project2':
                self.assertEqual(ignores, {'ignore2'})

    @patch('codx.junior.project.project_discover.find_all_projects')
    def test_observers_are_recreated(self, mock_find_all_projects):
        mock_find_all_projects.return_value = {
            'project1': MagicMock(project_path='/path/to/project1', knowledge_file_ignore=[]),
            'project2': MagicMock(project_path='/path/to/project2', knowledge_file_ignore=[]),
        }
        self.watcher.check_for_new_projects()
        self.assertEqual(len(self.watcher.observers), 2)

        # Update projects to only one
        mock_find_all_projects.return_value = {
            'project1': MagicMock(project_path='/path/to/project1', knowledge_file_ignore=[]),
        }
        self.watcher.check_for_new_projects()
        self.assertEqual(len(self.watcher.observers), 1)

        # Now test with 4 projects, 2 sharing the same parent path
        mock_find_all_projects.return_value = {
            'project1': MagicMock(project_path='/path/to/project1', knowledge_file_ignore=[]),
            'project2': MagicMock(project_path='/path/to/project2', knowledge_file_ignore=[]),
            'project3': MagicMock(project_path='/path/to/project1/subproject1', knowledge_file_ignore=[]),
            'project4': MagicMock(project_path='/path/to/project3', knowledge_file_ignore=[]),
        }
        self.watcher.check_for_new_projects()
        self.assertEqual(len(self.watcher.observers), 3)

if __name__ == '__main__':
    unittest.main()