import logging
import jwt
import bcrypt

from fastapi import Request

from codx.junior.settings import read_global_settings, write_global_settings
from codx.junior.model.model import CodxUser, CodxUserLogin
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

    def login_user(self, user: CodxUserLogin = None, token: str = None) -> CodxUser:
        try:
            if token:
                try:
                    decoded = jwt.decode(token, self.global_settings.secret, algorithms=["HS256"])
                    user = CodxUserLogin(**decoded)
                except Exception as ex:
                    logging.error(f"Invalid token {ex}")
                    if not user:
                        raise ex

            stored_user = self.find_user(username=user.username)
            stored_login = self.find_user_login(username=user.username)

            if stored_user:
                if token:
                    return stored_user
                if stored_login:
                        
                    # Verify existing password
                    if bcrypt.checkpw(user.password.encode('utf-8'), stored_login.password.encode('utf-8')):
                        stored_user.token = jwt.encode({ "username": stored_user.username }, self.global_settings.secret, algorithm="HS256")
                        return stored_user
                    else:
                        logger.error("Invalid password")
                elif user.username and user.password:
                    # Create a new user login with the hashed password
                    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
                    new_login = CodxUserLogin(username=user.username, email=user.email, password=hashed_password.decode('utf-8'))
                    self.global_settings.user_logins.append(new_login)
                    write_global_settings(self.global_settings)
                    
                    stored_user.token = jwt.encode({ "username": stored_user.username }, self.global_settings.secret, algorithm="HS256")
                    return stored_user
            else:
                logger.error(f"Invalid login, stored_user not found for {user}, token: {token}")    
            return None
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
    if token:
        user = user_security_manager.login_user(token=token)
    logger.info(f"Authenticating request: {request.url} token {token}: {user} - headers: {request.headers}")
    return user
