/**
 * Chat Search Response Model
 * 
 * Represents the response from the /api/chats/search endpoint.
 * Results are temporary and not persisted in the store state.
 */
export class ChatSearchResponse {
  constructor(data = {}) {
    this.results = data.results || []
    this.total = data.total || 0
    this.page = data.page || 1
    this.page_size = data.page_size || 20
    this.total_pages = data.total_pages || 0
    this.has_next = data.has_next || false
    this.has_prev = data.has_prev || false
    this.error = data.error || null
  }

  /**
   * Get search result at index
   */
  getResult(index) {
    return this.results[index] || null
  }

  /**
   * Get chat from result
   */
  getChatFromResult(index) {
    return this.getResult(index)?.chat || null
  }

  /**
   * Check if there are more pages to load
   */
  hasMorePages() {
    return this.has_next
  }

  /**
   * Check if this is the first page
   */
  isFirstPage() {
    return this.page === 1 && !this.has_prev
  }

  /**
   * Get next page number
   */
  getNextPage() {
    return this.has_next ? this.page + 1 : null
  }

  /**
   * Get previous page number
   */
  getPreviousPage() {
    return this.has_prev ? this.page - 1 : null
  }

  /**
   * Check if search has errors
   */
  hasError() {
    return !!this.error
  }

  /**
   * Get result summary
   */
  getSummary() {
    return {
      resultsCount: this.results.length,
      total: this.total,
      page: this.page,
      pageSize: this.page_size,
      totalPages: this.total_pages
    }
  }
}

export default ChatSearchResponse