import os
import uuid
import shutil
import time
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from pathlib import Path
import traceback

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
    'openai._base_client'
])


from flask import send_file

from fastapi import FastAPI, Request, Response, UploadFile
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
from fastapi_socketio import SocketManager

from codx.junior.model import (
    Chat,
    Message,
    Settings,
    KnowledgeReloadPath,
    KnowledgeSearch,
    KnowledgeDeleteSources,
    Profile,
    Document,
    LiveEdit,
    GlobalSettings
)

from codx.junior.settings import CODXJuniorSettings 

from codx.junior.profiles.profile_manager import ProfileManager
from codx.junior.chat_manager import ChatManager

from codx.junior.engine import (
    select_afected_files_from_knowledge, 
    improve_existing_code,
    check_knowledge_status,
    create_project,
    select_afefcted_documents_from_knowledge,
    check_project_changes,
    reload_knowledge,
    delete_knowledge_source,
    delete_knowledge,
    knowledge_search,
    chat_with_project,
    check_project,
    extract_tags,
    get_keywords,
    find_all_projects,
    read_global_settings,
    write_global_settings,
    add_global_settings,
    coder_open_file,
    api_image_to_text
)

from codx.junior.scheduler import add_work

STATIC_FOLDER=os.environ.get("STATIC_FOLDER")
IMAGE_UPLOAD_FOLDER = f"{os.path.dirname(__file__)}/images"
os.makedirs(IMAGE_UPLOAD_FOLDER, exist_ok=True)

def process_projects_changes():
    projects_to_check = [settings for settings in find_all_projects() if settings.watching]
    # logger.info(f"[process_projects_changes]: {[p.project_name for p in projects_to_check]}") 
    
    for ix, settings in enumerate(projects_to_check):
        # logger.info(f"[process_projects_changes]: check {settings.project_name} - {ix}")
        if settings.watching:
            try:
                check_project_changes(settings=add_global_settings(settings))
            except Exception as ex:
                logger.error(f"Processing {settings.project_name} error: {ex}")

logger.info("Starting process_projects_changes job")
add_work(process_projects_changes)

class CODXJuniorAPI:
    def start(self):
        app = FastAPI(
            title="CODXJuniorAPI",
            description="API for CODXJunior",
            version="1.0",
            openapi_url="/api/openapi.json",
            docs_url="/api/docs",
            redoc_url="/api/redoc",
            ssl_context='adhoc'
        )

        socket_manager = SocketManager(app=app)

        @app.on_event("startup")
        def startup_event():
            logger.info(f"Creating FASTAPI: {app.__dict__}")
        
        @app.exception_handler(Exception)
        async def my_exception_handler(request: Request, ex: Exception):
            return JSONResponse(status_code=500, 
                content=traceback.format_exception(ex))

        @app.middleware("http")
        async def add_process_time_header(request: Request, call_next):
            logger.info("FASTAPI::add_process_time_header")
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            return response

        @app.middleware("http")
        async def add_gpt_engineer_settings(request: Request, call_next):
            logger.info("FASTAPI::add_process_time_header")
            logger.info(f"Request {request.url}")
            codx_path = request.query_params.get("codx_path")
            settings = None
            global_settings = read_global_settings()
            if codx_path:
                try:
                    settings = add_global_settings(CODXJuniorSettings.from_project(codx_path))
                except Exception as ex:
                    logger.error(f"Error loading settings {codx_path}: {ex}")
            request.state.settings = settings        
            logger.info(f"Request settings: {settings.__dict__ if settings else {}}\nGlobal: {global_settings.__dict__}")
            return await call_next(request)

        @app.get("/")
        def index():
            return RedirectResponse(url="/index.html")

        @app.get("/api/health")
        def api_health_check():
            return "ok"

        @app.get("/api/projects")
        def api_find_all_projects():
            return find_all_projects(detailed=True)

        @app.get("/api/knowledge/reload")
        def api_knowledge_reload(request: Request):
            settings = request.state.settings
            check_project_changes(settings=settings)
            reload_knowledge(settings=settings)
            return check_knowledge_status(settings=settings)

        @app.post("/api/knowledge/reload-path")
        def api_knowledge_reload_path(knowledge_reload_path: KnowledgeReloadPath, request: Request):
            settings = request.state.settings
            logger.info(f"**** API:knowledge_reload_path {knowledge_reload_path}")
            reload_knowledge(settings=settings, path=knowledge_reload_path.path)
            return check_knowledge_status(settings=settings)

        @app.post("/api/knowledge/delete")
        def api_knowledge_reload_path(knowledge_delete_sources: KnowledgeDeleteSources, request: Request):
            settings = request.state.settings
            return delete_knowledge_source(settings=settings, sources=knowledge_delete_sources.sources)

        @app.delete("/api/knowledge/delete")
        def api_knowledge_reload_all(request: Request):
            settings = request.state.settings
            return delete_knowledge(settings=settings)


        @app.post("/api/knowledge/reload-search")
        def api_knowledge_search_endpoint(knowledge_search_params: KnowledgeSearch, request: Request):
            logger.info("API:knowledge_search_endpoint")
            settings = request.state.settings
            return knowledge_search(settings=settings, knowledge_search=knowledge_search_params)

        @app.get("/api/knowledge/status")
        def api_knowledge_status(request: Request):
            settings = request.state.settings
            return check_knowledge_status(settings=settings)

        @app.get("/api/chats")
        def api_list_chats(request: Request):
            settings = request.state.settings
            chat_name = request.query_params.get("chat_name")
            chat_manager = ChatManager(settings=settings)
            if chat_name:
                return chat_manager.load_chat(chat_name=chat_name)
            return chat_manager.list_chats()

        @app.post("/api/chats")
        def api_chat(chat: Chat, request: Request):
            settings = request.state.settings
            streaming = request.query_params.get("streaming")
            if streaming:
              def doStreaming():
                data_buffer = DataBuffer()
                chat_with_project(settings=settings, chat=chat, use_knowledge=True)
                ChatManager(settings=settings).save_chat(chat) 
              return StreamingResponse()
            else:
              chat_with_project(settings=settings, chat=chat, use_knowledge=True)
              ChatManager(settings=settings).save_chat(chat)
              return chat.messages[-1]

        @app.put("/api/chats")
        def api_save_chat(chat: Chat, request: Request):
            settings = request.state.settings
            ChatManager(settings=settings).save_chat(chat)

        @app.delete("/api/chats")
        def api_delete_chat(request: Request):
            settings = request.state.settings
            chat_name = request.query_params.get("chat_name")
            ChatManager(settings=settings).delete_chat(chat_name)

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
            settings = request.state.settings
            # Perform search on Knowledge using the input
            improve_existing_code(chat=chat, settings=settings)
            ChatManager(settings=settings).save_chat(chat)
            return chat

        @app.post("/api/run/edit")
        def api_run_edit(chat: Chat, request: Request):
            settings = request.state.settings
            # Perform search on Knowledge using the input
            # Return the search results as response
            message, errors = run_edits(settings=settings, chat=chat)
            return {
              "messages": chat.messages + [{ "role": "assistant", "content": message }],
              "errors": errors
            }

        @app.get("/api/settings")
        def api_settings_check(request: Request):
            logger.info("/api/settings")
            settings = request.state.settings
            check_project(settings=settings)
            return settings

        @app.put("/api/settings")
        async def api_save_settings(request: Request):
            settings = await request.json()
            CODXJuniorSettings.from_json(settings).save_project()
            
            return api_settings_check(request)

        @app.get("/api/profiles")
        def api_list_profile(request: Request):
            settings = request.state.settings
            return ProfileManager(settings=settings).list_profiles()

        @app.post("/api/profiles")
        def api_create_profile(profile: Profile, request: Request):
            settings = request.state.settings
            return ProfileManager(settings=settings).create_profile(profile)
            
        @app.get("/api/profiles/{profile_name}")
        def api_read_profile(profile_name, request: Request):
            settings = request.state.settings
            return  ProfileManager(settings=settings).read_profile(profile_name)

        @app.delete("/api/profiles/{profile_name}")
        def api_delete_profile(profile_name, request: Request):
            settings = request.state.settings
            ProfileManager(settings=settings).delete_profile(profile_name)
            return

        @app.get("/api/project/watch")
        def api_project_watch(request: Request):
            settings = request.state.settings
            settings.watching = True
            settings.save_project()
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
            settings = request.state.settings
            shutil.rmtree(settings.codx_path)
            logger.error(f"PROJECT REMOVED {settings.codx_path}")
            return { "ok": 1 }
        
        @app.get("/api/project/unwatch")
        def api_project_unwatch(request: Request):
            settings = request.state.settings
            settings.watching = False
            settings.save_project()
            return { "OK": 1 }

        @app.get("/api/knowledge/keywords")
        def api_get_keywords(request: Request):
            settings = request.state.settings
            query = request.query_params.get("query")
            return get_keywords(settings=settings, query=query)

        @app.post("/api/knowledge/keywords")
        def api_extract_tags(doc: Document, request: Request):
            settings = request.state.settings
            logging.info(f"Extract keywords from {doc}")
            doc = extract_tags(settings=settings, doc=doc)
            return doc.__dict__

        @app.get("/api/code-server/file/open")
        def api_list_chats(request: Request):
            file_name = request.query_params.get("file_name")
            coder_open_file(settings=request.state.settings, file_name=file_name)

        @app.get("/api/wiki")
        def api_get_wiki(request: Request):
            settings = request.state.settings
            file_path = request.query_params.get("file_path")
            try:
                with open(f"{settings.project_wiki}{file_path}") as f:
                  return Response(content=f.read(), media_type="text/html")
            except:
                return Response(content="# No project wiki...yet!", media_type="text/html")

        @app.get("/api/global/settings")
        def api_read_global_settings():
            return read_global_settings()
        
        @app.post("/api/global/settings")
        def api_write_global_settings(global_settings: GlobalSettings):
            return write_global_settings(global_settings=global_settings)

        @app.post("/api/image-to-text")
        async def api_image_to_text_endpoint(file: UploadFile):
            file_bytes = await file.read()            
            return api_image_to_text(file_bytes)


        # socket_handlers
        @app.sio.on('join')
        async def handle_join(sid, *args, **kwargs):
            await app.sio.emit('lobby', 'User joined')


        if STATIC_FOLDER:
            os.makedirs(STATIC_FOLDER, exist_ok=True)
            logger.info(f"API Static folder: {STATIC_FOLDER}")
            app.mount("/", StaticFiles(directory=STATIC_FOLDER, html=True), name="client_chat")
        app.mount("/api/images", StaticFiles(directory=IMAGE_UPLOAD_FOLDER), name="images")

        return app
            
