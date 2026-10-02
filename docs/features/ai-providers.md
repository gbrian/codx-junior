# AI providers and models

codx-junior works with any **OpenAI-compatible** provider: OpenAI, Ollama, LocalAI, LiteLLM, vLLM and others. Mix cloud and local models as you like.

![AI models](/images/NOV2025/codx-junior-ai-models.png)

## Providers

A provider has a name, an API URL, an API key and optionally an admin URL and a pricing URL. You can set its cost in cxjcoins per 1K tokens and limits on tool calls and tool loops per request.

## Models

Add the models you want from each provider. A model can override the provider's price and limits. Reload the model list at any time from the provider.

## Models by purpose

Choose a default model for each purpose in **Global settings**, and override it per project:

| Purpose | Used for |
| --- | --- |
| LLM | Chats, tasks and agents |
| RAG | Knowledge search |
| Embeddings | Indexing files |
| Wiki | Wiki pages |
| Vision | Reading images and screenshots |
| Image | Generating images |

Each chat, profile or `@codx` mention can also pick its own model.

## Local models

The installer includes **LocalAI** for running models on your own hardware, reachable at `/codx-localai/app` and protected by codx-junior's login. The API image also supports **vLLM** on CPU and **sentence-transformers** for local embeddings.

## MCP servers

Projects can register **MCP servers** (name, URL, API key and an active flag) in their settings.
