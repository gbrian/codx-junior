import Service from "./service"

export class WikiService extends Service {
  async rebuild() {
    await this.$storex.session.emit({ event: 'codx-junior-wiki-rebuild' })
  }

  buildStep(step) {
    this.$storex.api.get(`/api/wiki-engine/build?step=${step}`)
  }
  
  getCategories() {
    return this.$storex.api.get('/api/wiki-engine/categories')
  }

  getConfig() {
    return this.$storex.api.get('/api/wiki-engine/config')
  }
}
