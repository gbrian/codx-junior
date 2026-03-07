## Security and Authentication

This document outlines the API endpoints related to security and authentication within the codx-api project. It covers user management, GitHub OAuth integration, and general authentication mechanisms.

### User Management and Authentication Endpoints

#### `/users/oauth-login-url/{oauth_provider}`

This GET endpoint generates and returns the OAuth login URL for a specified provider.

**Parameters:**

*   `oauth_provider` (str): The name of the OAuth provider (e.g., "github").
*   `redirect_uri` (query parameter): The URI to redirect to after authentication.

**Functionality:**

1.  Retrieves provider-specific information using `get_oauth_provider`.
2.  If the provider is "github", it initializes `GitHubOAuth` and generates the authorization URL.
3.  Returns an error if the provider is not supported.

**Example Response (for GitHub):**

```json
{
  "auth_url": "https://github.com/login/oauth/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URI&scope=read:user&state=SOME_STATE_STRING"
}
```

#### `/users/oauth-login`

This POST endpoint handles the OAuth login process, exchanging the provided code for a user token.

**Request Body:**

*   `oauth_provider` (str): The name of the OAuth provider.
*   `code` (str): The authorization code received from the OAuth provider.
*   `state` (str): The state parameter used to maintain state between the request and callback.
*   `redirect_uri` (str): The redirect URI used during the authorization process.

**Functionality:**

1.  Retrieves provider-specific information.
2.  For "github":
    *   Retrieves the `GitHubOAuth` instance associated with the `state`.
    *   Exchanges the `code` for an access token using `github_oauth.get_access_token()`.
    *   Fetches user information using `github_oauth.get_user_info()`.
    *   Finds or creates a `CodxUser` record using `UserSecurityManager.find_github_user()`.
    *   Logs in the user using `UserSecurityManager.login_user()`.
3.  Returns an error if the OAuth login fails or the provider is not supported.

#### `/users/login`

This POST endpoint handles user login. It can initiate an OAuth flow or process direct username/password login.

**Request Body:**

*   `oauth_provider` (str, optional): If provided, initiates the OAuth login flow by returning the OAuth URL.
*   `username` (str): The user's username (required for direct login).
*   `password` (str): The user's password (required for direct login).

**Functionality:**

1.  If `oauth_provider` is present in the body, it calls `/users/oauth-login-url` to get the OAuth login URL and returns it.
2.  For direct login:
    *   Creates a `CodxUserLogin` object from the request body.
    *   Authenticates the user using `get_authenticated_user`.
    *   If authentication is successful, sets a "codx-session" cookie with the user's token.
    *   If authentication fails, clears the "codx-session" cookie and attempts to log in using `UserSecurityManager.login_user()`.

#### `/users` (PUT)

This PUT endpoint updates user information.

**Authentication:** Requires authentication using `get_authenticated_user`.

**Request Body:**

*   A `CodxUser` object containing the updated user details.

**Functionality:**

1.  Verifies that the username in the authenticated user matches the username in the request body. Raises an exception if they do not match.
2.  Updates the user information using `UserSecurityManager.update_user()`.

#### `/users` (GET)

This GET endpoint lists all users.

**Functionality:**

1.  Retrieves the list of users using `UserSecurityManager.list_user()`.

### GitHub OAuth Integration

The `codx.junior.security.github_oauth` module provides functionalities for integrating with GitHub for OAuth authentication.

*   `GitHubOAuth`: A class that handles the OAuth flow with GitHub, including generating authorization URLs, exchanging codes for access tokens, and fetching user information.
*   `GITHUB_CLIENTS`: A dictionary used to store `GitHubOAuth` instances, likely keyed by the `state` parameter for security.

```python
# /codx/junior/api/users.py
import logging
import datetime
from fastapi import APIRouter, Request, Response, Depends
import httpx

from codx.junior.engine import (
  CODXJuniorSession,
)

from codx.junior.security.user_management import UserSecurityManager, get_authenticated_user
from codx.junior.model.model import CodxUser, CodxUserLogin, GlobalSettings
from codx.junior.security.github_oauth import GitHubOAuth, GITHUB_CLIENTS

from codx.junior.settings import get_oauth_provider

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/forward-auth")
async def proxy_forward_auth(request: Request):
    logger.info("[proxy_forward_auth] headers: %s", request.headers)
    cookies = request.headers.get("cookie", "").split(":")[-1].split(";")
    logger.info("[proxy_forward_auth] cookies: %s", cookies)
    
    return "ok"

@router.get("/users/oauth-login-url/{oauth_provider}")
async def get_oauth_login_url(oauth_provider: str, request: Request):
    """Generate and return the OAuth login URL."""
    redirect_uri = request.query_params.get("redirect_uri")
    provider_info = get_oauth_provider(oauth_provider)
    if not provider_info:
        logger.error(f"OAuth provider not found: {oauth_provider} - {global_settings.oauth_providers}")
        return {"error": f"Provider {oauth_provider} not supported"}

    if oauth_provider == "github":
        github_oauth = GitHubOAuth(client_id=provider_info.client_id, client_secret=provider_info.secret, redirect_uri=redirect_uri)
        auth_url = github_oauth.get_authorization_url()
        return { "auth_url": auth_url }

    return {"error": "Provider not supported"}

@router.post("/users/oauth-login")
async def oauth_login(request: Request):
    """Handle OAuth login and fetch user token using the provided code."""
    payload = await request.json()
    oauth_provider = payload["oauth_provider"] 
    provider_info = get_oauth_provider(oauth_provider)
    if not provider_info:
        logger.error(f"OAuth provider not found: {oauth_provider}")
        return {"error": f"Provider {oauth_provider} not supported"}
    
    if oauth_provider == "github":
        code = payload["code"]
        state = payload["state"]
        redirect_uri = payload["redirect_uri"]
        
        github_oauth = GITHUB_CLIENTS[state]
        token_data = github_oauth.get_access_token(code=code)
        
        if token_data:
            logger.info("github_oauth token_data: %s", token_data)
            user_info = github_oauth.get_user_info(token_data['access_token'])
            user_security = UserSecurityManager()
            codx_user = user_security.find_github_user(account=user_info["login"])
            return user_security.login_user(
                                user=CodxUserLogin(**codx_user.__dict__), 
                                oauth_password=state)

    logger.error(f"GitHub OAuth login failed for provider: {oauth_provider}")
    return {"error": "OAuth login failed"}

@router.post("/users/login")
async def user_login(request: Request, response: Response):
    body = await request.json()
    oauth_provider = body.get("oauth_provider")
    if oauth_provider:
        # Fetch OAuth URL and return it to redirect the user
        oauth_data = await get_oauth_login_url(oauth_provider=oauth_provider)
        return oauth_data

    login_user = CodxUserLogin(**body)
    user = get_authenticated_user(request=request)
    logger.info(f"user_login user: {user} - body: {login_user}")
    if user:
        response.set_cookie(key="codx-session", value=user.token)
        return user
    response.set_cookie(key="codx-session", value="")
    return UserSecurityManager().login_user(user=login_user)

@router.put("/users")
async def user_update(request: Request, user: CodxUser = Depends(get_authenticated_user)):
    body = await request.json()
    user_security_manager = UserSecurityManager()
    user_changes = CodxUser(**body)
    if user.username != user_changes.username:
      logger.error(f"User {user} not match {user_changes}")
      raise Exception("Invalid data")
    return user_security_manager.update_user(user_changes)

@router.get("/users")
def list_update():
    return UserSecurityManager().list_user()
```