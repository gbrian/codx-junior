/**
 * Files API module
 * Handles file operations: list, read, search, upload
 */

export const filesModule = (API) => ({
  list(path) {
    return API.get(`/api/files?path=${encodeURIComponent(path)}`)
  },

  read(path) {
    return API.get(`/api/files/read?path=${encodeURIComponent(path)}`)
  },

  search({ search, searchPath, page = 0, pageSize = 50, rawSearch = false, useRegex = false }) {
    const params = new URLSearchParams()
    params.append('search', search)
    if (searchPath) {
      params.append('search_path', searchPath)
    }
    params.append('page', page)
    params.append('page_size', pageSize)
    params.append('raw_search', rawSearch)
    params.append('use_regex', useRegex)
    return API.get(`/api/files/search?${params.toString()}`)
  },

  searchContent({ query, searchPath, page = 0, pageSize = 50, caseSensitive = false, rawSearch = false, useRegex = false }) {
    const params = new URLSearchParams()
    params.append('q', query)
    if (searchPath) {
      params.append('search_path', searchPath)
    }
    params.append('page', page)
    params.append('page_size', pageSize)
    params.append('case_sensitive', caseSensitive)
    params.append('raw_search', rawSearch)
    params.append('use_regex', useRegex)
    return API.get(`/api/files/search-content?${params.toString()}`)
  },

  upload(file, path, process = false) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('path', path)
    formData.append('process', process)
    return API.post(`/api/files/upload`, formData)
  },

  uploadMultiple(files, process = false) {
    const formData = new FormData()
    files.forEach((file) => {
      formData.append('files', file)
    })
    formData.append('process', process)
    return API.post(`/api/files/upload-multiple`, formData)
  },

  diff({ path, content, from_branch, to_branch }) {
    return API.post(`/api/files/diff`, {
      path,
      content,
      from_branch: from_branch || null,
      to_branch: to_branch || null
    })
  },

  write(source, page_content) {
    return API.post(`/api/files/write?path=${encodeURIComponent(source)}`, { page_content, metadata: { source } })
  },

  reset(source) {
    return API.get(`/api/files/reset?path=${encodeURIComponent(source)}`)
  }
})