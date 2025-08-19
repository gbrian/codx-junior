import os
import subprocess
import logging

from codx.junior.settings import CODXJuniorSettings, read_global_settings
from codx.junior.utils.utils import exec_command
from codx.junior.security.user_management import UserSecurityManager
from codx.junior.model.model import CodxUser
from codx.junior.db import Chat


"""Changed files older than MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS won't be processed"""
MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS = 60 * 60

CODX_JUNIOR_API_BACKGROUND = os.environ.get("CODX_JUNIOR_API_BACKGROUND")

logger = logging.getLogger(__name__)

APPS = [
    {
        "name": "chrome",
        "icon": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Google_Chrome_icon_%28February_2022%29.svg/768px-Google_Chrome_icon_%28February_2022%29.svg.png",
        "description": "Google chrome engine",
    }
]

APPS_COMMANDS = {
    "chrome": "google-chrome --no-sandbox --no-default-browser-check"
}

AGENT_DONE_WORD = "$$@@AGENT_DONE@@$$$"

def create_project(project_path: str, user: CodxUser):
    logger.info(f"Create new project {project_path}")
    global_settings = read_global_settings()
    projects_root_path = global_settings.projects_root_path or f"{os.environ['HOME']}/projects"
    os.makedirs(projects_root_path, exist_ok=True)

    repo_url = None 
    if project_path.startswith("http"):
        repo_url = project_path
        repo_name = repo_url.split("/")[-1].split(".")[0]
        project_path = f"{projects_root_path}/{repo_name}"
        command = f"git clone --depth=1 {repo_url} {project_path}"
        logger.info(f"Cloning repo {repo_url} {repo_name} {project_path}")
        exec_command(command=command)
    
    existing_project = find_project_by_project_path(project_path=project_path)
    if existing_project:
        logger.info(f"Project already exists {repo_url} {repo_name} {project_path}")
        return existing_project

    settings = CODXJuniorSettings()
    settings.project_name = project_path.split("/")[-1]
    settings.codx_path = f"{project_path}/.codx"
    settings.watching = True
    settings.repo_url = repo_url
    settings.save_project()
    if not os.path.isdir(os.path.join(project_path, ".git")):
        exec_command("git init", cwd=project_path)
    
    _, stderr = exec_command("git branch")
    new_project = CODXJuniorSettings.from_project_file(f"{project_path}/.codx/project.json")
    if user:
        UserSecurityManager().add_user_to_project(project_id=new_project.project_id, user=user, permissions='admin')
    return new_project


def coder_open_file(settings: CODXJuniorSettings, file_name: str):
    logger.info(f"coder_open_file {file_name}")
    os.system(f"code-server -r {file_name}")


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

def find_all_user_projects(user: CodxUser, with_metrics: bool = False):
    user_security_manager = UserSecurityManager()
    for settings in find_all_projects(with_metrics=with_metrics).values():
        permissions = user_security_manager.get_user_project_access(user=user, settings=settings)
        if permissions:
            yield {
                **settings.__dict__,
                "permissions": permissions
            }

def find_all_projects(with_metrics: bool = False):
    user_security_manager = UserSecurityManager()
    all_projects = {}
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
    
    def update_projects_with_details():
        for project in all_projects.values():
            try:
                project.__dict__["_metrics"] = CODXJuniorSession(settings=project).get_project_metrics()
            except Exception as ex:
                project.__dict__["_error"] = str(ex)
        return all_projects
    return update_projects_with_details() if with_metrics else all_projects

def update_engine():
    try:
        command = ["git", "pull"]
        subprocess.run(command)
    except Exception as ex:
        logger.exception(ex)
        return ex
