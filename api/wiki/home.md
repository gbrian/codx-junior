# Welcome to the codx-junior Wiki

This wiki serves as a concise, endpoint-centric reference for the **codx-junior** project, documenting core architecture, API endpoints, routing configuration, and middleware generation for external-facing services.

## Documentation Updates
The wiki has been restructured for improved clarity and navigation. Key changes include:
- Sections reordered to flow logically: Overview → Endpoints → Routing Logic → Authentication → Dynamic Configuration, with the dedicated References section removed and cross-links integrated inline.
- API endpoints are now described in prose, with explicit authentication notes (e.g., config endpoints are internal-only with no auth, routes endpoints require appropriate roles).
- A dedicated Authentication Middleware section confirms that every generated route enforces `codx-junior-auth` alongside route-specific middlewares.
- Routing Logic consolidates handling of external HTTP/HTTPS URLs versus container-port apps, noting that the latter are managed by Traefik's Docker label provider.
- Dynamic configuration building uses URL parsing and strip-prefix middleware; errors are caught and logged, returning `{ "http": {} }` to prevent Traefik polling disruptions.
- The standalone References section has been removed; all references are embedded within section text for better flow.
- Across modules (including `traefik.py`), documentation has been reframed from detailed implementation mechanics to concise high-level summaries, emphasizing intent and top-level behavior for improved maintainability.
- **Traefik-specific updates**: Documentation condensed to focus on two primary endpoints (`/config` and `/routes`), explicit authentication (`codx-junior-auth` applied to all routes), and dynamic configuration using strip-prefix middleware for external sub-paths while intentionally skipping container-port apps (managed by Traefik's Docker label provider). Error handling ensures exceptions are caught, logged, and return `{ "http": {} }` to keep Traefik’s polling loop stable.

## Core Architecture
- **App Module**: Initializes the FastAPI server, defines routing and middleware, manages background tasks, and integrates with Socket.IO. External apps with paths starting with `http://` or `https://` are dynamically configured with authentication and path-stripping middleware; others are handled by Traefik Docker labels.
- **Engine Module**: Orchestrates core backend operations including project provisioning, session lifecycle management, and high-level business logic.
- **AI and Knowledge Management**: Covers agents, models, and utilities for workflow automation, AI configurations, embeddings, code analysis, document enrichment, and vector-based storage.
- **Utility Functions**: Provides centralized tools supporting asynchronous execution, configurable scopes, and bulk optimizations across web content, project navigation, file operations, code and task management, media, tutorial management, and Git version control.

The wiki follows a focused Architecture → Endpoints → Middleware flow to improve navigation and highlight key infrastructure and access control aspects.

## Navigation
Use the sidebar to explore categorized sections such as Project Overview, App Module, Engine Module, AI and Knowledge Management, Security and Authentication, Session Management, and Utility Functions.