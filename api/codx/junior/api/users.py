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

from codx.junior.global_settings import get_oauth_provider, get_global_settings
from codx.junior.analytics.analytics import Analytics
from codx.junior.globals import ANALYTICS_DATA_PATH

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


@router.get("/users/me/refresh")
async def refresh_user_info(request: Request, user: CodxUser = Depends(get_authenticated_user)):
    """
    Return the authenticated user's profile enriched with today's token
    consumption and effective per-rule limits.

    Response shape
    --------------
    {
      ...user fields...,
      "token_usage_today": {
        "input_tokens":  <int>,
        "output_tokens": <int>,
        "total_tokens":  <int>,
        "calls":         <int>,
        "total_duration_seconds": <float>
      },
      "token_limits_today": [
        {
          "rule_index":       <int>,
          "provider":         <str|null>,
          "model":            <str|null>,
          "limit_per_day":    <int>,
          "effective_limit":  <int|null>,   # null → unlimited
          "tokens_used":      <int>,
          "tokens_remaining": <int|null>,   # null → unlimited
          "extension":        <dict|null>
        },
        ...
      ]
    }
    """
    today = datetime.date.today().isoformat()

    # ── Token usage for today ──────────────────────────────────────────────────
    try:
        analytics = Analytics(analytics_path=ANALYTICS_DATA_PATH)
        usage_today = analytics.get_total_usage(
            start_date=today,
            end_date=today,
            username=user.username,
        )
    except Exception as exc:
        logger.warning("refresh_user_info: could not read analytics for %s: %s", user.username, exc)
        usage_today = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "calls": 0,
            "total_duration_seconds": 0.0,
        }

    total_tokens_used_today = usage_today.get("total_tokens", 0)

    # ── Per-rule effective limits ──────────────────────────────────────────────
    limits_today = []
    for idx, rule in enumerate(user.token_limit_rules or []):
        effective = rule.effective_limit(today)
        remaining = None if effective is None else max(0, effective - total_tokens_used_today)
        limits_today.append({
            "rule_index": idx,
            "provider": rule.provider,
            "model": rule.model,
            "limit_per_day": rule.limit_per_day,
            "effective_limit": effective,
            "tokens_used": total_tokens_used_today,
            "tokens_remaining": remaining,
            "extension": rule.extension.dict() if rule.extension else None,
        })

    # ── Build response ─────────────────────────────────────────────────────────
    user_dict = user.dict()
    user_dict["token_usage_today"] = usage_today
    user_dict["token_limits_today"] = limits_today

    logger.info(
        "refresh_user_info: user=%s today=%s total_tokens=%d rules=%d",
        user.username,
        today,
        total_tokens_used_today,
        len(limits_today),
    )

    return user_dict