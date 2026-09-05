class MCPServer {
  constructor(data = {}) {
    this.id = data.id || null
    this.name = data.name || ''
    this.url = data.url || ''
    this.api_key = data.api_key || ''
    this.active = data.active !== undefined ? data.active : true
  }

  isValid() {
    return this.name && this.url
  }

  toJSON() {
    return {
      id: this.id,
      name: this.name,
      url: this.url,
      api_key: this.api_key,
      active: this.active
    }
  }

  static fromJSON(data) {
    return new MCPServer(data)
  }
}

export default MCPServer