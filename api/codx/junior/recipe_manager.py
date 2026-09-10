"""
Recipe Manager for codx-junior.

Recipes are reusable, ordered sets of steps to accomplish a goal.
Supports tutorials, automations, workflows, playbooks, and custom use cases.

Lifecycle:
    1. Author creates a Recipe template (is_template=True, immutable).
    2. User/system instantiates from template (deep-copy, is_template=False).
    3. Steps are executed/progressed, metrics updated on each step.
    4. Instance tracks progress and can be resumed/archived.

Examples:
    - Tutorial: "Learn FastAPI" (recipe_type='tutorial')
    - Automation: "Keep project docs in sync" (recipe_type='automation', auto_execute=True)
    - Workflow: "Code review checklist" (recipe_type='workflow')
    - Playbook: "Debug high memory usage" (recipe_type='playbook')
"""
import uuid
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from copy import deepcopy

from codx.junior.settings import CODXJuniorSettings
from codx.junior.db import Recipe, RecipeStep, RecipeMetrics, Chat, Message
from codx.junior.chat_manager import ChatManager

logger = logging.getLogger(__name__)

RECIPE_BOARD = "recipes"
RECIPE_TEMPLATE_COLUMN = "templates"
RECIPE_ACTIVE_COLUMN = "active"
RECIPE_ARCHIVED_COLUMN = "archived"

COMPLETION_NOT_STARTED = None
COMPLETION_IN_PROGRESS = "in_progress"
COMPLETION_DONE = "completed"
COMPLETION_SKIPPED = "skipped"
COMPLETION_FAILED = "failed"


class RecipeManager:
    """
    Manages recipe discovery, instantiation, step execution, and progress tracking.
    
    A recipe is immutable when it's a template (is_template=True).
    Instances (is_template=False) are mutable and track progress.
    """

    def __init__(
        self,
        settings: CODXJuniorSettings,
        chat_manager: Optional[ChatManager] = None,
    ):
        self.settings = settings
        self.chat_manager = chat_manager or ChatManager(settings=settings)

    # =========================================================================
    # Template Discovery & Management
    # =========================================================================

    def list_templates(
        self,
        recipe_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all recipe templates, optionally filtered by type or tags.

        Args:
            recipe_type: Filter by type ('tutorial', 'automation', etc.). None = all.
            tags: Filter templates having ALL these tags. None = no tag filter.

        Returns:
            List of template summaries with metadata.
        """
        all_recipes = self._load_all_recipes()
        templates = [r for r in all_recipes if r.is_template]

        # Filter by type
        if recipe_type:
            templates = [r for r in templates if r.recipe_type == recipe_type]

        # Filter by tags
        if tags:
            templates = [
                r for r in templates
                if all(tag in r.tags for tag in tags)
            ]

        return [self._template_summary(t) for t in templates]

    def get_template(self, recipe_id: str) -> Optional[Recipe]:
        """Load a template recipe by ID."""
        all_recipes = self._load_all_recipes()
        for r in all_recipes:
            if r.id == recipe_id and r.is_template:
                return r
        return None

    def create_template(
        self,
        name: str,
        recipe_type: str = "workflow",
        description: str = "",
        goal: Optional[str] = None,
        tags: Optional[List[str]] = None,
        owner: Optional[str] = None,
    ) -> Recipe:
        """
        Create a new empty recipe template.

        Author can add steps via `add_step_to_template`.

        Args:
            name: Recipe name
            recipe_type: Type ('tutorial', 'automation', 'workflow', etc.)
            description: What this recipe does
            goal: High-level success target
            tags: Categorization tags
            owner: User who created this

        Returns:
            Persisted Recipe template
        """
        recipe = Recipe(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            goal=goal,
            recipe_type=recipe_type,
            is_template=True,
            version="1.0.0",
            steps=[],
            tags=tags or [],
            owner=owner,
            kanban_board=RECIPE_BOARD,
            kanban_column=RECIPE_TEMPLATE_COLUMN,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        return self._persist_recipe(recipe)

    def add_step_to_template(
        self,
        recipe_id: str,
        name: str,
        description: str = "",
        step_type: str = "action",
        is_required: bool = True,
        success_criteria: Optional[str] = None,
        estimated_duration_seconds: Optional[int] = None,
        meta_data: Optional[Dict[str, Any]] = None,
    ) -> Recipe:
        """
        Add a new step to a template recipe.

        Steps are auto-indexed in order of addition.

        Args:
            recipe_id: The template recipe ID
            name: Step name
            description: Step purpose and details
            step_type: 'instruction', 'exercise', 'validation', 'action'
            is_required: Must complete to proceed
            success_criteria: How to know step is done
            estimated_duration_seconds: Expected duration
            meta_data: Custom step config

        Returns:
            Updated Recipe with new step added
        """
        recipe = self.get_template(recipe_id)
        if not recipe:
            raise ValueError(f"Template '{recipe_id}' not found")

        step_index = len(recipe.steps)
        new_step = RecipeStep(
            step_index=step_index,
            chat_id=None,  # Will be populated when template is instantiated
            name=name,
            description=description,
            step_type=step_type,
            is_required=is_required,
            success_criteria=success_criteria,
            estimated_duration_seconds=estimated_duration_seconds,
            meta_data=meta_data,
        )
        recipe.steps.append(new_step)
        recipe.updated_at = datetime.now().isoformat()
        return self._persist_recipe(recipe)

    # =========================================================================
    # Instance Creation & Execution
    # =========================================================================

    def create_instance(
        self,
        template_id: str,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Recipe:
        """
        Create a live recipe instance from a template.

        Deep-copies the template:
        - Creates a Chat for each RecipeStep
        - Sets is_template=False, template_id=template_id
        - Initializes metrics for progress tracking

        Args:
            template_id: The template recipe ID to instantiate
            user_id: User who initiated this instance
            project_id: Associated project

        Returns:
            Persisted Recipe instance with all step chats created
        """
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template '{template_id}' not found")

        new_instance_id = str(uuid.uuid4())
        instance_steps: List[RecipeStep] = []

        # Create a Chat for each step
        for step in template.steps:
            step_chat = Chat(
                id=str(uuid.uuid4()),
                name=step.name,
                description=step.description,
                board=RECIPE_BOARD,
                column=RECIPE_ACTIVE_COLUMN,
                recipe_id=new_instance_id,
                recipe_step_index=step.step_index,
                messages=[],
                users=[user_id] if user_id else [],
                project_id=project_id,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            )
            saved_chat = self.chat_manager.save_chat(step_chat)

            # Clone step with chat reference
            cloned_step = RecipeStep(
                step_index=step.step_index,
                chat_id=saved_chat.id,
                name=step.name,
                description=step.description,
                step_type=step.step_type,
                is_required=step.is_required,
                success_criteria=step.success_criteria,
                estimated_duration_seconds=step.estimated_duration_seconds,
                meta_data=deepcopy(step.meta_data) if step.meta_data else None,
            )
            instance_steps.append(cloned_step)

        # Create instance recipe
        instance = Recipe(
            id=new_instance_id,
            name=template.name,
            description=template.description,
            goal=template.goal,
            recipe_type=template.recipe_type,
            is_template=False,
            template_id=template_id,
            version=template.version,
            steps=instance_steps,
            tags=template.tags,
            owner=user_id,
            kanban_board=RECIPE_BOARD,
            kanban_column=RECIPE_ACTIVE_COLUMN,
            project_id=project_id,
            metrics=RecipeMetrics(
                total_steps=len(instance_steps),
                completed_steps=0,
                skipped_steps=0,
                failed_steps=0,
                completion_percent=0,
            ),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        return self._persist_recipe(instance)

    # =========================================================================
    # Step Progress Tracking
    # =========================================================================

    def complete_step(
        self,
        recipe_id: str,
        step_index: int,
        notes: Optional[str] = None,
    ) -> Recipe:
        """
        Mark a step as completed and update metrics.

        Args:
            recipe_id: The instance recipe ID
            step_index: Which step to mark complete
            notes: Optional completion notes

        Returns:
            Updated Recipe instance with metrics refreshed
        """
        return self._update_step_status(
            recipe_id=recipe_id,
            step_index=step_index,
            status=COMPLETION_DONE,
            notes=notes,
        )

    def skip_step(
        self,
        recipe_id: str,
        step_index: int,
        reason: Optional[str] = None,
    ) -> Recipe:
        """Mark a step as skipped (if optional)."""
        recipe = self.get_instance(recipe_id)
        if not recipe:
            raise ValueError(f"Recipe '{recipe_id}' not found")

        step = recipe.steps[step_index]
        if step.is_required:
            raise ValueError(
                f"Cannot skip required step {step_index}: {step.name}"
            )

        return self._update_step_status(
            recipe_id=recipe_id,
            step_index=step_index,
            status=COMPLETION_SKIPPED,
            notes=reason,
        )

    def fail_step(
        self,
        recipe_id: str,
        step_index: int,
        error: Optional[str] = None,
    ) -> Recipe:
        """Mark a step as failed."""
        return self._update_step_status(
            recipe_id=recipe_id,
            step_index=step_index,
            status=COMPLETION_FAILED,
            notes=error,
        )

    def start_step(self, recipe_id: str, step_index: int) -> Recipe:
        """Mark a step as in-progress."""
        return self._update_step_status(
            recipe_id=recipe_id,
            step_index=step_index,
            status=COMPLETION_IN_PROGRESS,
        )

    def _update_step_status(
        self,
        recipe_id: str,
        step_index: int,
        status: str,
        notes: Optional[str] = None,
    ) -> Recipe:
        """Internal: update step status and refresh metrics."""
        recipe = self.get_instance(recipe_id)
        if not recipe:
            raise ValueError(f"Recipe '{recipe_id}' not found")

        # Update step chat status
        if step_index < len(recipe.steps):
            step = recipe.steps[step_index]
            chat = self.chat_manager.find_by_id(step.chat_id)
            if chat:
                chat.status = status
                if notes:
                    # Append note as a system message
                    from codx.junior.db import Message
                    note_msg = Message(
                        role="system",
                        content=notes,
                        created_at=datetime.now().isoformat(),
                    )
                    chat.messages.append(note_msg)
                self.chat_manager.save_chat(chat)

        # Refresh metrics
        self._update_metrics(recipe)
        recipe.updated_at = datetime.now().isoformat()
        return self._persist_recipe(recipe)

    def _update_metrics(self, recipe: Recipe) -> None:
        """Recalculate progress metrics from all step chats."""
        if not recipe.metrics:
            recipe.metrics = RecipeMetrics(total_steps=len(recipe.steps))

        recipe.metrics.total_steps = len(recipe.steps)
        completed = 0
        skipped = 0
        failed = 0
        last_completed = None

        for i, step in enumerate(recipe.steps):
            chat = self.chat_manager.find_by_id(step.chat_id)
            if chat:
                if chat.status == COMPLETION_DONE:
                    completed += 1
                    last_completed = i
                elif chat.status == COMPLETION_SKIPPED:
                    skipped += 1
                elif chat.status == COMPLETION_FAILED:
                    failed += 1

        recipe.metrics.completed_steps = completed
        recipe.metrics.skipped_steps = skipped
        recipe.metrics.failed_steps = failed
        recipe.metrics.last_completed_step_index = last_completed
        pct = (completed / len(recipe.steps) * 100) if recipe.steps else 0
        recipe.metrics.completion_percent = round(pct)
        recipe.metrics.updated_at = datetime.now().isoformat()

    # =========================================================================
    # Instance Retrieval & Progress
    # =========================================================================

    def get_instance(self, recipe_id: str) -> Optional[Recipe]:
        """Load a live recipe instance by ID."""
        all_recipes = self._load_all_recipes()
        for r in all_recipes:
            if r.id == recipe_id and not r.is_template:
                return r
        return None

    def list_instances(
        self,
        user_id: Optional[str] = None,
        template_id: Optional[str] = None,
        recipe_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List active recipe instances, optionally filtered.

        Args:
            user_id: Filter by instance owner
            template_id: Filter by template source
            recipe_type: Filter by recipe type

        Returns:
            List of instance summaries with progress
        """
        all_recipes = self._load_all_recipes()
        instances = [r for r in all_recipes if not r.is_template]

        if user_id:
            instances = [r for r in instances if r.owner == user_id]
        if template_id:
            instances = [r for r in instances if r.template_id == template_id]
        if recipe_type:
            instances = [r for r in instances if r.recipe_type == recipe_type]

        return [self._instance_summary(i) for i in instances]

    def get_progress(self, recipe_id: str) -> Dict[str, Any]:
        """
        Get detailed progress snapshot for a recipe instance.

        Returns:
            Progress summary with step-by-step status
        """
        recipe = self.get_instance(recipe_id)
        if not recipe:
            raise ValueError(f"Recipe instance '{recipe_id}' not found")

        if not recipe.metrics:
            self._update_metrics(recipe)

        step_details = []
        for step in recipe.steps:
            chat = self.chat_manager.find_by_id(step.chat_id)
            step_details.append({
                "step_index": step.step_index,
                "name": step.name,
                "step_type": step.step_type,
                "status": chat.status if chat else None,
                "is_required": step.is_required,
                "message_count": len(chat.messages) if chat else 0,
            })

        return {
            "recipe_id": recipe_id,
            "name": recipe.name,
            "recipe_type": recipe.recipe_type,
            "template_id": recipe.template_id,
            "metrics": recipe.metrics.model_dump() if recipe.metrics else {},
            "steps": step_details,
        }

    # =========================================================================
    # Helpers
    # =========================================================================

    def _template_summary(self, recipe: Recipe) -> Dict[str, Any]:
        """Summarize a template for listing."""
        return {
            "recipe_id": recipe.id,
            "name": recipe.name,
            "recipe_type": recipe.recipe_type,
            "description": recipe.description,
            "goal": recipe.goal,
            "version": recipe.version,
            "step_count": len(recipe.steps),
            "tags": recipe.tags,
            "owner": recipe.owner,
            "created_at": recipe.created_at,
        }

    def _instance_summary(self, recipe: Recipe) -> Dict[str, Any]:
        """Summarize an instance for listing."""
        self._update_metrics(recipe)
        return {
            "recipe_id": recipe.id,
            "name": recipe.name,
            "recipe_type": recipe.recipe_type,
            "template_id": recipe.template_id,
            "owner": recipe.owner,
            "completion_percent": recipe.metrics.completion_percent if recipe.metrics else 0,
            "completed_steps": recipe.metrics.completed_steps if recipe.metrics else 0,
            "total_steps": recipe.metrics.total_steps if recipe.metrics else 0,
            "created_at": recipe.created_at,
            "updated_at": recipe.updated_at,
        }

    def _load_all_recipes(self) -> List[Recipe]:
        """
        Load all recipes from storage (templates + instances).

        In a real implementation, this would query a database.
        For now, we scan chat storage and reconstruct recipes.

        Returns:
            List of all Recipe objects
        """
        # TODO: Implement recipe-specific storage (separate collection/table)
        # For MVP, we can store Recipe metadata in chat.meta_data or kanban column
        # This is a placeholder that should be replaced with proper DB queries
        recipes: List[Recipe] = []
        # Placeholder: would load from Recipe collection in MongoDB, PostgreSQL, etc.
        return recipes

    def _persist_recipe(self, recipe: Recipe) -> Recipe:
        """
        Persist a recipe to storage.

        TODO: Implement recipe-specific storage
        """
        # Placeholder: would save to Recipe collection
        return recipe