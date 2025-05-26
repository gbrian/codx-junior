# test_wiki_manager.py

import unittest
from unittest.mock import Mock, patch, mock_open
import os

from codx.junior.api.codx.junior.wiki.wiki_manager import WikiManager
from codx.junior.settings import CODXJuniorSettings


class TestWikiManager(unittest.TestCase):

    def setUp(self):
        # Mock settings
        self.mock_settings = Mock(spec=CODXJuniorSettings)
        self.mock_settings.get_project_wiki_path.return_value = '/path/to/wiki'
        self.mock_settings.project_name = 'MyProject'
        self.mock_settings.project_icon = 'icon.png'
        self.mock_settings.project_path = '/path/to/project'
        
        # Initialize WikiManager with mocked settings
        self.manager = WikiManager(self.mock_settings)

    @patch('os.makedirs')
    @patch('os.path.exists', return_value=False)
    @patch('shutil.copytree')
    @patch('builtins.open', new_callable=mock_open, read_data='PROJECT_NAME')
    def test_initialize_vitepress_creates_config(self, mock_open, mock_copytree, mock_exists, mock_makedirs):
        # Test initializing VitePress configuration
        self.manager.create_vitepress_config()

        # Assert make directories and copy tree called
        mock_makedirs.assert_called_with('/path/to/wiki/.vitepress')
        mock_copytree.assert_called_with(os.path.join(os.path.dirname(__file__), 'wiki_template'), '/path/to/wiki', dirs_exist_ok=True)
        
        # Assert template content is replaced
        mock_open().write.assert_any_call('MyProject')  # PROJECT_NAME replaced

    @patch('codx.junior.utils.exec_command', return_value=('', ''))
    @patch('os.path.isdir', return_value=True)
    def test_build_wiki_executes_command(self, mock_isdir, mock_exec_command):
        # Test build wiki method
        self.manager.build_wiki()

        # Assert exec_command was called with correct parameters
        mock_exec_command.assert_called_with('bash wiki-manager.sh', cwd='/path/to/wiki')

    @patch('os.path.exists', side_effect=[False, True])  # Assuming wiki dir doesn't exist initially
    @patch('os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs', return_value=None)
    def test_update_wiki_creates_wiki_content(self, mock_makedirs, mock_open, mock_exists):
        # Mock the knowledge_wiki.generate_wiki method
        self.manager.knowledge_wiki = Mock()
        self.manager.knowledge_wiki.generate_wiki.return_value = "Generated Wiki Content"

        # Test updating wiki for a new file
        file_path = '/path/to/project/newfile.py'
        self.manager.update_wiki(file_path)

        # Verify directories are created and the file is written
        mock_makedirs.assert_called_once_with('/path/to/wiki/newfile')
        mock_open().write.assert_called_once_with("Generated Wiki Content")

    @patch('os.remove')
    @patch('os.path.exists', return_value=True)
    def test_delete_wiki_file_removes_file(self, mock_exists, mock_remove):
        # Test delete_wiki_file method
        file_path = '/path/to/project/deletedfile.py'
        self.manager.delete_wiki_file(file_path)
        
        # Assert file removal
        mock_remove.assert_called_once_with('/path/to/wiki/deletedfile.py.md')
        
    @patch('builtins.open', new_callable=mock_open, read_data=' ')
    def test_update_vitepress_config(self, mock_open):
        # Test `update_vitepress_config` method
        
        new_files = ['/path/to/project/newfile.py']
        deleted_files = ['/path/to/project/deletedfile.py']
        
        self.manager.update_vitepress_config(new_files, deleted_files)
        
        # Check if the config file has updated entries
        written_data = mock_open().write.call_args[0][0]
        self.assertIn('.pages.push("/newfile.py.md");', written_data)
        self.assertNotIn('/deletedfile.py.md', written_data)
    
    # Additional tests for update_wiki_tree and related methods can be constructed similarly

if __name__ == '__main__':
    unittest.main()
