import unittest
from unittest.mock import MagicMock, patch
from codx.junior.chat.chat_engine import ChatEngine, Chat, Message

# Mock classes that would be implemented elsewhere in the package
class MockSettings:
    def get_agent_max_iterations(self):
        return 10

    def get_llm_settings(self):
        class MockAISettings:
            model = 'default-model'

        return MockAISettings()

    @property
    def project_path(self):
        return '/mock/project/path'

    @property
    def use_knowledge(self):
        return True

    @property
    def project_id(self):
        return 'mock-project-id'

class MockEventManager:
    def chat_event(self, chat, message, event_type='info'):
        pass

class MockProfileManager:
    pass

class TestChatEngine(unittest.TestCase):
    def setUp(self):
        self.settings = MockSettings()
        self.event_manager = MockEventManager()
        self.profile_manager = MockProfileManager()

        # Create an instance of ChatEngine
        self.chat_engine = ChatEngine(self.settings, self.event_manager, self.profile_manager)

    @patch('codx.junior.chat.chat_engine.ChatEngine.switch_project')
    def test_switch_project(self, mock_switch_project):
        mock_switch_project.return_value = self.chat_engine
        result = self.chat_engine.switch_project('new-project-id')
        self.assertIs(result, self.chat_engine)
        mock_switch_project.assert_called_once_with('new-project-id')

    @patch('codx.junior.chat.chat_engine.AI')
    def test_get_ai(self, MockAI):
        mock_ai_instance = MockAI.return_value
        result = self.chat_engine.get_ai('test-model')
        self.assertEqual(result, mock_ai_instance)
        MockAI.assert_called_once_with(settings=self.settings, llm_model='test-model')

