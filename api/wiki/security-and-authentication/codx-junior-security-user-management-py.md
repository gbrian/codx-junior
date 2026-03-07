The `UserSecurityManager` class is responsible for handling user authentication, authorization, and management within the CODX Junior project.

### User Management

The `UserSecurityManager` provides functionalities to:

*   **Find a user by username:** The `find_user` method searches for a user based on their username.
    ```python /codx/junior/security/user_management.py
    def find_user(self, username: str = None) -> Optional[CodxUser]:
        return next((user for user in self.global_settings.users
                     if user.username == username), None)
    ```
*   **Find a user by GitHub account:** The `find_github_user` method allows searching for users who have linked their GitHub accounts.
    ```python /codx/junior/security/user_management.py
    def find_github_user(self, account) -> Optional[CodxUser]:
        return next((user for user in self.global_settings.users
                     if user.github == account), None)
    ```
*   **Find user login information:** The `find_user_login` method retrieves login details for a given username.
    ```python /codx/junior/security/user_management.py
    def find_user_login(self, username: str = None) -> Optional[CodxUserLogin]:
        return next((login for login in self.global_settings.user_logins
                     if login.username == username), None)
    ```
*   **List users:** The `list_user` method returns a list of all users with their usernames and avatars.
    ```python /codx/junior/security/user_management.py
    def list_user(self):
        return [{
            "username": user.username,
            "avatar": user.avatar
        } for user in self.global_settings.users]
    ```
*   **Update user information:** The `update_user` method allows updating a user's email, avatar, theme, and password.
    ```python /codx/junior/security/user_management.py
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
            logger.info("Update user and save settings")
            self.save_settings()

        return existing_user
    ```

### Authentication

*   **Get user token:** The `get_user_token` method generates a JWT token for a given user.
    ```python /codx/junior/security/user_management.py
    def get_user_token(self, user: CodxUser):
        return jwt.encode({ "username": user.username }, self.global_settings.secret, algorithm="HS256")
    ```
*   **Get user from token:** The `get_user_from_token` method decodes a JWT token to retrieve user information.
    ```python /codx/junior/security/user_management.py
    def get_user_from_token(self, token):
        if not token:
            return None
        try:
            decoded = jwt.decode(token, self.global_settings.secret, algorithms=["HS256"])
            return CodxUserLogin(**decoded)
        except:
            return None
    ```
*   **Login user:** The `login_user` method handles user login using either credentials or a token. It also supports GitHub OAuth authentication.
    ```python /codx/junior/security/user_management.py
    def login_user(self, user: CodxUserLogin = None, token: str = None, oauth_password: str = None) -> CodxUser:
        # ... implementation details ...
        return None
    ```

### Project Access Control

*   **Get user project access:** The `get_user_project_access` method determines the permissions a user has for a specific project. Administrators have 'admin' access by default.
    ```python /codx/junior/security/user_management.py
    def get_user_project_access(self, user: CodxUser, settings: CODXJuniorSettings):
        if user:
            if user.role == 'admin':
                return 'admin'
            for p in user.projects:
                if p.project_id == settings.project_id:
                    return p.permissions
        return ''
    ```
*   **Add user to project:** The `add_user_to_project` method assigns permissions to a user for a given project.
    ```python /codx/junior/security/user_management.py
    def add_user_to_project(self, user: CodxUser, project_id: str, permissions: str):
        # ... implementation details ...
        self.save_settings()
    ```
*   **Get users with project access:** The `get_users_with_project_access` method lists users who have access to a specific project.
    ```python /codx/junior/security/user_management.py
    def get_users_with_project_access(self, project_id: str):
        # ... implementation details ...
        return users_with_access
    ```

### Helper Functions

*   **`save_settings`:** This method persists the global settings, including user and login information.
    ```python /codx/junior/security/user_management.py
    def save_settings(self):
        write_global_settings(self.global_settings)
    ```
*   **`get_authenticated_user`:** This function is used in FastAPI requests to authenticate a user based on the "authentication" header.
    ```python /codx/junior/security/user_management.py
    def get_authenticated_user(request: Request) -> CodxUser:
        user_security_manager = UserSecurityManager()
        token = request.headers.get("authentication", " ").split(" ")[-1]
        user = None
        if token:
            user = user_security_manager.login_user(token=token)
        user_name = user.username if user else ""
        logger.info(f"Authenticating request: {request.url} token {token}: {user_name} - headers: {request.headers}")
        return user
    ```
*   **`get_authenticated_user_from_token`:** This function is similar to `get_authenticated_user` but is designed for WebSocket connections or other scenarios where a token is provided directly.
    ```python /codx/junior/security/user_management.py
    def get_authenticated_user_from_token(token: str) -> CodxUser:
        user_security_manager = UserSecurityManager()
        user = None
        if token:
            user = user_security_manager.login_user(token=token)
        user_name = user.username if user else ""
        logger.info(f"Authenticating request: WS token {token}: {user_name}")
        return user
    ```