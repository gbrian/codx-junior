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
    'chromadb.api.segment'
    ])


from fastapi import FastAPI, Request, Response, UploadFile
from fastapi.staticfiles import StaticFiles
from flask import send_file
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from gpt_engineer.api.model import (
    Chat,
    Message,
    Settings,
    KnowledgeReloadPath,
    KnowledgeSearch,
    KnowledgeDeleteSources,
    Profile,
    Document
)
from gpt_engineer.api.app_service import clarify_business_request

from gpt_engineer.core.settings import GPTEngineerSettings 
from gpt_engineer.core.dbs import DBs
from gpt_engineer.api.profile_manager import ProfileManager
from gpt_engineer.core.chat_manager import ChatManager

from gpt_engineer.api.engine import (
    select_afected_files_from_knowledge, 
    improve_existing_code,
    check_knowledge_status,
    run_edits,
    create_project,
    select_afefcted_documents_from_knowledge,
    check_project_changes,
    reload_knowledge,
    delete_knowledge_source,
    knowledge_search,
    chat_with_project,
    check_project,
    extract_tags,
    get_keywords,
    find_all_projects
)

from gpt_engineer.core.scheduler import add_work

IMAGE_UPLOAD_FOLDER = f"{os.path.dirname(__file__)}/images"
os.makedirs(IMAGE_UPLOAD_FOLDER, exist_ok=True)

def process_projects_changes():
    check_projects = [settings for settings in find_all_projects() if settings.watching]
    for settings in check_projects:
        try:
            check_project_changes(settings=settings)
        except Exception as ex:
            logger.exception(f"Processing {gpteng_path} error: {ex}")
            pass

logger.info("Starting process_projects_changes job")
add_work(process_projects_changes)

class GPTEngineerAPI:
    def start(self):
        app = FastAPI(
            title="GPTEngineerAPI",
            description="API for GPTEngineer",
            version="1.0",
            openapi_url="/api/openapi.json",
            docs_url="/api/docs",
            redoc_url="/api/redoc",
            ssl_context='adhoc'
        )

        app.mount("/static", StaticFiles(directory="gpt_engineer/api/client_chat", html=True), name="client_chat")
        app.mount("/api/images", StaticFiles(directory=IMAGE_UPLOAD_FOLDER), name="images")

        @app.on_event("startup")
        def startup_event():
            logger.info("Creating FASTAPI")
        
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
            gpteng_path = request.query_params.get("gpteng_path")
            settings = None
            if gpteng_path:
                try:
                    settings = GPTEngineerSettings.from_project(gpteng_path)
                    ai_logs = ["openai._base_client"]
                    if settings.log_ai:
                        enable_logs(ai_logs)
                    else:
                        disable_logs(ai_logs)
                except:
                    pass
            request.state.settings = settings
            return await call_next(request)


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
                chat = chat_with_project(settings=settings, chat=chat, use_knowledge=True)
                ChatManager(settings=settings).save_chat(chat) 
              return StreamingResponse()
            else:
              chat = chat_with_project(settings=settings, chat=chat, use_knowledge=True)
              ChatManager(settings=settings).save_chat(chat)
              return chat.messages[-1]

        @app.put("/api/chats")
        def api_save_chat(chat: Chat, request: Request):
            settings = request.state.settings
            ChatManager(settings=settings).save_chat(chat)

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
            # Return the search results as response
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
            GPTEngineerSettings.from_json(settings).save_project()
            
            return api_settings_check(request)

        @app.get("/api/project/create")
        def api_project_create(request: Request):
            project_path = request.query_params.get("project_path")
            if not project_path or not os.path.isdir(project_path):
                return
            settings = GPTEngineerSettings()
            settings.gpteng_path = f"{project_path}/.gpteng"
            settings.project_path = project_path
            logger.info(f"/api/project/create project_path: {project_path}")
            create_project(settings=settings)
            return settings

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
                settings = GPTEngineerSettings.from_project(project_path)
            except:
                settings = GPTEngineerSettings()
                settings.project_path = project_path
                settings.project_name = settings.project_path.split("/")[-1] 
                settings.gpteng_path = f"{settings.project_path}/.gpteng"
                settings.save_project()
                settings = GPTEngineerSettings.from_project(settings.gpteng_path)
            return settings
        
        @app.delete("/api/projects")
        def api_project_delete(request: Request):
            settings = request.state.settings
            shutil.rmtree(settings.gpteng_path)
            logger.error(f"PROJECT REMOVED {settings.gpteng_path}")
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

        @app.get("/code-server/file/open/:file_name")
        def api_list_chats(file_name: str):
            os.system(f"code-server -r {file_name}")

        @app.get("/api/wiki")
        def api_get_wiki(request: Request):
            settings = request.state.settings
            file_path = request.query_params.get("file_path")
            try:
                with open(f"{settings.project_wiki}{file_path}") as f:
                  return Response(content=f.read(), media_type="text/html")
            except:
                return Response(content="# No project wiki...yet!", media_type="text/html")

        return app
            
