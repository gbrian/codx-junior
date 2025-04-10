import logging
import datetime
import jwt


from fastapi import Request, HTTPException, Depends

from codx.junior.settings import read_global_settings, write_global_settings
from codx.junior.model.model import CodxUser, CodxUserLogin
from codx.junior.settings import CODXJuniorSettings

logger = logging.getLogger(__name__)


class UserSecurityManager():
    def __init__(self):
        self.global_settings = read_global_settings()
    
    def find_user(self, username: str = None,  email: str = None) -> CodxUser:
        return next((user for user in self.global_settings.users
            if user.username == username or user.email == email), None)

    def login_user(self, user: CodxUserLogin = None, token: str = None) -> CodxUser:
        try:
            if token:
                decoded = jwt.decode(token, self.global_settings.secret, algorithms=["HS256"])
                user = CodxUserLogin(**decoded)
            user = self.find_user(username=user.username, email=user.email)
            if user:
                user.token = jwt.encode({"email": user.email}, self.global_settings.secret, algorithm="HS256")
            return user
        except Exception as ex:
            logger.error(f"Invalid login {ex} {user} token: {token}")
            return None

    def update_user(self, user: CodxUser):
        existing_user = self.find_user(username=user.username)
        if existing_user:
            existing_user.email = user.email
            existing_user.avatar = user.avatar
            existing_user.theme = user.theme
        write_global_settings(self.global_settings)
        return existing_user

    def get_user_project_access(self, user: CodxUser, settings: CODXJuniorSettings):
        if user.role == 'admin':
            return ['admin']
        for p in user.projects:
            if p.project_id == settings.project_id:
                return p.permissions
        return []
        


async def get_authenticated_user(request: Request) -> CodxUser:
    user_security_manager = UserSecurityManager()
    token = request.headers.get("authentication", " ").split(" ")[-1]
    user = None
    logger.info(f"Authenticating request: {request.url} token {token}")
    if token:
        # Attempt to login user with token
        user = user_security_manager.login_user(token=token)
    return user

