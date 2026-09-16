"""
WorkspaceFileGenerator — AI-powered generation of Docker and config files for workspaces.

Generates docker-compose.yaml, Dockerfile, .env, and other configuration files
based on workspace definition using AI.
"""

import os
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from langchain.messages import HumanMessage, SystemMessage

from codx.junior.settings import CODXJuniorSettings
from codx.junior.ai import AI
from codx.junior.workspaces.model import Workspace, WorkspaceApp
from codx.junior.model.model import CodxUser

logger = logging.getLogger(__name__)


# ---- AI Prompts ----

DOCKER_COMPOSE_PROMPT = """
Generate a production-ready docker-compose.yaml for a workspace with the following requirements:

Workspace Name: {workspace_name}
Description: {workspace_description}
Apps to run:
{apps_list}

CPU Limit: {cpu_limit}
Memory Limit: {memory_limit}
Use Sysbox: {use_sysbox}

Requirements:
1. Include a Traefik reverse proxy service for routing
2. Create services for each app with proper port mappings
3. Use environment variables for configuration
4. Include proper networking setup
5. Add health checks where applicable
6. Use meaningful container names and service names
7. Include volume mounts for data persistence if needed
8. For VNC apps, use port 6080 by default and scheme https
9. Return ONLY the yaml content, no markdown code fences or explanations

Docker Compose version: 3.8
Base image recommendation: ubuntu:22.04 or appropriate language-specific image
"""

DOCKERFILE_PROMPT = """
Generate a production-ready Dockerfile for a workspace application with the following specs:

App Name: {app_name}
App Description: {app_description}
Base Image: {base_image}
Exposed Port: {port}
Requirements:
1. Include proper layer caching optimization
2. Use multi-stage builds if applicable
3. Include security best practices (non-root user)
4. Set appropriate working directory
5. Install minimal dependencies
6. Include health check if applicable
7. Return ONLY the Dockerfile content, no markdown code fences or explanations

Additional Context:
- This app runs inside a workspace container
- It should be stateless and scalable
"""

ENV_FILE_PROMPT = """
Generate a .env file for workspace configuration with these settings:

Workspace Name: {workspace_name}
Apps: {apps_list}
CPU: {cpu_limit}
Memory: {memory_limit}

Include:
1. Workspace-level variables (name, description, id)
2. Service discovery variables
3. Performance tuning variables (based on resources)
4. Security variables where needed
5. Comments explaining each variable

Return ONLY the .env content, no markdown code fences or explanations.
"""

NGINX_CONFIG_PROMPT = """
Generate an nginx configuration file for routing workspace apps with the following setup:

Apps:
{apps_list}

Requirements:
1. Create upstream definitions for each app
2. Set up server blocks with proper SSL configuration
3. Add compression and caching headers
4. Include security headers (HSTS, CSP, etc.)
5. Configure logging
6. Add rate limiting if needed

Return ONLY the nginx config content, no markdown code fences or explanations.
"""


class WorkspaceFileGenerator:
    """
    Generates Docker and configuration files for workspaces using AI.
    
    Supports generation of:
    - docker-compose.yaml
    - Dockerfile
    - .env files
    - nginx configuration
    - Other config files
    """

    def __init__(self, settings: CODXJuniorSettings):
        """
        Initialize the generator with project settings.
        
        Args:
            settings: CODXJuniorSettings instance for the project.
        """
        self.settings = settings
        self._ai: Optional[AI] = None
        logger.debug("WorkspaceFileGenerator initialized")

    def _get_ai(self) -> AI:
        """
        Lazily initialize and return AI instance.
        
        Returns:
            Configured AI instance.
        """
        if not self._ai:
            self._ai = AI(
                settings=self.settings,
                llm_model=self.settings.get_llm_settings().model,
                user=CodxUser(username="workspace-generator"),
            )
        return self._ai

    async def generate_docker_compose(
        self,
        workspace: Workspace
    ) -> str:
        """
        Generate docker-compose.yaml for a workspace using AI.
        
        Args:
            workspace: Workspace definition.
            
        Returns:
            Generated docker-compose.yaml content as string.
        """
        apps_list = self._format_apps_for_prompt(workspace.apps)
        
        prompt_content = DOCKER_COMPOSE_PROMPT.format(
            workspace_name=workspace.name,
            workspace_description=workspace.description or "Development workspace",
            apps_list=apps_list,
            cpu_limit=workspace.resources.cpus or "2",
            memory_limit=workspace.resources.memory or "4g",
            use_sysbox="yes" if workspace.use_sysbox else "no"
        )
        
        try:
            ai = self._get_ai()
            messages = [
                SystemMessage(content="You are an expert Docker and DevOps engineer."),
                HumanMessage(content=prompt_content),
            ]
            response = ai.chat(messages=messages)
            content = response[-1].content.strip()
            
            # Clean up any markdown code fences
            content = self._strip_code_fences(content, "yaml")
            
            logger.info(
                "Generated docker-compose.yaml for workspace '%s'",
                workspace.name
            )
            return content
        except Exception as ex:
            logger.exception(
                "Error generating docker-compose for workspace '%s': %s",
                workspace.name,
                ex
            )
            raise

    async def generate_dockerfile(
        self,
        app: WorkspaceApp,
        base_image: str = "ubuntu:22.04"
    ) -> str:
        """
        Generate Dockerfile for a workspace app using AI.
        
        Args:
            app: WorkspaceApp definition.
            base_image: Base Docker image to use.
            
        Returns:
            Generated Dockerfile content as string.
        """
        prompt_content = DOCKERFILE_PROMPT.format(
            app_name=app.name,
            app_description=app.description or "Workspace application",
            base_image=base_image,
            port=app.port or 8080
        )
        
        try:
            ai = self._get_ai()
            messages = [
                SystemMessage(content="You are an expert Docker and DevOps engineer."),
                HumanMessage(content=prompt_content),
            ]
            response = ai.chat(messages=messages)
            content = response[-1].content.strip()
            
            # Clean up any markdown code fences
            content = self._strip_code_fences(content, "dockerfile")
            
            logger.info(
                "Generated Dockerfile for app '%s'",
                app.name
            )
            return content
        except Exception as ex:
            logger.exception(
                "Error generating Dockerfile for app '%s': %s",
                app.name,
                ex
            )
            raise

    async def generate_env_file(
        self,
        workspace: Workspace
    ) -> str:
        """
        Generate .env file for workspace configuration using AI.
        
        Args:
            workspace: Workspace definition.
            
        Returns:
            Generated .env content as string.
        """
        apps_list = self._format_apps_for_prompt(workspace.apps)
        
        prompt_content = ENV_FILE_PROMPT.format(
            workspace_name=workspace.name,
            apps_list=apps_list,
            cpu_limit=workspace.resources.cpus or "2",
            memory_limit=workspace.resources.memory or "4g"
        )
        
        try:
            ai = self._get_ai()
            messages = [
                SystemMessage(content="You are an expert in Docker and environment configuration."),
                HumanMessage(content=prompt_content),
            ]
            response = ai.chat(messages=messages)
            content = response[-1].content.strip()
            
            # Clean up any markdown code fences
            content = self._strip_code_fences(content, "bash")
            
            logger.info(
                "Generated .env file for workspace '%s'",
                workspace.name
            )
            return content
        except Exception as ex:
            logger.exception(
                "Error generating .env for workspace '%s': %s",
                workspace.name,
                ex
            )
            raise

    async def generate_nginx_config(
        self,
        workspace: Workspace
    ) -> str:
        """
        Generate nginx configuration for workspace routing using AI.
        
        Args:
            workspace: Workspace definition.
            
        Returns:
            Generated nginx.conf content as string.
        """
        apps_list = self._format_apps_for_prompt(workspace.apps)
        
        prompt_content = NGINX_CONFIG_PROMPT.format(
            apps_list=apps_list
        )
        
        try:
            ai = self._get_ai()
            messages = [
                SystemMessage(content="You are an expert in nginx configuration and web server security."),
                HumanMessage(content=prompt_content),
            ]
            response = ai.chat(messages=messages)
            content = response[-1].content.strip()
            
            # Clean up any markdown code fences
            content = self._strip_code_fences(content, "nginx")
            
            logger.info(
                "Generated nginx.conf for workspace '%s'",
                workspace.name
            )
            return content
        except Exception as ex:
            logger.exception(
                "Error generating nginx config for workspace '%s': %s",
                workspace.name,
                ex
            )
            raise

    async def generate_all_files(
        self,
        workspace: Workspace,
        target_folder: str
    ) -> Dict[str, str]:
        """
        Generate all configuration files for a workspace and save them to disk.
        
        Args:
            workspace: Workspace definition.
            target_folder: Folder path where files will be saved.
            
        Returns:
            Dict mapping file names to their generated content.
        """
        os.makedirs(target_folder, exist_ok=True)
        
        generated_files: Dict[str, str] = {}
        
        try:
            # Generate docker-compose.yaml
            logger.info("Generating docker-compose.yaml for workspace '%s'", workspace.name)
            docker_compose_content = await self.generate_docker_compose(workspace)
            docker_compose_path = os.path.join(target_folder, "docker-compose.yaml")
            with open(docker_compose_path, "w", encoding="utf-8") as f:
                f.write(docker_compose_content)
            generated_files["docker-compose.yaml"] = docker_compose_content
            logger.info("Saved docker-compose.yaml to '%s'", docker_compose_path)
            
            # Generate .env file
            logger.info("Generating .env file for workspace '%s'", workspace.name)
            env_content = await self.generate_env_file(workspace)
            env_path = os.path.join(target_folder, ".env")
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(env_content)
            generated_files[".env"] = env_content
            logger.info("Saved .env to '%s'", env_path)
            
            # Generate nginx config
            if workspace.apps:
                logger.info("Generating nginx.conf for workspace '%s'", workspace.name)
                nginx_content = await self.generate_nginx_config(workspace)
                nginx_path = os.path.join(target_folder, "nginx.conf")
                with open(nginx_path, "w", encoding="utf-8") as f:
                    f.write(nginx_content)
                generated_files["nginx.conf"] = nginx_content
                logger.info("Saved nginx.conf to '%s'", nginx_path)
            
            # Generate Dockerfiles for each app
            for app in workspace.apps:
                if app.name:
                    logger.info("Generating Dockerfile for app '%s'", app.name)
                    dockerfile_content = await self.generate_dockerfile(app)
                    app_folder = os.path.join(target_folder, app.name)
                    os.makedirs(app_folder, exist_ok=True)
                    dockerfile_path = os.path.join(app_folder, "Dockerfile")
                    with open(dockerfile_path, "w", encoding="utf-8") as f:
                        f.write(dockerfile_content)
                    generated_files[f"{app.name}/Dockerfile"] = dockerfile_content
                    logger.info("Saved Dockerfile to '%s'", dockerfile_path)
            
            logger.info(
                "Successfully generated %d files for workspace '%s'",
                len(generated_files),
                workspace.name
            )
            return generated_files
            
        except Exception as ex:
            logger.exception(
                "Error generating files for workspace '%s': %s",
                workspace.name,
                ex
            )
            raise

    @staticmethod
    def _format_apps_for_prompt(apps: List[WorkspaceApp]) -> str:
        """
        Format apps list for AI prompt.
        
        Args:
            apps: List of WorkspaceApp objects.
            
        Returns:
            Formatted string for prompt.
        """
        if not apps:
            return "No apps defined"
        
        lines = []
        for i, app in enumerate(apps, 1):
            lines.append(
                f"{i}. {app.name}: {app.description or 'N/A'} "
                f"(port: {app.port or 'auto'}, "
                f"vnc: {'yes' if app.is_vnc else 'no'})"
            )
        return "\n".join(lines)

    @staticmethod
    def _strip_code_fences(content: str, language: str = "") -> str:
        """
        Remove markdown code fences from content.
        
        Args:
            content: Content string potentially wrapped in code fences.
            language: Language identifier (optional, for matching).
            
        Returns:
            Content without code fences.
        """
        lines = content.split("\n")
        result = []
        skip = False
        
        for line in lines:
            # Check for opening fence
            if line.strip().startswith("```"):
                skip = not skip
                continue
            
            if not skip:
                result.append(line)
        
        return "\n".join(result).strip()