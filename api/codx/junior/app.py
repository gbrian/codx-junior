import os
import uuid
import shutil
import time
import logging
import asyncio
import socketio
import traceback

from multiprocessing.pool import ThreadPool
from threading import Thread

from pathlib import Path

from codx.junior.ai import AIManager

from codx.junior.sio.sio import sio
from codx.junior.sio.session_channel import SessionChannel

from codx.junior.profiling.profiler import profile_function

from codx.junior.log_parser import parse_logs
from codx.junior.browser import run_browser_manager

from codx.junior.api.chatGPTLikeApi import router as chatgpt_router
from codx.junior.api.users import router as users_router
from codx.junior.security.user_management import get_authenticated_user

CODX_JUNIOR_API_BACKGROUND = os.environ.get("CODX_JUNIOR_API_BACKGROUND")

logging.basicConfig(level = logging.DEBUG,format = '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s')
logger = logging.getLogger(__name__)

run_browser_manager()

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


from flask import send_file

from fastapi import FastAPI, Request, status, Response, UploadFile, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse

from codx.junior.db import (
    Chat,
    Message
)
from codx.junior.model.model import (
    KnowledgeReloadPath,
    KnowledgeSearch,
    KnowledgeDeleteSources,
    Profile,
    Document,
    LiveEdit,
    GlobalSettings,
    Screen,
    CodxUser
)

from codx.junior.settings import (
  CODXJuniorSettings,
  read_global_settings,
  write_global_settings
)

from codx.junior.profiles.profile_manager import ProfileManager
from codx.junior.chat_manager import ChatManager

from codx.junior.engine import (
    create_project,
    coder_open_file,
    find_all_projects,
    find_all_user_projects,
    CODXJuniorSession,
    SessionChannel
)

from codx.junior.utils import (
    exec_command,
)

from codx.junior.context import AICodeGerator

from codx.junior.background import start_background_services

CODX_JUNIOR_STATIC_FOLDER=os.environ.get("CODX_JUNIOR_STATIC_FOLDER")
IMAGE_UPLOAD_FOLDER = f"{os.path.dirname(__file__)}/images"
os.makedirs(IMAGE_UPLOAD_FOLDER, exist_ok=True)

app = FastAPI(
    title="CODXJuniorAPI",
    description="API for CODXJunior",
    version="1.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    ssl_context='adhoc'
)

app = FastAPI()

sio_asgi_app = socketio.ASGIApp(sio, app, socketio_path="/api/socket.io")
app.mount("/api/socket.io", sio_asgi_app)

app.include_router(chatgpt_router, prefix="/api")
app.include_router(users_router, prefix="/api")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
	exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
	logger.error(f"{request}: {exc_str}")
	content = {'status_code': 10422, 'message': exc_str, 'data': None}
	return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

@app.on_event("startup")
def startup_event():
    logger.info(f"Creating FASTAPI: {app.__dict__}")

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
        logger.info(f"Request {request.url} - {time.time() - start_time} ms")

@app.middleware("http")
async def add_gpt_engineer_settings(request: Request, call_next):
    codx_path = request.query_params.get("codx_path")
    if codx_path:
        try:
            sid = request.headers.get("x-sid")
            channel = SessionChannel(sid=sid, sio=sio)
            request.state.codx_junior_session = CODXJuniorSession(codx_path=codx_path, channel=channel)
            settings = request.state.codx_junior_session.settings
            # logger.info(f"CODXJuniorEngine settings: {settings.__dict__ if settings else {}}")
        except Exception as ex:
            logger.error(f"Error loading settings {codx_path}: {ex}\n{request.url}")
    return await call_next(request)

@app.get("/api/health")
def api_health_check():
    return "ok"

@app.get("/api/knowledge/reload")
async def api_knowledge_reload(request: Request):
    codx_junior_session = request.state.codx_junior_session
    await codx_junior_session.check_project_changes()
    await codx_junior_session.reload_knowledge()
    return codx_junior_session.check_knowledge_status()

@app.post("/api/knowledge/reload-path")
def api_knowledge_reload_path(knowledge_reload_path: KnowledgeReloadPath, request: Request):
    codx_junior_session = request.state.codx_junior_session
    logger.info(f"**** API:knowledge_reload_path {knowledge_reload_path}")
    exec_command(f"touch {knowledge_reload_path.path}")

@app.post("/api/knowledge/delete")
def api_knowledge_reload_path(knowledge_delete_sources: KnowledgeDeleteSources, request: Request):
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.delete_knowledge_source(sources=knowledge_delete_sources.sources)

@app.delete("/api/knowledge/delete")
def api_knowledge_reload_all(request: Request):
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.delete_knowledge()


@app.post("/api/knowledge/reload-search")
async def api_knowledge_search_endpoint(knowledge_search_params: KnowledgeSearch, request: Request):
    logger.info("API:knowledge_search_endpoint")
    codx_junior_session = request.state.codx_junior_session
    return (await codx_junior_session.knowledge_search(knowledge_search=knowledge_search_params))

@app.get("/api/knowledge/status")
def api_knowledge_status(request: Request):
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.check_knowledge_status()

@app.get("/api/chats")
def api_list_chats(request: Request):
    codx_junior_session = request.state.codx_junior_session
    file_path = request.query_params.get("file_path")
    chat_id = request.query_params.get("id")
    if chat_id:
        return codx_junior_session.get_chat_manager().find_by_id(chat_id=chat_id)
    if file_path:
        return codx_junior_session.get_chat_manager().load_chat_from_path(chat_file=file_path)
    return codx_junior_session.list_chats()

@profile_function
@app.post("/api/chats")
async def api_chat(chat: Chat, request: Request):
    codx_junior_session = request.state.codx_junior_session
    codx_junior_session.chat_event(chat=chat, message="Chatting with project...")
    await codx_junior_session.chat_with_project(chat=chat)
    await codx_junior_session.save_chat(chat)
    return chat

@profile_function
@app.post("/api/chats/from-url")
async def api_chat_form_url(chat: Chat, request: Request):
    codx_junior_session = request.state.codx_junior_session
    codx_junior_session.chat_event(chat=chat, message="Loading chat...")
    codx_junior_session.init_chat_from_url(chat=chat)
    await codx_junior_session.save_chat(chat)
    return chat

@profile_function
@app.post("/api/chats/sub-tasks")
async def api_chat_subtasks(chat: Chat, request: Request):
    codx_junior_session = request.state.codx_junior_session
    return await codx_junior_session.generate_tasks(chat=chat)

@app.put("/api/chats")
async def api_save_chat(chat: Chat, request: Request):
    codx_junior_session = request.state.codx_junior_session
    chat_only = request.query_params.get("chatonly") == "1"
    await codx_junior_session.save_chat(chat, chat_only=chat_only)

@app.delete("/api/chats")
def api_delete_chat(request: Request):
    codx_junior_session = request.state.codx_junior_session
    chat_id = request.query_params.get("chat_id")
    codx_junior_session.delete_chat(chat_id)

@app.get("/api/kanban")
def api_kanban(request: Request):
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.get_chat_manager().load_kanban()

@app.post("/api/kanban")
async def api_set_kanban(request: Request):
    codx_junior_session = request.state.codx_junior_session
    kanban = await request.json()
    codx_junior_session.get_chat_manager().save_kanban(kanban)


@app.post("/api/images")
def api_image_upload(file: UploadFile):
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Generate a unique filename using UUID
    unique_filename = f"{str(uuid.uuid4())}-{file.filename}"
    file_path = os.path.join(IMAGE_UPLOAD_FOLDER, unique_filename)
    
    # Save the file
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)   

    # Return the full URL to access the image
    image_url = '/api/images/' + unique_filename
    return image_url

@app.post("/api/run/improve")
async def api_run_improve(chat: Chat, request: Request):
    codx_junior_session = request.state.codx_junior_session
    await codx_junior_session.improve_existing_code(chat=chat)
    await codx_junior_session.save_chat(chat)
    return chat

@app.post("/api/run/improve/patch")
async def api_run_improve_patch(code_generator: AICodeGerator, request: Request):
    codx_junior_session = request.state.codx_junior_session
    info, error = await codx_junior_session.improve_existing_code_patch(code_generator=code_generator)
    return {
        "info": info, 
        "error": error
    }

@app.get("/api/run/changes/summary")
def api_changes_summary(request: Request):
    codx_junior_session = request.state.codx_junior_session
    refresh = request.query_params.get("refresh")
    return codx_junior_session.build_code_changes_summary(force=refresh == "true")

@app.get("/api/settings")
def api_settings_check(request: Request):
    logger.info("/api/settings")
    codx_junior_session = request.state.codx_junior_session
    codx_junior_session.check_project()
    return codx_junior_session.settings

@app.put("/api/settings")
async def api_save_settings(request: Request):
    settings = await request.json()
    CODXJuniorSettings.from_json(settings).save_project()
    find_all_projects()
    return api_settings_check(request)

@app.get("/api/profiles")
def api_list_profile(request: Request):
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.list_profiles()

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
    settings.watching = True
    settings.save_project()
    find_all_projects()
    return { "OK": 1 }

@app.get("/api/projects")
def api_find_all_projects(user: CodxUser = Depends(get_authenticated_user)):
    all_projects = find_all_user_projects(user)
    return list(all_projects)

@app.get("/api/projects/repo/branches")
def api_find_all_repo_branches(request: Request):
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.get_project_branches()

@app.get("/api/projects/repo/changes")
def api_find_all_repo_changes(request: Request):
    codx_junior_session = request.state.codx_junior_session
    main_branch = request.query_params.get("main_branch")
    return codx_junior_session.get_project_changes(main_branch=main_branch)

@app.get("/api/projects/readme")
def api_project_readme(request: Request):
    codx_junior_session = request.state.codx_junior_session
    document = codx_junior_session.get_readme()
    return Response(content=document or "> Not found", media_type="text/html")

@app.post("/api/projects")
def api_project_create(request: Request, user: CodxUser = Depends(get_authenticated_user)):
    project_path = request.query_params.get("project_path")
    try:
        return CODXJuniorSettings.from_project_file(f"${project_path}/.codx/project.json")
    except:
        return create_project(project_path=project_path, user=user)

@app.delete("/api/projects")
def api_project_delete(request: Request):
    codx_junior_session = request.state.codx_junior_session
    codx_junior_session.delete_project()
    return { "ok": 1 }

@app.get("/api/project/unwatch")
def api_project_unwatch(request: Request):
    codx_junior_session = request.state.codx_junior_session
    settings.watching = False
    settings.save_project()
    find_all_projects()
    return { "OK": 1 }

@app.get("/api/knowledge/keywords")
def api_get_keywords(request: Request):
    codx_junior_session = request.state.codx_junior_session
    query = request.query_params.get("query")
    return codx_junior_session.get_keywords(query=query)

@app.post("/api/knowledge/keywords")
def api_extract_tags(doc: Document, request: Request):
    codx_junior_session = request.state.codx_junior_session
    logging.info(f"Extract keywords from {doc}")
    doc = codx_junior_session.extract_tags(doc=doc)
    return doc.__dict__

@app.get("/api/code-server/file/open")
def api_list_chats(request: Request):
    file_name = request.query_params.get("file_name")
    settings = codx_junior_session = request.state.codx_junior_session.settings
    coder_open_file(settings=settings, file_name=file_name)

@app.get("/api/wiki")
def api_get_wiki(request: Request):
    codx_junior_session = request.state.codx_junior_session
    file_path = request.query_params.get("file_path")
    document = codx_junior_session.get_wiki_file(file_path)
    return Response(content=document or "> Not found", media_type="text/html")

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

@app.post("/api/files/write")
def api_post_file(doc: Document, request: Request):
    codx_junior_session = request.state.codx_junior_session
    path = request.query_params.get("path")
    return codx_junior_session.write_file(path=path, content=doc.page_content)

@app.get("/api/files/find")
def api_get_file(request: Request):
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
        return {}
    return read_global_settings()

@app.post("/api/global/settings")
def api_write_global_settings(global_settings: GlobalSettings):
    AIManager().reload_models(global_settings)
    write_global_settings(global_settings=global_settings)
    

@app.get("/api/logs")
def api_logs_list():
    stdout, _ = exec_command(f"ls {os.environ['CODX_SUPERVISOR_LOG_FOLDER']}")
    return [log for log in [log.strip().replace(".log", "") for log in stdout.split("\n")] if log]

@app.get("/api/logs/{log_name}")
def api_logs_tail(log_name: str, request: Request):
    log_file = f"{os.environ['CODX_SUPERVISOR_LOG_FOLDER']}/{log_name}.log"
    log_size = request.query_params.get("log_size") or "100"
    cmd = f"tail -n {log_size} {log_file}"
    try:
        logs, _ = exec_command(cmd)
        logger.info(f"api logs {logs}")

        return parse_logs(logs)
    except Exception as ex:
        logger.exception(f"Error reading logs: {ex}")

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
    except Exception as ex:
        logger.error(f"Error extracting screen resolutions {ex}")
    return screen

@app.post("/api/image-to-text")
async def api_image_to_text_endpoint(file: UploadFile):
    file_bytes = await file.read()            
    return api_image_to_text(file_bytes)

@app.post("/api/restart")
def api_restart():
    logger.info(f"****************** API RESTARTING... bye *******************")
    exec_command("sudo kill 7")

if CODX_JUNIOR_STATIC_FOLDER:
    os.makedirs(CODX_JUNIOR_STATIC_FOLDER, exist_ok=True)
    logger.info(f"API Static folder: {CODX_JUNIOR_STATIC_FOLDER}")
    app.mount("/", StaticFiles(directory=CODX_JUNIOR_STATIC_FOLDER, html=True), name="client_chat")

app.mount("/api/images", StaticFiles(directory=IMAGE_UPLOAD_FOLDER), name="images")

if CODX_JUNIOR_API_BACKGROUND:
    start_background_services(app)

