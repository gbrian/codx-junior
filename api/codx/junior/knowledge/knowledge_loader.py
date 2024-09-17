
import logging
import os
import time
import subprocess
import pathlib
from datetime import datetime

from langchain.document_loaders.generic import GenericLoader
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import CharacterTextSplitter

from gpt_engineer.utils import calculate_md5
from gpt_engineer.core.settings import GPTEngineerSettings
from gpt_engineer.knowledge.knowledge_code_splitter import KnowledgeCodeSplitter
from gpt_engineer.knowledge.knowledge_code_to_dcouments import KnowledgeCodeToDocuments

logger = logging.getLogger(__name__)


class KnowledgeLoader:
    def __init__(self, settings: GPTEngineerSettings):
        self.path = settings.project_path
        self.settings = settings
        self.text_splitter = CharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=500, chunk_overlap=0
        )

    def should_index_doc(self, file_path, last_update, current_sources):
        if not last_update:
            return True
        file_stats = os.stat(file_path)
        if file_stats.st_size == 0:
            return False

        if current_sources: 
            if file_path not in current_sources:
                # New file
                return True
            
            file_md5 = calculate_md5(file_path)
            current_file_md5 = current_sources[file_path].get("file_md5")
            if file_md5 == current_file_md5:
                return False

        last_doc_update = os.path.getmtime(file_path)
        if last_doc_update > last_update:
          return True

        return False

    def is_valid_file(self, file, last_update=None, path=None, current_sources=None):
        if not os.path.isfile(file):
            return False

        if path:
            if not (path in file):
                return False
        
        file_errors = [err for err in self.settings.knowledge_file_ignore.split(",") if err in file]
        if file_errors:
            return False
        
        if not self.should_index_doc(file_path=file, last_update=last_update, current_sources=current_sources):
            return False
    
        return True

    def load(self, last_update: datetime = None, path: str = None, current_sources=None):
        documents = []
        code_splitter = KnowledgeCodeSplitter()
        #code_splitter = KnowledgeCodeToDocuments(settings=self.settings)
        files = self.list_repository_files(
            last_update=last_update, path=path, current_sources=current_sources
        )
        for file_path in files:
            try:
                new_docs = code_splitter.load(file_path)
                if not new_docs:
                    logging.error(f"No documents generated for: {file_path}")
                    continue
                documents = documents + new_docs
            except Exception as ex:
                logging.exception(f"Error loading file {file_path}")  
        logger.debug(f"Loaded {len(documents)} documents from {len(files)} files")
        return documents

    def run_command(self, command):
        result = subprocess.run(command, cwd=self.path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        file_paths = result.stdout.decode('utf-8').split('\n')
        error = result.stderr.decode('utf-8') if result.stderr else None
        return file_paths, error

    def list_repository_files(self, last_update = None, path: str = None, current_sources=None):        
        full_file_paths = None
        if path:
            if os.path.isfile(path):
                full_file_paths = [path]
            else:  
                full_file_paths = [str(file_path) for file_path in pathlib.Path(path).rglob("*")]
            logging.info(f"Indexing {full_file_paths}")
        else:
            # Versioned files
            versioned_files, _ = self.run_command(['git', 'ls-files'])
            # Unversioned files
            unversioned_files, _ = self.run_command(['git', 'ls-files', '--others', '--exclude-standard'])
            # joining versioned and unversioned file paths
            full_file_paths = [os.path.join(self.path, file_path) for file_path in versioned_files + unversioned_files]
                        
            if self.settings.knowledge_external_folders:
                for ext_path in self.settings.knowledge_external_folders.split(","):
                    external_file_paths = [str(file_path) for file_path in pathlib.Path(ext_path).rglob("*")]
                    full_file_paths = full_file_paths + external_file_paths
        changed_file_paths = [file for file in full_file_paths \
                            if self.is_valid_file(file, last_update=last_update, path=path, current_sources=current_sources) ]
        
        return changed_file_paths

    def list_repository_folders(self):
        all_files = self.list_repository_files()
        return list(set([os.path.dirname(file_path) for file_path in all_files]))

    def fix_repo(self):
        _, error = self.run_command(['git', 'ls-files'])
        if error and "detected dubious ownership in repository" in error:
            fix = [err for err in error.split("\n") if "git config" in err][0]
            logging.info(f"Fixing git error {fix}")
            self.run_command(fix.strip().split(" "))

