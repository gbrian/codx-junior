## Security and Authentication: GitHub OAuth

This document outlines the implementation of GitHub OAuth for user authentication within the codx-api project. It provides a `GitHubOAuth` class to handle the OAuth flow, including generating authorization URLs, exchanging authorization codes for access tokens, and retrieving user information.

### GitHubOAuth Class

The `GitHubOAuth` class manages the entire process of authenticating users with GitHub.

#### Initialization (`__init__`)

When creating an instance of `GitHubOAuth`, you need to provide your GitHub application's `client_id`, `client_secret`, and `redirect_uri`. You can also specify the desired `scope` for the authentication. A unique `state` token is generated for each instance, and this is stored globally in `GITHUB_CLIENTS` for later retrieval.

```python
def __init__(self, client_id, client_secret, redirect_uri, scope=''):
    self.client_id = client_id
    self.client_secret = client_secret
    self.redirect_uri = redirect_uri
    self.scope = scope
    self.state = secrets.token_urlsafe(16)
    self.generate_pkce()
    GITHUB_CLIENTS[self.state] = self
```

#### PKCE Generation (`generate_pkce`)

This method generates the necessary Proof Key for Code Exchange (PKCE) parameters: `code_verifier` and `code_challenge`. PKCE enhances security by preventing authorization code interception attacks.

```python
def generate_pkce(self):
    """Generate code verifier and code challenge for PKCE."""
    # Ensure the code_verifier length is within the required 43 to 128 range by generating more characters
    code_verifier = secrets.token_urlsafe(64)  # Generates a string greater than 43 characters
    hashed = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = secrets.base64.urlsafe_b64encode(hashed).decode().strip('=')
    self.code_challenge = code_challenge
    self.code_verifier = code_verifier
```

#### Get Authorization URL (`get_authorization_url`)

This method constructs the URL that redirects the user to GitHub for authentication. It includes parameters like `client_id`, `redirect_uri`, `scope`, `state`, and the PKCE `code_challenge`. You can optionally specify a `login` for pre-filling the username or `allow_signup` to control whether new users can sign up.

```python
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
```

#### Get Access Token (`get_access_token`)

After the user authorizes your application on GitHub, they are redirected back to your `redirect_uri` with an authorization `code`. This method exchanges that `code` (along with `client_id`, `client_secret`, `redirect_uri`, and `code_verifier`) for an access token from GitHub's API. The corresponding `GitHubOAuth` instance is removed from `GITHUB_CLIENTS` upon successful retrieval of the token.

```python
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
```

#### Get User Info (`get_user_info`)

Once you have an `access_token`, this method can be used to retrieve the authenticated user's profile information from GitHub's API.

```python
def get_user_info(self, access_token):
    """Retrieve user information using the access token."""
    headers = {'Authorization': f'Bearer {access_token}'}
    user_info_url = 'https://api.github.com/user'
    response = requests.get(user_info_url, headers=headers)
    response.raise_for_status()
    return response.json()
```

```python
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

```