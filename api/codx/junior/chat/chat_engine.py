import json
import logging
import os
import time
import uuid
from contextlib import contextmanager
from json import JSONDecodeError
from typing import List, Tuple, Optional

from langchain.schema import (
    BaseMessage,
    AIMessage,
    HumanMessage,
)
from langchain.schema.document import Document

from codx.junior.ai import AI
from codx.junior.chat_manager import ChatManager
from codx.junior.context import (
    AICodeGenerator, find_relevant_documents
)
from codx.junior.db import Chat, Message
from codx.junior.globals import (
    AGENT_DONE_WORD,
)
from codx.junior.project.project_discover import (
  find_project_by_id,
  get_project_dependencies
)

from codx.junior.knowledge.knowledge_milvus import Knowledge
from codx.junior.profiles.profile_manager import ProfileManager
from codx.junior.profiling.profiler import profile_function
from codx.junior.settings import CODXJuniorSettings
from codx.junior.utils.chat_utils import ChatUtils, QueryMentions
from codx.junior.utils.utils import document_to_context

# Set up logging
logger = logging.getLogger(__name__)


class ChatEngine:
    def __init__(self,
                settings,
                event_manager):
        self.settings = settings
        self.event_manager = event_manager
        self.knowledge = Knowledge(settings=settings)


    def get_profile_manager(self):
        return ProfileManager(settings=self.settings)


    def get_chat_manager(self):
        return ChatManager(settings=self.settings)


    @contextmanager
    def chat_action(self, chat: Chat, event: str):
        self.event_manager.chat_event(chat=chat, message=f"{event} starting")
        logger.info(f"Start chat {chat.name}")
        try:
            yield
        except Exception as ex:
            self.event_manager.chat_event(chat=chat, message=f"{event} error: {ex}", event_type="error")
            logger.exception(f"Chat {chat.name} {event} error: {ex}")
        finally:
            self.event_manager.chat_event(chat=chat, message=f"{event} done")
            logger.info(f"Chat done {chat.name}")


    @profile_function
    async def chat_with_project(self, chat: Chat, disable_knowledge: bool = False, callback=None, append_references: bool=True, chat_mode: str=None, iteration: int = 0):
        timing_info: dict[str, float | None] = {
            "start_time": time.time(),
            "first_response": None
        }
        if chat.project_id and chat.project_id != self.settings.project_id:
            # Invoke project based on project_id
            return await self.switch_project(chat.project_id).chat_with_project(chat=chat,
                                                                            disable_knowledge=disable_knowledge,
                                                                            callback=callback,
                                                                            append_references=append_references,
                                                                            chat_mode=chat_mode,
                                                                            iteration=iteration)

        with self.chat_action(chat=chat, event=f"Processing AI request {chat.name}"):
            chat_mode = chat_mode or chat.mode or "chat"
            documents = []
            task_item = ""

            parent_chat = None
            if chat.parent_id:
                chat_manager = self.get_chat_manager()
                parent_chat = chat_manager.find_by_id(chat.parent_id)

            max_iterations = self.settings.get_agent_max_iterations()
            iterations_left = max_iterations - iteration

            def new_chat_message(role, content = ""):
                return Message(role=role,
                                content=content,
                                doc_id=str(uuid.uuid4()))

            response_message = new_chat_message("assistant")
            def send_message_event(content, done):
                if not response_message.is_thinking:
                    if content and content.startswith("<think>") \
                      and not response_message.content:
                          response_message.is_thinking = True

                elif response_message.is_thinking and \
                    "</think>" in content:
                        response_message.is_thinking = False
                
                content = content.replace("<think>", "").replace("</think>", "")

                if not timing_info.get("first_response"):
                    timing_info["first_response"] = time.time() - timing_info["start_time"]

                if response_message.is_thinking:
                    response_message.think = content
                else:
                    response_message.content = content
                sources =  []
                if documents:
                    sources = list(set([d.metadata["source"].replace(self.settings.project_path, "") for d in documents]))
                response_message.files = sources
                response_message.task_item = task_item
                response_message.done = done
                self.event_manager.message_event(chat=chat, message=response_message)

            send_message_event("", False)

            valid_messages = [message for message in chat.messages if not message.hide and not message.improvement]
            
            last_ai_messages = [m for m in valid_messages if m.role == "assistant"]
            last_ai_message = last_ai_messages[-1] if last_ai_messages else None
                
            user_message = valid_messages[-1] if valid_messages else HumanMessage(content="")
            query = user_message.content

            query_mentions: QueryMentions = self.get_query_mentions(query=query)

            def load_profiles():
                profile_manager = self.get_profile_manager()
                query_profiles = query_mentions.profiles
                chat_and_message_profiles = [profile_manager.read_profile(profile_name) \
                                             for profile_name \
                                             in chat.profiles + (user_message.profiles or [])]
                all_profiles = [p for p in chat_and_message_profiles + query_profiles if p]
                all_profiles = profile_manager.get_profiles_and_parents(all_profiles)
                profile_names = [p.name for p in all_profiles]
                logger.info(f"Loading profiles: {profile_names}")
                return all_profiles

            is_refine = chat_mode == "task"
            is_agent = chat_mode  == "agent"
            
            chat_profiles = load_profiles()
            
            chat_profiles_content = ""
            chat_profile_names = []
            chat_model = chat.llm_model
            messages = []

            parent_content = self.get_chat_analysis_parents(chat=chat)
            if parent_content:
                messages.append(HumanMessage(content=parent_content))

            # Find projects for this
            query_mention_projects: List[CODXJuniorSettings] = [p for p in query_mentions.projects if p and hasattr(p, "codx_path")]
            search_projects: List[CODXJuniorSettings] = list(({
                    settings.codx_path: settings for settings in query_mention_projects
                }).values())

            valid_profiles = []
            if chat_profiles:
                valid_profiles = [profile for profile in chat_profiles if profile]
                chat_profiles_content = chat_profiles_content + "\n".join([profile.content for profile in valid_profiles])
                chat_profile_names = [profile.name for profile in valid_profiles]
                if not chat_model:
                    chat_models = list(set([profile.llm_model for profile in valid_profiles if profile.llm_model]))
                    chat_model = chat_models[0] if chat_models else None
                if valid_profiles[0].chat_mode:
                    chat_mode = valid_profiles[0].chat_mode
                # None profile uses knowledge, disable knowledge
                if next((p for p in valid_profiles if p.chat_mode == 'task'), None):
                    is_refine = True

            if not search_projects:
                disable_knowledge = True
                self.event_manager.chat_event(chat=chat, message="Knowledge search is disabled: No search projects found")
            if disable_knowledge:
                self.event_manager.chat_event(chat=chat, message="Knowledge search is disabled: Disabled by invocation")
            if not self.settings.use_knowledge:
                disable_knowledge = True
                self.event_manager.chat_event(chat=chat, message="Knowledge search is disabled: Project settings disabled")
            if user_message.disable_knowledge:
                disable_knowledge = True
                self.event_manager.chat_event(chat=chat, message="Knowledge search is disabled: Disabled by user message")
    
            if is_refine:
                task_item = "analysis"
          
            logger.info(f"chat_with_project {chat.name} settings ready")
            for message in chat.messages[0:-1]:
                if message.hide or message.improvement:
                    continue
                msg = self.convert_message(message)
                messages.append(msg)

            context = ""
            documents = []
            chat_files = chat.file_list or []
            if parent_chat and parent_chat.file_list:
                chat_files = chat_files + parent_chat.file_list

            ignore_documents = chat_files.copy()
            if chat.name:
                ignore_documents.append(f"/{chat.name}")

            if chat_profile_names:
                self.event_manager.chat_event(chat=chat, message=f"Chat profiles: {chat_profile_names}")

            for chat_file in chat_files:
                chat_file_full_path = chat_file
                if self.settings.project_path not in chat_file_full_path and \
                    not os.path.isfile(chat_file_full_path):
                    if chat_file[0] == '/':
                        chat_file = chat_file[1:]
                    chat_file_full_path = f"{self.settings.project_path}/{chat_file}"
                try:
                  with open(chat_file_full_path, 'r') as f:
                      doc_context = document_to_context(
                        Document(page_content=f.read(),
                          metadata={ "source": chat_file }
                        )
                      )
                      messages.append(HumanMessage(content=f"""
                      ATTACHMENT: {chat_file}
                      {doc_context}
                      """))
                except Exception as ex:
                    logger.error(f"Error adding context file to chat {ex}")

            # Prepare AI
            ai_settings = self.settings.get_llm_settings()
            if chat_model:
                ai_settings.model = chat_model
            ai = self.get_ai(llm_model=ai_settings.model)
            tags  = [
                      f"{chat.mode}"
                    ] + [p.name for p in valid_profiles]
            if is_agent:
                tags.append("agent")
            ai_headers = {
              "tags": ",".join(tags)
            }
            def ai_chat(messages=[], prompt="", tags="", callback=None):
                headers = ai_headers
                if tags:
                    headers = { 
                      **ai_headers, 
                      "tags": ai_headers["tags"] + "," + tags 
                    }
                return ai.chat(messages=messages, prompt=prompt, callback=callback, headers=headers)

            if not disable_knowledge and search_projects:
                chat.messages.append(new_chat_message("assistant", content=f"Searching in {[p.project_name for p in search_projects]}"))
                logger.info(f"chat_with_project start project search {search_projects}")
                try:
                    doc_length = 0
                    if query:
                        query_context = "\n".join([message.content for message in messages])
                        search_query = self.create_knowledge_search_query(query=f"{query_context}\n{query}")
          
                        self.event_manager.chat_event(chat=chat, message=f"Knowledge searching for: {search_query}")
                        
                        documents, file_list = self.select_documents_from_knowledge(chat=chat,
                                                                                    query=search_query,
                                                                                    ignore_documents=ignore_documents,
                                                                                    search_projects=search_projects)
                        for doc in documents:
                            doc_context = document_to_context(doc)
                            context += f"{doc_context}\n"
                    
                        response_message.files = file_list
                        doc_length = len(documents)
                    self.event_manager.chat_event(chat=chat, message=f"Knowledge search found {doc_length} relevant documents")
                except Exception as ex:
                    self.event_manager.chat_event(chat=chat, message=f"!!Error searching in knowledge {ex}", event_type="error")
                    logger.exception(f"!!Error searching in knowledge {ex}")
                
            if context:
                messages.append(self.convert_message(
                    new_chat_message(role="user", content=f"""<project_files>{context}</project_files>""")))

            if is_refine:
                existing_document = last_ai_message.content if last_ai_message else "" 
                parent_task = self.get_chat_analysis_parents(chat=chat)
                task_content = ""

                if parent_task:
                    task_content = f"""
                    You are writing a child document.
                    This information comes from the parent document for your information:
                    <parent_document>
                    {parent_task}
                    </parent_document>
                    """
                
                if existing_document:
                    task_content += f"""
                    <document>
                    {existing_document}
                    </document>
                    
                    <comments>
                    {user_message.content}
                    </comments>

                    INSTRUCTIONS:
                     * Update the document with the comments
                     * Return only the document content with comments applied
                    """
                else:
                    task_content += user_message.content

                refine_message = new_chat_message(role="user", content=task_content)
                messages.append(self.convert_message(refine_message))

            elif is_agent:
                refine_message = new_chat_message(role="user", content=f"""
                You are responsible to end this task.
                Follow instructions and try to solve it with the minimum iterations needed.
                <task>
                { chat.name }
                </task>


                <parent_context>
                {self.get_chat_analysis_parents(chat=chat)}
                </parent_context>


                <user_request>
                {user_message.content}
                </user_request>
                
                You still have { iterations_left } attempts more to finish the task. 
                Return { AGENT_DONE_WORD } when the task is done.
                """)
                messages.append(self.convert_message(refine_message))
            else:
                messages.append(self.convert_message(user_message))


            if chat_profiles_content:
                messages[-1].content += f"\nInstructions:\n{chat_profiles_content}"
            self.event_manager.chat_event(chat=chat, message=f"Chatting with {ai_settings.model}")


            if not callback:
                callback = lambda content: send_message_event(content=content, done=False)

            try:
                input_messages_count = len(messages)
                response_messages = ai_chat(messages=messages, callback=callback)
                
                new_message_count = len(response_messages) - input_messages_count
                if new_message_count > 1: # Intermediate reasoning messages                
                    for reasoning_message in response_messages[input_messages_count + 1:-1]:
                        msg = new_chat_message(role=reasoning_message.type, content=reasoning_message.content)
                        msg.hide = True
                        chat.messages.append(msg)
                
                # Resposne message
                message_parts = response_messages[-1].content.replace("<think>", "").split("</think>")
                is_thinking = len(message_parts) == 2
                response_message.think = message_parts[0] if is_thinking else None
                response_message.content = message_parts[-1]
                response_message.is_thinking = False
                send_message_event(content=response_message.content, done=True)
            except Exception as ex:
                logger.exception(f"Error chatting with project: {ex} {chat.id}")
                response_message.content = f"Ops, sorry! There was an error with latest request: {ex}"


            response_message.meta_data["time_taken"] = time.time() - timing_info["start_time"]
            response_message.meta_data["first_chunk_time_taken"] = timing_info["first_response"]
            response_message.meta_data["model"] = ai_settings.model
            response_message.profiles = chat_profile_names
            
            chat.messages.append(response_message)


            # Chat description
            try:
                messages = messages.copy()
                if is_refine:
                    messages=[messages[-1]]
                description_message = ai_chat(messages=messages,
                                            prompt="Create a 5 lines summary of the conversation",
                                            tags="chat-summary")[-1]
                chat.description = description_message.content
            except Exception as ex:
                logger.exception(f"Error chatting with project: {ex} {chat.id}")
                response_message.content = f"Ops, sorry! There was an error with latest request: {ex}"


            if chat_mode == 'task':
                for message in chat.messages[:-1]:
                    if not message.is_answer:
                        message.hide = True


            is_agent_done = AGENT_DONE_WORD in response_message.content
            if is_agent and not is_agent_done and iterations_left:
              self.event_manager.chat_event(chat=chat, message=f"Agent iteration {iteration + 1}")
              return self.chat_with_project(chat=chat,
                    disable_knowledge=disable_knowledge,
                    callback=callback,
                    append_references=append_references,
                    chat_mode=chat_mode,
                    iteration=iteration + 1)
            else:    
              self.event_manager.chat_event(chat=chat, message="done")
            return chat, documents


    def switch_project(self, project_id: str) -> 'ChatEngine':
        """
        Switch to another project based on the provided project ID.

        :param project_id: The ID of the project to switch to.
        :return: The ChatEngine instance after switching the project.
        """
        if not project_id or project_id == self.settings.project_id:
            logger.debug(f"Already in project {project_id}")
            return self
        
        settings = find_project_by_id(project_id=project_id)
        if settings:
            self.settings = settings
            logger.info(f"Switched to project ID {project_id}")
        else:
            logger.warning(f"No settings found for project ID {project_id}")

        return self


    def get_ai(self, llm_model: Optional[str] = None) -> AI:
        """
        Get an AI instance configured for a specific model.

        :param llm_model: The name of the large language model.
        :return: An AI instance.
        """
        ai_instance = AI(settings=self.settings, llm_model=llm_model)
        logger.debug(f"AI instance created with model {llm_model}")
        return ai_instance


    def get_ai_code_generator_changes(self, response: str) -> AICodeGenerator:
        """
        Process the response string to generate AI code generator changes.

        :param response: The string output from the AI model.
        :return: An instance of AICodeGenerator containing the parsed changes.
        """
        code_generator = AICodeGenerator.from_response(response)
        for change in code_generator.code_changes:
            file_path = change.file_path
            if not file_path.startswith(self.settings.project_path):
                change.file_path = os.path.join(self.settings.project_path, file_path)
        
        logger.info(f"Code generator changes retrieved from response")
        return code_generator


    def select_documents_from_knowledge(self, chat: Chat, query: str, ignore_documents=None,
                                                 search_projects=None) -> Tuple[List[Document], List[str]]:
        """
        Select documents from knowledge base that are affected by a given query.

        :param chat: Current chat object.
        :param query: Search query for selecting documents.
        :param ignore_documents: List of documents to ignore during search.
        :param search_projects: Projects to search within.
        :return: Tuple of a list of documents and a list of file paths.
        """
        if search_projects is None:
            search_projects = []
        if ignore_documents is None:
            ignore_documents = []

        def process_rag_query(rag_query: str) -> Tuple[List[Document], List[str]]:
            docs: List[Document] = []
            file_list: Optional[List[str]] = None
            logger.debug(f"Searching projects for query: {rag_query}")
            for search_project in search_projects:
                if chat:
                    self.event_manager.chat_event(chat=chat, message=f"Searching knowledge in {search_project.project_name}")
                knowledge_documents = self.knowledge(settings=settings).search(query)
                
                project_docs, project_file_list = find_relevant_documents(query=rag_query, settings=search_project,knowledge_documents=knowledge_documents, ignore_documents=ignore_documents)
                project_file_list: list[str] = [os.path.join(search_project.project_path, file_path) for file_path in project_file_list]
                docs.extend(project_docs)
                if file_list:
                    file_list.extend(project_file_list)
                else:
                    file_list = project_file_list
            logger.info(f"Documents selected from knowledge: {len(docs)}")
            return docs, file_list

        logger.debug(f"Starting document selection with query: {query}")
        return process_rag_query(query)


    def create_knowledge_search_query(self, query: str) -> str:
        """
        Create a search query string from the input for knowledge base searching.

        :param query: The initial user query.
        :return: A processed query string suitable for knowledge base search.
        """
        ai = self.get_ai()
        enhanced_query = ai.chat(prompt=f"""
        <text>
        {query}
        </text>

        Extract keywords from the text to help searching in the knowledge base.
        Return just the search string without further decoration or comments.
        """)[-1].content.strip()
        
        logger.debug(f"Knowledge search query created: {enhanced_query}")
        return enhanced_query


    def get_query_mentions(self, query: str) -> QueryMentions:
        """
        Extract mentions of profiles and projects from the given query.

        :param query: The user's query string.
        :return: A dictionary containing lists of mentioned profiles and projects.
        """
        chat_utils = ChatUtils(profile_manager=self.get_profile_manager())
        query_mentions: QueryMentions = chat_utils.get_query_mentions(query=query)
        logger.debug(f"Query mentions extracted: {query_mentions}")
        return query_mentions


    def get_chat_analysis_parents(self, chat: Chat):
        """Given a chat, traverse all parents and return all analysis"""
        parent_content = []
        chat_manager = self.get_chat_manager()
        parent_chat = chat_manager.find_by_id(chat.parent_id)
        while parent_chat:
            messages = [message.content for message in parent_chat.messages if not message.hide]
            if messages:
              parent_content.append("\n".join(messages))
            parent_chat = chat_manager.find_by_id(parent_chat.parent_id)
        return "\n".join(parent_content)
    
    @staticmethod
    def convert_message(message):
        def parse_image(image):
            try:
                return json.loads(image)
            except JSONDecodeError as _:
                return {"src": image, "alt": ""}
        if message.images:
            images = [parse_image(image) for image in message.images]
            text_content = {
                "type": "text",
                "text": message.content
            }
            content = [text_content] + [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image["src"]
                    }
                } for image in images]

            # self.log_info(f"ImageMessage content: {content}")
            msg = BaseMessage(type="image", content=json.dumps(content))
        elif message.role == "user":
            msg = HumanMessage(content=message.content)
        else:
            msg = AIMessage(content=message.content)
    
        return msg
        
    def get_all_search_projects(self):
        project_child_projects, project_dependencies = get_project_dependencies(settings=self.settings)
        all_projects = [self.settings] + project_child_projects + project_dependencies
        return all_projects


    def index_chat(self, chat: Chat):
        """
        Index the chat as a Document in the knowledge system.
        Converts valid chat messages into a single Document with appropriate metadata.

        :param chat: The chat to index.
        """
        # Extract valid messages
        valid_messages = [message.content for message in chat.messages if not message.hide and not message.improvement]

        # Create Document from valid messages
        page_content = "\n".join(valid_messages)
        metadata = {
            "source": chat.file_path,
            "parser": "chat",
            "loader_type": "chat"
        }

        # Call the indexing function (assuming it exists)
        try:
            self.knowledge.index_document(page_content, metadata)
            logger.info(f"Chat indexed successfully: {chat.file_path}")
        except Exception as ex:
            logger.exception(f"Failed to index chat: {chat.file_path}, error: {ex}")
