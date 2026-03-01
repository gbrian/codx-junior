import logging
import re, json
import os
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from dotenv import load_dotenv
from azure.core.serialization import AzureJSONEncoder
from pydantic import BaseModel
from typing import List, Optional

logger = logging.getLogger(__name__)


class ThreadModel(BaseModel):
    status: Optional[str] = None
    file_path: Optional[str] = None
    line: Optional[int] = None
    comments: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)


class AzureDevopsPullRequestPlugin:
    def __init__(self, personal_access_token: str, organization_url: str, project_path: str):
        # Set up the Personal Access Token (PAT) and organization URL
        self.personal_access_token = personal_access_token
        self.organization_url = organization_url
        self.project_path = project_path

        logger.info(f"Settings {self.organization_url} {self.personal_access_token[0:10]}")

        # Establish a connection to Azure DevOps
        self.credentials = BasicAuthentication('', self.personal_access_token)
        self.connection = Connection(base_url=self.organization_url, creds=self.credentials)

    def as_json(self, az_obj: object) -> dict:
        if not az_obj:
            return {}
        as_string = json.dumps(az_obj.as_dict(), cls=AzureJSONEncoder)
        return json.loads(as_string)

    def read_threads(self, pr_url: str) -> List[ThreadModel]:
        match = re.search(r'https://dev.azure.com/(?P<org>.+?)/(?P<project>.+?)/_git/(?P<repo>.+?)/pullrequest/(?P<pr_id>.+?)$', pr_url)
        if not match:
            raise ValueError("Invalid pull request URL")

        organization, project, repo, pr_id = match.groups()
        git_client = self.connection.clients.get_git_client()
        threads = git_client.get_threads(
            repository_id=repo,
            pull_request_id=int(pr_id),
            project=project
        )
        return [ThreadModel(**{
            "status": thread.status,
            "file_path": thread.thread_context.file_path,
            "line": (thread.thread_context.right_file_start.line 
                     if thread.thread_context.right_file_start 
                     else thread.thread_context.left_file_start.line),
            "comments": " ".join(comment.content for comment in thread.comments)
        }) for thread in threads if thread.thread_context]
    
    def modify_file_content(self, file_contents: List[str], comments_to_insert: List[tuple]) -> List[str]:
        logger.debug("Modifying file content with comments.")
        comments_to_insert.sort()  # Ensure the comments are processed in line number order

        new_file_contents = []
        last_line = 0

        for line_num, content in comments_to_insert:
            logger.debug(f"Inserting comment on line {line_num}: {content}")
            if line_num > len(file_contents):
                last_line = len(file_contents)
                break
            new_file_contents.extend(file_contents[last_line:line_num])  # Add content up to the comment line
            new_file_contents.append(f'<codx-ok, please-wait...>{content}</codx-ok, please-wait...>\n')  # Add the comment
            last_line = line_num

        new_file_contents.extend(file_contents[last_line:])  # Add remaining content

        return new_file_contents

    def insert_comments_into_files(self, threads: List[ThreadModel]):
        logger.debug("Started inserting comments into files.")
        comments_by_file = {}
        for thread in threads:
            logger.debug(f"Processing thread: {thread}")
            if thread.status.lower() == 'active':
                file_path = thread.file_path
                if file_path not in comments_by_file:
                    comments_by_file[file_path] = []

                comments_by_file[file_path].append((thread.line, thread.comments))

        for file_path, comments_to_insert in comments_by_file.items():
            logger.debug(f"Processing file: {file_path}")
            abs_file_path = os.path.join(self.project_path, file_path)
            with open(abs_file_path, 'r') as file:
                file_contents = file.readlines()

            new_file_contents = self.modify_file_content(file_contents, comments_to_insert)

            with open(abs_file_path, 'w') as file:
                file.writelines(new_file_contents)
            logger.info(f"Comments inserted in {file_path}")
        logger.debug("Finished inserting all active comments successfully.")
    
    def apply_pr_comments_to_files(self, pr_url: str):
        threads = self.read_threads(pr_url)
        self.insert_comments_into_files(threads)

# Example instantiation and method invocation:
# plugin = AzureDevopsPullRequestPlugin(personal_access_token, organization_url, project_path)
# plugin.apply_pr_comments_to_files('https://dev.azure.com/world2meet/W2Fly/_git/app-mvn-mro-management-api/pullrequest/160928')