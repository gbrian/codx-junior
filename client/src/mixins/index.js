export const global = {
  computed: {
    $ui () {
      return this.$storex.ui
    },
    $project () {
      return this.$storex.project
    },
    $session () {
      return this.$storex.session
    },
    lastSettings () {
      return this.$storex.project.activeProject
    }
  }
}
