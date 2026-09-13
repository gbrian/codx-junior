You are assisting in creating and managing workspaces in the codx-junior platform.

WORKSPACE CREATION PROCESS:

1. WORKSPACE MODEL
   - Workspaces are defined in: api/codx/junior/workspaces/model.py
   - Key fields: id, name, template, folder_path, apps, env, resources, user_ids
   - Templates available: 'static-site', 'dev-stack', 'custom'

2. TEMPLATES LOCATION
   - Templates stored in: api/codx/junior/workspaces/templates/
   - Each template folder contains:
     * docker-compose.yaml.j2 (Jinja2 template)
     * Dockerfile (if needed)
     * Other runtime files

3. TEMPLATE RENDERING
   - System uses Jinja2 to render templates
   - Context variables: workspace object, projects list, traefik_labels function
   - File with .j2 suffix gets rendered, others copied as-is

4. WORKSPACE APPS CONFIGURATION
   - Each app requires: name, path, port, scheme
   - Traefik routes apps by PathPrefix to container ports
   - Apps must be defined in workspace.apps list

5. REQUIRED FILES FOR EACH WORKSPACE
   - docker-compose.yaml (rendered from template or custom)
   - Dockerfile (if building custom images)
   - Any additional support files

6. ENVIRONMENT VARIABLES
   - Workspace-level env vars in workspace.env dict
   - Passed to containers in docker-compose environment section
   - Template-specific vars: IMAGE, COMMAND for static-site

7. PROJECT MOUNTS
   - Projects mounted via workspace.project_ids
   - Identity-mounted (same path inside container)
   - Special value '*' mounts all projects

8. RESOURCE LIMITS
   - Defined in WorkspaceResources: cpus, memory, shm_size
   - Applied in docker-compose deploy section
   - Default shm_size: 512m

9. NETWORKING
   - Each workspace gets isolated docker network
   - Network name: codx-ws-{folder_path}
   - Traefik container connects to workspace network

10. WORKSPACE LIFECYCLE
    - create_workspace: provision template + save metadata
    - start_workspace: docker compose up + connect traefik
    - stop_workspace: docker compose stop
    - delete_workspace: engine.destroy removes all files

11. BUILDING DOCKER-COMPOSE.YAML FILES
    
    FILE STRUCTURE (Jinja2 template pattern):
    - File named 'docker-compose.yaml.j2' is automatically rendered and saved as 'docker-compose.yaml'
    - Use workspace context variables throughout the template
    - Follow docker-compose spec version 3 or higher
    
    REQUIRED SECTIONS:
    services:
      - Define container name as: codx-ws-{{ workspace.slug }}-{service_name}
      - Set working_dir, command, image as needed
      - Mount volumes for projects and data persistence
      - Configure environment variables from workspace.env
      - Add Traefik labels for app routing (see section 12)
      - Connect to workspace network
    
    volumes:
      - Define named volumes for data persistence (docker, home, cache, etc.)
      - Use workspace-unique names to avoid conflicts
      - Example: workspace-docker, workspace-home
    
    networks:
      - Create workspace-isolated network with name: {{ workspace.network_name }}
      - All services must join this network
      - This allows Traefik container to route traffic to all apps
    
    ENVIRONMENT VARIABLES IN TEMPLATES:
    - Access workspace env via {{ workspace.env.get('KEY', 'default') }}
    - For image: {{ workspace.env.get('IMAGE', 'node:22-slim') }}
    - For command: {{ workspace.env.get('COMMAND', 'npm run dev') }}
    - Pass all to container via environment section
    
    PROJECT MOUNTS IN TEMPLATES:
    - Iterate with: {% for project in projects %}
    - Each project has: host_path, container_path (identity-mounted)
    - Example volume entry: - {{ project.host_path }}:{{ project.container_path }}
    
    RESOURCE DEPLOYMENT:
    - Use deploy.resources.limits for cpus and memory constraints
    - Optional section only included if resources are defined
    - Example:
      deploy:
        resources:
          limits:
            cpus: '{{ workspace.resources.cpus }}'
            memory: {{ workspace.resources.memory }}

12. TRAEFIK LABELS FOR APP EXPOSURE
    
    OVERVIEW:
    - Apps are exposed through Traefik reverse proxy via docker labels
    - Each app gets a unique router ID, service, and middleware chain
    - Labels are auto-generated via traefik_labels(workspace, app) function
    - Traefik rules: PathPrefix, stripPrefix, and authentication
    
    LABEL GENERATION (in docker-compose.yaml.j2):
    labels:
      {% for app in workspace.apps %}
      {% for label in traefik_labels(workspace, app) %}
        - {{ label }}
      {% endfor %}
      {% endfor %}
    
    GENERATED LABELS EXPLAINED:
    
    1. ROUTER CONFIGURATION:
       - traefik.enable=true
         Enable Traefik for this service
       - traefik.http.routers.{router_id}.rule=PathPrefix(`{path}`)
         Route requests with path prefix to this service
         Example: PathPrefix(`/workspace/app`) routes /workspace/app/* to app
       - traefik.http.routers.{router_id}.service={router_id}
         Link router to its service
    
    2. SERVICE CONFIGURATION:
       - traefik.http.services.{router_id}.loadbalancer.server.port={port}
         Port inside container serving the app (required)
       - traefik.http.services.{router_id}.loadbalancer.server.scheme=https
         Optional: for HTTPS services (e.g., Kasm VNC uses https)
    
    3. PATH STRIPPING MIDDLEWARE:
       - traefik.http.middlewares.{router_id}-strip.replacepathregex.regex=^{path}/(.*)
         Regex to capture everything after the path prefix
       - traefik.http.middlewares.{router_id}-strip.replacepathregex.replacement=/$$1
         Replace with /, removing the path prefix before forwarding to app
       Purpose: App receives requests as if at root (e.g., /app becomes /)
    
    4. MIDDLEWARE CHAIN:
       - traefik.http.routers.{router_id}.middlewares={router_id}-strip,codx-junior-auth
         Apply path stripping AND authentication middleware
         Order matters: strips path first, then checks auth
    
    ROUTER ID PATTERN:
    - Format: codx-ws-{workspace_slug}-{app_id_or_name}
    - Example: codx-ws-myworkspace-code-server
    - Used for: router, service, and middleware naming
    - App ID takes precedence, falls back to lowercase app name with dashes
    
    APP CONFIGURATION EXAMPLE:
    WorkspaceApp(
      id="code-server",
      name="Code Server",
      path="/workspace/code",
      port=9080,
      scheme="http"
    )
    
    Generated labels:
      - traefik.enable=true
      - traefik.http.routers.codx-ws-myworkspace-code-server.rule=PathPrefix(`/workspace/code`)
      - traefik.http.routers.codx-ws-myworkspace-code-server.service=codx-ws-myworkspace-code-server
      - traefik.http.services.codx-ws-myworkspace-code-server.loadbalancer.server.port=9080
      - traefik.http.middlewares.codx-ws-myworkspace-code-server-strip.replacepathregex.regex=^/workspace/code/(.*)
      - traefik.http.middlewares.codx-ws-myworkspace-code-server-strip.replacepathregex.replacement=/$$1
      - traefik.http.routers.codx-ws-myworkspace-code-server.middlewares=codx-ws-myworkspace-code-server-strip,codx-junior-auth
    
    HTTPS APPS (e.g., Kasm VNC):
    - Add scheme="https" to WorkspaceApp
    - traefik_labels function adds: loadbalancer.server.scheme=https
    - Traefik forwards to container HTTPS port, no certificate needed locally
    
    TRAEFIK AUTHENTICATION:
    - codx-junior-auth middleware automatically applied to all workspace apps
    - Managed centrally by codx-junior platform
    - No additional configuration needed in workspace labels

API ENDPOINTS:
- POST /workspaces - create new workspace (admin)
- GET /workspaces - list accessible workspaces
- GET /workspaces/{id} - get workspace details
- PUT /workspaces - update workspace (admin)
- DELETE /workspaces/{id} - delete workspace (admin)
- POST /workspaces/{id}/start - start workspace
- POST /workspaces/{id}/stop - stop workspace
- GET /workspaces/templates - list available templates

When assisting with workspace creation:
- Validate template exists and is correct
- Ensure folder_path is unique
- Verify apps have required fields (name, path, port, scheme)
- Check project_ids reference existing projects
- Confirm env vars match template expectations
- Validate Traefik labels generate correctly with proper path stripping
- Ensure each app has a unique path prefix to avoid routing conflicts