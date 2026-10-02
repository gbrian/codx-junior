# Knowledge (RAG)

codx-junior indexes each project so the AI can find the right code and documents before it answers or acts.

![Knowledge](/images/NOV2025/codx-junior-rag-knowledge.png)

## How it works

1. Project files are split into chunks with a code-aware splitter.
2. Chunks are embedded with the project's **embeddings model** and stored in **Milvus**.
3. When a chat or an agent needs context, codx-junior searches the index, filters the results by relevance and passes them to the model.
4. The background worker re-indexes files as they change when **watching** is on.

## Search

* **Similarity search** with a configurable number of documents and relevance cutoffs.
* **AI search**: the model rewrites the query, searches with several terms and validates the results.
* **Keywords** and a **knowledge graph** help connect related files.
* Agents use the `project_search` tool with one or many queries at once.

Try queries yourself from the knowledge search dialog.

## Knowledge settings

Open **Settings → Knowledge settings** to:

* see index statistics and the list of indexed files,
* reload a single path or the whole project,
* delete sources from the index,
* edit **ignore patterns**,
* add **external folders** and include **sub-projects**,
* tune the search type, document count, relevance cutoff and RAG distance,
* enable tag extraction and document enrichment.

Chats can also be indexed: give a chat **knowledge topics** and its content becomes searchable knowledge for the project.
