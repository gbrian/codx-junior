import logging
import requests

from codx.junior.ai.ai import AI
from codx.junior.model.model import AISettings, AIModel
from codx.junior.model.ai_model import AIProvider, AIModelPrice

from codx.junior.ai.llmfactory import OllamaAI
from codx.junior.global_settings import (
  read_global_settings,
  get_provider_settings,
  get_model_settings
)

AI = AI
logger = logging.getLogger(__name__)

PRICING_EXTRACTION_SYSTEM_PROMPT = """
You are a pricing data extraction assistant.
Your task is to analyze raw HTML or text content from an AI provider's pricing page
and extract model pricing information.

You MUST respond ONLY with a valid JSON array. No explanations, no markdown, no code blocks.

Each element in the array must have exactly these fields:
- "model_name": string — the model identifier as listed on the pricing page
- "input_k_tokens_price": float — the cost per 1,000 input tokens in USD
- "output_k_tokens_price": float — the cost per 1,000 output tokens in USD

If a price is listed per 1M tokens, divide by 1000 to convert to per 1K tokens.
If a price is listed per 1 token, multiply by 1000 to convert to per 1K tokens.

Example output:
[
  {"model_name": "gpt-4o", "input_k_tokens_price": 0.005, "output_k_tokens_price": 0.015},
  {"model_name": "gpt-4o-mini", "input_k_tokens_price": 0.00015, "output_k_tokens_price": 0.0006}
]
""".strip()

PRICING_EXTRACTION_USER_PROMPT = """
Extract all model pricing information from the following pricing page content.
Provider: {provider_name}

Content:
{page_content}
""".strip()

# Maximum characters of page content to send to the AI to avoid exceeding context limits
MAX_PAGE_CONTENT_CHARS = 32_000


class AIManager:

    def reload_models(self, global_settings):
        active_models = [ai_model for ai_model \
                            in global_settings.ai_models if ai_model.ai_provider == 'llmfactory'] 
        for ai_model in active_models:
            try:
                info = self.load_model(model=ai_model.name, global_settings=global_settings)
                if not info:
                    logger.error(f"Error reloading model {ai_model}")
                    continue
                model_info = info['modelinfo']
                
                context_length_keys = [k for k in model_info.keys() if "context_length" in k]
                if context_length_keys:
                    context_length = model_info[context_length_keys[0]]
                    if hasattr(ai_model.settings, "context_length"):
                        ai_model.settings.context_length = context_length
                    if hasattr(ai_model.settings, "chunk_size"):
                        ai_model.settings.chunk_size = context_length

                embedding_length_keys = [k for k in model_info.keys() if "embedding_length" in k]
                if embedding_length_keys and hasattr(ai_model.settings, "vector_size"):
                    embedding_length = model_info[embedding_length_keys[0]]
                    ai_model.settings.vector_size = embedding_length
                
                self.prune_models(active_models=active_models, global_settings=global_settings)
            except Exception as ex:
                logger.error("Error '%s' reloading model: %s", str(ex), ai_model.name)

    def prune_models(self, active_models: [AIModel], global_settings):
        llmfactory = OllamaAI(ai_settings=get_provider_settings('llmfactory', global_settings=global_settings))
        llmfactory.prune_models([m.ai_model or m.name for m in active_models])

    def reload_model(self, model: AIModel):
        global_settings = read_global_settings()
        return self.load_model(model=model.name, global_settings=global_settings)

    def load_model(self, model: str, global_settings):
        ai_settings = get_model_settings(llm_model=model, global_settings=global_settings)
        return OllamaAI(ai_settings=ai_settings).load_model()

    # ------------------------------------------------------------------
    # Pricing
    # ------------------------------------------------------------------

    def _fetch_pricing_page(self, url: str) -> str:
        """
        Download the raw content of a pricing page.

        :param url: URL of the pricing page.
        :return: Text content of the page (HTML or plain text).
        :raises requests.RequestException: On network errors.
        """
        logger.info("Fetching pricing page: %s", url)
        response = requests.get(url, timeout=30, headers={"User-Agent": "codx-junior/1.0"})
        response.raise_for_status()
        return response.text

    def _extract_prices_with_ai(
        self,
        page_content: str,
        provider_name: str,
        global_settings,
    ) -> list[AIModelPrice]:
        """
        Use the configured LLM to parse the pricing page content and return a list
        of :class:`AIModelPrice` instances.

        :param page_content: Raw text/HTML of the pricing page.
        :param provider_name: Human-readable provider name (used in the prompt).
        :param global_settings: Application global settings (used to build the AI client).
        :return: Parsed list of model prices.
        """
        import json as _json
        from langchain.messages import HumanMessage, SystemMessage

        # Truncate to avoid blowing the context window
        truncated_content = page_content[:MAX_PAGE_CONTENT_CHARS]

        ai_settings = get_model_settings(
            llm_model=None,  # use the default / knowledge model
            global_settings=global_settings,
        )
        raise Exception("This ir not correct, we need CodxJuniorSettings")
        ai = AI(settings=global_settings)

        messages = [
            SystemMessage(content=PRICING_EXTRACTION_SYSTEM_PROMPT),
            HumanMessage(
                content=PRICING_EXTRACTION_USER_PROMPT.format(
                    provider_name=provider_name,
                    page_content=truncated_content,
                )
            ),
        ]

        response_messages = ai.chat(messages=messages)
        raw_response = response_messages[-1].content.strip()

        # Strip potential markdown code fences the model may add despite instructions
        if raw_response.startswith("```"):
            lines = raw_response.splitlines()
            # Remove first and last fence lines
            raw_response = "\n".join(
                line for line in lines if not line.startswith("```")
            ).strip()

        try:
            data = _json.loads(raw_response)
        except _json.JSONDecodeError as exc:
            logger.error(
                "Failed to parse AI pricing response as JSON for provider '%s': %s\nRaw response:\n%s",
                provider_name,
                exc,
                raw_response,
            )
            return []

        prices: list[AIModelPrice] = []
        for item in data:
            try:
                prices.append(AIModelPrice(**item))
            except Exception as parse_exc:
                logger.warning(
                    "Skipping malformed price entry for provider '%s': %s — %s",
                    provider_name,
                    item,
                    parse_exc,
                )

        return prices

    def load_ai_models_prices(self, global_settings) -> dict[str, list[AIModelPrice]]:
        """
        For every :class:`AIProvider` in *global_settings* that has a ``pricing_url``
        set, download the pricing page, extract model prices using the AI, and store
        the result back into ``provider.price_list``.

        :param global_settings: Application global settings object that exposes
            ``ai_providers`` (``List[AIProvider]``).
        :return: A mapping of ``provider_name -> List[AIModelPrice]`` for all
            providers that were successfully processed.
        """
        results: dict[str, list[AIModelPrice]] = {}

        providers: list[AIProvider] = getattr(global_settings, "ai_providers", [])
        if not providers:
            logger.warning("load_ai_models_prices: no ai_providers found in global_settings.")
            return results

        for provider in providers:
            if not provider.pricing_url:
                logger.debug(
                    "Skipping provider '%s': no pricing_url configured.", provider.name
                )
                continue

            try:
                page_content = self._fetch_pricing_page(provider.pricing_url)
            except Exception as fetch_exc:
                logger.error(
                    "Failed to fetch pricing page for provider '%s' from '%s': %s",
                    provider.name,
                    provider.pricing_url,
                    fetch_exc,
                )
                continue

            try:
                prices = self._extract_prices_with_ai(
                    page_content=page_content,
                    provider_name=provider.name or provider.provider or "unknown",
                    global_settings=global_settings,
                )
            except Exception as ai_exc:
                logger.error(
                    "Failed to extract prices with AI for provider '%s': %s",
                    provider.name,
                    ai_exc,
                )
                continue

            provider.price_list = prices
            results[provider.name or provider.provider] = prices

            logger.info(
                "Loaded %d model price(s) for provider '%s'.",
                len(prices),
                provider.name,
            )

        return results