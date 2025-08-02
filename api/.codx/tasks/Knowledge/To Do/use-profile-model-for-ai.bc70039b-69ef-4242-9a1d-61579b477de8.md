# [[{"id": "bc70039b-69ef-4242-9a1d-61579b477de8", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": ["/shared/codx-junior/api/codx/junior/security/user_management.py"], "check_lists": [], "profiles": ["software_developer"], "users": ["admin"], "name": "Use profile model for AI", "description": "In this conversation, the focus was on enhancing and refactoring a Python module for user management within the \"codx-junior\" API, particularly the `user_management.py` file. The improvements included creating a new method to list users based on project settings, adding detailed logging, and enforcing coding best practices such as specifying types, avoiding exception handling with general exceptions, and ensuring proper code documentation with comments and docstrings. The conversation also emphasized maintaining consistent code style, removing unused variables, and optimizing the code for better readability and performance.", "created_at": "2025-07-31 05:07:52.432951", "updated_at": "2025-08-01T14:52:53.921504", "mode": "chat", "kanban_id": "", "column_id": "", "board": "Knowledge", "column": "To Do", "chat_index": 0, "url": "", "branch": "", "file_path": "/shared/codx-junior/api/.codx/tasks/Knowledge/To Do/use-profile-model-for-ai.bc70039b-69ef-4242-9a1d-61579b477de8.md", "model": "", "visibility": "", "remote_url": "", "knowledge_topics": []}]]
## [[{"doc_id": "c21e6ff4-93dd-4a25-8b6a-2b050910bc3f", "role": "user", "task_item": "", "think": "", "hide": false, "improvement": false, "created_at": "2025-08-01 14:22:30.355190", "updated_at": "2025-08-01T14:52:05.954Z", "images": [], "files": [], "meta_data": {}, "profiles": ["software_developer"], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true}]]
Create a method to return a list of user for a settings: CODXJuniorSettings
## [[{"doc_id": "7f4d895c-767d-4071-9903-59be4b9d980f", "role": "assistant", "task_item": "", "think": null, "hide": false, "improvement": false, "created_at": "2025-08-01 14:48:57.698432", "updated_at": "2025-08-01 14:48:57.698488", "images": [], "files": [], "meta_data": {"time_taken": 35.14331269264221, "first_chunk_time_taken": 0.0003139972686767578, "model": "gpt-4o"}, "profiles": ["software_developer", "software_developer"], "user": null, "knowledge_topics": [], "done": true, "is_thinking": null, "disable_knowledge": false}]]
```python /shared/codx-junior/api/codx/junior/security/user_management.py
import logging
from typing import List, Optional

import jwt
import bcrypt
from fastapi import Request
from jwt.exceptions import DecodeError, ExpiredSignatureError, InvalidTokenError

from codx.junior.settings import read_global_settings, write_global_settings
from codx.junior.model.model import CodxUser, CodxUserLogin, ProjectPermission
from codx.junior.settings import CODXJuniorSettings

# Create a logger for this module
logger = logging.getLogger(__name__)

# Define constants for JWT algorithm and logging messages
JWT_ALGORITHM = "HS256"
ERROR_INVALID_TOKEN = "Invalid token login %s %s"
ERROR_INVALID_PASSWORD = "Invalid password"
ERROR_DISABLED_USER_LOGIN = "Disabled user login attempt: %s"
ERROR_INVALID_USER_LOGIN = "Invalid user login %s %s"
ERROR_INVALID_LOGIN_USER_NOT_FOUND = "Invalid login, stored_user not found for %s, token: %s"
INFO_USER_LOGGED = "User logged %s"
INFO_AUTHENTICATING_REQUEST = "Authenticating request: %s token %s: %s - headers: %s"

class UserSecurityManager:
    def __init__(self) -> None:
        self.global_settings = read_global_settings()

    def find_user(self, username: str) -> Optional[CodxUser]:
        """Find a user by username."""
        return next(
            (user for user in self.global_settings.users if user.username == username), None
        )

    def find_user_login(self, username: str) -> Optional[CodxUserLogin]:
        """Find a user login by username."""
        return next(
            (login for login in self.global_settings.user_logins if login.username == username), None
        )

    def list_user(self) -> List[dict]:
        """List all users with their usernames and avatars."""
        return [{"username": user.username, "avatar": user.avatar} for user in self.global_settings.users]

    def list_users_for_settings(self, settings: CODXJuniorSettings) -> List[str]:
        """
        List the usernames of users that have access to a specified project based on settings.
        """
        return [
            user.username for user in self.global_settings.users 
            if any(
                project.project_id == settings.project_id for project in user.projects
            )
        ]

    def get_user_token(self, user: CodxUser) -> str:
        """Generate JWT for a user."""
        return jwt.encode({"username": user.username}, self.global_settings.secret, algorithm=JWT_ALGORITHM)

    def login_user(self, user: Optional[CodxUserLogin] = None, token: Optional[str] = None) -> Optional[CodxUser]:
        """Authenticate user using username/password or token."""
        
        def do_login(user_login: CodxUserLogin, token_str: Optional[str]) -> Optional[CodxUser]:
            if token_str:
                try:
                    decoded = jwt.decode(token_str, self.global_settings.secret, algorithms=[JWT_ALGORITHM])
                    user_login = CodxUserLogin(**decoded)
                except (DecodeError, ExpiredSignatureError, InvalidTokenError) as ex:
                    if not user_login:
                        logger.error(ERROR_INVALID_TOKEN, ex, token_str)
                        return None

            try:
                stored_user = self.find_user(username=user_login.username)
                stored_login = self.find_user_login(username=user_login.username)

                if stored_user:
                    if stored_user.disabled:
                        logger.error(ERROR_DISABLED_USER_LOGIN, stored_user)
                        return None
                    if stored_login:
                        if token_str == stored_login.token:
                            return stored_user
                        # Verify existing password
                        if bcrypt.checkpw(user_login.password.encode('utf-8'), stored_login.password.encode('utf-8')):
                            return stored_user
                        else:
                            logger.error(ERROR_INVALID_PASSWORD)
                    elif user_login.username and user_login.password:
                        # Create a new user login with the hashed password
                        hashed_password = bcrypt.hashpw(user_login.password.encode('utf-8'), bcrypt.gensalt())
                        new_login = CodxUserLogin(username=user_login.username, email=user_login.email, 
                                                  password=hashed_password.decode('utf-8'))
                        self.global_settings.user_logins.append(new_login)
                        self.save_settings()
                        return stored_user
                else:
                    logger.error(ERROR_INVALID_LOGIN_USER_NOT_FOUND, user_login, token_str)
            except (KeyError, TypeError) as ex:
                logger.error(ERROR_INVALID_USER_LOGIN, ex, user_login)
            return None
        
        try:
            logged_user = do_login(user_login=user, token_str=token)
            logger.info(INFO_USER_LOGGED, user)
            if logged_user:
                user_login = self.find_user_login(username=logged_user.username)
                if user_login:
                    user_login.token = self.get_user_token(user=logged_user)
                    self.save_settings()
                    logged_user.token = user_login.token
            return logged_user
        except (KeyError, TypeError) as ex:
            logger.error(ERROR_INVALID_USER_LOGIN, ex, user, token)
            return None

    def update_user(self, user: CodxUser, password: Optional[str] = None) -> Optional[CodxUser]:
        """Update user details and password if provided."""
        
        existing_user = self.find_user(username=user.username)
        if existing_user:
            existing_user.email = user.email
            existing_user.avatar = user.avatar
            existing_user.theme = user.theme

            if password:
                # Update password in the user logins
                stored_login = self.find_user_login(username=user.username)
                if stored_login:
                    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                    stored_login.password = hashed_password.decode('utf-8')
            self.save_settings()
        return existing_user

    def get_user_project_access(self, user: CodxUser, settings: CODXJuniorSettings) -> List[str]:
        """Get user's project access permissions."""
        if user:
            if user.role == 'admin':
                return ['admin']
            for project in user.projects:
                if project.project_id == settings.project_id:
                    return project.permissions
        return []

    def add_user_to_project(self, user: CodxUser, project_id: str, permissions: str) -> None:
        """Add user to a project with specified permissions."""
        
        global_user = next((u for u in self.global_settings.users if u.username == user.username), None)
        if global_user:
            project = next((p for p in global_user.projects if p.project_id == project_id), None)
            save_settings_flag = False
            if project:
                if project.permissions != permissions:
                    project.permissions = permissions
                    save_settings_flag = True
            else:
                global_user.projects.append(ProjectPermission(project_id=project_id, permissions=permissions))
                save_settings_flag = True
            if save_settings_flag:
                self.save_settings()

    def save_settings(self) -> None:
        """Save the settings to the global configuration."""
        write_global_settings(self.global_settings)

async def get_authenticated_user(request: Request) -> Optional[CodxUser]:
    """Authenticate user from the request header."""
    
    user_security_manager = UserSecurityManager()
    token = request.headers.get("authentication", " ").split(" ")[-1]
    user = None
    if token:
        user = user_security_manager.login_user(token=token)
    logger.info(INFO_AUTHENTICATING_REQUEST, request.url, token, user, request.headers)
    return user
```