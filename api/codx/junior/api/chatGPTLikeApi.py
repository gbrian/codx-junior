import logging
import datetime
from fastapi import APIRouter, Request

from codx.junior.engine import (
  CODXJuniorSession,
  find_all_projects
)
from codx.junior.profiles.profile_manager import ProfileManager

logger = logging.getLogger(__name__)

def get_active_profiles_for_api():
    active_profiles = []
    for project in find_all_projects().values():
        profile_manager = ProfileManager(settings=project)
        profiles = profile_manager.list_profiles()
        for profile in profiles:
            try:
                if profile.api_settings.active:
                    active_profiles.append({
                      "name": profile.api_settings.model_name or f"{project.project_name}/{profile.name}",
                      "description": profile.api_settings.description or profile.description,
                    })
            except AttributeError:
                continue  # In case `api_settings` or expected fields are not present
    return active_profiles

router = APIRouter()

@router.get("/v1/models", tags=["chatgpt"])
async def list_models():
    return {"object": "list", "data": get_active_profiles_for_api()}


@router.post("/v1/completions", tags=["chatgpt"])
async def create_completion(request: Request):
    body = await request.json()
    model = body.get("model")
    project_name, profile_name = model.split("/")
    project = [p for p in find_all_projects().values() if p.project_name == project_name][0]
    session = CODXJuniorSession(settings=project)
    messages = body.get("messages")
    chat = await session.api_chat_with_project(profile_name=profile_name, messages=messages)
    completion_response = {
        "id": chat.name,
        "object": "chat.completion",
        "created": datetime.datetime.now(),
        "model": model,
        "choices": [
          {
            "index": 0,
            "message": {
              "role": "assistant",
              "content": chat.messages[-1].content,
              "refusal": None,
              "annotations": []
            },
            "logprobs": None,
            "finish_reason": "stop"
          }
        ],
        "usage": {
          "prompt_tokens": 19,
          "completion_tokens": 10,
          "total_tokens": 29,
          "prompt_tokens_details": {
            "cached_tokens": 0,
            "audio_tokens": 0
          },
          "completion_tokens_details": {
            "reasoning_tokens": 0,
            "audio_tokens": 0,
            "accepted_prediction_tokens": 0,
            "rejected_prediction_tokens": 0
          }
        },
        "service_tier": "default"
      }

    return completion_response