
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
      const newArgs = { ...args, project: args.project || $storex.projects.activeProject };
      return func.call(this, newArgs);
    };
  }

  const $navigator = {
    get activeProject() {
      return $storex.projects.activeProject
    },
    async onRouteChanged({ from, to, next }) {
      if (to.path.startsWith("/auth")) {
        const { code, state } = to.query
        const provider = to.path.split("/").reverse()[0]

        if (!provider || !code) {
          $storex.session.onError("Missing OAuth provider or code");
          return next('/');
        }

        try {
          await $storex.users.oauthLogin({ provider, code, state });
          next('/');
        } catch (error) {
          $storex.session.onError("Failed to complete OAuth login");
          next('/');
        }
      } else {
        next()
      }
    },
    kanban: {
      board: getArgs(async function(args) {
        const { project, board } = args;
        if (project !== $navigator.activeProject) {
          await $storex.projects.setActiveProject(project);
        }
        $storex.projects.setActiveBoard(board);
        $storex.ui.showTab('tasks');
        $router.push(routes.kanban.board(args));
      })
    }
  }
  return $navigator
}