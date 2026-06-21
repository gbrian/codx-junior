import asyncio
import faulthandler
import logging
import hashlib
import os
import shutil
import time
import traceback
import uuid

import socketio
from flask import jsonify

from concurrent.futures import ThreadPoolExecutor

faulthandler.enable()

from codx.junior.ai import AIManager

from codx.junior.sio.sio import sio
from codx.junior.sio.session_channel import SessionChannel

from codx.junior.profiling.profiler import profile_function

from codx.junior.api.chatGPTLikeApi import router as chatgpt_router
from codx.junior.api.users import router as users_router
from codx.junior.api.wiki import router as wiki_router
from codx.junior.api.github import router as github_router
from codx.junior.api.file_finder import router as file_finder_router
from codx.junior.api.db_router import router as db_router
from codx.junior.api.global_settings import router as global_settings_router
from codx.junior.api.project_search import router as project_search
from codx.junior.api.knowledge import router as knowledge_router
from codx.junior.api.chat import router as chat_router
from codx.junior.api.views import router as views_router
from codx.junior.api.analytics import router as analytics_router
from codx.junior.api.logs import router as logs_router
from codx.junior.api.projects import router as projects_router


from codx.junior.security.user_management import get_authenticated_user

from codx.junior.chat.chat_export import ExportedDocument

from codx.junior.globals import LOGS_FOLDER


CODX_JUNIOR_API_BACKGROUND = os.environ.get("CODX_JUNIOR_API_BACKGROUND")

logger = logging.getLogger(__name__)

def disable_logs(logs):
  for logger_id in logs:
      logging.getLogger(logger_id).setLevel(logging.WARNING)

def enable_logs(logs):
  for logger_id in logs:
      logging.getLogger(logger_id).setLevel(logging.DEBUG)

disable_logs([
    'httpx',
    'httpcore.http11',
    'httpcore.connection',
    'openai._base_client',
    'watchfiles.main',
    'asyncio',
    'codx.junior.project_watcher',
    'selenium.webdriver.common.selenium_manager'
])

from fastapi import FastAPI, Request, status, Response, UploadFile, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from starlette.status import HTTP_504_GATEWAY_TIMEOUT

from contextlib import asynccontextmanager

from codx.junior.db import (
    Chat
)
from codx.junior.model.model import (
    KnowledgeReloadPath,
    KnowledgeSearch,
    KnowledgeDeleteSources,
    Profile,
    Document,
    GlobalSettings,
    Screen,
    CodxUser,
    AIModel
)

from codx.junior.settings import (
  CODXJuniorSettings
)
from codx.junior.global_settings import (
  read_global_settings,
  write_global_settings
)

from codx.junior.engine import (
    CODXJuniorSession
)

from codx.junior.project.project_discover import (
    find_all_projects,
    find_all_user_projects,  
)

from codx.junior.project.project_manager import (
    create_project,
)

from codx.junior.utils.utils import (
    exec_command,
)

from codx.junior.background import start_background_services, stop_background_services


CODX_JUNIOR_STATIC_FOLDER=os.environ.get("CODX_JUNIOR_STATIC_FOLDER")
IMAGE_UPLOAD_FOLDER = f"{CODX_JUNIOR_STATIC_FOLDER}/images"
os.makedirs(IMAGE_UPLOAD_FOLDER, exist_ok=True)

GLOBAL_REQUEST_TIMEOUT=280


app = FastAPI(
    title="CODXJuniorAPI",
    description="API for CODXJunior",
    version="1.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    ssl_context='adhoc'
)

sio_asgi_app = socketio.ASGIApp(sio, app, socketio_path="/api/socket.io")
app.mount("/api/socket.io", sio_asgi_app)

app.include_router(chatgpt_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(wiki_router, prefix="/api")
app.include_router(github_router, prefix="/api")
app.include_router(file_finder_router, prefix="/api")
app.include_router(db_router, prefix="/api")
app.include_router(global_settings_router, prefix="/api")
app.include_router(project_search, prefix="/api")
app.include_router(knowledge_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(views_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(logs_router, prefix="/api")
app.include_router(projects_router, prefix="/api")

APP_STOP_EVENT = asyncio.Event()
    
@app.on_event("startup")
async def startup_event():
    start_background_services(APP_STOP_EVENT)
    logger.info("FASTAPI startup")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("FASTAPI shutdown")
    APP_STOP_EVENT.set()
    await stop_background_services()
    
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
	exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
	logger.error(f"%s: %s", request, exc_str)
	content = {'status_code': 10422, 'message': exc_str, 'data': None}
	return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

@app.on_event("startup")
def startup_event():
    logger.info("Creating FASTAPI (BACKGROUND: %s): %s", CODX_JUNIOR_API_BACKGROUND, app.__dict__)

@app.exception_handler(Exception)
async def my_exception_handler(request: Request, ex: Exception):
    return JSONResponse(status_code=500, 
        content=traceback.format_exception(ex))

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    process_time = None
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    finally:
        logger.info("Request %s - %d ms", request.url, time.time() - start_time)


def get_codx_junior_session(request, codx_path):
    user = get_authenticated_user(request=request)
    sid = request.headers.get("x-sid")
    channel = SessionChannel(sid=sid, sio=sio)
    return CODXJuniorSession(codx_path=codx_path, 
                              channel=channel,
                              user=user)

@app.middleware("http")
async def add_codx_junior_settings(request: Request, call_next):
    codx_path = request.query_params.get("codx_path")
    if codx_path and codx_path not in ["undefined", "null"]:
        try:
            codx_path = request.query_params.get("codx_path")
            codx_path = request.headers.get("x-codx-path", codx_path)
            request.state.codx_junior_session = get_codx_junior_session(request, codx_path)
            request.state.codx_junior_session.update_last_access_time()
        except Exception as ex:
            logger.error("Error loading settings %s: %s\n%s", codx_path, ex, request.url)
    return await call_next(request)

# Adding a middleware returning a 504 error if the request processing time is above a certain threshold
@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    try:
        start_time = time.time()
        logger.info("HTTP starting: %s", request.url)
        return await asyncio.wait_for(call_next(request), timeout=GLOBAL_REQUEST_TIMEOUT)

    except asyncio.TimeoutError:
        process_time = time.time() - start_time
        return JSONResponse({'detail': 'Request processing time exceeded limit',
                             'processing_time': process_time},
                            status_code=HTTP_504_GATEWAY_TIMEOUT)

@app.get("/api/health")
def api_health_check():
    return "ok"

@app.post("/api/run/improve")
async def api_run_improve(chat: Chat, request: Request):
    codx_junior_session = request.state.codx_junior_session
    await codx_junior_session.improve_existing_code(chat=chat)
    await codx_junior_session.save_chat(chat)
    return chat

@app.post("/api/run/improve/patch")
async def api_run_improve_patch(data: dict, request: Request):
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.apply_patch(patch=data["patch"])

@app.get("/api/run/changes/summary")
def api_changes_summary(request: Request):
    codx_junior_session = request.state.codx_junior_session
    refresh = request.query_params.get("refresh")
    return codx_junior_session.build_code_changes_summary(force=refresh == "true")

@app.get("/api/test/sio")
def test_sio(request: Request):
    codx_junior_session = request.state.codx_junior_session
    message = request.query_params.get("message") or "sio_test"
    return codx_junior_session.send_event(message=message)

@app.get("/api/settings")
def api_settings_check(request: Request):
    logger.info("/api/settings")
    codx_junior_session = request.state.codx_junior_session
    codx_junior_session.check_project()
    return codx_junior_session.settings

@app.put("/api/settings")
async def api_save_settings(request: Request):
    settings = await request.json()
    settings = CODXJuniorSettings.from_json(settings).save_project()
    find_all_projects()
    return api_settings_check(request)

@app.get("/api/profiles")
def api_list_profile(request: Request):
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.list_profiles()

@app.get("/api/profiles/tools")
def api_list_profile_tools(request: Request):
    from codx.junior.tools import TOOLS
    return [t["tool_json"]["function"] for t in TOOLS]

@app.post("/api/profiles")
async def api_create_profile(profile: Profile, request: Request):
    codx_junior_session = request.state.codx_junior_session
    return await codx_junior_session.save_profile(profile=profile)
    
@app.get("/api/profiles/{profile_name}")
def api_read_profile(profile_name, request: Request):
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.read_profile(profile_name)

@app.delete("/api/profiles/{profile_name}")
def api_delete_profile(profile_name, request: Request):
    codx_junior_session = request.state.codx_junior_session
    codx_junior_session.delete_profile(profile_name)
    return

@app.get("/api/project/watch")
def api_project_watch(request: Request):
    codx_junior_session = request.state.codx_junior_session
    codx_junior_session.watch_project(True)
    find_all_projects()
    return { "OK": 1 }

@app.get("/api/projects")
def api_find_all_projects(request: Request, user: CodxUser = Depends(get_authenticated_user)):
    projects = list(find_all_user_projects(user))
    workspaces = read_global_settings().workspaces

    user_role = user.role

    def user_has_workspace_access(workspace) -> bool:
        """
        Check if the user has access to the workspace.
        - Admins always have access.
        - If workspace.user_ids is empty, all users have access.
        - Otherwise, only users whose username is in user_ids have access.
        """
        if user_role == "admin":
            return True
        if not workspace.user_ids:
            return True
        return user and user.username in workspace.user_ids

    user_workspaces = [w for w in workspaces \
        if user_has_workspace_access(w) and \
        ("*" in w.project_ids or next((p for p in projects if p.project_id in w.project_ids), None))] 

    if user_role != "admin":
        for workspace in user_workspaces:
            workspace.apps = [app for app in workspace.apps if not app.roles or user_role in app.roles]

    return {
        "projects": projects,
        "workspaces": user_workspaces
    }

@app.get("/api/projects/metrics")
async def api_chat_metrics(request: Request):
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.project_metrics()

@app.get("/api/projects/repo/branches")
def api_find_all_repo_branches(request: Request):
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.get_project_branches()

@app.get("/api/projects/repo/branch/commits")
def api_find_all_repo_branch_commits(request: Request):
    codx_junior_session = request.state.codx_junior_session
    branch = request.query_params.get("branch")
    return codx_junior_session.get_project_branch_commits(branch=branch)

@app.get("/api/projects/repo/changes")
def api_find_all_repo_changes(request: Request):
    codx_junior_session = request.state.codx_junior_session
    from_branch = request.query_params.get("from_branch")
    to_branch = request.query_params.get("to_branch")
    return codx_junior_session.get_repo_changes(from_branch=from_branch, to_branch=to_branch)

@app.get("/api/projects/readme")
def api_project_readme(request: Request):
    codx_junior_session = request.state.codx_junior_session
    document = codx_junior_session.get_readme()
    return Response(content=document or "> Not found", media_type="text/html")

@app.get("/api/projects/ai/models")
def api_project_ai_models(request: Request):
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.settings.get_project_ai_models()

@app.post("/api/projects/ai/models/reload")
def api_project_ai_models_reload(request: Request, model: AIModel):
    return AIManager().reload_model(model)

@app.post("/api/projects")
def api_project_create(request: Request, user: CodxUser = Depends(get_authenticated_user)):
    project_path = request.query_params.get("project_path")
    try:
        return CODXJuniorSettings.from_project_file(f"${project_path}/.codx/project.json")
    except Exception:
        return create_project(project_path=project_path, user=user)

@app.delete("/api/projects")
def api_project_delete(request: Request):
    codx_junior_session = request.state.codx_junior_session
    codx_junior_session.delete_project()
    return { "ok": 1 }

@app.get("/api/project/unwatch")
def api_project_unwatch(request: Request):
    codx_junior_session = request.state.codx_junior_session
    codx_junior_session.watch_project(False)
    find_all_projects()
    return { "OK": 1 }

@app.post("/api/images")
async def api_image_upload(file: UploadFile):
    """
    Upload an image file and store it using an MD5 hash as the filename.
    Returns the relative URL path to access the uploaded image.
    """
    # Read the file content as bytes
    file_content: bytes = await file.read()

    if not file_content:
        return JSONResponse(content={'error': 'No selected file'}, status_code=400)

    # Create an MD5 hash from the file content to use as a unique filename
    md5_hash: str = hashlib.md5(file_content).hexdigest()

    # Define the target directory for message images
    message_image_folder = f"{CODX_JUNIOR_STATIC_FOLDER}/images/message"
    os.makedirs(message_image_folder, exist_ok=True)

    # Create the full path for the image using the hash
    image_path = os.path.join(message_image_folder, md5_hash)

    # Save the file only if it doesn't already exist (avoids duplicate writes)
    if not os.path.exists(image_path):
        logger.info("Saving uploaded image to %s", image_path)
        # Open in binary write mode - no encoding argument for binary mode
        with open(image_path, "wb") as file_object:
            file_object.write(file_content)

    # Return the relative path to access the image
    image_url = f'/images/message/{md5_hash}'
    return {"path": image_url}

@app.get("/api/code-server/file/open")
def api_file_open(request: Request):
    file_name = request.query_params.get("file_name")
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.coder_open_file(file_name=file_name)

@app.get("/api/files")
def api_get_files(request: Request):
    codx_junior_session = request.state.codx_junior_session
    path = request.query_params.get("path")
    return codx_junior_session.read_directory(path=path)

@app.get("/api/files/read")
def api_get_file(request: Request):
    codx_junior_session = request.state.codx_junior_session
    path = request.query_params.get("path")
    return codx_junior_session.read_file(path=path)

@app.post("/api/files/diff")
async def api_get_file_diff(request: Request):
    codx_junior_session = request.state.codx_junior_session
    data = await request.json()
    return codx_junior_session.diff_file(path=data["path"], content=data["content"])

@app.post("/api/files/diff/comments")
async def api_get_file_diff_comments(request: Request):
    codx_junior_session = request.state.codx_junior_session
    data = await request.json()
    return codx_junior_session.diff_file_comments(path=data["path"], content=data["content"], comments=data["comments"])

@app.post("/api/files/write")
async def api_post_file(doc: Document, request: Request):
    codx_junior_session = request.state.codx_junior_session
    file_path = request.query_params.get("path")
    return await codx_junior_session.write_project_file(file_path=file_path, content=doc.page_content, process=False)

@app.get("/api/files/reset")
async def api_reset_file(request: Request):
    codx_junior_session = request.state.codx_junior_session
    file_path = request.query_params.get("path")
    return await codx_junior_session.reset_project_file(file_path=file_path)

@app.get("/api/files/find")
def api_find_files(request: Request):
    codx_junior_session = request.state.codx_junior_session
    search = request.query_params.get("search")
    return codx_junior_session.search_files(search=search)

@app.get("/api/apps")
def api_apps_list(request: Request):
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.get_project_apps()

@app.get("/api/apps/run")
def api_apps_run(request: Request):
    codx_junior_session = request.state.codx_junior_session
    app_name = request.query_params.get("app")
    return codx_junior_session.run_app(app_name=app_name)


@app.get("/api/global/settings")
def api_read_global_settings(user: CodxUser = Depends(get_authenticated_user)):
    if not user or user.role != 'admin':
        return {
          "error": "User is not admin"
        }
    return read_global_settings()

@app.post("/api/global/settings")
def api_write_global_settings(global_settings: GlobalSettings):
    AIManager().reload_models(global_settings)
    logger.info("/api/global/settings save global settings")
    write_global_settings(global_settings=global_settings)
    
@app.post("/api/run/script")
def run_script(data: dict, request: Request):
    codx_junior_session = request.state.codx_junior_session
    std, _ = exec_command(data["script"], cwd=codx_junior_session.settings.abs_project_path)
    return std

@app.get("/api/system/logs")
def api_logs_list():
    stdout, _ = exec_command("sudo docker ps --format {{.Names}}")
    containers = [f"🐋:{log}" for log in [log.strip().replace(".log", "") for log in stdout.split("\n")] if log]
   
    stdout, _ = exec_command(f"ls {LOGS_FOLDER}")
    files = [f"🗃️:{log}" for log in [log.strip().replace(".log", "") for log in stdout.split("\n")] if log]
   
    return sorted(containers + files)

@app.get("/api/system/logs/{log_name}")
def api_logs_tail(log_name: str, request: Request):
    log_size = request.query_params.get("log_size")
    if not str(log_size).isnumeric():
        log_size = 100

    if "🐋" in log_name:
        stdout, err_logs = exec_command(f"sudo docker logs -n {log_size} {log_name.split(':')[1]}")
        if err_logs:
            logger.error("Error reading logs %s: %s", log_name, err_logs)
        return stdout.split("\n")
    else:   
        log_name = log_name.split(":")[-1]
        log_file = f"{LOGS_FOLDER}/{log_name}.log"
        cmd = f"tail -n {log_size} {log_file}"
        try:
            logs, err_logs = exec_command(cmd)
            if err_logs:
                logger.error("Error reading logs %s: %s", log_name, err_logs)

            def is_valid_log(line: str) -> bool:
                """Filter out log lines related to the logs endpoint itself."""
                return "/api/system/logs" not in line

            return [line for line in logs.split("\n") if is_valid_log(line)]
        except OSError as ex:
            logger.exception("Error reading logs: %s", ex)

@app.post("/api/screen")
def api_screen_set(screen: Screen):
    CODX_JUNIOR_DISPLAY = os.environ["CODX_JUNIOR_DISPLAY"]
    return exec_command(f"xrandr -s {screen.resolution}", env={"DISPLAY": CODX_JUNIOR_DISPLAY})

@app.get("/api/screen")
def api_screen_get():
    screen = Screen()
    try:
        CODX_JUNIOR_DISPLAY = os.environ["CODX_JUNIOR_DISPLAY"]
        res, _ = exec_command(f"xrandr --current", env={"DISPLAY": CODX_JUNIOR_DISPLAY})
        # Screen 0: minimum 32 x 32, current 1920 x 1080, maximum 32768 x 32768
        lines = res.split("\n")
        screen_line = [l for l in lines if l.startswith("Screen ")][0]
        screen.resolution = screen_line.split("current ")[1].split(",")[0].replace(" ", "")
    except (IndexError, KeyError) as ex:
        logger.error("Error extracting screen resolutions %s", ex)
    return screen

@app.post("/api/image-to-text")
async def api_image_to_text_endpoint(file: UploadFile, request: Request):
    codx_junior_session = request.state.codx_junior_session
    file_bytes = await file.read()
    return codx_junior_session.api_image_to_text(file_bytes)

@app.post("/api/restart")
def api_restart():
    logger.info("****************** API RESTARTING... bye *******************")
    exec_command("sudo kill 7")

@app.post("/api/shutdown")
def api_shutdown():
    """API endpoint to shut down the server."""
    logger.info("Received request to shut down the server. Terminating...")
    os._exit(0)
    
logger.info("API Static folder: %s", CODX_JUNIOR_STATIC_FOLDER)
logger.info("API Images folder: %s", IMAGE_UPLOAD_FOLDER)

app.mount("/api/static", StaticFiles(directory=CODX_JUNIOR_STATIC_FOLDER, html=True), name="static")

# Made with ❤️ by codx-junior