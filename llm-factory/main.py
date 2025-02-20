from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

######
## Models
#####

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)