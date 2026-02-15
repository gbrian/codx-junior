import pytest
from unittest.mock import MagicMock, patch
from project_file_watcher import ProjectFileWatcher

@pytest.fixture
def mock_awatch():
    with patch('project_file_watcher.awatch') as mock_awatch:
        mock_awatch.return_value = [("modified", "/valid/path/to/file.py")]
        yield mock_awatch

@pytest.fixture
def mock_knowledge():
    with patch('project_file_watcher.Knowledge') as MockKnowledge:
        MockKnowledge.return_value.is_valid_file.return_value = True
        yield MockKnowledge

@pytest.fixture
def mock_callback():
    return MagicMock()

def test_file_watcher(mock_awatch
, mock_knowledge, mock_callback):
    # Initialize ProjectFileWatcher
    project_settings = {'project_path': '/project/path'}
    stop_event = MagicMock()
    
    watcher = ProjectFileWatcher(project_settings, stop_event, mock_callback)

    # Trigger the file watch
    watcher._start_watching()

    # Validate the callback was called
    mock_callback.assert_called_with([("modified", "/valid/path/to/file.py")])