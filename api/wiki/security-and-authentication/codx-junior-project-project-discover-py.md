This document describes functions for discovering and managing projects within the `codx-api` system.

### Project Discovery

The primary functions for finding projects are:

*   **`find_all_projects()`**: This function discovers all projects by searching for `.codx` directories and `project.json` files. It uses a background thread (`_update_all_projects`) to perform this search asynchronously and caches the results.
    ```python /codx/junior/project/project_discover.py
    def find_all_projects():
        global _ALL_PROJECTS_PROC
        global _ALL_PROJECTS

        if not _ALL_PROJECTS_PROC:
            _ALL_PROJECTS_PROC = Thread(target=_update_all_projects)
            _ALL_PROJECTS_PROC.start()

        if not _ALL_PROJECTS and _ALL_PROJECTS_PROC:
            logger.info("Waiting for _ALL_PROJECTS_PROC")
            _ALL_PROJECTS_PROC.join(timeout=60)

        return _ALL_PROJECTS
    ```
*   **`find_project_from_file_path(file_path: str)`**: Given a file path, this function identifies the parent project to which the file belongs. It checks if the file path starts with either the project's general path or its `.codx` path.
    ```python /codx/junior/project/project_discover.py
    def find_project_from_file_path(file_path: str):
        """Given a file path, find the project parent"""
        all_projects = find_all_projects().values()
        matches = [p for p in all_projects if file_path.startswith(p.project_path) or \
                                                    file_path.startswith(p.codx_path)]
        if matches:
            logger.info(f"Find projects for file {file_path}: {[m.project_name for m in matches]}")
            return sorted(matches, key=lambda p: len(p.project_path))[-1]
        return None
    ```
*   **`find_project_by_id(project_id: str)`**: Retrieves a project using its unique `project_id`.
    ```python /codx/junior/project/project_discover.py
    def find_project_by_id(project_id: str):
        """Given a project id, find the project"""
        all_projects = find_all_projects().values()
        matches = [p for p in all_projects if p.project_id == project_id]
        return matches[0] if matches else None
    ```
*   **`find_project_by_project_path(project_path: str)`**: Finds a project based on its file system path.
    ```python /codx/junior/project/project_discover.py
    def find_project_by_project_path(project_path: str):
        """Given a project id, find the project"""
        all_projects = find_all_projects().values()
        matches = [p for p in all_projects if p.project_path == project_path]
        return matches[0] if matches else None
    ```
*   **`find_project_by_name(project_name: str)`**: Locates a project by its `project_name`.
    ```python /codx/junior/project/project_discover.py
    def find_project_by_name(project_name: str):
        """Given a project project_name, find the project"""
        all_projects = find_all_projects().values()
        matches = [p for p in all_projects if p.project_name == project_name]
        project = matches[0] if matches else None
        logger.exception("find_project_by_name '%s' not found", project_name)
        return project
    ```
*   **`find_all_user_projects(user: CodxUser)`**: Returns all projects accessible by a specific `CodxUser`. This function considers user permissions managed by `UserSecurityManager`.
    ```python /codx/junior/project/project_discover.py
    def find_all_user_projects(user: CodxUser):
        user_security_manager = UserSecurityManager()
        all_projects = find_all_projects().values()
        def find_parent(project_path):
            all_parents = [p for p in all_projects \
                            if project_path.startswith(p.project_path) and \
                              project_path != p.project_path]
            all_parents.sort(key=lambda p: p.project_path)
            return all_parents[-1] if all_parents else None

        for settings in all_projects:
            current_settings = settings
            while current_settings:
                permissions = user_security_manager.get_user_project_access(user=user, settings=current_settings)
                if permissions:
                    yield CODXJuniorProject(** {
                        **settings.__dict__,
                        "permissions": permissions
                    })
                    current_settings = None
                else:
                    current_settings_name = current_settings.project_name
                    current_settings = find_parent(current_settings.project_path)
    ```
*   **`find_project_parents(project: CODXJuniorSettings, user: CodxUser = None)`**: Identifies all parent projects for a given project. If a `user` is provided, it filters parents based on user access.
    ```python /codx/junior/project/project_discover.py
    def find_project_parents(project: CODXJuniorSettings, user: CodxUser = None):
        all_user_projects = find_all_user_projects(user) if user else find_all_projects().values()
        project_path = project.project_path
        all_parents = [p for p in all_user_projects if project_path.startswith(p.project_path) and project_path != p.project_path]
        return sorted(all_parents, key=lambda project: len(project.project_path))
    ```
*   **`find_active_projects()`**: Returns projects that have been accessed within the last 30 minutes.

### Internal Project Discovery (`_update_all_projects`)

This private function is responsible for the core project discovery logic. It:
1.  Determines the root path for projects.
2.  Uses the `find` command to locate all `.codx` directories.
3.  Filters these paths to ensure they contain a `project.json` file.
4.  Iterates through each valid project file:
    *   Checks read/write permissions for the `project.json` file.
    *   Loads project settings using `CODXJuniorSettings.from_project_file`.
    *   Validates the project settings, prioritizing projects within the defined `projects_root_path` in case of duplicates.
    *   Retrieves users with access to the project via `UserSecurityManager`.
    *   Calculates project metrics using `CODXJuniorMetrics`.
    *   Stores valid projects in a dictionary keyed by `project_id`.
5.  Updates the global `_ALL_PROJECTS` variable with the discovered projects.

```python /codx/junior/project/project_discover.py
@profile_function
def _update_all_projects():
    global _ALL_PROJECTS_PROC
    global _ALL_PROJECTS

    all_projects = {}
    projects_root_path = get_projects_root_path()
    user_security_manager = UserSecurityManager()
    project_path = "/"
    result = subprocess.run("find / -name .codx".split(" "), cwd=project_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    all_codx_path = result.stdout.decode('utf-8').split("\n")
    paths = [p for p in all_codx_path if os.path.isfile(f"{p}/project.json")]

    logger.info(f"[find_all_projects] projects root path: {projects_root_path}")
    logger.info(f"[find_all_projects] found {len(paths)} project files")

    def is_valid_project(settings):
        if not settings or not settings.project_name:
            return False
        existing_project = all_projects.get(settings.project_id, None)
        if existing_project and existing_project.project_path.startswith(projects_root_path):
            # EDGE CASE: In case of duplicates, give preference to projects in the "projects_root_path" folder
            return False
        return True

    for codx_path in paths:
        try:
            project_file_path = f"{codx_path}/project.json"
            # Check read/write permissions
            if not (os.access(project_file_path, os.R_OK) and os.access(project_file_path, os.W_OK)):
                logger.warning(f"Skipping {project_file_path} due to insufficient permissions")
                continue

            settings = CODXJuniorProject(**CODXJuniorSettings.from_project_file(project_file_path).__dict__)
            if is_valid_project(settings):
                project_users = user_security_manager.get_users_with_project_access(project_id=settings.project_id)
                settings.users = project_users
                settings.metrics = CODXJuniorMetrics(settings=settings).project_metrics()

                # logger.info("Project %s users: %s", settings.project_name, settings.users)
                all_projects[settings.project_id] = settings
            else:
                # logger.error(f"Error duplicate project at: {settings.project_path} at {project_exists[0].project_path}")
                pass
        except Exception as ex:
            logger.exception(f"Error loading project {str(codx_path)} : {ex}")
    _ALL_PROJECTS = all_projects
    # logger.info("All projects: %s", _ALL_PROJECTS)
    _ALL_PROJECTS_PROC = None
```

### Project Dependencies

*   **`get_project_dependencies(settings: CODXJuniorSettings)`**: This function returns the direct child projects and any other projects that the given project depends on, based on the `project.json` configuration.
    ```python /codx/junior/project/project_discover.py
    def get_project_dependencies(settings: CODXJuniorSettings):
        """Returns all projects related with this project, including child projects and links"""
        project_child_projects = settings.get_sub_projects()
        project_dependencies = [find_project_by_name(project_name) for project_name in settings.get_project_dependencies()]
        return project_child_projects, project_dependencies
    ```