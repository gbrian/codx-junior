/**
 * Traefik maintenance model definitions (client-side JSDoc).
 *
 * Mirrors:
 *   api/codx/junior/traefik/model.py
 *   api/codx/junior/traefik/builder.py
 *
 * A rule has no `scope` field: the storage it lives in (global settings or a
 * project's .codx/project.json) is the scope. The API adds `scope` to the
 * merged route rows so the UI can show badges and decide editability.
 */

/**
 * @typedef {'url'|'workspace_app'|'container'} TraefikTargetType
 */

/**
 * @typedef {Object} TraefikRule
 * @property {string}  id
 * @property {string}  name
 * @property {string}  description
 * @property {boolean} enabled
 * @property {TraefikTargetType} target_type
 * @property {string}  url                  - target_type === 'url'
 * @property {string}  workspace_slug       - target_type === 'workspace_app'
 * @property {string}  app_id               - target_type === 'workspace_app'
 * @property {string}  container_name       - target_type === 'container'
 * @property {number|null} container_port   - target_type === 'container'
 * @property {string}  rule                 - Traefik rule expression
 * @property {string}  path_prefix          - public prefix used by strip_prefix
 * @property {string[]} entrypoints
 * @property {string[]} middlewares
 * @property {boolean} auth
 * @property {boolean} strip_prefix
 * @property {number|null} priority
 * @property {string|null} created_at
 * @property {string|null} updated_at
 */

/**
 * One row in the merged route list. Workspace rows are read-only; custom rows
 * are editable only in the settings screen that owns their storage.
 *
 * @typedef {Object} TraefikRoute
 * @property {string}  id
 * @property {string}  router_id
 * @property {string}  name
 * @property {string}  description
 * @property {'workspace'|'custom'} source
 * @property {'workspace'|'global'|'project'} scope
 * @property {string|null} project_id
 * @property {string|null} project_name
 * @property {string[]} project_ids
 * @property {string}  workspace_id
 * @property {string}  workspace_slug
 * @property {string}  workspace_name
 * @property {string}  app_id
 * @property {string}  app_name
 * @property {boolean} editable
 * @property {boolean} enabled
 * @property {'docker-labels'|'http-provider'} [managed_by]
 * @property {string}  rule
 * @property {TraefikTargetType|string} target_type
 * @property {string}  target
 * @property {string|null} target_url
 * @property {string}  container_name
 * @property {number|null} container_port
 * @property {string[]} middlewares
 * @property {string[]} entrypoints
 * @property {number|null} priority
 * @property {string}  path_prefix
 * @property {string[]} issues
 */

/**
 * @typedef {Object} TraefikWorkspaceAppTarget
 * @property {string}  id
 * @property {string}  name
 * @property {string}  path
 * @property {string}  route_path    - public prefix (for external apps) or path
 * @property {number|null} port
 * @property {boolean} external
 * @property {boolean} targetable
 */

/**
 * @typedef {Object} TraefikWorkspaceTarget
 * @property {string} id
 * @property {string} slug
 * @property {string} name
 * @property {string[]} project_ids
 * @property {TraefikWorkspaceAppTarget[]} apps
 */

/**
 * @typedef {Object} TraefikContainerTarget
 * @property {string} id
 * @property {string} name
 * @property {string} image
 * @property {string} state
 * @property {boolean} running
 * @property {number[]} ports
 * @property {string[]} networks
 * @property {Record<string,string[]>} network_aliases
 * @property {string} compose_project
 * @property {string} compose_service
 * @property {boolean} traefik_enable
 * @property {boolean|null} reachable
 */

/**
 * @typedef {Object} TraefikTargets
 * @property {TraefikWorkspaceTarget[]} workspaces
 * @property {TraefikContainerTarget[]} containers
 * @property {string[]} traefik_networks
 * @property {string|null} error
 * @property {{domain: string, auth_middleware: string, entrypoints: string[]}} defaults
 */

/** Factory for a blank rule used by the editor. */
export function createTraefikRule(overrides = {}) {
  return {
    id: '',
    name: '',
    description: '',
    enabled: true,
    target_type: 'workspace_app',
    url: '',
    workspace_slug: '',
    app_id: '',
    container_name: '',
    container_port: null,
    rule: '',
    path_prefix: '',
    entrypoints: ['web', 'websecure'],
    middlewares: [],
    auth: true,
    strip_prefix: false,
    priority: null,
    created_at: null,
    updated_at: null,
    ...overrides,
  }
}

/** Generate a browser-side rule id (the API also fills missing ids). */
export function createTraefikRuleId() {
  const uuid = globalThis.crypto?.randomUUID?.()
  if (uuid) return `rule-${uuid.slice(0, 8)}`
  return `rule-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}
