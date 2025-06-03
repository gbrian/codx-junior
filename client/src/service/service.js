export default class Service {
  constructor($storex) {
    this.$storex = $storex
  }
  
  get api() {
    return $storex.api
  }
  get $projects() {
    return $storex.projects
  }
  get project() {
    return $storex.projects.activeProject
  }
  get session() {
    return $storex.session
  }
  get user() {
    return $storex.api.user
  }
  get users() {
    return $storex.users
  }
  get globalSettings() {
    return $storex.api.globalSettings
  }
}