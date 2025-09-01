import os
import logging
import subprocess

from threading import Thread

from codx.junior.profiling.profiler import profile_function

from codx.junior.security.user_management import UserSecurityManager
from codx.junior.settings import CODXJuniorSettings
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
    
    logger.info("find_all_projects: %s", _ALL_PROJECTS)
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
    for settings in find_all_projects().values():
        permissions = user_security_manager.get_user_project_access(user=user, settings=settings)
        if permissions:
            yield {
                **settings.__dict__,
                "permissions": permissions
            }   

def get_project_dependencies(settings: CODXJuniorSettings):
    """Returns all projects related with this project, including child projects and links"""
    project_child_projects = self.settings.get_sub_projects()
    project_dependencies = [find_project_by_name(project_name) for project_name in self.settings.get_project_dependencies()]
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
    #logger.info(f"[find_all_projects] paths: {paths}")
    def is_valid_project(settings):
        if not settings or not settings.project_name:
            return False
        if [p for p in all_projects.values() if p.project_name == settings.project_name]:
            return False
        return True

    for codx_path in paths:
        try:
            project_file_path = f"{codx_path}/project.json"
            settings = CODXJuniorSettings.from_project_file(project_file_path)
            if is_valid_project(settings):
                all_projects[settings.project_id] = settings
                settings.__dict__["users"] = user_security_manager.get_users_with_project_access(project_id=settings.project_id)
            else:
                # logger.error(f"Error duplicate project at: {settings.project_path} at {project_exists[0].project_path}")
                pass 
        except Exception as ex:
            logger.exception(f"Error loading project {str(codx_path)} : {ex}")
    _ALL_PROJECTS = all_projects
    _ALL_PROJECTS_PROC = None