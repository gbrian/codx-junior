# [[{"id": "0", "parent_id": "", "status": "", "tags": [], "file_list": [], "profiles": [], "name": "Image to text", "created_at": "2024-10-18T10:21:08.742639", "updated_at": "2025-01-10T04:34:40.476791", "mode": "chat", "board": "Default", "column": "tasks", "chat_index": 0, "live_url": "", "branch": "", "file_path": "/shared/codx-junior/api/.codx/tasks/Default/tasks/Image to text.md"}]]
## [[{"role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2024-10-18T10:21:08.742716", "updated_at": "2025-01-10 04:28:05.776892", "images": [], "files": []}]]
create api_image_to_text() in engine.py will receive a file form the fastapi request body at app.py
Then will extract text from the image using pytesseract
Example:
```python
from PIL import Image

import pytesseract

# If you don't have tesseract executable in your PATH, include the following:
pytesseract.pytesseract.tesseract_cmd = r'<full_path_to_your_tesseract_executable>'
# Example tesseract_cmd = r'C:\Program Files (x86)\Tesseract-OCR\tesseract'

# Simple image to string
print(pytesseract.image_to_string(Image.open('test.png')))

# In order to bypass the image conversions of pytesseract, just use relative or absolute image path
# NOTE: In this case you should provide tesseract supported images or tesseract will return error
print(pytesseract.image_to_string('test.png'))
```