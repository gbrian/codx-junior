import os
import logging
from typing import Dict, Any
import pypandoc
from codx.junior.db import Chat

logger = logging.getLogger(__name__)

class ExportedDocument:
    def __init__(self, content: bytes, file_name: str, content_type: str):
        self.content = content
        self.file_name = file_name
        self.content_type = content_type

class ChatExport:
    def __init__(self, chat_tree: Dict[str, Any], export_format: str):
        self.chat_tree = chat_tree
        self.export_format = export_format

    def build_markdown_document(self) -> str:
        """
        Traverse the chat tree and generate a markdown document.
        Ignore messages with the 'hide' flag set to True.
        """
        def traverse_chat_tree(node, depth=0):
            markdown = ""
            if isinstance(node, Chat):
                valid_messages = [msg for msg in node.messages if not msg.hide]
                for msg in valid_messages:
                    markdown += f"{'#' * (depth + 1)} {msg.content}\n\n"
            for child in node.get("children", []):
                markdown += traverse_chat_tree(child, depth + 1)
            return markdown

        return traverse_chat_tree(self.chat_tree)

    def convert_to_format(self, markdown: str) -> bytes:
        """
        Use pypandoc to convert the markdown document into the desired format.
        """
        output_file = f"/tmp/chat_export.{self.export_format}"
        try:
            pypandoc.convert_text(markdown, to=self.export_format, format='md', outputfile=output_file)
            with open(output_file, 'rb') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error converting markdown to {self.export_format}: {e}")
            raise
        finally:
            # Ensure the temporary file is removed after conversion
            try:
                os.remove(output_file)
            except Exception as e:
                logger.error(f"Error removing temporary file {output_file}: {e}")

        return content

    def export_chat(self) -> ExportedDocument:
        """
        Build the markdown document and convert it to the desired format.
        Return an ExportedDocument with headers for the client and the document content.
        """
        markdown = self.build_markdown_document()
        content = markdown if self.export_format == "markdown" else self.convert_to_format(markdown)
        file_name = f"chat_export.{self.export_format}"
        content_type = f"application/{self.export_format}"
        return ExportedDocument(content=content, file_name=file_name, content_type=content_type)
