## Extract Document Tags

This document provides a template for extracting tags from a document and formatting them as a CSV list.

### Usage

The following content is used to extract tags:

*   **FILE NAME:** `{{ source }}`
*   **LANGUAGE:** `{{ language }}`
*   **CONTENT:** `{{ page_content }}`

The desired output format is a CSV list:

```csv
key1,key2,key_three
```

### Example

If the `page_content` is:

"This document discusses the use of FastAPI for building web applications. It covers concepts like middleware and background tasks. Socket.IO is also mentioned for real-time communication."

And the `language` is "en", the extracted CSV list might look like:

```csv
fastapi,web applications,middleware,background tasks,socket.io,real-time communication
```

---

*This documentation was generated from the file `/codx/junior/knowledge/prepromts/extract_document_tags.md`.*