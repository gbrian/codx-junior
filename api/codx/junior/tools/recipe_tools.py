"""
Recipe tools for codx-junior.

Provides tools for discovering, instantiating, and managing recipes
(tutorials, automations, workflows, playbooks).

Made with ❤️ by codx-junior
"""
import logging
from typing import Optional

from codx.junior.settings import CODXJuniorSettings
from codx.junior.recipe_manager import RecipeManager
from .model import ToolResponse

logger = logging.getLogger(__name__)


def list_recipes(
    recipe_type: Optional[str] = None,
    tags: Optional[str] = None,
    **kwargs,
) -> ToolResponse:
    """
    List available recipe templates.

    Args:
        recipe_type: Filter by type ('tutorial', 'automation', 'workflow', 'playbook')
        tags: Comma-separated tags to filter by

    Returns:
        ToolResponse with recipe list
    """
    settings: CODXJuniorSettings = kwargs.get("settings")
    if not settings:
        raise Exception("Invalid project settings")

    manager = RecipeManager(settings=settings)
    
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    templates = manager.list_templates(
        recipe_type=recipe_type,
        tags=tag_list,
    )

    if not templates:
        msg = f"No recipes found"
        if recipe_type:
            msg += f" of type '{recipe_type}'"
        if tags:
            msg += f" with tags '{tags}'"
        return ToolResponse(
            user_response=f"{msg}.",
            llm_response=msg,
        )

    lines = ["## Available Recipes\n"]
    for t in templates:
        lines.append(
            f"**{t['name']}** ({t['recipe_type']}) — `{t['recipe_id']}`"
        )
        lines.append(f"  {t['description']}")
        if t['goal']:
            lines.append(f"  Goal: {t['goal']}")
        lines.append(f"  {t['step_count']} steps | v{t['version']}")
        if t['tags']:
            lines.append(f"  Tags: {', '.join(t['tags'])}")
        lines.append("")

    return ToolResponse(
        user_response="\n".join(lines),
        llm_response=(
            f"Found {len(templates)} recipe templates. "
            + (f"Type: {recipe_type}. " if recipe_type else "")
            + (f"Tags: {tags}. " if tags else "")
        ),
    )


def start_recipe(recipe_id: str, **kwargs) -> ToolResponse:
    """
    Create a live recipe instance from a template.

    Args:
        recipe_id: The template recipe_id to instantiate

    Returns:
        ToolResponse confirming instance creation
    """
    settings: CODXJuniorSettings = kwargs.get("settings")
    if not settings:
        raise Exception("Invalid project settings")

    user = kwargs.get("user")
    user_id = user.username if user else None

    manager = RecipeManager(settings=settings)
    
    try:
        instance = manager.create_instance(
            template_id=recipe_id,
            user_id=user_id,
        )
    except ValueError as e:
        return ToolResponse(
            user_response=f"❌ Could not start recipe: {e}",
            llm_response=f"Recipe instantiation failed: {e}",
        )

    step_lines = []
    for step in instance.steps:
        status_icon = "⬜"
        step_lines.append(
            f"{status_icon} Step {step.step_index}: **{step.name}** "
            f"({step.step_type}) — `{step.chat_id}`"
        )
        if step.description:
            step_lines.append(f"   {step.description}")

    lines = [
        f"🚀 Recipe **{instance.name}** started!",
        f"Instance ID: `{instance.id}`",
        f"Type: {instance.recipe_type}",
        f"Steps: {len(instance.steps)}",
        "",
        *step_lines,
    ]

    return ToolResponse(
        user_response="\n".join(lines),
        llm_response=(
            f"Recipe instance '{instance.id}' created from template '{recipe_id}' "
            f"with {len(instance.steps)} steps."
        ),
    )


def get_recipe_progress(recipe_id: str, **kwargs) -> ToolResponse:
    """
    Get progress summary for a recipe instance.

    Args:
        recipe_id: The instance recipe_id

    Returns:
        ToolResponse with progress details
    """
    settings: CODXJuniorSettings = kwargs.get("settings")
    if not settings:
        raise Exception("Invalid project settings")

    manager = RecipeManager(settings=settings)
    
    try:
        progress = manager.get_progress(recipe_id=recipe_id)
    except ValueError as e:
        return ToolResponse(
            user_response=f"❌ Recipe not found: {e}",
            llm_response=f"Could not fetch recipe progress: {e}",
        )

    m = progress["metrics"]
    pct = m.get("completion_percent", 0)
    
    lines = [
        f"## Recipe Progress: **{progress['name']}**",
        f"Progress: {pct}% complete",
        f"Steps: {m.get('completed_steps', 0)}/{m.get('total_steps', 0)} done, "
        f"{m.get('failed_steps', 0)} failed",
        "",
    ]

    for step in progress["steps"]:
        status_icons = {
            "completed": "✅",
            "in_progress": "🔄",
            "skipped": "⏭️",
            "failed": "❌",
        }
        icon = status_icons.get(step["status"] or "", "⬜")
        lines.append(
            f"{icon} Step {step['step_index']}: **{step['name']}** "
            f"({step['step_type']}) — {step['message_count']} messages"
        )

    return ToolResponse(
        user_response="\n".join(lines),
        llm_response=(
            f"Recipe '{recipe_id}': {pct}% complete, "
            f"{m.get('completed_steps', 0)}/{m.get('total_steps', 0)} steps done."
        ),
    )


def complete_recipe_step(recipe_id: str, step_index: int, **kwargs) -> ToolResponse:
    """
    Mark a recipe step as completed.

    Args:
        recipe_id: The instance recipe_id
        step_index: The step to mark complete (0-based)

    Returns:
        ToolResponse confirming completion
    """
    settings: CODXJuniorSettings = kwargs.get("settings")
    if not settings:
        raise Exception("Invalid project settings")

    manager = RecipeManager(settings=settings)
    
    try:
        updated = manager.complete_step(recipe_id=recipe_id, step_index=step_index)
    except (ValueError, IndexError) as e:
        return ToolResponse(
            user_response=f"❌ Could not complete step: {e}",
            llm_response=f"Step completion failed: {e}",
        )

    step = updated.steps[step_index]
    if updated.metrics:
        pct = updated.metrics.completion_percent
        return ToolResponse(
            user_response=(
                f"✅ Step **{step.name}** marked as completed!\n"
                f"Overall progress: {pct}%"
            ),
            llm_response=f"Step {step_index} completed. Recipe {pct}% done.",
        )
    
    return ToolResponse(
        user_response=f"✅ Step **{step.name}** marked as completed!",
        llm_response=f"Step {step_index} status updated to 'completed'.",
    )