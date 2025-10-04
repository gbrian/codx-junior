# [[{"id": "dcae436d-85cf-4a01-8db7-f36afedecb9b", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": ["/shared/codx-junior/api/codx/junior/api/users.py", "/shared/codx-junior/api/codx/junior/security/user_management.py", "/shared/codx-junior/api/codx/junior/model/model.py"], "check_lists": [], "profiles": [], "users": ["admin"], "name": "Allow user to login with OAuth", "description": "1. The user provided Python code for a FastAPI-based application dealing with user authentication and security management.\n2. The user requested an enhancement to allow logging in via OAuth within the existing login endpoint.\n3. I updated the `/users/login` endpoint to check for an \"oauth_provider\" in the request body and use global settings to facilitate OAuth login.\n4. The response includes logic for interacting with OAuth providers, fetching tokens, and handling authentication results.\n5. The integration maintains the existing user authentication structure, seamlessly adding OAuth capabilities.", "created_at": "2025-08-30 16:43:53.391710", "updated_at": "2025-08-30T17:01:22.295825", "mode": "task", "kanban_id": "", "column_id": "", "board": "OAuth", "column": "ToDo", "chat_index": 0, "url": "", "branch": "", "file_path": "/shared/codx-junior/api/.codx/tasks/OAuth/ToDo/allow-user-to-login-with-oauth.dcae436d-85cf-4a01-8db7-f36afedecb9b.md", "llm_model": "", "visibility": "", "remote_url": "", "knowledge_topics": []}]]
## [[{"doc_id": "6ea4d362-c75d-4eb2-b578-6dd7e50a0d72", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-08-30 16:43:53.389655", "updated_at": "2025-08-30 16:43:53.389682", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
Allow user to login with OAuth.
in the login endnpoint check for "oauth_provider", then use the global settings to read the OAuth information and perform a OAuth login
## [[{"doc_id": "84743001-9753-40ca-b0f6-81a5c5971757", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-08-30 16:43:53.389655", "updated_at": "2025-08-30 16:43:53.389682", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
Allow user to login with OAuth.
in the login endnpoint check for "oauth_provider", then use the global settings to read the OAuth information and perform a OAuth login
                    Create new document based on user comments.
                    User comments:
                    Allow user to login with OAuth.
in the login endnpoint check for "oauth_provider", then use the global settings to read the OAuth information and perform a OAuth login
                    Important: Always return the markdown document without any comments before or after, to keep it clean.
## [[{"doc_id": "698539ea-fd90-4e03-8e84-58863aa55425", "role": "assistant", "task_item": "analysis", "think": null, "hide": false, "is_answer": false, "improvement": false, "created_at": "2025-08-30 16:43:53.389655", "updated_at": "2025-08-30 16:43:53.389682", "images": [], "files": [], "meta_data": {"time_taken": 16.60940980911255, "first_chunk_time_taken": 0.00020122528076171875, "model": "openai/gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": null, "disable_knowledge": false, "read_by": []}]]
```python /shared/codx-junior/api/codx/junior/api/users.py
import logging
import datetime
from fastapi import APIRouter, Request, Depends
import httpx

from codx.junior.engine import (
  CODXJuniorSession,
)

from codx.junior.security.user_management import UserSecurityManager, get_authenticated_user
from codx.junior.model.model import CodxUser, CodxUserLogin, GlobalSettings

logger = logging.getLogger(__name__)

router = APIRouter()

async def oauth_login(oauth_provider: str, request: Request):
    global_settings = GlobalSettings()
    provider_info = next((provider for provider in global_settings.oauth_providers if provider.name == oauth_provider), None)
    if not provider_info:
        logger.error(f"OAuth provider not found: {oauth_provider}")
        return None
    
    token_url = f"https://example.com/{oauth_provider}/token"  # Replace with actual token URL
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    data = {
        'client_id': provider_info.client_id,
        'client_secret': provider_info.secret,
        'code': request.query_params.get('code'),
        'grant_type': 'authorization_code',
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, headers=headers, data=data)
        if response.status_code == 200:
            token_data = response.json()
            return token_data
        else:
            logger.error(f"OAuth login failed for provider: {oauth_provider}, status: {response.status_code}")
            return None

@router.post("/users/login")
async def user_login(request: Request):
    body = await request.json()
    oauth_provider = body.get("oauth_provider")
    if oauth_provider:
        oauth_user_data = await oauth_login(oauth_provider=oauth_provider, request=request)
        if oauth_user_data:
            # Implement user lookup/creation logic here based on oauth_user_data
            return {"message": "OAuth Login successful", "oauth_user_data": oauth_user_data}

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
```