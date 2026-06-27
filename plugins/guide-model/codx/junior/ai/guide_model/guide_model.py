import os
import pickle
import multiprocessing
from llama_cpp import Llama
from codx.junior.globals import CODX_JUNIOR_MODELS_PATH


class GuideModel:
    def __init__(self, model_name: str, n_ctx: int = 4096):
        self.model_path = os.path.join(CODX_JUNIOR_MODELS_PATH, model_name)
        self.state_path = f"{self.model_path}.guide.state"
        self.n_ctx = n_ctx
        self.llm = None
        self.guide_text = ""

        # Auto-detect optimal threads for CPU
        self.threads = max(1, multiprocessing.cpu_count() // 2)

        self._load_model()

    def _load_model(self):
        """Initializes the model in CPU-only mode."""
        self.llm = Llama(
            model_path=self.model_path,
            n_ctx=self.n_ctx,
            n_threads=self.threads,
            verbose=False
        )

    def _save_state(self):
        """Serializes and saves the current LlamaState to disk using pickle."""
        state = self.llm.save_state()
        with open(self.state_path, "wb") as f:
            pickle.dump(state, f)
        print(f"[GuideModel] Guide state saved to {self.state_path}")

    def _restore_state(self) -> bool:
        """
        Attempts to restore LlamaState from disk using pickle.
        Returns True if successful, False otherwise.
        """
        try:
            with open(self.state_path, "rb") as f:
                state = pickle.load(f)
            self.llm.load_state(state)
            print(f"[GuideModel] Guide state restored from {self.state_path}")
            return True
        except Exception as e:
            print(f"[GuideModel] Failed to restore state: {e}")
            return False

    def load_guide(self, guide_text: str, force_refresh: bool = False):
        """
        Loads the project guide document into the model's context.
        Restores cached state from disk if available to avoid reprocessing.
        """
        self.guide_text = guide_text.strip()

        if os.path.exists(self.state_path) and not force_refresh:
            print(f"[GuideModel] Restoring guide state from {self.state_path}...")
            if self._restore_state():
                return

        print("[GuideModel] Processing guide for the first time (this may take a moment)...")
        # Prime the KV cache with the guide context
        self.llm(self.guide_text, max_tokens=1)
        self._save_state()
        print(f"[GuideModel] Guide processed and state saved to {self.state_path}")

    def ask(self, question: str) -> str:
        """
        Queries the model using the pre-loaded guide context to find project resources.
        The prompt must start with the guide text exactly to hit the KV cache.
        """
        if not self.guide_text:
            raise RuntimeError("[GuideModel] No guide loaded. Call load_guide() first.")

        full_prompt = (
            f"{self.guide_text}\n\n"
            f"Question: {question}\n"
            f"Answer:"
        )

        output = self.llm(
            full_prompt,
            max_tokens=200,
            stop=["Question:", "\n\n"],
            echo=False
        )
        return output["choices"][0]["text"].strip()

    def reload_guide(self, new_guide_text: str):
        """Updates the guide document and overwrites the saved state."""
        self.load_guide(new_guide_text, force_refresh=True)

    def find_resource(self, resource_description: str) -> str:
        """
        Convenience method specifically for finding project resources
        by description using the loaded guide.
        """
        question = f"Where can I find the project resource for: {resource_description}?"
        return self.ask(question)