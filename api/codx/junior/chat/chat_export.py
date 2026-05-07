import os
import logging
from typing import Dict, Any, List
import pypandoc
from codx.junior.db import Chat, Message

logger = logging.getLogger(__name__)

class ExportedDocument:
    def __init__(self, content: bytes, file_name: str, content_type: str):
        self.content = content
        self.file_name = file_name
        self.content_type = content_type

class ChatExport:
    def __init__(self, chat, content, export_format: str):
        self.chat = chat
        self.content = content
        self.export_format = export_format

    def convert_to_format(self, markdown: str) -> bytes:
        output_file = f"/tmp/chat_export.{self.export_format}"
        
        # Define extra arguments to handle Unicode/Emojis
        extra_args = ['--pdf-engine=xelatex'] if self.export_format == 'pdf' else []
        
        try:
            pypandoc.convert_text(
                markdown, 
                to=self.export_format, 
                format='md', 
                outputfile=output_file,
                extra_args=extra_args  # Pass the engine flag here
            )
            with open(output_file, 'rb') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error converting markdown to {self.export_format}: {e}")
            raise
        finally:
            if os.path.exists(output_file):
                os.remove(output_file)

        return content

    def export_chat(self) -> ExportedDocument:
        """
        Build the markdown document and convert it to the desired format.
        Return an ExportedDocument with headers for the client and the document content.
        """
        markdown = self.content
        content = markdown if self.export_format == "markdown" else self.convert_to_format(markdown)
        file_name = f"chat_export.{self.export_format}"
        content_type = f"application/{self.export_format}"
        logger.info("Exporting document: %s, format: %s, size: %s", self.chat.name, self.export_format, len(markdown))
        return ExportedDocument(content=content, file_name=file_name, content_type=content_type)
