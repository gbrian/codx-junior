from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from browser_use import Agent
import asyncio

app = FastAPI()

# Define the expected payload schema
class BrowsePayload(BaseModel):
    ai_settings: dict
    chat: str

@app.post("/browse")
async def browse(payload: BrowsePayload):
    # Extract AI settings and chat message from the payload
    ai_settings = payload.ai_settings
    chat = payload.chat

    try:
        # Create the agent with the provided settings
        agent = Agent(
            task=chat,
            llm=ChatOpenAI(**ai_settings)
        )
        
        # Run the agent and get the result
        result = await agent.run()

        return {"message": "Success", "result": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Ensure the browser is always running
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_browser())

async def run_browser():
    while True:
        # Here, implement the logic to keep the browser running
        await asyncio.sleep(10)  # Adjust the sleep time as necessary

# To run the FastAPI server, use:
# uvicorn main:app --reload

@codx: to keep browse running all the time we need a browser_context. Check browser docs --knowledge
