# /shared/codx-junior/api/tests/mention_manager/test_mention_manager.py
import unittest
import logging
from unittest.mock import MagicMock, patch
from typing import List
from codx.junior.mentions.mention_manager import MentionManager, Mention, MentionFlags
from codx.junior.settings import CODXJuniorSettings

# Configure logging for the testing module
logger = logging.getLogger(__name__)

class TestMentionManager(unittest.TestCase):

    def setUp(self):
        """
        Set up mock managers and initialize MentionManager with mocked dependencies.
        This ensures isolation and prevents dependency on external modules
        during testing.
        """
        event_manager = MagicMock()
        settings = CODXJuniorSettings()
        
        self.mention_manager = MentionManager(settings, event_manager)

    def test_extract_mentions_single_line(self) -> None:
        """
        Test extracting mentions from a single-line content.
        """
        content = "Some text @codx: mention content"
        mentions: List[Mention] = self.mention_manager.extract_mentions(content)
        
        self.assertEqual(len(mentions), 1)
        self.assertEqual(mentions[0].mention, "mention content")
        logger.debug("test_extract_mentions_single_line passed.")

    def test_extract_mentions_single_line_with_comment(self) -> None:
        """
        Test extracting mentions from a single line that includes comments.
        """
        content = "# Some comment related to @codx: another mention"
        mentions: List[Mention] = self.mention_manager.extract_mentions(content)
        
        self.assertEqual(len(mentions), 1)
        self.assertEqual(mentions[0].mention, "another mention")
        logger.debug("test_extract_mentions_single_line_with_comment passed.")

    def test_extract_mentions_multi_line(self) -> None:
        """
        Test extracting mentions across multiple lines.
        """
        content = "Some text\n<codx Start of mention\nContinued mention content\n</codx>"
        mentions: List[Mention] = self.mention_manager.extract_mentions(content)
        
        self.assertEqual(len(mentions), 1)
        self.assertIn("Start of mention", mentions[0].mention)
        logger.debug("test_extract_mentions_multi_line passed.")

    def test_mention_flags(self) -> None:
        """
        Test the extraction of mention flags such as model type and chat id.
        """
        content = "@codx: --knowledge --model=gpt --chat-id=1234 --code"
        mentions: List[Mention] = self.mention_manager.extract_mentions(content)
        mention = mentions[0]

        self.assertTrue(mention.flags.knowledge)
        self.assertEqual(mention.flags.model, "gpt")
        self.assertEqual(mention.flags.chat_id, "1234")
        self.assertTrue(mention.flags.code)
        self.assertFalse(hasattr(mention.flags, 'image') and mention.flags.image)
        logger.debug("test_mention_flags passed.")

    def test_mentions_stream(self) -> None:
        """
        Test the transformation of mention content to indicate progress.
        """
        content = "Some initial text\n@codx: mention\nMore text"
        modified_content = self.mention_manager.notify_mentions_in_progress(content)
        
        self.assertIn("@codx-ok, please-wait...:", modified_content)
        logger.debug("test_mentions_stream passed.")

    def test_file_changes_does_not_contain_mentions(self) -> None:
        """
        Test the stripping of mention instructions from the content.
        """
        content = """
        <codx Start of mention content
        More mention content
        </codx>
        Normal content
        """
  
        mentions: List[Mention] = self.mention_manager.extract_mentions(content)
        modified_content = self.mention_manager.strip_mentions(content, mentions)
        
        for mention in mentions:
            self.assertNotIn(mention.mention, modified_content)
        logger.debug("test_file_changes_does_not_contain_mentions passed.")

    def test_is_processing_mentions(self) -> None:
        """
        Test detection of processing state within content.
        """
        content_with_progress = "Some text\n@codx-ok, please-wait...: mention"
        content_without_progress = "Some text\n@codx: mention"
        self.assertTrue(self.mention_manager.is_processing_mentions(content_with_progress))
        self.assertFalse(self.mention_manager.is_processing_mentions(content_without_progress))
        logger.debug("test_is_processing_mentions passed.")

    def test_notify_mentions_error(self) -> None:
        """
        Test appending error notification to content.
        """
        content = "Some text\n@codx-ok, please-wait...: mention"
        error = "an error occurred"
        modified_content = self.mention_manager.notify_mentions_error(content, error)
        
        self.assertIn(f"codx-error: {error}", modified_content)
        logger.debug("test_notify_mentions_error passed.")

    def test_replace_mentions(self) -> None:
        """
        Test replacing mention content with new content.
        """
        original_content = "Some text\n@codx: mention\nMore text"
        mentions: List[Mention] = [Mention(mention="mention", start_line=1, end_line=1, new_content="updated content")]
        replaced_content = self.mention_manager.replace_mentions(original_content, mentions)
        
        self.assertIn("updated content", replaced_content)
        self.assertNotIn("@codx: mention", replaced_content)
        logger.debug("test_replace_mentions passed.")

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data='file content')
    def test_read_file(self, mock_open) -> None:
        """
        Test reading file content, including special cases for .ipynb files.
        """
        file_path = 'example.txt'
        content = self.mention_manager.read_file(file_path)
        
        self.assertEqual(content, 'file content')
        logger.debug("test_read_file passed.")

