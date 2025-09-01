import logging
import requests
import secrets
import hashlib

logger = logging.getLogger(__name__)

GITHUB_CLIENTS = {}

class GitHubOAuth:
    def __init__(self, client_id, client_secret, redirect_uri, scope=''):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.state = secrets.token_urlsafe(16)
        self.generate_pkce()
        GITHUB_CLIENTS[self.state] = self

    def generate_pkce(self):
        """Generate code verifier and code challenge for PKCE."""
        # Ensure the code_verifier length is within the required 43 to 128 range by generating more characters
        code_verifier = secrets.token_urlsafe(64)  # Generates a string greater than 43 characters
        hashed = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = secrets.base64.urlsafe_b64encode(hashed).decode().strip('=')
        self.code_challenge = code_challenge
        self.code_verifier = code_verifier

    def get_authorization_url(self, login=None, allow_signup=True, prompt=None):
        """Generate the GitHub authorization URL."""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': self.scope,
            'state': self.state,
            'code_challenge': self.code_challenge,
            'code_challenge_method': 'S256',
            'allow_signup': str(allow_signup).lower()
        }
        if login:
            params['login'] = login
        if prompt:
            params['prompt'] = prompt

        auth_url = requests.Request('GET', 'https://github.com/login/oauth/authorize', params=params).prepare().url
        return auth_url

    def get_access_token(self, code):
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
            'code_verifier': self.code_verifier
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
        del GITHUB_CLIENTS[self.state]        
        return response.json()

    def get_user_info(self, access_token):
        """Retrieve user information using the access token."""
        headers = {'Authorization': f'Bearer {access_token}'}
        user_info_url = 'https://api.github.com/user'
        response = requests.get(user_info_url, headers=headers)
        response.raise_for_status()
        return response.json()
