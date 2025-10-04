# [[{"id": "86a797e7-2a4c-43af-9473-f19f7be24492", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": ["/shared/codx-junior/api/codx/junior/security/github_oauth.py"], "check_lists": [], "profiles": [], "users": ["admin"], "name": "Fix oauth PKCE", "description": "1. The user provided specific instructions for content creation, emphasizing the maintenance of a clean markdown document.\n2. A JSON object was included detailing a Python script for handling GitHub OAuth, focusing on class structure and functionality.\n3. The script implements PKCE (Proof Key for Code Exchange), mandates code verifiers to be between 43 and 128 characters, and restricts characters to a defined set.\n4. The assistant adjusted the script to ensure the code verifier meets the PKCE requirements.\n5. The response returned the revised Python script in the designated file path without extra comments.", "created_at": "2025-09-01 15:14:16.729889", "updated_at": "2025-09-01T15:17:30.670225", "mode": "task", "kanban_id": "", "column_id": "", "board": "OAuth", "column": "ToDo", "chat_index": 0, "url": "", "branch": "", "file_path": "/shared/codx-junior/api/.codx/tasks/OAuth/ToDo/fix-oauth-pkce.86a797e7-2a4c-43af-9473-f19f7be24492.md", "llm_model": "", "visibility": "", "remote_url": "", "knowledge_topics": []}]]
## [[{"doc_id": "c920a994-dccb-41c6-bee0-b6fa15300144", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-01 15:14:16.727904", "updated_at": "2025-09-01 15:14:16.727930", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
PKCE code_verifiers must be between 43 and 128 characters long (inclusive) and must contain only the following characters: [a-zA-Z0-9_.~-] 
## [[{"doc_id": "2b794448-5f8a-4091-9561-e5b67283fec4", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-01 15:14:16.727904", "updated_at": "2025-09-01 15:14:16.727930", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
PKCE code_verifiers must be between 43 and 128 characters long (inclusive) and must contain only the following characters: [a-zA-Z0-9_.~-] 
                    Create new document based on user comments.
                    User comments:
                    PKCE code_verifiers must be between 43 and 128 characters long (inclusive) and must contain only the following characters: [a-zA-Z0-9_.~-] 
                    Important: Always return the markdown document without any comments before or after, to keep it clean.
## [[{"doc_id": "55e27e8e-fd4f-4a09-bc93-0a23275b4db5", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-01 15:14:16.727904", "updated_at": "2025-09-01 15:14:16.727930", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]


## [[{"doc_id": "dfb81785-06ee-4a6b-a428-10d21baf3992", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-01 15:14:16.727904", "updated_at": "2025-09-01 15:14:16.727930", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]


                    Create new document based on user comments.
                    User comments:
                    

                    Important: Always return the markdown document without any comments before or after, to keep it clean.
## [[{"doc_id": "8e437541-c77d-499d-8b59-bb78ba6c1f8c", "role": "assistant", "task_item": "analysis", "think": null, "hide": false, "is_answer": false, "improvement": false, "created_at": "2025-09-01 15:14:16.727904", "updated_at": "2025-09-01 15:14:16.727930", "images": [], "files": [], "meta_data": {"time_taken": 5.708592653274536, "first_chunk_time_taken": 0.0002002716064453125, "model": "openai/gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": null, "disable_knowledge": false, "read_by": []}]]
```python /shared/codx-junior/api/codx/junior/security/github_oauth.py
import logging
import requests
import secrets
import hashlib

logger = logging.getLogger(__name__)

class GitHubOAuth:
    def __init__(self, client_id, client_secret, redirect_uri, scope=''):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.state = secrets.token_urlsafe(16)

    def generate_pkce(self):
        """Generate code verifier and code challenge for PKCE."""
        # Ensure the code_verifier length is within the required 43 to 128 range by generating more characters
        code_verifier = secrets.token_urlsafe(64)  # Generates a string greater than 43 characters
        hashed = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = secrets.base64.urlsafe_b64encode(hashed).decode().strip('=')
        return code_verifier, code_challenge

    def get_authorization_url(self, login=None, allow_signup=True, prompt=None):
        """Generate the GitHub authorization URL."""
        code_verifier, code_challenge = self.generate_pkce()
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': self.scope,
            'state': self.state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'allow_signup': str(allow_signup).lower()
        }
        if login:
            params['login'] = login
        if prompt:
            params['prompt'] = prompt

        auth_url = requests.Request('GET', 'https://github.com/login/oauth/authorize', params=params).prepare().url
        return auth_url, code_verifier

    def get_access_token(self, code, code_verifier):
        """Exchange code for an access token."""
        token_url = 'https://github.com/login/oauth/access_token'
        headers = {
          'Accept': 'application/json'
        }
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri,
            'code_verifier': code_verifier,
            'repository_id': ''
        }
        logger.info("get_access_token %s", data)
        query_string = "&".join([f"{k}={data[k]}" for k in data.keys()])
        response = requests.post(f"{token_url}?{query_string}", headers=headers)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            logger.exception("Error requesting github access_token: %s - %s - %s",
                err.request.url,
                str(err),
                err.response.text)
            raise err
        return response.json()

    def get_user_info(self, access_token):
        """Retrieve user information using the access token."""
        headers = {'Authorization': f'Bearer {access_token}'}
        user_info_url = 'https://api.github.com/user'
        response = requests.get(user_info_url, headers=headers)
        response.raise_for_status()
        return response.json()
```