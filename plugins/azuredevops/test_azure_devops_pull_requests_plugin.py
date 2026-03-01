import pytest
import unittest
from unittest.mock import MagicMock, patch
from azure_devops_pull_requests_plugin import AzureDevopsPullRequestPlugin, ThreadModel

@pytest.fixture
def setup_plugin():
    # Set up the mock environment, token, and URL for testing
    personal_access_token = 'fake_token'
    organization_url = 'https://dev.azure.com/fake_org'
    project_path = '/path/to/project'
    plugin = AzureDevopsPullRequestPlugin(personal_access_token, organization_url, project_path)
    return plugin

def test_read_threads(setup_plugin):
    plugin = setup_plugin
    # Mock the connection and git client methods
    plugin.connection = MagicMock()
    git_client_mock = MagicMock()
    plugin.connection.clients.get_git_client.return_value = git_client_mock

    # Mock the pull request threads data
    threads_data = [
        MagicMock(status='active', 
                  thread_context=MagicMock(file_path='src/file1.py', right_file_start=MagicMock(line=10)),
                  comments=[MagicMock(content='Comment 1')]),
        MagicMock(status='resolved',
                  thread_context=MagicMock(file_path='src/file2.py', left_file_start=MagicMock(line=20)),
                  comments=[MagicMock(content='Comment 2')])
    ]

    # Set the return value for get_threads method
    git_client_mock.get_threads.return_value = threads_data

    # Call the read_threads method
    pr_url = 'https://dev.azure.com/fake_org/fake_project/_git/fake_repo/pullrequest/1'
    threads = plugin.read_threads(pr_url)

    # Assertions to ensure the read_threads method works as expected
    assert len(threads) == 2
    assert threads[0].status == 'active'
    assert threads[0].file_path == 'src/file1.py'
    assert threads[0].line == 10
    assert threads[0].comments == 'Comment 1'

def test_modify_file_content(setup_plugin):
    plugin = setup_plugin
    # Original file content
    file_contents = ['Line 1\n', 'Line 2\n', 'Line 3\n']
    # Comments to insert
    comments_to_insert = [(1, 'Comment 1'), (2, 'Comment 2')]

    # Expected file content after insertion
    expected_content = [
        'Line 1\n',
        '<codx-ok, please-wait...>Comment 1</codx-ok, please-wait...>\n',
        'Line 2\n',
        '<codx-ok, please-wait...>Comment 2</codx-ok, please-wait...>\n',
        'Line 3\n'
    ]

    # Call the modify_file_content method
    modified_content = plugin.modify_file_content(file_contents, comments_to_insert)

    # Assertions to ensure the method works as expected
    assert modified_content == expected_content