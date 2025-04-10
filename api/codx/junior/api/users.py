import logging
import datetime
from fastapi import APIRouter, Request, Depends

from codx.junior.engine import (
  CODXJuniorSession,
)

from codx.junior.security.user_management import UserSecurityManager, get_authenticated_user
from codx.junior.model.model import CodxUser, CodxUserLogin


logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/users/login")
async def user_login(request: Request, user: CodxUser = Depends(get_authenticated_user)):
    if user:
        return user
    body = await request.json()
    return UserSecurityManager().login_user(CodxUserLogin(**body))

@router.put("/users")
async def user_update(request: Request, user: CodxUser = Depends(get_authenticated_user)):  
    body = await request.json()
    user_security_manager = UserSecurityManager() 
    user_changes = CodxUser(**body)
    if user.username != user_changes.username:
      logger.error(f"User {user} not match {user_changes}")
      raise Exception("Invalid data")
    return user_security_manager.update_user(user_changes)
