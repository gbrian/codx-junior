/**
 * Tools Model
 * Represents available tools with their definitions and metadata
 */

export default {
  /**
   * Extract unique tags from tools list
   * @param {Array} tools - Array of tool objects with tags property
   * @returns {Array} - Sorted array of unique tags
   */
  extractTags(tools = []) {
    const tagsSet = new Set()
    tools.forEach(tool => {
      if (tool.tags && Array.isArray(tool.tags)) {
        tool.tags.forEach(tag => tagsSet.add(tag))
      }
    })
    return Array.from(tagsSet).sort()
  },

  /**
   * Get tools by tag(s)
   * @param {Array} tools - Array of tool objects
   * @param {Array|String} tags - Single tag or array of tags to filter by
   * @param {Boolean} matchAll - If true, tool must have ALL tags; if false, ANY tag
   * @returns {Array} - Filtered tools
   */
  getToolsByTags(tools = [], tags = [], matchAll = true) {
    if (!tags || (Array.isArray(tags) && tags.length === 0)) {
      return tools
    }

    const tagsArray = Array.isArray(tags) ? tags : [tags]

    return tools.filter(tool => {
      if (!tool.tags || !Array.isArray(tool.tags)) return false
      
      if (matchAll) {
        return tagsArray.every(tag => tool.tags.includes(tag))
      } else {
        return tagsArray.some(tag => tool.tags.includes(tag))
      }
    })
  },

  /**
   * Get profiles that use tool(s) with specific tag(s)
   * @param {Array} profiles - Array of profile objects
   * @param {Array} tools - Array of tool objects
   * @param {Array} selectedTags - Tags to filter by
   * @returns {Array} - Filtered profiles
   */
  getProfilesByToolTags(profiles = [], tools = [], selectedTags = []) {
    if (!selectedTags || selectedTags.length === 0) {
      return profiles
    }

    const toolsByTag = this.getToolsByTags(tools, selectedTags, false)
    const toolNames = toolsByTag.map(t => t.tool_json?.function?.name).filter(Boolean)

    return profiles.filter(profile => {
      if (!profile.tools || !Array.isArray(profile.tools)) return false
      return profile.tools.some(tool => toolNames.includes(tool))
    })
  }
}