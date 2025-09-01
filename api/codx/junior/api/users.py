import logging
import datetime
from fastapi import APIRouter, Request, Depends
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
async def user_login(request: Request):
    body = await request.json()
    oauth_provider = body.get("oauth_provider")
    if oauth_provider:
        # Fetch OAuth URL and return it to redirect the user
        oauth_data = await get_oauth_login_url(oauth_provider=oauth_provider)
        return oauth_data

    login_user = CodxUserLogin(**body)
    user = await get_authenticated_user(request=request)
    logger.info(f"user_login user: {user} - body: {login_user}")
    if user:
        return user
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
