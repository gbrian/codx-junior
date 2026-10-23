# API

## REST API

The backend is a FastAPI application served under `/api`. Interactive documentation is available on your instance at:

* `/api/docs` (Swagger UI)
* `/api/redoc`
* `/api/openapi.json`

Real-time events (chat streaming, notifications, progress) use Socket.IO at `/api/socket.io`.

Requests are authenticated with the user token returned by `POST /api/users/login`.

## OpenAI-compatible endpoint

Any [profile](/features/profiles) can be exposed as a model. Turn on **API settings → active** in the profile and optionally give it a model name and description. Then use it from any OpenAI-compatible client:

| Endpoint | Description |
| --- | --- |
| `GET /api/v1/models` | Lists the profiles exposed as models, named `<project>/<profile>` unless a model name is set. |
| `POST /api/v1/completions` | Sends chat `messages` to a `<project>/<profile>` model and returns a chat completion. |

This lets you plug codx-junior's project-aware assistants into other tools, such as IDE extensions.
