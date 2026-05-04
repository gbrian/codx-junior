import Service from "./service"

export class WikiService extends Service {
  async rebuild() {
    await this.$session.emit({ event: 'codx-junior-wiki-rebuild' })
  }

  buildStep(step) {
    this.$api.get(`/api/wiki-engine/build?step=${step}`)
  }
  
  getCategories() {
    return this.$api.get('/api/wiki-engine/categories')
  }

  getConfig() {
    return this.$api.get('/api/wiki-engine/config')
  }
}
