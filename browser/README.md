# Browser Project

## Requirements

1. **API for Browser-Use Agent:**
   - The system allows running a browser-use agent through an API.
   - Implements the `browse` function using the `Agent` class.

2. **Chat Endpoint:**
   - Exposes a "chat" endpoint for interacting with the agent.
   - Utilizes the `chat` attribute in `BrowsePayload` for communication.

3. **Constantly Running Browser:**
   - Ensures the browser is always running for continuous interaction.
   - Uses asynchronous operations and a startup event in the FastAPI application.

## Project Structure

- **Root Path:** `/projects/codx-junior/browser`
- **Folder Structure:**
  - `docs/`
  - `tests/`

## Setup and Installation

1. Clone the repository.
2. Navigate to the project directory.
3. Create a virtual environment:
   ```bash
   python -m venv venv
   ```
4. Activate the virtual environment:

   - On Windows:
     ```bash
     venv\Scripts\activate
     ```

   - On macOS and Linux:
     ```bash
     source venv/bin/activate
     ```

5. Install dependencies using:
   ```bash
   pip install .
   ```
   (This utilizes the `pyproject.toml` file.)

6. Run the server with:
   ```bash
   uvicorn main:app --reload
   ```

Please refer to the `docs/` directory for detailed documentation.