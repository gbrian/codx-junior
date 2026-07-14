import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from codx.junior.workspaces.model import Workspace
from codx.junior.project.project_discover import find_all_projects
from codx.junior.workspaces.engines.compose import DockerComposeEngine

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"

AVAILABLE_TEMPLATES = {
    "static-site": "Single container running a web site / dev server (e.g. Vue)",
    "dev-stack": "Sysbox container with systemd + inner Docker for full-stack development",
    "custom": "Empty workspace, admin provides all files",
}


def get_project_mounts(workspace: Workspace) -> list[dict]:
    """
    Resolve host paths for the workspace's projects.

    Only the projects listed in workspace.project_ids are mounted — never
    the whole projects folder. project_ids == ["*"] mounts all projects.
    Projects are identity-mounted (same path inside the container) to match
    the default workspace convention.
    """
    all_projects = find_all_projects() or {}  # Dict[project_id, CODXJuniorSettings]

    if "*" in workspace.project_ids:
        projects = list(all_projects.values())
    else:
        projects = [
            all_projects[pid] for pid in workspace.project_ids
            if pid in all_projects
        ]

    return [
        {
            "project_id": project.project_id,
            "host_path": project.abs_project_path,
            "container_path": project.abs_project_path,
        }
        for project in projects
    ]

def render_template(workspace: Workspace, target_dir: Path) -> None:
    """Render the workspace template into target_dir."""
    if workspace.template == "custom":
        target_dir.mkdir(parents=True, exist_ok=True)
        return

    template_dir = TEMPLATES_DIR / workspace.template
    if not template_dir.exists():
        raise ValueError(f"Unknown workspace template: {workspace.template}")

    env = Environment(loader=FileSystemLoader(str(template_dir)), keep_trailing_newline=True)
    context = {
        "workspace": workspace,
        "projects": get_project_mounts(workspace),
        "traefik_labels": DockerComposeEngine.traefik_labels,
    }

    target_dir.mkdir(parents=True, exist_ok=True)
    for file in template_dir.rglob("*"):
        if not file.is_file():
            continue
        rel = file.relative_to(template_dir)
        dest = target_dir / str(rel).removesuffix(".j2")
        dest.parent.mkdir(parents=True, exist_ok=True)
        if file.suffix == ".j2":
            dest.write_text(env.get_template(str(rel)).render(**context))
        else:
            dest.write_bytes(file.read_bytes())
        logger.info("Rendered %s -> %s", rel, dest)    