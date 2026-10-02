# AI Knowledge Service Core

## Overview
The AI Knowledge Service Core serves as the central intelligence engine for the application ecosystem. It is designed to provide advanced understanding and actionable insights by moving beyond simple data retrieval towards comprehensive knowledge synthesis. This module achieves this by integrating sophisticated generative AI features with a structured, foundational resource: the Knowledge Graph.

At its heart, this service manages complex business logic and interconnected specialized domain knowledge, allowing it to answer "why" questions, not just "what." It is highly modular, separating concerns into specialized components for core data modeling, specific workflow execution (like cancellations), and content management (wiki domains). The architecture supports asynchronous processing, ensuring that demanding AI computations do not block critical application threads.

**Key Responsibilities:**
*   Maintaining a robust Knowledge Graph structure for all system entities and relationships.
*   Handling domain-specific workflows, notably complex cancellation processes.
*   Generating and structuring human-readable, wiki-style content based on expert knowledge sources.
*   Facilitating interaction between raw data, structured knowledge, and generative AI models.

## Files in Domain
The following files contain the core logic and services that constitute this domain:

**`/home/codx-junior-projects/codx-junior/.dockerignore`**
A standard development utility file used to specify paths and patterns that should be excluded from the Docker build context, ensuring optimized and minimal deployment images.

**`/home/codx-junior-projects/codx-junior/api/codx/junior/ai/cancellation.py`**
This module encapsulates the complex business logic required for managing cancellation processes. It handles state changes, associated data dependencies, and specific transactional requirements related to canceling services or accounts within the defined domain scope.

**`/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_graph.py`**
This is the core architectural component responsible for managing the knowledge graph data structure. It provides methods for ingesting, storing, querying, and traversing complex relationships (nodes and edges) between various entities within the system state.

**`/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_domains.py`**
Dedicated to content management, this module provides utilities for organizing and serving domain expertise in a structured, wiki-style format. It maintains the canonical documentation and specialized knowledge required by the AI service without requiring graph manipulation for simple retrieval tasks.

## Dependencies
This module is designed as an independent intelligence core within the application structure. While it relies heavily on underlying operational capabilities (e.g., database connections, external AI APIs), it abstracts these dependencies at the domain level. Therefore, there are no stated internal file-to-file dependencies that prevent its operation or testing.

## Used By
Currently, this module is self-contained and does not explicitly list files that consume its services. Its foundational nature means that *all* major service controllers within the application architecture must interact with—and therefore utilize—at least a piece of functionality provided by this Core module (Knowledge Graph management or AI processing).

## Entry Points
The following modules represent the primary, exposed entry points for other internal and external services to access the intelligence capabilities of the core.

*   `/home/codx-junior-projects/codx-junior/.dockerignore` (Utility)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/cancellation.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/knowledge/knowledge_graph.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_domains.py`