import os
import pytest
from unittest.mock import MagicMock, patch, mock_open
from codx.junior.ai.guide_model import GuideModel
from codx.junior.ai.guide_model_manager import GuideModelManager


SAMPLE_GUIDE = """
# My Project Guide

## Structure
- src/auth/auth_service.py - Authentication module
- src/api/routes.py - API routes
- src/db/models.py - Database models

## Overview
This is a sample project guide for testing purposes.
"""

SAMPLE_MODEL_NAME = "smollm2-360m-instruct-q4_k_m.gguf"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_manager_instances():
    """Ensure GuideModelManager registry is clean between tests."""
    GuideModelManager._instances.clear()
    yield
    GuideModelManager._instances.clear()


@pytest.fixture
def mock_llama():
    """Returns a fully mocked Llama instance."""
    llm = MagicMock()
    llm.return_value = {
        "choices": [{"text": " src/auth/auth_service.py"}]
    }
    return llm


@pytest.fixture
def guide_model(mock_llama):
    """Returns a GuideModel with a mocked Llama backend."""
    with patch("codx.junior.ai.guide_model.Llama", return_value=mock_llama):
        model = GuideModel(model_name=SAMPLE_MODEL_NAME)
    return model, mock_llama


# ---------------------------------------------------------------------------
# GuideModel — initialization
# ---------------------------------------------------------------------------

class TestGuideModelInit:
    def test_model_path_is_set(self, guide_model):
        model, _ = guide_model
        assert model.model_path.endswith(SAMPLE_MODEL_NAME)

    def test_state_path_derived_from_model_path(self, guide_model):
        model, _ = guide_model
        assert model.state_path == f"{model.model_path}.guide.state"

    def test_default_n_ctx(self, guide_model):
        model, _ = guide_model
        assert model.n_ctx == 4096

    def test_custom_n_ctx(self, mock_llama):
        with patch("codx.junior.ai.guide_model.Llama", return_value=mock_llama):
            model = GuideModel(model_name=SAMPLE_MODEL_NAME, n_ctx=2048)
        assert model.n_ctx == 2048

    def test_threads_at_least_one(self, guide_model):
        model, _ = guide_model
        assert model.threads >= 1

    def test_llm_initialized(self, guide_model):
        model, mock_llm = guide_model
        assert model.llm is mock_llm

    def test_guide_text_empty_on_init(self, guide_model):
        model, _ = guide_model
        assert model.guide_text == ""

    def test_llama_called_with_correct_args(self, mock_llama):
        with patch("codx.junior.ai.guide_model.Llama", return_value=mock_llama) as MockLlama:
            model = GuideModel(model_name=SAMPLE_MODEL_NAME, n_ctx=512)
        call_kwargs = MockLlama.call_args.kwargs
        assert call_kwargs["n_ctx"] == 512
        assert call_kwargs["verbose"] is False


# ---------------------------------------------------------------------------
# GuideModel — load_guide
# ---------------------------------------------------------------------------

class TestGuideModelLoadGuide:
    def test_loads_state_from_disk_when_exists(self, guide_model):
        model, mock_llm = guide_model
        with patch("os.path.exists", return_value=True):
            model.load_guide(SAMPLE_GUIDE)
        mock_llm.load_state.assert_called_once_with(model.state_path)

    def test_does_not_save_state_when_loading_from_disk(self, guide_model):
        model, mock_llm = guide_model
        with patch("os.path.exists", return_value=True):
            model.load_guide(SAMPLE_GUIDE)
        mock_llm.save_state.assert_not_called()

    def test_processes_and_saves_state_on_first_run(self, guide_model):
        model, mock_llm = guide_model
        with patch("os.path.exists", return_value=False):
            model.load_guide(SAMPLE_GUIDE)
        mock_llm.save_state.assert_called_once_with(model.state_path)

    def test_force_refresh_skips_disk_state(self, guide_model):
        model, mock_llm = guide_model
        with patch("os.path.exists", return_value=True):
            model.load_guide(SAMPLE_GUIDE, force_refresh=True)
        mock_llm.load_state.assert_not_called()
        mock_llm.save_state.assert_called_once()

    def test_guide_text_is_stored(self, guide_model):
        model, mock_llm = guide_model
        with patch("os.path.exists", return_value=False):
            model.load_guide(SAMPLE_GUIDE)
        assert model.guide_text == SAMPLE_GUIDE.strip()

    def test_guide_text_is_stripped(self, guide_model):
        model, mock_llm = guide_model
        padded_guide = "   \n" + SAMPLE_GUIDE + "\n   "
        with patch("os.path.exists", return_value=False):
            model.load_guide(padded_guide)
        assert model.guide_text == SAMPLE_GUIDE.strip()

    def test_llm_primed_with_guide_context(self, guide_model):
        model, mock_llm = guide_model
        with patch("os.path.exists", return_value=False):
            model.load_guide(SAMPLE_GUIDE)
        mock_llm.assert_called_once_with(SAMPLE_GUIDE.strip(), max_tokens=1)


# ---------------------------------------------------------------------------
# GuideModel — ask
# ---------------------------------------------------------------------------

class TestGuideModelAsk:
    def _loaded_model(self, guide_model):
        model, mock_llm = guide_model
        with patch("os.path.exists", return_value=False):
            model.load_guide(SAMPLE_GUIDE)
        mock_llm.reset_mock()
        mock_llm.return_value = {
            "choices": [{"text": " src/auth/auth_service.py"}]
        }
        return model, mock_llm

    def test_ask_raises_if_no_guide_loaded(self, guide_model):
        model, _ = guide_model
        with pytest.raises(RuntimeError, match="No guide loaded"):
            model.ask("Where is auth?")

    def test_ask_calls_llm_with_full_prompt(self, guide_model):
        model, mock_llm = self._loaded_model(guide_model)
        model.ask("Where is auth?")
        call_args = mock_llm.call_args
        prompt = call_args[0][0]
        assert model.guide_text in prompt
        assert "Where is auth?" in prompt
        assert "Answer:" in prompt

    def test_ask_returns_stripped_answer(self, guide_model):
        model, mock_llm = self._loaded_model(guide_model)
        answer = model.ask("Where is auth?")
        assert answer == "src/auth/auth_service.py"

    def test_ask_passes_stop_tokens(self, guide_model):
        model, mock_llm = self._loaded_model(guide_model)
        model.ask("Where is auth?")
        call_kwargs = mock_llm.call_args.kwargs
        assert "stop" in call_kwargs
        assert "Question:" in call_kwargs["stop"]

    def test_ask_passes_max_tokens(self, guide_model):
        model, mock_llm = self._loaded_model(guide_model)
        model.ask("Where is auth?")
        call_kwargs = mock_llm.call_args.kwargs
        assert call_kwargs["max_tokens"] == 200

    def test_ask_echo_is_false(self, guide_model):
        model, mock_llm = self._loaded_model(guide_model)
        model.ask("Any question?")
        call_kwargs = mock_llm.call_args.kwargs
        assert call_kwargs["echo"] is False

    def test_prompt_structure(self, guide_model):
        model, mock_llm = self._loaded_model(guide_model)
        question = "Where is the DB layer?"
        model.ask(question)
        prompt = mock_llm.call_args[0][0]
        assert prompt == (
            f"{model.guide_text}\n\n"
            f"Question: {question}\n"
            f"Answer:"
        )


# ---------------------------------------------------------------------------
# GuideModel — reload_guide
# ---------------------------------------------------------------------------

class TestGuideModelReloadGuide:
    def test_reload_calls_load_guide_with_force_refresh(self, guide_model):
        model, mock_llm = guide_model
        with patch.object(model, "load_guide") as mock_load:
            model.reload_guide("new guide text")
        mock_load.assert_called_once_with("new guide text", force_refresh=True)

    def test_reload_updates_guide_text(self, guide_model):
        model, mock_llm = guide_model
        new_guide = "# Updated Guide\n- new/path/module.py"
        with patch("os.path.exists", return_value=False):
            model.reload_guide(new_guide)
        assert model.guide_text == new_guide.strip()


# ---------------------------------------------------------------------------
# GuideModel — find_resource
# ---------------------------------------------------------------------------

class TestGuideModelFindResource:
    def test_find_resource_delegates_to_ask(self, guide_model):
        model, mock_llm = guide_model
        with patch("os.path.exists", return_value=False):
            model.load_guide(SAMPLE_GUIDE)
        mock_llm.reset_mock()
        mock_llm.return_value = {"choices": [{"text": " src/db/models.py"}]}

        with patch.object(model, "ask", wraps=model.ask) as mock_ask:
            result = model.find_resource("database models")

        mock_ask.assert_called_once()
        call_arg = mock_ask.call_args[0][0]
        assert "database models" in call_arg

    def test_find_resource_returns_answer(self, guide_model):
        model, mock_llm = guide_model
        with patch("os.path.exists", return_value=False):
            model.load_guide(SAMPLE_GUIDE)
        mock_llm.reset_mock()
        mock_llm.return_value = {"choices": [{"text": " src/db/models.py"}]}
        result = model.find_resource("database models")
        assert result == "src/db/models.py"

    def test_find_resource_question_format(self, guide_model):
        model, mock_llm = guide_model
        with patch("os.path.exists", return_value=False):
            model.load_guide(SAMPLE_GUIDE)
        mock_llm.reset_mock()
        mock_llm.return_value = {"choices": [{"text": " answer"}]}

        with patch.object(model, "ask") as mock_ask:
            mock_ask.return_value = "answer"
            model.find_resource("auth service")

        expected_question = "Where can I find the project resource for: auth service?"
        mock_ask.assert_called_once_with(expected_question)


# ---------------------------------------------------------------------------
# GuideModelManager — get_or_create
# ---------------------------------------------------------------------------

class TestGuideModelManagerGetOrCreate:
    def _make_guide_model(self):
        mock_llm = MagicMock()
        mock_llm.return_value = {"choices": [{"text": "answer"}]}
        with patch("codx.junior.ai.guide_model.Llama", return_value=mock_llm):
            with patch("os.path.exists", return_value=False):
                model = GuideModel(model_name=SAMPLE_MODEL_NAME)
        return model

    def test_creates_new_instance_for_new_project(self):
        with patch("codx.junior.ai.guide_model_manager.GuideModel") as MockGuideModel:
            instance = MagicMock()
            MockGuideModel.return_value = instance
            result = GuideModelManager.get_or_create(
                project_path="/projects/my-app",
                guide_text=SAMPLE_GUIDE
            )
        assert result is instance
        assert "/projects/my-app" in GuideModelManager._instances

    def test_returns_existing_instance_for_same_project(self):
        with patch("codx.junior.ai.guide_model_manager.GuideModel") as MockGuideModel:
            instance = MagicMock()
            MockGuideModel.return_value = instance
            first = GuideModelManager.get_or_create(
                project_path="/projects/my-app",
                guide_text=SAMPLE_GUIDE
            )
            second = GuideModelManager.get_or_create(
                project_path="/projects/my-app",
                guide_text=SAMPLE_GUIDE
            )
        assert first is second
        assert MockGuideModel.call_count == 1

    def test_uses_default_model_name_when_not_specified(self):
        with patch("codx.junior.ai.guide_model_manager.GuideModel") as MockGuideModel:
            MockGuideModel.return_value = MagicMock()
            GuideModelManager.get_or_create(
                project_path="/projects/my-app",
                guide_text=SAMPLE_GUIDE
            )
        call_kwargs = MockGuideModel.call_args.kwargs
        assert call_kwargs["model_name"] == GuideModelManager.DEFAULT_MODEL_NAME

    def test_uses_custom_model_name_when_specified(self):
        custom_model = "qwen2.5-0.5b.gguf"
        with patch("codx.junior.ai.guide_model_manager.GuideModel") as MockGuideModel:
            MockGuideModel.return_value = MagicMock()
            GuideModelManager.get_or_create(
                project_path="/projects/my-app",
                guide_text=SAMPLE_GUIDE,
                model_name=custom_model
            )
        call_kwargs = MockGuideModel.call_args.kwargs
        assert call_kwargs["model_name"] == custom_model

    def test_load_guide_called_on_creation(self):
        with patch("codx.junior.ai.guide_model_manager.GuideModel") as MockGuideModel:
            instance = MagicMock()
            MockGuideModel.return_value = instance
            GuideModelManager.get_or_create(
                project_path="/projects/my-app",
                guide_text=SAMPLE_GUIDE
            )
        instance.load_guide.assert_called_once_with(SAMPLE_GUIDE, force_refresh=False)

    def test_force_refresh_calls_reload_guide_on_existing(self):
        with patch("codx.junior.ai.guide_model_manager.GuideModel") as MockGuideModel:
            instance = MagicMock()
            MockGuideModel.return_value = instance
            GuideModelManager.get_or_create(
                project_path="/projects/my-app",
                guide_text=SAMPLE_GUIDE
            )
            updated_guide = SAMPLE_GUIDE + "\n## New Section"
            GuideModelManager.get_or_create(
                project_path="/projects/my-app",
                guide_text=updated_guide,
                force_refresh=True
            )
        instance.reload_guide.assert_called_once_with(updated_guide)

    def test_different_projects_get_different_instances(self):
        with patch("codx.junior.ai.guide_model_manager.GuideModel") as MockGuideModel:
            MockGuideModel.side_effect = [MagicMock(), MagicMock()]
            result_a = GuideModelManager.get_or_create(
                project_path="/projects/app-a",
                guide_text=SAMPLE_GUIDE
            )
            result_b = GuideModelManager.get_or_create(
                project_path="/projects/app-b",
                guide_text=SAMPLE_GUIDE
            )
        assert result_a is not result_b
        assert MockGuideModel.call_count == 2


# ---------------------------------------------------------------------------
# GuideModelManager — remove
# ---------------------------------------------------------------------------

class TestGuideModelManagerRemove:
    def test_remove_existing_project(self):
        with patch("codx.junior.ai.guide_model_manager.GuideModel") as MockGuideModel:
            MockGuideModel.return_value = MagicMock()
            GuideModelManager.get_or_create(
                project_path="/projects/my-app",
                guide_text=SAMPLE_GUIDE
            )
        GuideModelManager.remove("/projects/my-app")
        assert "/projects/my-app" not in GuideModelManager._instances

    def test_remove_nonexistent_project_does_not_raise(self):
        # Should silently pass with no error
        GuideModelManager.remove("/projects/nonexistent")

    def test_remove_only_removes_target_project(self):
        with patch("codx.junior.ai.guide_model_manager.GuideModel") as MockGuideModel:
            MockGuideModel.side_effect = [MagicMock(), MagicMock()]
            GuideModelManager.get_or_create("/projects/app-a", SAMPLE_GUIDE)
            GuideModelManager.get_or_create("/projects/app-b", SAMPLE_GUIDE)

        GuideModelManager.remove("/projects/app-a")

        assert "/projects/app-a" not in GuideModelManager._instances
        assert "/projects/app-b" in GuideModelManager._instances


# ---------------------------------------------------------------------------
# GuideModelManager — list_active_projects
# ---------------------------------------------------------------------------

class TestGuideModelManagerListActiveProjects:
    def test_empty_when_no_projects(self):
        assert GuideModelManager.list_active_projects() == []

    def test_lists_registered_projects(self):
        with patch("codx.junior.ai.guide_model_manager.GuideModel") as MockGuideModel:
            MockGuideModel.side_effect = [MagicMock(), MagicMock()]
            GuideModelManager.get_or_create("/projects/app-a", SAMPLE_GUIDE)
            GuideModelManager.get_or_create("/projects/app-b", SAMPLE_GUIDE)

        active = GuideModelManager.list_active_projects()
        assert "/projects/app-a" in active
        assert "/projects/app-b" in active
        assert len(active) == 2

    def test_removed_project_not_in_list(self):
        with patch("codx.junior.ai.guide_model_manager.GuideModel") as MockGuideModel:
            MockGuideModel.side_effect = [MagicMock(), MagicMock()]
            GuideModelManager.get_or_create("/projects/app-a", SAMPLE_GUIDE)
            GuideModelManager.get_or_create("/projects/app-b", SAMPLE_GUIDE)

        GuideModelManager.remove("/projects/app-a")
        active = GuideModelManager.list_active_projects()

        assert "/projects/app-a" not in active
        assert "/projects/app-b" in active