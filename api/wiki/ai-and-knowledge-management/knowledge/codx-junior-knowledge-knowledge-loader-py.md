The `KnowledgeLoader` class is responsible for loading and processing documents from a project's codebase. It integrates with Git to identify relevant files and uses a `KnowledgeCodeSplitter` to extract meaningful content.

### Core Functionality

The `KnowledgeLoader` performs the following key tasks:

1.  **File Identification:** It identifies files within the project's repository, including versioned and unversioned files, and optionally includes files from external folders specified in the settings.
2.  **File Filtering:** It filters files based on several criteria:
    *   **File Size:** Excludes empty files or files larger than 50KB.
    *   **Modification Time:** Excludes files modified within the last 10 minutes to avoid indexing incomplete changes.
    *   **Change Detection:** Checks if a file has been modified since the last indexing by comparing modification times and MD5 checksums.
    *   **Ignore Paths:** Skips files located in paths specified in `knowledge_file_ignore` settings or provided `ignore_paths` during loading.
3.  **Document Extraction:** For each valid file, it uses a `KnowledgeCodeSplitter` to extract document chunks.
4.  **Error Handling:** Logs errors if no documents are generated for a file or if any other exceptions occur during the loading process.
5.  **Repository Fix:** Includes a method `fix_repo` to address common Git ownership issues that might prevent file listing.

### Key Methods

*   `__init__(self, settings: CODXJuniorSettings)`: Initializes the `KnowledgeLoader` with project settings and the project path.
*   `should_index_doc(self, file_path, last_update, current_sources)`: Determines if a document should be indexed based on modification time, size, and existence in previous sources.
*   `is_valid_file(self, file, current_sources_and_updates=None, path=None, current_sources=None, knowledge_file_ignore=[])`: Checks if a given file is valid for indexing based on various criteria including ignore lists and update status.
*   `load(self, current_sources_and_updates: datetime = None, path: str = None, current_sources=None, ignore_paths=[])`: Loads and processes documents from the repository files. It can load all files, a specific file, or files within a given path.
*   `get_git_files(self)`: Retrieves a list of all versioned and unversioned files within the Git repository that are within the project's path.
*   `run_git_command(self, command, cwd: str = None)`: A helper method to execute Git commands and return their output and errors.
*   `list_repository_files(self, current_sources_and_updates = None, path: str = None, current_sources=None, ignore_paths=[])`: Returns a list of files that are candidates for indexing after applying all filtering logic.
*   `list_repository_folders(self)`: Returns a list of unique directory paths containing the files identified for indexing.
*   `fix_repo(self)`: Attempts to fix Git repository issues related to ownership detection.

```python
# /codx/junior/knowledge/knowledge_loader.py
import logging
import os
import time
import subprocess
import pathlib
from datetime import datetime

from langchain_community.document_loaders import DirectoryLoader, TextLoader


from codx.junior.settings import CODXJuniorSettings
from codx.junior.knowledge.knowledge_code_splitter import KnowledgeCodeSplitter
from codx.junior.knowledge.knowledge_code_to_dcouments import KnowledgeCodeToDocuments


from codx.junior.utils.utils import (
  exec_command,
  calculate_md5
)

logger = logging.getLogger(__name__)


class KnowledgeLoader:
    def __init__(self, settings: CODXJuniorSettings):
        self.path = settings.project_path
        self.settings = settings

    def should_index_doc(self, file_path, last_update, current_sources):
        if not last_update:
            return True
        file_stats = os.stat(file_path)
        if file_stats.st_size == 0 or file_stats.st_size > (50 * 1024):
            return False

        # Check if the file was modified within the last 10 minutes
        ten_minutes_ago = time.time() - 10 * 60
        if file_stats.st_mtime > ten_minutes_ago:
            return False
        
        if current_sources: 
            if file_path not in current_sources:
                # New file
                return True
            
            file_md5 = calculate_md5(file_path)
            current_file_md5 = current_sources[file_path].get("file_md5")
            if file_md5 == current_file_md5:
                return False

        last_doc_update = int(os.path.getmtime(file_path))
        logger.info("File last update check last_update: %s - last_doc_update: %s", last_update, last_doc_update)
        
        if not last_update or last_doc_update > last_update:
          return True

        return False

    def is_valid_file(self, file, current_sources_and_updates=None, path=None, current_sources=None, knowledge_file_ignore: [str] =[]):
        if not os.path.isfile(file):
            return False

        if path:
            if not (path in file):
                return False
        file_errors = [err for err in knowledge_file_ignore if err in file]
        if file_errors:
            return False
        last_update = None
        if current_sources_and_updates and file in current_sources_and_updates:
            last_update = current_sources_and_updates[file]["metadata"]["last_update"]
            last_update = datetime.fromisoformat(last_update)
            
        if not self.should_index_doc(file_path=file, last_update=last_update, current_sources=current_sources):
            return False
    
        return True

    def load(self, current_sources_and_updates: datetime = None, path: str = None, current_sources=None, ignore_paths=[]):
        documents = []
        code_splitter = KnowledgeCodeSplitter(settings=self.settings)
        #code_splitter = KnowledgeCodeToDocuments(settings=self.settings)
        files = self.list_repository_files(
            path=path,
            current_sources_and_updates=current_sources_and_updates,
            current_sources=current_sources,
            ignore_paths=ignore_paths
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

        bad_docs = [doc for doc in documents if not doc.page_content]
        good_docs = [doc for doc in documents if doc.page_content]
        if bad_docs:
            logger.debug(f"Loaded {len(documents)} documents from {len(files)} files. OK: {len(good_docs)} ERROR: {len(bad_docs)}")
        return good_docs

    def get_git_files(self):
        git_parent_folder, _ = exec_command("git rev-parse --git-dir", cwd=self.path)
        git_parent_folder = git_parent_folder.strip()
        
        # logger.info(f"git_parent_folder: '{git_parent_folder}'")
        
        git_parent = self.path
        if "/.git" in git_parent_folder:
            git_parent = git_parent_folder.replace("/.git", "")
        
        # Versioned files
        versioned_files, _ = self.run_git_command(['git', 'ls-files'], cwd=git_parent)
        # Unversioned files
        unversioned_files, _ = self.run_git_command(['git', 'ls-files', '--others', '--exclude-standard'], cwd=git_parent)
        
        # joining versioned and unversioned file paths
        full_file_paths = [os.path.join(git_parent, file_path) for file_path in versioned_files + unversioned_files]

        current_path_files = [f for f in full_file_paths if f.startswith(self.path)]
        
        # logger.info(f"""list_repository_files checking {self.path}: 
        # git root: {git_parent_folder}
        # git_parent: {git_parent}
        # git files {len(full_file_paths)}
        # this folder files {len(current_path_files)}
        # """)
        return current_path_files

    def run_git_command(self, command, cwd: str = None):
        if not cwd:
            cwd = self.path
        result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        file_paths = result.stdout.decode('utf-8').split('\n')
        error = result.stderr.decode('utf-8') if result.stderr else None
        return file_paths, error

    def list_repository_files(self, current_sources_and_updates = None, path: str = None, current_sources=None, ignore_paths=[]):        
        full_file_paths = None
        if path:
            if os.path.isfile(path):
                full_file_paths = [path]
            else:  
                full_file_paths = [str(file_path) for file_path in pathlib.Path(path).rglob("*")]
            logging.info(f"Indexing {full_file_paths}")
        else:
            
            # filter if we are in a sub-path
            full_file_paths = self.get_git_files()
                        
            if self.settings.knowledge_external_folders:
                for ext_path in self.settings.knowledge_external_folders.split(","):
                    external_file_paths = [str(file_path) for file_path in pathlib.Path(ext_path).rglob("*")]
                    full_file_paths = full_file_paths + external_file_paths

        knowledge_file_ignore = self.settings.knowledge_file_ignore or ""
        knowledge_file_ignore = ignore_paths + [ignore for ignore in knowledge_file_ignore.split(",") if len(ignore.strip())]
        # logger.info(f"knowledge ignore files {knowledge_file_ignore}")
        changed_file_paths = [file for file in full_file_paths \
                            if self.is_valid_file(file,
                                current_sources_and_updates=current_sources_and_updates,
                                path=path,
                                current_sources=current_sources,
                                knowledge_file_ignore=knowledge_file_ignore) ]
        
        return changed_file_paths

    def list_repository_folders(self):
        all_files = self.list_repository_files()
        return list(set([os.path.dirname(file_path) for file_path in all_files]))

    def fix_repo(self):
        _, error = self.run_git_command(['git', 'ls-files'])
        if error and "detected dubious ownership in repository" in error:
            fix = [err for err in error.split("\n") if "git config" in err][0]
            logging.info(f"Fixing git error {fix}")
            self.run_git_command(fix.strip().split(" "))

```