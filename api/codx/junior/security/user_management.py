import logging
import jwt
import bcrypt

from fastapi import Request

from codx.junior.settings import read_global_settings, write_global_settings
from codx.junior.model.model import (
  CodxUser,
  CodxUserLogin,
  ProjectPermission
)
from codx.junior.settings import CODXJuniorSettings

logger = logging.getLogger(__name__)

class UserSecurityManager():
    def __init__(self):
        self.global_settings = read_global_settings()

    def find_user(self, username: str = None) -> CodxUser:
        return next((user for user in self.global_settings.users
                     if user.username == username), None)
    
    def find_user_login(self, username: str = None) -> CodxUserLogin:
        return next((login for login in self.global_settings.user_logins
                     if login.username == username), None)

    def list_user(self):
        return [{
            "username": user.username,
            "avatar": user.avatar
        } for user in self.global_settings.users]

    def get_user_token(self, user: CodxUser):
        return jwt.encode({ "username": user.username }, self.global_settings.secret, algorithm="HS256")
    
    def login_user(self, user: CodxUserLogin = None, token: str = None) -> CodxUser:
        def do_login(user: CodxUserLogin, token: str):
            if token:
                try:
                    decoded = jwt.decode(token, self.global_settings.secret, algorithms=["HS256"])
                    user = CodxUserLogin(**decoded)
                except Exception as ex:
                    logging.error(f"Invalid token {ex}")
                    if not user:
                        return None

            stored_user = self.find_user(username=user.username)
            stored_login = self.find_user_login(username=user.username)

            if stored_user:
                if not stored_user.enabled:
                    logger.error(f"Disabled user login attempt: {stored_user}")
                    return None
                if token == stored_login.token:
                    return stored_user
                if stored_login:    
                    # Verify existing password
                    if bcrypt.checkpw(user.password.encode('utf-8'), stored_login.password.encode('utf-8')):
                        return stored_user
                    else:
                        logger.error("Invalid password")
                elif user.username and user.password:
                    # Create a new user login with the hashed password
                    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
                    new_login = CodxUserLogin(username=user.username, email=user.email, password=hashed_password.decode('utf-8'))
                    self.global_settings.user_logins.append(new_login)
                    self.save_settings()
                    
                    return stored_user
            else:
                logger.error(f"Invalid login, stored_user not found for {user}, token: {token}")    
            return None
        try:
            logged_user = do_login(user=user, token=token)
            if logged_user:
                user_login = self.find_user_login(username=logged_user.username)
                user_login.token = self.get_user_token(user=logged_user)
                self.save_settings()
                logged_user.token = user_login.token
            return logged_user
        except Exception as ex:
            logger.exception(f"Invalid login {ex} {user} token: {token}")
            return None

    def update_user(self, user: CodxUser, password: str = None):
        existing_user = self.find_user(username=user.username)
        if existing_user:
            existing_user.email = user.email
            existing_user.avatar = user.avatar
            existing_user.theme = user.theme

            if password:
                # Update password in the user logins
                stored_login = self.find_user_login(username=user.username, email=user.email)
                if stored_login:
                    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                    stored_login.password = hashed_password.decode('utf-8')
            self.save_settings()

        return existing_user

    def get_user_project_access(self, user: CodxUser, settings: CODXJuniorSettings):
        if user.role == 'admin':
            return ['admin']
        for p in user.projects:
            if p.project_id == settings.project_id:
                return p.permissions
        return []

    def add_user_to_project(self, user: CodxUser, project_id: str, permissions: str):
        global_user = next((u for u in self.global_settings.users if u.username == user.username))
        project = next((p for p in global_user.projects if p.project_id == project_id), None)
        save_settings = False
        if project:
            if project.permissions != permissions:
                project.permissions = permissions
                save_settings = True
        else:
            global_user.projects.append(ProjectPermission(
              project_id=project_id,
              permissions=permissions
            ))
            save_settings = True
        if save_settings:
            self.save_settings()

    def save_settings(self):
        write_global_settings(self.global_settings)

async def get_authenticated_user(request: Request) -> CodxUser:
    user_security_manager = UserSecurityManager()
    token = request.headers.get("authentication", " ").split(" ")[-1]
    user = None
    if token:
        user = user_security_manager.login_user(token=token)
    logger.info(f"Authenticating request: {request.url} token {token}: {user} - headers: {request.headers}")
    return user
