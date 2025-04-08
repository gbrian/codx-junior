import logging
import datetime
from fastapi import APIRouter, Request

from codx.junior.engine import (
  CODXJuniorSession,
)

from codx.junior.security.user_management import UserSecurityManager 
from codx.junior.model.model import CodxUserLogin


logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/users/login")
async def create_completion(request: Request):  
    body = await request.json()
    user = UserSecurityManager().login_user(CodxUserLogin(**body))
    return user