/**
 * Chat Search Request Model
 * 
 * Encapsulates all search parameters and settings for the /api/chats/search endpoint.
 * Provides validation, serialization, and convenience methods for chat search operations.
 */
export class ChatSearchRequest {
  constructor(options = {}) {
    this.query = options.query || ''
    this.from_date = options.from_date || null
    this.to_date = options.to_date || null
    this.page = Math.max(1, options.page || 1)
    this.page_size = Math.max(1, Math.min(100, options.page_size || 20))
    
    // Search field filters - all default to true
    this.filters = {
      search_name: options.filters?.search_name ?? true,
      search_description: options.filters?.search_description ?? true,
      search_messages: options.filters?.search_messages ?? true,
      search_message_metadata: options.filters?.search_message_metadata ?? true,
      search_history: options.filters?.search_history ?? true,
      search_files: options.filters?.search_files ?? true,
      search_model: options.filters?.search_model ?? true,
      search_status: options.filters?.search_status ?? true,
      search_mode: options.filters?.search_mode ?? true
    }
  }

  /**
   * Validate search query
   */
  isValid() {
    return this.query && this.query.trim().length > 0
  }

  /**
   * Get validation errors
   */
  getValidationErrors() {
    const errors = []
    if (!this.query || this.query.trim().length === 0) {
      errors.push('Query cannot be empty')
    }
    if (this.page < 1) {
      errors.push('Page must be at least 1')
    }
    if (this.page_size < 1 || this.page_size > 100) {
      errors.push('Page size must be between 1 and 100')
    }
    if (this.from_date && this.to_date) {
      const from = new Date(this.from_date)
      const to = new Date(this.to_date)
      if (from > to) {
        errors.push('From date must be before to date')
      }
    }
    return errors
  }

  /**
   * Check if any filters are enabled
   */
  hasAnyFilters() {
    return Object.values(this.filters).some(v => v === true)
  }

  /**
   * Check if all filters are enabled
   */
  allFiltersEnabled() {
    return Object.values(this.filters).every(v => v === true)
  }

  /**
   * Toggle a specific filter
   */
  setFilter(filterName, enabled) {
    if (filterName in this.filters) {
      this.filters[filterName] = enabled
    }
    return this
  }

  /**
   * Enable all filters
   */
  enableAllFilters() {
    Object.keys(this.filters).forEach(key => {
      this.filters[key] = true
    })
    return this
  }

  /**
   * Disable all filters
   */
  disableAllFilters() {
    Object.keys(this.filters).forEach(key => {
      this.filters[key] = false
    })
    return this
  }

  /**
   * Move to next page
   */
  nextPage() {
    this.page += 1
    return this
  }

  /**
   * Move to previous page
   */
  previousPage() {
    if (this.page > 1) {
      this.page -= 1
    }
    return this
  }

  /**
   * Reset to first page
   */
  resetPage() {
    this.page = 1
    return this
  }

  /**
   * Serialize to JSON for API request
   */
  toJSON() {
    return {
      query: this.query,
      from_date: this.from_date || undefined,
      to_date: this.to_date || undefined,
      page: this.page,
      page_size: this.page_size,
      filters: this.allFiltersEnabled() ? undefined : this.filters
    }
  }

  /**
   * Create from JSON response
   */
  static fromJSON(json) {
    return new ChatSearchRequest(json)
  }

  /**
   * Clone this request
   */
  clone() {
    return new ChatSearchRequest(this.toJSON())
  }
}

export default ChatSearchRequest