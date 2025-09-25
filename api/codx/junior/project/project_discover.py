import os
import logging
import subprocess

from threading import Thread

from codx.junior.profiling.profiler import profile_function

from codx.junior.security.user_management import UserSecurityManager
from codx.junior.settings import CODXJuniorSettings, CODXJuniorProject
from codx.junior.model.model import CodxUser

logger = logging.getLogger(__name__)

_ALL_PROJECTS = None
_ALL_PROJECTS_PROC = None
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

def find_project_from_file_path(file_path: str):
    """Given a file path, find the project parent"""
    all_projects = find_all_projects().values()
    matches = [p for p in all_projects if file_path.startswith(p.project_path)]
    if matches:
        logger.info(f"Find projects for file {file_path}: {[m.project_name for m in matches]}")
        return sorted(matches, key=lambda p: len(p.project_path))[-1]
    return None
  
def find_project_by_id(project_id: str):
    """Given a project id, find the project"""
    all_projects = find_all_projects().values()
    matches = [p for p in all_projects if p.project_id == project_id]
    return matches[0] if matches else None

def find_project_by_project_path(project_path: str):
    """Given a project id, find the project"""
    all_projects = find_all_projects().values()
    matches = [p for p in all_projects if p.project_path == project_path]
    return matches[0] if matches else None

def find_project_by_name(project_name: str):
    """Given a project project_name, find the project"""
    all_projects = find_all_projects().values()
    matches = [p for p in all_projects if p.project_name == project_name]
    return matches[0] if matches else None

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

def get_project_dependencies(settings: CODXJuniorSettings):
    """Returns all projects related with this project, including child projects and links"""
    project_child_projects = settings.get_sub_projects()
    project_dependencies = [find_project_by_name(project_name) for project_name in settings.get_project_dependencies()]
    return project_child_projects, project_dependencies

# private
@profile_function
def _update_all_projects():
    global _ALL_PROJECTS_PROC
    global _ALL_PROJECTS

    all_projects = {}
    user_security_manager = UserSecurityManager()
    project_path = "/"
    result = subprocess.run("find / -name .codx".split(" "), cwd=project_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    all_codx_path = result.stdout.decode('utf-8').split("\n")
    paths = [p for p in all_codx_path if os.path.isfile(f"{p}/project.json")]
    logger.info(f"[find_all_projects] found {len(paths)} project flies")
    def is_valid_project(settings):
        if not settings or not settings.project_name:
            return False
        if [p for p in all_projects.values() if p.project_name == settings.project_name]:
            return False
        return True

    for codx_path in paths:
        try:
            project_file_path = f"{codx_path}/project.json"
            settings = CODXJuniorProject(**CODXJuniorSettings.from_project_file(project_file_path).__dict__)
            if is_valid_project(settings):
                project_users = user_security_manager.get_users_with_project_access(project_id=settings.project_id)
                settings.users = project_users
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


def find_project_parents(project: CODXJuniorSettings, user: CodxUser = None):
    all_user_projects = find_all_user_projects(user) if user else find_all_projects().values()
    project_path = project.project_path
    all_parents = [p for p in all_user_projects if project_path.startswith(p.project_path)]
    return all_parents
