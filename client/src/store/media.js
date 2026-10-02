import { getterTree, mutationTree, actionTree } from 'typed-vuex'

export const namespaced = true

const STORAGE_KEY = 'codx-media-store'

// ── Data type factories ───────────────────────────────────────────────────────

export const createMediaItem = (overrides = {}) => ({
  id: crypto.randomUUID(),
  name: '',
  type: 'image', // image | video | audio | document | other
  url: '',
  mimeType: '',
  size: 0, // in bytes
  duration: null, // for audio/video in seconds
  width: null, // for images/videos
  height: null, // for images/videos
  thumbnail: null,
  tags: [],
  createdAt: new Date().toISOString(),
  uploadedBy: null,
  resourceType: null, // team | channel | chat | profile
  resourceId: null,
  metadata: {},
  ...overrides
})

export const createMediaLibrary = (overrides = {}) => ({
  id: crypto.randomUUID(),
  name: '',
  description: '',
  type: 'team', // team | channel | chat | profile
  resourceId: null,
  mediaItems: [],
  createdAt: new Date().toISOString(),
  ...overrides
})

// ── Persistence helpers ───────────────────────────────────────────────────────

function persist(state) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      mediaLibraries: state.mediaLibraries,
      mediaItems: state.mediaItems
    }))
  } catch (e) {
    console.warn('[media] persist error', e)
  }
}

function load() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
  } catch {
    return {}
  }
}

// ── Store ─────────────────────────────────────────────────────────────────────

export const state = () => ({
  mediaLibraries: [],
  mediaItems: [],
  uploadProgress: {}
})

export const getters = getterTree(state, {
  libraryById: state => id => state.mediaLibraries.find(l => l.id === id) || null,
  librariesByResource: state => (resourceType, resourceId) =>
    state.mediaLibraries.filter(l => l.type === resourceType && l.resourceId === resourceId),
  mediaItemById: state => id => state.mediaItems.find(m => m.id === id) || null,
  mediaByLibrary: state => libraryId => {
    const library = state.mediaLibraries.find(l => l.id === libraryId)
    if (!library) return []
    return state.mediaItems.filter(m => library.mediaItems.includes(m.id))
  },
  mediaByResource: state => (resourceType, resourceId) => {
    const libraries = state.mediaLibraries.filter(l => l.type === resourceType && l.resourceId === resourceId)
    const mediaIds = libraries.flatMap(l => l.mediaItems)
    return state.mediaItems.filter(m => mediaIds.includes(m.id))
  },
  searchMedia: state => (query, type = null) => {
    const q = query.toLowerCase()
    return state.mediaItems.filter(m => {
      const matchesQuery = m.name.toLowerCase().includes(q) || 
                          m.tags.some(t => t.toLowerCase().includes(q))
      const matchesType = !type || m.type === type
      return matchesQuery && matchesType
    })
  }
})

export const mutations = mutationTree(state, {
  setMediaLibraries(state, libraries) {
    state.mediaLibraries = libraries
  },
  setMediaItems(state, items) {
    state.mediaItems = items
  },
  upsertMediaLibrary(state, library) {
    const idx = state.mediaLibraries.findIndex(l => l.id === library.id)
    if (idx >= 0) {
      state.mediaLibraries = state.mediaLibraries.map((l, i) => i === idx ? { ...l, ...library } : l)
    } else {
      state.mediaLibraries = [...state.mediaLibraries, library]
    }
    persist(state)
  },
  removeMediaLibrary(state, libraryId) {
    const library = state.mediaLibraries.find(l => l.id === libraryId)
    if (library) {
      // Remove associated media items
      state.mediaItems = state.mediaItems.filter(m => !library.mediaItems.includes(m.id))
    }
    state.mediaLibraries = state.mediaLibraries.filter(l => l.id !== libraryId)
    persist(state)
  },
  upsertMediaItem(state, item) {
    const idx = state.mediaItems.findIndex(m => m.id === item.id)
    if (idx >= 0) {
      state.mediaItems = state.mediaItems.map((m, i) => i === idx ? { ...m, ...item } : m)
    } else {
      state.mediaItems = [...state.mediaItems, item]
    }
    persist(state)
  },
  removeMediaItem(state, mediaId) {
    state.mediaItems = state.mediaItems.filter(m => m.id !== mediaId)
    // Remove from libraries
    state.mediaLibraries = state.mediaLibraries.map(l => ({
      ...l,
      mediaItems: l.mediaItems.filter(id => id !== mediaId)
    }))
    persist(state)
  },
  addMediaToLibrary(state, { libraryId, mediaId }) {
    state.mediaLibraries = state.mediaLibraries.map(l => {
      if (l.id !== libraryId) return l
      if (!l.mediaItems.includes(mediaId)) {
        return { ...l, mediaItems: [...l.mediaItems, mediaId] }
      }
      return l
    })
    persist(state)
  },
  removeMediaFromLibrary(state, { libraryId, mediaId }) {
    state.mediaLibraries = state.mediaLibraries.map(l => {
      if (l.id !== libraryId) return l
      return { ...l, mediaItems: l.mediaItems.filter(id => id !== mediaId) }
    })
    persist(state)
  },
  setUploadProgress(state, { mediaId, progress }) {
    state.uploadProgress = { ...state.uploadProgress, [mediaId]: progress }
  },
  removeUploadProgress(state, mediaId) {
    const { [mediaId]: _, ...rest } = state.uploadProgress
    state.uploadProgress = rest
  }
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    init({ state }) {
      const saved = load()
      if (saved.mediaLibraries) {
        state.mediaLibraries = saved.mediaLibraries
        state.mediaItems = saved.mediaItems || []
      }
    },

    // ── Media Libraries ───────────────────────────────────────────────────────
    createLibrary({ commit }, { name, description = '', resourceType, resourceId }) {
      const library = createMediaLibrary({
        name,
        description,
        type: resourceType,
        resourceId
      })
      commit('upsertMediaLibrary', library)
      return library
    },

    updateLibrary({ commit }, library) {
      commit('upsertMediaLibrary', library)
    },

    deleteLibrary({ commit }, libraryId) {
      commit('removeMediaLibrary', libraryId)
    },

    // ── Media Items ───────────────────────────────────────────────────────────
    async uploadMedia({ state, commit }, { 
      file = null, 
      url = null, 
      libraryId, 
      name = null,
      tags = [],
      resourceType = null,
      resourceId = null
    }) {
      const mediaId = crypto.randomUUID()
      const fileName = name || file?.name || 'media'
      
      try {
        // Determine media type and create item
        let mimeType = file?.type || ''
        let mediaType = 'other'
        let metadata = {}

        if (mimeType.startsWith('image/')) {
          mediaType = 'image'
        } else if (mimeType.startsWith('video/')) {
          mediaType = 'video'
        } else if (mimeType.startsWith('audio/')) {
          mediaType = 'audio'
        } else if (mimeType.includes('pdf') || mimeType.includes('document')) {
          mediaType = 'document'
        }

        // Handle file upload
        let finalUrl = url
        if (file) {
          commit('setUploadProgress', { mediaId, progress: 0 })
          
          // Simulate file upload with progress
          const uploadPromise = new Promise((resolve) => {
            const reader = new FileReader()
            reader.onloadstart = () => commit('setUploadProgress', { mediaId, progress: 10 })
            reader.onprogress = (e) => {
              const progress = Math.round((e.loaded / e.total) * 90) + 10
              commit('setUploadProgress', { mediaId, progress })
            }
            reader.onload = () => {
              // In real app, send to server
              finalUrl = reader.result
              commit('setUploadProgress', { mediaId, progress: 100 })
              setTimeout(() => {
                commit('removeUploadProgress', mediaId)
              }, 500)
              resolve(finalUrl)
            }
            reader.readAsDataURL(file)
          })
          
          finalUrl = await uploadPromise
          
          // Extract metadata
          if (mediaType === 'image') {
            const img = new Image()
            img.onload = () => {
              metadata = { width: img.width, height: img.height }
            }
            img.src = finalUrl
          }
        }

        const mediaItem = createMediaItem({
          name: fileName,
          type: mediaType,
          url: finalUrl,
          mimeType,
          size: file?.size || 0,
          tags,
          resourceType,
          resourceId,
          metadata
        })

        commit('upsertMediaItem', mediaItem)

        // Add to library if provided
        if (libraryId) {
          commit('addMediaToLibrary', { libraryId, mediaId: mediaItem.id })
        }

        return mediaItem
      } catch (error) {
        commit('removeUploadProgress', mediaId)
        console.error('[media] upload error:', error)
        throw error
      }
    },

    updateMediaItem({ commit }, mediaItem) {
      commit('upsertMediaItem', mediaItem)
    },

    deleteMediaItem({ commit }, mediaId) {
      commit('removeMediaItem', mediaId)
    },

    addToLibrary({ commit }, { libraryId, mediaId }) {
      commit('addMediaToLibrary', { libraryId, mediaId })
    },

    removeFromLibrary({ commit }, { libraryId, mediaId }) {
      commit('removeMediaFromLibrary', { libraryId, mediaId })
    }
  }
)