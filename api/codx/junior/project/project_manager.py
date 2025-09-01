import logging
from multiprocessing import Process

from codx.junior.security.user_management import UserSecurityManager
from codx.junior.settings import CODXJuniorSettings
from codx.junior.engine import CODXJuniorSession
from codx.junior.model.model import CodxUser
    
logger = logging.getLogger(__name__)
    
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
