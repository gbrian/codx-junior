# [[{"id": "0", "parent_id": "", "status": "", "tags": [], "file_list": [], "profiles": [], "name": "Image to text", "created_at": "2024-10-18T10:21:08.742639", "updated_at": "2024-10-18T10:21:08.742639", "mode": "chat", "board": "<none>", "column": "new column", "column_index": 10000, "chat_index": 0, "live_url": "", "branch": ""}]]
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
## [[{"role": "system", "hide": true, "improvement": false, "created_at": "2024-10-18T10:21:08.742747", "images": [], "files": []}]]
# INSTRUCTIONS:
              
              BEGIN INSTRUCTIONS
    This is a converation between you and the user about the project api.
    Please always keep your answers short and simple unless a more detailed answer has been requested.
    END INSTRUCTIONS
    

              # REQUEST
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
              
## [[{"role": "assistant", "hide": false, "improvement": false, "created_at": "2024-10-18T10:21:08.742771", "images": [], "files": ["/codx/junior/app.py"]}]]
To create the `api_image_to_text` function in `engine.py` and integrate it with FastAPI in `app.py`, follow these steps:

1. **Create the `api_image_to_text` function in `engine.py`:**

```python
# /projects/codx-junior/api/codx/junior/engine.py

from PIL import Image
import pytesseract
import io

def api_image_to_text(image_bytes):
    # Convert bytes data to a PIL Image
    image = Image.open(io.BytesIO(image_bytes))
    
    # Extract text from image using pytesseract
    text = pytesseract.image_to_string(image)
    
    return text
```

2. **Integrate the function in `app.py` to handle the FastAPI request:**

```python
# /projects/codx-junior/api/codx/junior/app.py

from fastapi import UploadFile, File
from fastapi.responses import JSONResponse
from .engine import api_image_to_text

# Add this endpoint in the FastAPI app
@app.post("/api/image-to-text")
async def api_image_to_text_endpoint(file: UploadFile = File(...)):
    # Read the file bytes
    file_bytes = await file.read()
    
    # Call the function to extract text
    extracted_text = api_image_to_text(file_bytes)
    
    # Return the extracted text as a JSON response
    return JSONResponse(content={"extracted_text": extracted_text})
```

**Explanation:**

- **`engine.py`:** The `api_image_to_text` function takes image bytes as input, converts them to a PIL Image, and uses `pytesseract` to extract text.
  
- **`app.py`:** The `/api/image-to-text` endpoint receives an image file, reads its bytes, and passes them to `api_image_to_text`. The extracted text is returned as a JSON response.