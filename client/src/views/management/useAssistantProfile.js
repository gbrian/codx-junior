/**
 * ============================================================================
 * Assistant profile resolution — who answers the management dashboard chat.
 * ----------------------------------------------------------------------------
 * Management is assisted by ONE profile (`ProjectManager` by default). Its
 * avatar is the assistant's identity: it is painted on the button that opens
 * the chat, in the chat header and next to its name.
 *
 * WHY A SHARED CACHE
 * ------------------
 * The avatar (button) and the composer (profile selector) need the SAME profile
 * list of the SAME project. Fetching it twice per keystroke would be wasteful
 * and could paint two different avatars for the same project, so the list is
 * fetched once per project and shared through `profilesByProject`.
 *
 * WHAT IS *NOT* CACHED
 * --------------------
 * A project that has no API client (`$api`) — for instance the light
 * `{ id, name }` objects the dashboard receives from `/api/management/*` — is
 * never cached: it may not be fully loaded yet, and caching an empty list would
 * hide the avatar forever. Those calls simply return `[]` and are retried the
 * next time the project is resolved.
 * ============================================================================
 */
import { computed, ref, watch } from 'vue'
import { $storex } from '@/store'

/** project_id → Promise<profile[]> (deduplicated, shared by every consumer) */
const profilesByProject = new Map()

/** Id of a project coming from the store OR from the dashboard API payload. */
export function projectIdOf(project) {
  return project?.project_id || project?.id || null
}

/**
 * Resolve the project that actually owns the API client.
 *
 * The dashboard works with normalised `{ id, name }` rows (it aggregates
 * projects coming from `/api/management/*`), which carry no `$api`. Those rows
 * are mapped back to the live project of the store, which does.
 */
export function liveProject(project) {
  if (!project) return null
  if (project.$api || project.api) return project
  const id = projectIdOf(project)
  if (!id) return null
  const all = $storex?.projects?.allProjectsById || {}
  return all[id] || project
}

/**
 * Profiles of a project, fetched once and shared.
 * @param {Object} project Live store project or a normalised `{ id }` row.
 * @returns {Promise<Object[]>} Sorted profiles (`[]` when it cannot be loaded).
 */
export function loadProjectProfiles(project) {
  const live = liveProject(project)
  const id = projectIdOf(live)
  if (!id) return Promise.resolve([])

  const api = live?.$api || live?.api
  // No client yet → do not cache, so the next call can resolve it for real
  if (!api?.profiles?.list) return Promise.resolve([])

  if (!profilesByProject.has(id)) {
    const request = Promise.resolve(api.profiles.list())
      .then(list => [...(list || [])].sort((a, b) => (a.name > b.name ? 1 : -1)))
      .catch((error) => {
        console.error('[management] Could not load the project profiles:', error)
        // Drop the failed entry so a later call retries
        profilesByProject.delete(id)
        return []
      })
    profilesByProject.set(id, request)
  }

  return profilesByProject.get(id)
}

/** The profile that assists management, out of a profile list. */
export function findAssistantProfile(profiles, name = 'ProjectManager') {
  return (profiles || []).find(profile => profile.name === name) || null
}

/**
 * Reactive assistant profile for a project.
 *
 * @param {() => Object|null} projectGetter Reactive project source.
 * @param {string} [profileName='ProjectManager'] Profile that assists managers.
 * @returns {{profile, loading, avatarUrl, name}} `avatarUrl` falls back to the
 *          legacy `avatar` field and is `null` when the profile has no image.
 */
export function useAssistantProfile(projectGetter, profileName = 'ProjectManager') {
  const profile = ref(null)
  const loading = ref(false)
  // Guards against a slow response for a previous project overwriting the
  // current one (the user can switch projects while the list is in flight).
  let token = 0

  const project = computed(() => projectGetter() || null)
  const projectId = computed(() => projectIdOf(project.value))

  async function load() {
    const current = ++token
    if (!projectId.value) {
      profile.value = null
      loading.value = false
      return
    }
    loading.value = true
    const list = await loadProjectProfiles(project.value)
    if (current !== token) return
    profile.value = findAssistantProfile(list, profileName)
    loading.value = false
  }

  watch(projectId, load, { immediate: true })

  return {
    profile,
    loading,
    avatarUrl: computed(() => profile.value?.avatar_url || profile.value?.avatar || null),
    name: computed(() => profile.value?.name || profileName)
  }
}