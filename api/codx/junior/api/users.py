import logging
import datetime
from fastapi import APIRouter, Request

from codx.junior.engine import (
  CODXJuniorSession,
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/users/login")
async def create_completion(request: Request):  
    body = await request.json()
    return { **body, "avatar": "https://avatar.iran.liara.run/public/21", "token": "" }