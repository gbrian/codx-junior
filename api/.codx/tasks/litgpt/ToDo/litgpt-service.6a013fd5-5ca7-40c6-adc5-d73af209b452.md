# [[{"id": "6a013fd5-5ca7-40c6-adc5-d73af209b452", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": [], "check_lists": [], "profiles": [], "users": ["admin"], "name": "litgpt-service", "description": "In this conversation, we built a FastAPI application with endpoints to manage AI model fine-tuning and chat completion processes. The API includes endpoints for project creation, dataset uploads, and model operations using a project-specific directory structure. We implemented additional endpoints for backing up and restoring tuned models. All file and command interactions are organized by project ID to ensure data management consistency. Lastly, instructions were provided to run this FastAPI application locally.", "created_at": "2025-08-30 12:19:18.184223", "updated_at": "2025-08-30T13:24:56.013759", "mode": "task", "kanban_id": "", "column_id": "", "board": "litgpt", "column": "ToDo", "chat_index": 0, "url": "", "branch": "", "file_path": "/shared/codx-junior/api/.codx/tasks/litgpt/ToDo/litgpt-service.6a013fd5-5ca7-40c6-adc5-d73af209b452.md", "llm_model": "", "visibility": "", "remote_url": "", "knowledge_topics": []}]]
## [[{"doc_id": "c3d33b09-3f16-4a38-9313-cc4417fe143f", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-08-30 12:19:18.182148", "updated_at": "2025-08-30 12:19:18.182176", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
Based on the references below, create a FastAPI app with endpoints to:
 * fine tune models 
 * chat_completion


```
# 0) setup your dataset
curl -L https://huggingface.co/datasets/ksaw008/finance_alpaca/resolve/main/finance_alpaca.json -o my_custom_dataset.json


# 1) Finetune a model (auto downloads weights)
litgpt finetune microsoft/phi-2 \
  --data JSON \
  --data.json_path my_custom_dataset.json \
  --data.val_split_fraction 0.1 \
  --out_dir out/custom-model


# 2) Test the model
litgpt chat out/custom-model/final


# 3) Deploy the model
litgpt serve out/custom-model/final
```


## [[{"doc_id": "e17f12ae-ebba-471b-bf90-e4c86e38403d", "role": "assistant", "task_item": "", "think": null, "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-08-30 12:19:18.182148", "updated_at": "2025-08-30 12:19:18.182176", "images": [], "files": [], "meta_data": {"time_taken": 11.597596645355225, "first_chunk_time_taken": 0.0002512931823730469, "model": "openai/gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": null, "disable_knowledge": false, "read_by": []}]]
To create a FastAPI application with endpoints to fine-tune models and perform chat completions, we can implement it based on the provided commands and documentation. We'll create an API with two primary endpoints: one for fine-tuning a model and another for using the model for chat completions. Here's how you can build it:

```python /app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import os

app = FastAPI()

# Define a Pydantic model for input data for fine-tuning
class FinetuneRequest(BaseModel):
    model_name: str
    dataset_path: str
    val_split_fraction: float
    output_dir: str

# Define a Pydantic model for chat completion input
class ChatCompletionRequest(BaseModel):
    input_text: str
    model_dir: str

@app.post("/finetune")
async def finetune_model(request: FinetuneRequest):
    try:
        # Construct the fine-tune command
        command = [
            "litgpt", "finetune", request.model_name,
            "--data", "JSON",
            "--data.json_path", request.dataset_path,
            f"--data.val_split_fraction={request.val_split_fraction}",
            "--out_dir", request.output_dir
        ]
        
        # Execute the command
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=result.stderr)

        return {"message": "Model fine-tuning started successfully.", "output": result.stdout}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat_completion")
async def chat_completion(request: ChatCompletionRequest):
    try:
        # Construct the chat command
        command = ["litgpt", "chat", request.model_dir]
        
        # Execute the command
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate(input=request.input_text)

        if process.returncode != 0:
            raise HTTPException(status_code=500, detail=stderr)

        return {"response": stdout}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Explanation:

- **FastAPI Setup:** The application is initialized using FastAPI, with routes for `finetune` and `chat_completion`.

- **Fine-tuning Endpoint (`/finetune`):** This endpoint accepts a request containing the model name, dataset path, validation split fraction, and output directory. It constructs and executes a subprocess command using `litgpt` to run the fine-tuning process. If successful, it returns a success message; otherwise, it returns an error.

- **Chat Completion Endpoint (`/chat_completion`):** This endpoint accepts the input text for the model and the directory where the trained model is saved. It communicates with the `litgpt` service to generate a chat response.

- **Pydantic Models:** These are used to validate the input data for both endpoints, ensuring that the correct data structure is received.

- **Error Handling:** Both routes include error handling to raise HTTP exceptions if any issues occur during subprocess execution.

### Instructions to Run the API:

1. Save the code to a file named `main.py`.
2. Install FastAPI and Uvicorn (if not already installed) using `pip install fastapi[all]`.
3. Start the FastAPI app by running `uvicorn app.main:app --reload`.
4. Interact with the API at `http://localhost:8000`.
## [[{"doc_id": "36125a42-0c7c-4d3e-8971-5bcd462c6748", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-08-30 12:19:18.182148", "updated_at": "2025-08-30 12:19:18.182176", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
Add enpoints to upoload a dataset and model instructions.
The create project payload will be:
 * project: Project id
 * model: model name to fine tune
 * dettings: dict A dictinary of settings to pass to the fine tune instructions
 
 The upload dataset will be PUT /projects/{project_id}/data and will uploaded a zipped json datatset


Create local folders using the project id to store the data and settings
## [[{"doc_id": "2882c230-5c1e-407c-a177-742b1f1ad094", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-08-30 12:19:18.182148", "updated_at": "2025-08-30 12:19:18.182176", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
Add enpoints to upoload a dataset and model instructions.
The create project payload will be:
 * project: Project id
 * model: model name to fine tune
 * dettings: dict A dictinary of settings to pass to the fine tune instructions
 
 The upload dataset will be PUT /projects/{project_id}/data and will uploaded a zipped json datatset


Create local folders using the project id to store the data and settings
                    Update the document with user comments:
                    <document>
                    To create a FastAPI application with endpoints to fine-tune models and perform chat completions, we can implement it based on the provided commands and documentation. We'll create an API with two primary endpoints: one for fine-tuning a model and another for using the model for chat completions. Here's how you can build it:

```python /app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import os

app = FastAPI()

# Define a Pydantic model for input data for fine-tuning
class FinetuneRequest(BaseModel):
    model_name: str
    dataset_path: str
    val_split_fraction: float
    output_dir: str

# Define a Pydantic model for chat completion input
class ChatCompletionRequest(BaseModel):
    input_text: str
    model_dir: str

@app.post("/finetune")
async def finetune_model(request: FinetuneRequest):
    try:
        # Construct the fine-tune command
        command = [
            "litgpt", "finetune", request.model_name,
            "--data", "JSON",
            "--data.json_path", request.dataset_path,
            f"--data.val_split_fraction={request.val_split_fraction}",
            "--out_dir", request.output_dir
        ]
        
        # Execute the command
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=result.stderr)

        return {"message": "Model fine-tuning started successfully.", "output": result.stdout}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat_completion")
async def chat_completion(request: ChatCompletionRequest):
    try:
        # Construct the chat command
        command = ["litgpt", "chat", request.model_dir]
        
        # Execute the command
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate(input=request.input_text)

        if process.returncode != 0:
            raise HTTPException(status_code=500, detail=stderr)

        return {"response": stdout}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Explanation:

- **FastAPI Setup:** The application is initialized using FastAPI, with routes for `finetune` and `chat_completion`.

- **Fine-tuning Endpoint (`/finetune`):** This endpoint accepts a request containing the model name, dataset path, validation split fraction, and output directory. It constructs and executes a subprocess command using `litgpt` to run the fine-tuning process. If successful, it returns a success message; otherwise, it returns an error.

- **Chat Completion Endpoint (`/chat_completion`):** This endpoint accepts the input text for the model and the directory where the trained model is saved. It communicates with the `litgpt` service to generate a chat response.

- **Pydantic Models:** These are used to validate the input data for both endpoints, ensuring that the correct data structure is received.

- **Error Handling:** Both routes include error handling to raise HTTP exceptions if any issues occur during subprocess execution.

### Instructions to Run the API:

1. Save the code to a file named `main.py`.
2. Install FastAPI and Uvicorn (if not already installed) using `pip install fastapi[all]`.
3. Start the FastAPI app by running `uvicorn app.main:app --reload`.
4. Interact with the API at `http://localhost:8000`.
                    </document>
                    User comments:
                    Add enpoints to upoload a dataset and model instructions.
The create project payload will be:
 * project: Project id
 * model: model name to fine tune
 * dettings: dict A dictinary of settings to pass to the fine tune instructions
 
 The upload dataset will be PUT /projects/{project_id}/data and will uploaded a zipped json datatset


Create local folders using the project id to store the data and settings
                    Important: Always return the markdown document without any comments before or after, to keep it clean.
## [[{"doc_id": "fecdb27d-69fb-4e5b-8283-87e0f3970f28", "role": "assistant", "task_item": "analysis", "think": null, "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-08-30 12:19:18.182148", "updated_at": "2025-08-30 12:19:18.182176", "images": [], "files": [], "meta_data": {"time_taken": 10.30495548248291, "first_chunk_time_taken": 0.0001430511474609375, "model": "openai/gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": null, "disable_knowledge": false, "read_by": []}]]
To create a FastAPI application with endpoints to fine-tune models and perform chat completions, we can implement it based on the provided commands and documentation. We'll create an API with two primary endpoints: one for fine-tuning a model and another for using the model for chat completions. Here's how you can build it:

```python /app/main.py
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import subprocess
import os
import shutil
import zipfile

app = FastAPI()

# Define a Pydantic model for creating a project and its settings
class CreateProjectRequest(BaseModel):
    project: str
    model: str
    settings: dict

# Define a Pydantic model for input data for fine-tuning
class FinetuneRequest(BaseModel):
    model_name: str
    dataset_path: str
    val_split_fraction: float
    output_dir: str

# Define a Pydantic model for chat completion input
class ChatCompletionRequest(BaseModel):
    input_text: str
    model_dir: str

@app.post("/create_project")
async def create_project(request: CreateProjectRequest):
    try:
        # Create project directory
        project_dir = f"./projects/{request.project}"
        os.makedirs(project_dir, exist_ok=True)

        # Save settings to a file
        settings_path = os.path.join(project_dir, "settings.json")
        with open(settings_path, "w") as f:
            f.write(str(request.settings))

        return {"message": f"Project {request.project} created successfully."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/projects/{project_id}/data")
async def upload_dataset(project_id: str, file: UploadFile = File(...)):
    try:
        # Create data directory for the project
        data_dir = f"./projects/{project_id}/data"
        os.makedirs(data_dir, exist_ok=True)

        # Ensure the uploaded file is a zip file
        if not file.filename.endswith(".zip"):
            raise HTTPException(status_code=400, detail="Only zip files are allowed.")

        # Save the uploaded file
        zip_path = os.path.join(data_dir, file.filename)
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Extract the zip file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(data_dir)

        return {"message": f"Dataset for project {project_id} uploaded and extracted successfully."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/finetune")
async def finetune_model(request: FinetuneRequest):
    try:
        # Construct the fine-tune command
        command = [
            "litgpt", "finetune", request.model_name,
            "--data", "JSON",
            "--data.json_path", request.dataset_path,
            f"--data.val_split_fraction={request.val_split_fraction}",
            "--out_dir", request.output_dir
        ]
        
        # Execute the command
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=result.stderr)

        return {"message": "Model fine-tuning started successfully.", "output": result.stdout}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat_completion")
async def chat_completion(request: ChatCompletionRequest):
    try:
        # Construct the chat command
        command = ["litgpt", "chat", request.model_dir]
        
        # Execute the command
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate(input=request.input_text)

        if process.returncode != 0:
            raise HTTPException(status_code=500, detail=stderr)

        return {"response": stdout}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Explanation:

- **FastAPI Setup:** The application is initialized using FastAPI, with routes for creating projects, uploading datasets, fine-tuning, and chat completion.

- **Project Creation Endpoint (`/create_project`):** This endpoint accepts a request containing the project ID, model name, and settings. It creates a directory for the project and stores the settings in a file.

- **Dataset Upload Endpoint (`/projects/{project_id}/data`):** This endpoint allows uploading a zip file containing a JSON dataset. It extracts the dataset into the project-specific data directory.

- **Fine-tuning Endpoint (`/finetune`):** Uses provided parameters to start fine-tuning a model.

- **Chat Completion Endpoint (`/chat_completion`):** Generates chat responses using a trained model.

- **Directory Management:** For both projects and datasets, local directories are created using the project ID to organize data and settings.

### Instructions to Run the API:

1. Save the code to a file named `main.py`.
2. Install FastAPI and Uvicorn (if not already installed) using `pip install fastapi[all]`.
3. Start the FastAPI app by running `uvicorn app.main:app --reload`.
4. Interact with the API at `http://localhost:8000`.
## [[{"doc_id": "32b77a69-0a01-4365-9ec8-99195f1ece9e", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-08-30 12:19:18.182148", "updated_at": "2025-08-30 12:19:18.182176", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
* Add enpoints to backup and restore tunned models
* Make sure all operations interaction with litgpt or files uses the project_id as the base path 
## [[{"doc_id": "0c41bbe9-5b11-4edb-a4f3-c896981f915b", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-08-30 12:19:18.182148", "updated_at": "2025-08-30 12:19:18.182176", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
* Add enpoints to backup and restore tunned models
* Make sure all operations interaction with litgpt or files uses the project_id as the base path 
                    Update the document with user comments:
                    <document>
                    To create a FastAPI application with endpoints to fine-tune models and perform chat completions, we can implement it based on the provided commands and documentation. We'll create an API with two primary endpoints: one for fine-tuning a model and another for using the model for chat completions. Here's how you can build it:

```python /app/main.py
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import subprocess
import os
import shutil
import zipfile

app = FastAPI()

# Define a Pydantic model for creating a project and its settings
class CreateProjectRequest(BaseModel):
    project: str
    model: str
    settings: dict

# Define a Pydantic model for input data for fine-tuning
class FinetuneRequest(BaseModel):
    model_name: str
    dataset_path: str
    val_split_fraction: float
    output_dir: str

# Define a Pydantic model for chat completion input
class ChatCompletionRequest(BaseModel):
    input_text: str
    model_dir: str

@app.post("/create_project")
async def create_project(request: CreateProjectRequest):
    try:
        # Create project directory
        project_dir = f"./projects/{request.project}"
        os.makedirs(project_dir, exist_ok=True)

        # Save settings to a file
        settings_path = os.path.join(project_dir, "settings.json")
        with open(settings_path, "w") as f:
            f.write(str(request.settings))

        return {"message": f"Project {request.project} created successfully."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/projects/{project_id}/data")
async def upload_dataset(project_id: str, file: UploadFile = File(...)):
    try:
        # Create data directory for the project
        data_dir = f"./projects/{project_id}/data"
        os.makedirs(data_dir, exist_ok=True)

        # Ensure the uploaded file is a zip file
        if not file.filename.endswith(".zip"):
            raise HTTPException(status_code=400, detail="Only zip files are allowed.")

        # Save the uploaded file
        zip_path = os.path.join(data_dir, file.filename)
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Extract the zip file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(data_dir)

        return {"message": f"Dataset for project {project_id} uploaded and extracted successfully."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/finetune")
async def finetune_model(request: FinetuneRequest):
    try:
        # Construct the fine-tune command
        command = [
            "litgpt", "finetune", request.model_name,
            "--data", "JSON",
            "--data.json_path", request.dataset_path,
            f"--data.val_split_fraction={request.val_split_fraction}",
            "--out_dir", request.output_dir
        ]
        
        # Execute the command
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=result.stderr)

        return {"message": "Model fine-tuning started successfully.", "output": result.stdout}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat_completion")
async def chat_completion(request: ChatCompletionRequest):
    try:
        # Construct the chat command
        command = ["litgpt", "chat", request.model_dir]
        
        # Execute the command
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate(input=request.input_text)

        if process.returncode != 0:
            raise HTTPException(status_code=500, detail=stderr)

        return {"response": stdout}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Explanation:

- **FastAPI Setup:** The application is initialized using FastAPI, with routes for creating projects, uploading datasets, fine-tuning, and chat completion.

- **Project Creation Endpoint (`/create_project`):** This endpoint accepts a request containing the project ID, model name, and settings. It creates a directory for the project and stores the settings in a file.

- **Dataset Upload Endpoint (`/projects/{project_id}/data`):** This endpoint allows uploading a zip file containing a JSON dataset. It extracts the dataset into the project-specific data directory.

- **Fine-tuning Endpoint (`/finetune`):** Uses provided parameters to start fine-tuning a model.

- **Chat Completion Endpoint (`/chat_completion`):** Generates chat responses using a trained model.

- **Directory Management:** For both projects and datasets, local directories are created using the project ID to organize data and settings.

### Instructions to Run the API:

1. Save the code to a file named `main.py`.
2. Install FastAPI and Uvicorn (if not already installed) using `pip install fastapi[all]`.
3. Start the FastAPI app by running `uvicorn app.main:app --reload`.
4. Interact with the API at `http://localhost:8000`.
                    </document>
                    User comments:
                    * Add enpoints to backup and restore tunned models
* Make sure all operations interaction with litgpt or files uses the project_id as the base path 
                    Important: Always return the markdown document without any comments before or after, to keep it clean.
## [[{"doc_id": "d677b949-fd20-4dec-9999-d9a245704542", "role": "assistant", "task_item": "analysis", "think": null, "hide": false, "is_answer": false, "improvement": false, "created_at": "2025-08-30 12:19:18.182148", "updated_at": "2025-08-30 12:19:18.182176", "images": [], "files": [], "meta_data": {"time_taken": 34.29006338119507, "first_chunk_time_taken": 0.0001983642578125, "model": "openai/gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": null, "disable_knowledge": false, "read_by": []}]]
To create a FastAPI application with endpoints to fine-tune models and perform chat completions, we can implement it based on the provided commands and documentation. We'll create an API with two primary endpoints: one for fine-tuning a model and another for using the model for chat completions. Here's how you can build it:

```python /app/main.py
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import subprocess
import os
import shutil
import zipfile

app = FastAPI()

# Define a Pydantic model for creating a project and its settings
class CreateProjectRequest(BaseModel):
    project: str
    model: str
    settings: dict

# Define a Pydantic model for input data for fine-tuning
class FinetuneRequest(BaseModel):
    project_id: str
    val_split_fraction: float

# Define a Pydantic model for chat completion input
class ChatCompletionRequest(BaseModel):
    input_text: str
    project_id: str

@app.post("/create_project")
async def create_project(request: CreateProjectRequest):
    try:
        # Create project directory
        project_dir = f"./projects/{request.project}"
        os.makedirs(project_dir, exist_ok=True)

        # Save settings to a file
        settings_path = os.path.join(project_dir, "settings.json")
        with open(settings_path, "w") as f:
            f.write(str(request.settings))

        return {"message": f"Project {request.project} created successfully."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/projects/{project_id}/data")
async def upload_dataset(project_id: str, file: UploadFile = File(...)):
    try:
        # Create data directory for the project
        data_dir = f"./projects/{project_id}/data"
        os.makedirs(data_dir, exist_ok=True)

        # Ensure the uploaded file is a zip file
        if not file.filename.endswith(".zip"):
            raise HTTPException(status_code=400, detail="Only zip files are allowed.")

        # Save the uploaded file
        zip_path = os.path.join(data_dir, file.filename)
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Extract the zip file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(data_dir)

        return {"message": f"Dataset for project {project_id} uploaded and extracted successfully."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/finetune")
async def finetune_model(request: FinetuneRequest):
    try:
        # Establish project paths
        project_dir = f"./projects/{request.project_id}"
        dataset_path = os.path.join(project_dir, "data")
        output_dir = os.path.join(project_dir, "model")

        # Construct the fine-tune command
        command = [
            "litgpt", "finetune", request.project_id,
            "--data", "JSON",
            "--data.json_path", dataset_path,
            f"--data.val_split_fraction={request.val_split_fraction}",
            "--out_dir", output_dir
        ]
        
        # Execute the command
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=result.stderr)

        return {"message": "Model fine-tuning started successfully.", "output": result.stdout}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat_completion")
async def chat_completion(request: ChatCompletionRequest):
    try:
        # Construct the chat command
        model_dir = f"./projects/{request.project_id}/model"
        command = ["litgpt", "chat", model_dir]
        
        # Execute the command
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate(input=request.input_text)

        if process.returncode != 0:
            raise HTTPException(status_code=500, detail=stderr)

        return {"response": stdout}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/backup/{project_id}")
async def backup_model(project_id: str):
    try:
        # Define paths
        project_dir = f"./projects/{project_id}"
        model_dir = os.path.join(project_dir, "model")
        backup_path = os.path.join(project_dir, f"{project_id}_backup.zip")

        # Create a zip of the model directory
        shutil.make_archive(backup_path.replace('.zip', ''), 'zip', model_dir)

        return {"message": f"Model for project {project_id} backed up successfully.", "backup_path": backup_path}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/restore/{project_id}")
async def restore_model(project_id: str, backup_file: UploadFile = File(...)):
    try:
        # Define paths
        project_dir = f"./projects/{project_id}"
        model_dir = os.path.join(project_dir, "model")

        # Ensure the uploaded file is a zip file
        if not backup_file.filename.endswith(".zip"):
            raise HTTPException(status_code=400, detail="Only zip files are allowed.")

        # Save the uploaded backup file
        backup_path = os.path.join(project_dir, backup_file.filename)
        with open(backup_path, "wb") as buffer:
            shutil.copyfileobj(backup_file.file, buffer)

        # Extract the zip file
        with zipfile.ZipFile(backup_path, 'r') as zip_ref:
            zip_ref.extractall(model_dir)

        return {"message": f"Model for project {project_id} restored successfully from backup."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Explanation:

- **FastAPI Setup:** The application is initialized using FastAPI, with routes for creating projects, uploading datasets, fine-tuning, chat completion, and new endpoints for backup and restore.

- **Project Creation Endpoint (`/create_project`):** This endpoint accepts a request containing the project ID, model name, and settings. It creates a directory for the project and stores the settings in a file.

- **Dataset Upload Endpoint (`/projects/{project_id}/data`):** This endpoint allows uploading a zip file containing a JSON dataset. It extracts the dataset into the project-specific data directory.

- **Fine-tuning Endpoint (`/finetune`):** Uses the project ID to start fine-tuning a model based on the dataset located in the project directory.

- **Chat Completion Endpoint (`/chat_completion`):** Generates chat responses using a trained model from the specific project directory.

- **Backup Endpoint (`/backup/{project_id}`):** Creates a backup of the tuned model in the form of a zip archive.

- **Restore Endpoint (`/restore/{project_id}`):** Restores a model from a supplied backup zip file. 

- **Directory Management:** For all operations, the project ID is used to determine the base path for project-specific directories.

### Instructions to Run the API:

1. Save the code to a file named `main.py`.
2. Install FastAPI and Uvicorn (if not already installed) using `pip install fastapi[all]`.
3. Start the FastAPI app by running `uvicorn app.main:app --reload`.
4. Interact with the API at `http://localhost:8000`.