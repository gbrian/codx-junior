import os
import json
import logging
import pathlib
import uuid
import traceback

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from codx.junior.utils.utils import (
  exec_command
)
from codx.junior.model.model import (
    GlobalSettings,
    AISettings,
    AIModel,
    AIProvider
)

logger = logging.getLogger(__name__)

GLOBAL_SETTINGS = None
HOME=os.environ.get("HOME")

GLOBAL_SETTINGS_FOLDER=os.environ.get("CODX_JUNIOR_CONFIG_FOLDER", HOME)
GLOBAL_SETTINGS_PATH=f"{GLOBAL_SETTINGS_FOLDER}/global_settings.json"

def backup_up_global_settings():
    backup_dir = os.path.join(os.path.dirname(GLOBAL_SETTINGS_PATH), "codx-junior-backup")
    os.makedirs(backup_dir, exist_ok=True)
    
    # Create a backup file name with the current date and time
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"global_settings_backup_{timestamp}.json")
    logger.info("Saving global_settings backup: %s", backup_file)
    try:
        with open(GLOBAL_SETTINGS_PATH, "r") as f:
            settings_data = f.read()
        
        with open(backup_file, "w") as f:
            f.write(settings_data)
    except Exception as ex:
        logger.error(f"Error backing up global settings: {ex}")

    try:        
        # Maintain only the last 20 backups
        backups = sorted(pathlib.Path(backup_dir).glob("global_settings_backup_*.json"), key=os.path.getmtime)
        if len(backups) > 20:
            for old_backup in backups[:-20]:
                old_backup.unlink()
    except Exception as ex:
        logger.error(f"Error cleaning up global backup settings: {ex}")


logger.info(f"GLOBAL_SETTINGS_PATH is: {GLOBAL_SETTINGS_PATH}")

def get_global_settings():
    return GLOBAL_SETTINGS

def get_provider_settings(ai_provider: str, global_settings = None) -> AIProvider:
    global_settings = global_settings or GLOBAL_SETTINGS
    ai_provider_settings = [p for p in global_settings.ai_providers if p.name == ai_provider]
    if not ai_provider_settings:
        raise Exception(f"LLM AI provider not found: {ai_provider}")
    
    ai_provider = ai_provider_settings[0]
    ai_provider.api_url = os.path.expandvars(ai_provider.api_url or "")
    ai_provider.api_key = os.path.expandvars(ai_provider.api_key or "")

    return ai_provider

def get_model(llm_model: str, global_settings = None) -> AIModel:
    global_settings = global_settings or GLOBAL_SETTINGS
    return next((m for m in global_settings.ai_models if m.name == llm_model or m.ai_model == llm_model), None)

def save_model(model: AIModel, global_settings = None) -> AIModel:
    global_settings = read_global_settings()
    global_settings.ai_models = [m for m in global_settings.ai_models if m.name != model.name] + [model]
    write_global_settings(global_settings=global_settings)

def get_model_settings(llm_model: str, global_settings = None) -> AISettings:
    global_settings = global_settings or GLOBAL_SETTINGS
    model_settings = get_model(llm_model, global_settings)

    if not model_settings:
        raise Exception(f"LLM model not found: {llm_model}")
    model: AIModel = model_settings
    provider = get_provider_settings(model.ai_provider, global_settings=global_settings)
    ai_settings = AISettings(
        **model.settings.__dict__,
        provider=provider.provider,
        provider_type=provider.provider,
        api_url=provider.api_url,
        api_key=provider.api_key,
        model=model.ai_model or model.name,
        model_type=model.model_type,
        system=model.system,
        prompt_template=model.prompt_template,
        url=model.url
    )
    return ai_settings

def read_global_settings():
    global GLOBAL_SETTINGS
    try:
        with open(GLOBAL_SETTINGS_PATH) as f:
            GLOBAL_SETTINGS = GlobalSettings(**json.loads(f.read()))
    except Exception as ex:
        logger.error(f"Error {ex} loading global settings from {GLOBAL_SETTINGS_PATH}")
        GLOBAL_SETTINGS = GlobalSettings()
        write_global_settings(GLOBAL_SETTINGS)
    return GLOBAL_SETTINGS


def write_global_settings(global_settings: GlobalSettings):
    global GLOBAL_SETTINGS
    logger.exception(f"WRITE GLOBAL_SETTINGS ({GLOBAL_SETTINGS_PATH}): {global_settings}, \n{traceback.format_stack()}")
    try:
        global_settings_data = json.dumps(global_settings.dict(), indent=2)

        backup_up_global_settings()
        
        with open(GLOBAL_SETTINGS_PATH, "w") as f:
            f.write(global_settings_data)

        if global_settings.git.username:
            exec_command(
                f'git config --global user.name "{global_settings.git.username}"'
            )
        if global_settings.git.email:
            exec_command(f'git config --global user.email "{global_settings.git.email}"')

        GLOBAL_SETTINGS = global_settings
    except Exception as ex:
        logger.exception(f"Error saving global settings: {ex}: \n {global_settings}")

def get_oauth_provider(oauth_provider: str):
    global_settings = read_global_settings()
    return next((provider for provider in global_settings.oauth_providers \
                if provider.name == oauth_provider), None)

read_global_settings()
# logger.info(f"GLOBAL_SETTINGS: {GLOBAL_SETTINGS}")
