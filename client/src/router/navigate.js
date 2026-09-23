export default function Navigate({ $router, $storex }) {

  const routes = { 
    kanban: {
      board({ project: { project_name }, board }) {
        return `/${project_name}/kanban/${board}`
      }
    }
  }

  function getArgs(func) { 
    return function(args) {
      const newArgs = { ...args, project: args.project || $storex.projects.activeProject }
      return func.call(this, newArgs)
    }
  }

  let historyRegistered = false

  const $navigator = {
    get activeProject() {
      return $storex.projects.activeProject
    },
    init() {
      // 1. Check if this is the first page in the tab's session history
      if (window.history.length === 1) {
        
        // 2. Replace the current history entry with the root URL
        window.history.replaceState(null, '', '/');
        
        // 3. Push the current page on top of the root URL
        window.history.pushState(null, '', window.location.href);
      }
    },
    async onRouteChanged({ from, to }) {

      // ── OAuth callback ──────────────────────────────────────────────
      if (to.path.startsWith('/auth')) {
        const { code, state } = to.query
        const provider = to.path.split('/').reverse()[0]

        if (!provider || !code) {
          $storex.session.onError('Missing OAuth provider or code')
          return '/'
        }

        try {
          await $storex.users.oauthLogin({ provider, code, state })
          return '/'
        } catch (error) {
          $storex.session.onError('Failed to complete OAuth login')
          return '/'
        }
      }

      // ── Standalone routes has name (opt-out of mobile/desktop redirect) ─────
      if (!!to.name) {
        return true
      }

      // ── Mobile redirect ─────────────────────────────────────────────
      if ($storex.ui.isMobile && to.name !== 'mobile') {
        return { name: 'mobile', replace: true }
      }

      // ── Desktop: redirect /mobile → home ───────────────────────────
      if (!$storex.ui.isMobile && to.name === 'mobile') {
        return { name: 'home', replace: true }
      }

      return true
    },
    kanban: {
      board: getArgs(async function(args) {
        const { project, board } = args
        if (project !== $navigator.activeProject) {
          await $storex.projects.activeProjectChanged(project)
        }
        $storex.projects.setActiveBoard(board)
        $storex.ui.showTab('tasks')
        $router.push(routes.kanban.board(args))
      })
    }
  }
  return $navigator
}