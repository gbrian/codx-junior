# [[{"id": "0", "parent_id": "", "status": "", "tags": [], "file_list": [], "profiles": [], "name": "Image to text", "created_at": "2024-10-18T10:21:08.742639", "updated_at": "2024-10-20T06:18:45.099971", "mode": "chat", "board": "<none>", "column": "Profiles", "column_index": 0, "chat_index": 0, "live_url": "", "branch": ""}]]
## [[{"role": "user", "hide": false, "improvement": false, "created_at": "2024-10-18T10:21:08.742716", "images": [], "files": []}]]
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