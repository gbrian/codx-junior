# User settings & external connector extension points

Where to plug a per-user external account (e.g. Gmail) into codx-junior.

## User model & persistence
- `CodxUser` is a pydantic model in `api/codx/junior/model/user.py`.
- Per-user sub-models are plain pydantic classes added as list fields on `CodxUser`
  (precedent: `token_limit_rules`, `token_limit_requests`).
- Persistence goes through `api/codx/junior/global_settings.py`, which stores each
  `GlobalSettings` field as its own section file via `GlobalSettingsManager`.
  Use `write_settings_section(section, data)` for partial updates.
- Security logic lives in `api/codx/junior/security/user_management.py`
  (`UserSecurityManager`, `get_authenticated_user`).

## OAuth
- Working precedent: `api/codx/junior/security/github_oauth.py` — `GitHubOAuth` class
  with PKCE (`generate_pkce`), state registry (`GITHUB_CLIENTS[state]`),
  `get_authorization_url()`, `get_access_token(code)`, `get_user_info(token)`.
- Provider config resolution: `get_oauth_provider(name)` in `global_settings.py`.
  Resolution order: env vars first (`CODX_{NAME}_CLIENT_ID`, `CODX_{NAME}_SECRET`,
  `CODX_{NAME}_TOKEN_URL`), then the `oauth_providers` settings section.
- Login routes are in `api/codx/junior/api/users.py`
  (`/users/oauth-login-url/{provider}`, `/users/oauth-login`).

## Front-end
- Per-user account UI: `client/src/components/security/AccountSettings.vue`
  (Vue 3, daisyUI classes, `$user`, `$users`, `$toast` globals).
- Admin OAuth provider UI: `client/src/components/oauth_settings/OAuthSettings.vue`.
- Client API modules: `client/src/api/modules/*.js`, user store `client/src/store/users.js`.

## Conventions worth keeping
- Tokens/secrets must never be serialised into API responses or written to logs.
- Consent-scope growth forces re-consent: request the minimal scope per increment and
  handle "account connected but missing scope" explicitly instead of failing silently.

## Kanban
- External integrations live on board `External connectors`
  (existing columns: `WhatsApp`, `GMAIL`).