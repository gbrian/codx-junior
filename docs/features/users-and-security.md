# Users and security

## Users and roles

Admins manage users in **Global settings → Users**. Each user has:

* a username, email, avatar and theme,
* a **role**: `admin` or `user`,
* **project permissions**, optionally inherited by sub-projects,
* access to specific **workspace apps**,
* personal **environment variables**,
* a [wallet and token limits](/features/budget-and-analytics).

Users can be disabled without being deleted.

## Signing in

* **Username and password.** The `admin` user sets its password on the first login.
* **GitHub OAuth.** Configure an OAuth provider in **Global settings → OAuth**. GitHub accounts listed as admins get the admin role. A user can be restricted to GitHub-only login.

## Protecting apps

Every app routed by Traefik (workspace apps, LocalAI, the Traefik dashboard) goes through codx-junior's **forward-auth** endpoint. Only signed-in users with access to that app can open it.

## Settings history

Global settings are versioned by section. Admins can review previous versions and roll back a change.
