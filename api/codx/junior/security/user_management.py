import logging
import jwt
import bcrypt
import os

from datetime import datetime

from fastapi import Request

from typing import Optional, List

from codx.junior.global_settings import read_global_settings, write_global_settings
from codx.junior.model.user import (
  CodxUser,
  CodxUserLogin,
  CompanyMembership,
  ProjectPermission,
  PROJECT_PERMISSION_ADMIN,
  PROJECT_PERMISSION_KNOWLEDGE_ADMIN,
  COMPANY_ROLE_ADMIN,
  COMPANY_ROLE_MANAGER,
  COMPANY_ROLE_MEMBER,
  COMPANY_ROLES,
  USER_ROLE_ADMIN,
  USER_ROLE_COMPANY_ADMIN,
  WORKSPACE_MODE_AUTO,
  WORKSPACE_MODES,
)
from codx.junior.settings import CODXJuniorSettings

logger = logging.getLogger(__name__)

# Project permissions that allow changing what the profiles learn in the
# project (rules written to the profile enrichment and knowledge files).
PROFILE_KNOWLEDGE_PERMISSIONS = {
    PROJECT_PERMISSION_ADMIN,
    PROJECT_PERMISSION_KNOWLEDGE_ADMIN,
}

# ---------------------------------------------------------------------------
# GitHub Admin Helper
# ---------------------------------------------------------------------------

def get_github_admin_accounts() -> List[str]:
    """
    Read the GITHUB_ADMINS environment variable and return a list of
    GitHub usernames that should be granted admin role.

    Format: comma-separated list (case-insensitive matching)
    Example: "user1,user2,user3"

    Returns:
        List of GitHub usernames (normalized to lowercase).
    """
    github_admins_env = os.getenv("GITHUB_ADMINS", "")
    if not github_admins_env.strip():
        return []
    
    # Split by comma, strip whitespace, and normalize to lowercase
    admins = [
        account.strip().lower()
        for account in github_admins_env.split(",")
        if account.strip()
    ]
    return admins


def is_github_admin_account(github_username: str) -> bool:
    """
    Check if a GitHub username is in the GITHUB_ADMINS list.

    Args:
        github_username: The GitHub account username to check.

    Returns:
        True if the account is in the admin list, False otherwise.
    """
    if not github_username:
        return False
    
    admin_accounts = get_github_admin_accounts()
    return github_username.lower() in admin_accounts


class UserSecurityManager():
    def __init__(self):
        self.global_settings = read_global_settings()

    def find_user(self, username: str = None) -> Optional[CodxUser]:
        return next((CodxUser(**user.__dict__) for user in self.global_settings.users
                     if user.username == username), None)

    def find_github_user(self, account) -> Optional[CodxUser]:
        return next((CodxUser(**user.__dict__) for user in self.global_settings.users
                     if user.github == account), None)

    def find_user_login(self, username: str = None) -> Optional[CodxUserLogin]:
        return next((login for login in self.global_settings.user_logins
                     if login.username == username), None)

    def list_user(self):
        """
        Return the user catalog used by pickers and the company manager.

        Only ``username`` / ``avatar`` were returned before. The company shell
        also needs the role and the company memberships to resolve a company
        roster and to render the People view, so they are included as optional
        keys (every existing consumer keeps working untouched).
        """
        return [{
            "username": user.username,
            "avatar": user.avatar,
            "email": user.email,
            "role": user.role,
            "disabled": bool(user.disabled),
            "companies": [
                membership.model_dump()
                for membership in (user.companies or [])
            ],
        } for user in self.global_settings.users]

    # ── Company membership ───────────────────────────────────────────────────

    def find_company_memberships(self, company_id: str) -> List[dict]:
        """
        Return every user that belongs to *company_id*.

        Args:
            company_id: Company id.

        Returns:
            A list of ``{username, email, avatar, role, company_role, title,
            disabled}`` entries. The company role is the membership role, not
            the global role.
        """
        company_id = str(company_id or "")
        result = []
        for user in self.global_settings.users:
            membership = next(
                (
                    item
                    for item in (user.companies or [])
                    if item.company_id == company_id
                ),
                None,
            )
            if not membership:
                continue
            result.append({
                "username": user.username,
                "email": user.email,
                "avatar": user.avatar,
                "role": user.role,
                "company_role": membership.role,
                "title": membership.title,
                "disabled": bool(user.disabled),
                "joined_at": membership.joined_at,
            })
        return sorted(result, key=lambda item: (item["company_role"], item["username"].lower()))

    def company_role(self, company_id: str, user: Optional[CodxUser]) -> str:
        """Return *user*'s role in *company_id* (``""`` when not a member)."""
        if not user:
            return ""
        if getattr(user, "role", "") == USER_ROLE_ADMIN:
            return COMPANY_ROLE_ADMIN
        membership = next(
            (
                item
                for item in (getattr(user, "companies", None) or [])
                if item.company_id == str(company_id or "")
            ),
            None,
        )
        return membership.role if membership else ""

    def can_manage_company(self, company_id: str, user: Optional[CodxUser]) -> bool:
        """``True`` when *user* can manage the work of *company_id*."""
        return self.company_role(company_id, user) in (
            COMPANY_ROLE_ADMIN,
            COMPANY_ROLE_MANAGER,
        )

    def can_admin_company(self, company_id: str, user: Optional[CodxUser]) -> bool:
        """``True`` when *user* can administer *company_id* (add users, settings)."""
        return self.company_role(company_id, user) == COMPANY_ROLE_ADMIN

    def add_company_member(
        self,
        company_id: str,
        username: str,
        role: str = COMPANY_ROLE_MEMBER,
        title: str = "",
    ) -> dict:
        """
        Add (or update) a user's membership in a company.

        Args:
            company_id: Company id.
            username: Username of an existing codx-junior user.
            role: ``admin`` | ``manager`` | ``member``.
            title: Optional title inside the company.

        Returns:
            The membership as a dictionary.

        Raises:
            ValueError: When the user does not exist or the role is invalid.
        """
        username = str(username or "").strip()
        if not username:
            raise ValueError("username is required")
        role = str(role or COMPANY_ROLE_MEMBER).strip().lower()
        if role not in COMPANY_ROLES:
            raise ValueError(
                f"invalid company role '{role}' (expected one of "
                f"{', '.join(COMPANY_ROLES)})"
            )
        stored_user = next(
            (item for item in self.global_settings.users if item.username == username),
            None,
        )
        if stored_user is None:
            raise ValueError(f"user '{username}' does not exist")
        stored_user.companies = list(stored_user.companies or [])
        membership = next(
            (
                item
                for item in stored_user.companies
                if item.company_id == str(company_id)
            ),
            None,
        )
        if membership is None:
            membership = CompanyMembership(
                company_id=str(company_id),
                role=role,
                title=title,
                joined_at=datetime.now().isoformat(),
            )
            stored_user.companies.append(membership)
        else:
            membership.role = role
            membership.title = title
        self.save_settings()
        return membership.model_dump()

    def remove_company_member(self, company_id: str, username: str) -> bool:
        """
        Remove a user from a company.

        Returns:
            ``True`` when a membership was removed, ``False`` when there was
            nothing to remove.
        """
        stored_user = next(
            (
                item
                for item in self.global_settings.users
                if item.username == str(username or "")
            ),
            None,
        )
        if stored_user is None:
            return False
        before = len(stored_user.companies or [])
        stored_user.companies = [
            item
            for item in (stored_user.companies or [])
            if item.company_id != str(company_id or "")
        ]
        removed = len(stored_user.companies) != before
        if removed:
            self.save_settings()
        return removed

    def create_company_user(
        self,
        company_id: str,
        username: str,
        password: str = "",
        email: str = "",
        role: str = COMPANY_ROLE_MEMBER,
        title: str = "",
        user_role: str = "user",
    ) -> dict:
        """
        Create a codx-junior account **and** enroll it in a company.

        This is the operation behind "company admins can add users": a company
        admin does not need global settings access to onboard a teammate. When
        the account already exists the membership is simply added.

        Args:
            company_id: Company id.
            username: Login name.
            password: Initial password (required for a new account).
            email: Optional email.
            role: Company role.
            title: Optional company title.
            user_role: Global role for a new account (``user`` by default).

        Returns:
            ``{"username", "created", "membership"}``.

        Raises:
            ValueError: On invalid input.
        """
        username = str(username or "").strip()
        if not username:
            raise ValueError("username is required")
        existing = self.find_user(username=username)
        if existing is not None:
            membership = self.add_company_member(
                company_id=company_id,
                username=username,
                role=role,
                title=title,
            )
            return {
                "username": username,
                "created": False,
                "membership": membership,
            }

        password = str(password or "")
        if len(password) < 4:
            raise ValueError("a password of at least 4 characters is required")

        new_user = CodxUser(
            username=username,
            email=str(email or ""),
            avatar=f"https://gravatar.com/avatar/baa8db8ab2afb7ababc235269e762662?s=200&d=robohash&r={username}",
            role=user_role if user_role in ("user", "manager", USER_ROLE_COMPANY_ADMIN) else "user",
        )
        self.global_settings.users.append(new_user)
        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        self.global_settings.user_logins.append(
            CodxUserLogin(
                username=username,
                email=str(email or ""),
                password=hashed_password,
            )
        )
        self.save_settings()
        membership = self.add_company_member(
            company_id=company_id,
            username=username,
            role=role,
            title=title,
        )
        return {
            "username": username,
            "created": True,
            "membership": membership,
        }

    def set_workspace_mode(self, user: CodxUser, mode: str) -> CodxUser:
        """
        Persist the preferred product shell of *user*.

        Args:
            user: Authenticated user.
            mode: ``auto`` | ``company`` | ``work``.

        Returns:
            The updated stored user.

        Raises:
            ValueError: On an invalid mode.
        """
        mode = str(mode or "").strip().lower()
        if mode not in WORKSPACE_MODES:
            raise ValueError(
                f"invalid workspace_mode '{mode}' (expected one of "
                f"{', '.join(WORKSPACE_MODES)})"
            )
        stored = self.find_user(username=getattr(user, "username", ""))
        if stored is None:
            raise ValueError("user does not exist")
        stored.workspace_mode = mode
        self.save_settings()
        return stored

    def get_user_token(self, user: CodxUser):
        return jwt.encode({ "username": user.username }, self.global_settings.secret, algorithm="HS256")
    
    def get_user_from_token(self, token):
        if not token:
            return None
        try:
            decoded = jwt.decode(token, self.global_settings.secret, algorithms=["HS256"])
            return CodxUserLogin(**decoded)
        except:
            return None

    def login_user(self, user: CodxUserLogin = None, token: str = None, oauth_password: str = None) -> CodxUser:
        def do_login(user: CodxUserLogin, token: str):
            if token:
                user = self.get_user_from_token(token)
                if not user:
                    logging.error(f"Invalid token login {token}")
                    return None
            try:
                stored_user = self.find_user(username=user.username)
                stored_login = self.find_user_login(username=user.username)

                if stored_user:
                    if stored_user.disabled:
                        logger.error(f"Disabled user login attempt: {stored_user}")
                        return None
                    
                    # Check if user is GitHub-only and attempting password login
                    if stored_user.github_only and not oauth_password:
                        logger.error(
                            f"GitHub-only user '{stored_user.username}' attempted password login. "
                            "Use GitHub OAuth instead."
                        )
                        return None
                    
                    if stored_login:
                        if token == stored_login.token:
                            return stored_user
                        if not user.password and oauth_password:
                            return stored_user
                        # Verify existing password (skip for GitHub-only users with oauth)
                        if oauth_password:
                            # OAuth login, no password verification needed
                            return stored_user
                        if bcrypt.checkpw(user.password.encode('utf-8'), stored_login.password.encode('utf-8')):
                            return stored_user
                        else:
                            logger.error("Invalid password")
                    elif user.username and (user.password or oauth_password):
                        password = user.password or oauth_password
                        # Create a new user login with the hashed password
                        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                        new_login = CodxUserLogin(username=user.username, email=user.email, password=hashed_password.decode('utf-8'))
                        self.global_settings.user_logins.append(new_login)
                        logger.info("Create a new user login with the hashed password and save settings")
                        self.save_settings()
                        
                        return stored_user
                else:
                    logger.error(f"Invalid login, stored_user not found for {user}, token: {token}")    
            except Exception as ex:
                logging.error(f"Invalid user login {ex} {user}")
            
            return None
            
        try:
            logged_user = do_login(user=user, token=token)
            logger.info(f"do_login user: {user} token: {token} logged_user: {logged_user}")
            if logged_user:
                user_login = self.find_user_login(username=logged_user.username)
                
                if not self.get_user_from_token(user_login.token):
                    user_login.token = self.get_user_token(user=logged_user)
                    logger.info("User logged and save settings")
                    self.save_settings()
                
                logged_user.token = user_login.token
            return logged_user
        except Exception as ex:
            logger.error(f"Invalid login {ex} {user} token: {token}")
            return None

    def update_user(self, user: CodxUser, password: str = None):
        existing_user = self.find_user(username=user.username)
        if existing_user:
            existing_user.email = user.email
            existing_user.avatar = user.avatar
            existing_user.theme = user.theme
            # The user may choose the product shell (company vs working mode).
            # Role and company memberships are NOT editable from the account
            # screen: they are granted by a company/global admin.
            existing_user.workspace_mode = getattr(
                user, "workspace_mode", existing_user.workspace_mode
            ) or WORKSPACE_MODE_AUTO

            if password:
                # Prevent password update for GitHub-only users
                if existing_user.github_only:
                    logger.error(
                        f"Cannot set password for GitHub-only user '{existing_user.username}'. "
                        "Use GitHub OAuth for authentication."
                    )
                    raise Exception("Password cannot be set for GitHub-only users")
                
                # Update password in the user logins
                stored_login = self.find_user_login(username=user.username)
                if stored_login:
                    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                    stored_login.password = hashed_password.decode('utf-8')
            logger.info("Update user and save settings")
            self.save_settings()

        return existing_user

    def get_user_project_access(self, user: CodxUser, settings: CODXJuniorSettings):
        if user:
            if user.role == 'admin':
                return 'admin'
            for p in user.projects:
                if p.project_id == settings.project_id:
                    return p.permissions
        return ''

    def can_manage_profile_knowledge(self, user: CodxUser, settings: CODXJuniorSettings) -> bool:
        """
        Return True when *user* may change what the profiles learn in *settings*'
        project.

        Allowed, in order:
          1. codx-junior admins (``user.role == "admin"``),
          2. project admins (``permissions == "admin"``),
          3. project knowledge admins (``permissions == "knowledge_admin"``).

        The knowledge admin role exists so a project can delegate the custody of
        what the profiles learn (rules and knowledge files) without handing over
        full project administration.

        Args:
            user: User performing the operation (may be None).
            settings: Project the operation applies to.

        Returns:
            True when the user may write profile learning resources.

        Example:
            >>> UserSecurityManager().can_manage_profile_knowledge(user, settings)
            True
        """
        if not user or not getattr(user, "username", ""):
            return False
        if getattr(user, "role", "") == 'admin':
            return True
        return self.get_user_project_access(user=user, settings=settings) \
            in PROFILE_KNOWLEDGE_PERMISSIONS

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
            logger.info("Add user to project and save settings")
            self.save_settings()

    def get_users_with_project_access(self, project_id: str):
        users_with_access = []
        for user in self.global_settings.users:
            add = user.role == 'admin'
            if not add:
                for project in user.projects:
                    if project.project_id == project_id:
                        add = True
                        break
            if add:
                users_with_access.append({
                    "username": user.username,
                    "avatar": user.avatar
                })
                        
        return users_with_access

    def save_settings(self):
        write_global_settings(self.global_settings)

def get_authenticated_user(request: Request) -> CodxUser:
    user_security_manager = UserSecurityManager()
    token = request.headers.get("authentication", " ").split(" ")[-1]
    user = None
    if token:
        user = user_security_manager.login_user(token=token)
    user_name = user.username if user else ""
    logger.info(f"Authenticating request: {request.url} token {token}: {user_name} - headers: {request.headers}")
    return user


def get_authenticated_user_from_token(token: str) -> CodxUser:
    user_security_manager = UserSecurityManager()
    user = None
    if token:
        user = user_security_manager.login_user(token=token)
    user_name = user.username if user else ""
    logger.info(f"WebSocket token {token}: {user_name}")
    return user