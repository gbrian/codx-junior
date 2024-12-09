import os
import uuid
import shutil
import time
import logging
import socketio
import threading

import logging
logging.basicConfig(level = logging.DEBUG,format = '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s')
logger = logging.getLogger(__name__)

from pathlib import Path
import traceback

from codx.junior.browser import start_broswser
start_broswser()

def disable_logs(logs):
  for logger_id in logs:
      logging.getLogger(logger_id).setLevel(logging.WARNING)

def enable_logs(logs):
  for logger_id in logs:
      logging.getLogger(logger_id).setLevel(logging.DEBUG)

disable_logs([
    'apscheduler.scheduler',
    'apscheduler.executors.default',
    'httpx',
    'httpcore.http11',
    'httpcore.connection',
    'chromadb.config',
    'chromadb.auth.registry',
    'chromadb.api.segment',
    'openai._base_client',
    'openai._base_client',
])


from flask import send_file

from fastapi import FastAPI, Request, Response, UploadFile
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse

from codx.junior.model import (
    Chat,
    Message,
    KnowledgeReloadPath,
    KnowledgeSearch,
    KnowledgeDeleteSources,
    Profile,
    Document,
    LiveEdit,
    GlobalSettings,
    Screen
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
    CODXJuniorSession,
    SessionChannel
)

from codx.junior.utils import (
    exec_command,
)

from codx.junior.scheduler import add_work

STATIC_FOLDER=os.environ.get("STATIC_FOLDER")
IMAGE_UPLOAD_FOLDER = f"{os.path.dirname(__file__)}/images"
os.makedirs(IMAGE_UPLOAD_FOLDER, exist_ok=True)

WATCHING_PROJECTS = {}

def check_project_changes(settings):
    try:
        return CODXJuniorSession(settings=settings).check_project_changes()
    except Exception as ex:
        logger.error(f"Processing {settings.project_name} error: {ex}")        
    return False

def process_project_changes(settings):
    WATCHING_PROJECTS[settings.codx_path] = True
    # logger.info(f"[check_project_changes]: check {settings.project_name}")
    try:
        CODXJuniorSession(settings=settings).process_project_changes()
    except Exception as ex:
        logger.error(f"Processing {settings.project_name} error: {ex}")        
    WATCHING_PROJECTS[settings.codx_path] = False


def process_projects_changes():
    while True:
        try:
            projects_to_check = [settings for settings in find_all_projects() if settings.watching]
            watching_projects = [p for p in projects_to_check if p.watching]
            for ix, settings in enumerate(watching_projects):
                has_changes = check_project_changes(settings=settings)
                if not has_changes:
                    continue
                logger.info(f"[process_projects_changes]: {settings.project_name} has_changes: {has_changes}")
                process_project_changes(settings=settings)
        except Exception as ex:
            logger.exception("Error processing watching projects {ex}")        
    time.sleep(5)

logger.info("Starting process_projects_changes job")

# Background changes loop
threading.Thread(target=process_projects_changes).start()

# Init all projects
find_all_projects()

app = FastAPI(
    title="CODXJuniorAPI",
    description="API for CODXJunior",
    version="1.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    ssl_context='adhoc'
)

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
            user_sid = request.headers.get("x-sid")
            channel = SessionChannel(sid=user_sid, sio=sio)
            request.state.codx_junior_session =  CODXJuniorSession(
                                                    codx_path=codx_path,
                                                    app=app,
                                                    channel=channel)
            settings = request.state.codx_junior_session.settings
            # logger.info(f"CODXJuniorEngine settings: {settings.__dict__ if settings else {}}")
        except Exception as ex:
            logger.error(f"Error loading settings {codx_path}: {ex}\n{request.url}")
    return await call_next(request)

@app.get("/")
def index():
    return RedirectResponse(url="/index.html")

@app.get("/api/health")
def api_health_check():
    return "ok"

@app.get("/api/projects")
def api_find_all_projects():
    all_projects = find_all_projects()
    return all_projects

@app.get("/api/knowledge/reload")
def api_knowledge_reload(request: Request):
    codx_junior_session = request.state.codx_junior_session
    codx_junior_session.check_project_changes()
    codx_junior_session.reload_knowledge()
    return codx_junior_session.check_knowledge_status()

@app.post("/api/knowledge/reload-path")
def api_knowledge_reload_path(knowledge_reload_path: KnowledgeReloadPath, request: Request):
    codx_junior_session = request.state.codx_junior_session
    logger.info(f"**** API:knowledge_reload_path {knowledge_reload_path}")
    codx_junior_session.reload_knowledge(path=knowledge_reload_path.path)
    return codx_junior_session.check_knowledge_status()

@app.post("/api/knowledge/delete")
def api_knowledge_reload_path(knowledge_delete_sources: KnowledgeDeleteSources, request: Request):
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.delete_knowledge_source(sources=knowledge_delete_sources.sources)

@app.delete("/api/knowledge/delete")
def api_knowledge_reload_all(request: Request):
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.delete_knowledge()


@app.post("/api/knowledge/reload-search")
def api_knowledge_search_endpoint(knowledge_search_params: KnowledgeSearch, request: Request):
    logger.info("API:knowledge_search_endpoint")
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.knowledge_search(knowledge_search=knowledge_search_params)

@app.get("/api/knowledge/status")
def api_knowledge_status(request: Request):
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.check_knowledge_status()

@app.get("/api/chats")
def api_list_chats(request: Request):
    codx_junior_session = request.state.codx_junior_session
    chat_name = request.query_params.get("chat_name")
    board = request.query_params.get("board")
    if chat_name:
        return codx_junior_session.load_chat(board=board, chat_name=chat_name)
    return codx_junior_session.list_chats()

@app.post("/api/chats")
def api_chat(chat: Chat, request: Request):
    codx_junior_session = request.state.codx_junior_session
    codx_junior_session.chat_with_project(chat=chat, use_knowledge=True)
    return chat

@app.put("/api/chats")
def api_save_chat(chat: Chat, request: Request):
    codx_junior_session = request.state.codx_junior_session
    codx_junior_session.save_chat(chat)

@app.delete("/api/chats")
def api_delete_chat(request: Request):
    codx_junior_session = request.state.codx_junior_session
    chat_name = request.query_params.get("chat_name")
    board = request.query_params.get("board")
    codx_junior_session.delete_chat(board, chat_name)

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
def api_run_improve(chat: Chat, request: Request):
    codx_junior_session = request.state.codx_junior_session
    codx_junior_session.improve_existing_code(chat=chat)
    codx_junior_session.save_chat(chat)
    return chat

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
def api_create_profile(profile: Profile, request: Request):
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.save_profile(profile=profile)
    
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

@app.post("/api/projects")
def api_project_create(request: Request):
    project_path = request.query_params.get("project_path")
    settings = None
    try:
        settings = CODXJuniorSettings.from_project(project_path)
    except:
        return create_project(project_path=project_path)

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


@app.get("/api/global/settings")
def api_read_global_settings():
    return read_global_settings()


@app.get("/api/logs")
def api_logs_list():
    return ['codx-junior-api', 'codx-junior-web', 'firefox', 'novnc', 'vncserver', 'supervisord']

@app.get("/api/logs/{log_name}")
def api_logs_tail(log_name: str, request: Request):
    log_file = f"/var/log/supervisor/{log_name}.log"
    log_size = request.query_params.get("log_size") or "1000"
    logs, _ = exec_command(f"tail -n {log_size} {log_file}")
    return logs


@app.post("/api/global/settings")
def api_write_global_settings(global_settings: GlobalSettings):
    return write_global_settings(global_settings=global_settings)

@app.post("/api/screen")
def api_screen_set(screen: Screen):
    return exec_command(f"sudo xrandr -s {screen.resolution}")

@app.get("/api/screen")
def api_screen_get():
    screen = Screen()
    res, _ = exec_command(f"sudo xrandr --current")
    # Screen 0: minimum 32 x 32, current 1920 x 1080, maximum 32768 x 32768
    screen.resolution = res.split("\n")[0].split("current ")[1].split(",")[0].replace(" ", "")
    return screen

@app.post("/api/image-to-text")
async def api_image_to_text_endpoint(file: UploadFile):
    file_bytes = await file.read()            
    return api_image_to_text(file_bytes)

@app.post("/api/restart")
def api_restart():
    logger.info(f"****************** API RESTART... NOT WORKING...")

#Socket io (sio) create a Socket.IO server
sio = socketio.AsyncServer(cors_allowed_origins='*',async_mode='asgi')
#wrap with ASGI application
socket_app = socketio.ASGIApp(sio)
app.mount("/", socket_app)


@sio.on("error")
async def error():
    logger.error(f"Socket error")

@sio.on("connect")
async def connect(sid, env):
    logger.info("New Client Connected to This id :"+" "+str(sid))

@sio.on("disconnect")
async def disconnect(sid):
    logger.info("Client Disconnected: "+" "+str(sid))

if STATIC_FOLDER:
    os.makedirs(STATIC_FOLDER, exist_ok=True)
    logger.info(f"API Static folder: {STATIC_FOLDER}")
    app.mount("/", StaticFiles(directory=STATIC_FOLDER, html=True), name="client_chat")

app.mount("/api/images", StaticFiles(directory=IMAGE_UPLOAD_FOLDER), name="images")

