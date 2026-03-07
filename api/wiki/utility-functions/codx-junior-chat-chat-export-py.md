This document describes the `ChatExport` class, a utility for exporting chat conversations into various formats.

## `ChatExport` Class

The `ChatExport` class is designed to handle the conversion of chat content into different exportable formats, such as Markdown, PDF, or DOCX, by leveraging the `pypandoc` library.

### Initialization

The `ChatExport` class is initialized with the following parameters:

*   `chat`: An object representing the chat conversation.
*   `content`: A string containing the chat content in Markdown format.
*   `export_format`: A string specifying the desired output format for the export (e.g., "markdown", "pdf", "docx").

### Methods

#### `convert_to_format(self, markdown: str) -> bytes`

This method uses `pypandoc` to convert the provided Markdown `content` into the format specified by `self.export_format`.

*   **Purpose**: To transform the chat content from Markdown to a target format.
*   **Input**:
    *   `markdown`: A string containing the chat content in Markdown format.
*   **Output**: A `bytes` object containing the converted document content.
*   **Error Handling**: Logs any errors encountered during the conversion process and raises the exception. It also ensures temporary files are removed.

#### `export_chat(self) -> ExportedDocument`

This method orchestrates the export process. It first builds the Markdown document and then converts it to the desired format if it's not already Markdown. Finally, it returns an `ExportedDocument` object containing the file content, file name, and content type.

*   **Purpose**: To generate the final exported document in the specified format.
*   **Output**: An `ExportedDocument` object. This object includes:
    *   `content`: The binary content of the exported file.
    *   `file_name`: The name of the exported file (e.g., "chat\_export.pdf").
    *   `content_type`: The MIME type of the exported file (e.g., "application/pdf").
*   **Logging**: Logs information about the export, including the chat name, format, and size of the document.

### `ExportedDocument` Class

A simple data class to hold the results of an export operation.

#### Initialization

The `ExportedDocument` class is initialized with:

*   `content`: The binary content of the exported file.
*   `file_name`: The desired name for the exported file.
*   `content_type`: The MIME type of the file.

```python /codx/junior/chat/chat_export.py
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
        markdown = self.content
        content = markdown if self.export_format == "markdown" else self.convert_to_format(markdown)
        file_name = f"chat_export.{self.export_format}"
        content_type = f"application/{self.export_format}"
        logger.info("Exporting document: %s, format: %s, size: %s", self.chat.name, self.export_format, len(markdown))
        return ExportedDocument(content=content, file_name=file_name, content_type=content_type)
```