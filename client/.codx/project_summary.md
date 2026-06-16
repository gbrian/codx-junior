# Codx Junior UI Project Summary

**Description:** A sophisticated frontend Single Page Application (SPA) designed as an AI-powered digital workspace ("Codx Junior"). It unifies structured chat APIs, live code environments, advanced file management, version control views, system settings, and collaborative modules into a single professional user interface.

### 🌐 Core Infrastructure & Architecture
Defines the application state, routing strategy, and service layer for cross-module communication.
*   `src/main.ts`: Application entry point and overall bootstrap logic.
*   `/src/store/*`: Global centralized state management systems (`chats.js`, `users.js`, etc.).
*   `/src/router/*`, `/src/service/*`: Handles navigation routes and abstracts external data services (Chat, Project APIs).

### 🖥️ Main Workspaces & Views
High-level container components representing major operational sections of the workspace.
*   **Desktop View:** `/src/views/HomeView.vue`, `/src/views/DesktopView.vue` (Simulates multi-window desktop interaction).
*   **Chat Interface:** `/src/views/ChatView.vue` (The primary dedicated layout for all chat features).
*   **System Configuration:** `/src/views/GlobalSettings.vue`, `/src/views/KnowledgeSettings.vue` (Manages system settings, plugins, and knowledge base setup).

### ✨ Modular Systems & Tooling Components
Reusable components implementing specialized business logic, workflow management, or complex data presentation.
*   **AI Chat Flow:** `/src/components/chat/*`: Handles message lists, input processing, model selection, and message interaction details.
*   **Code Environment (Monaco):** `/src/components/monaco/*`, `/src/components/code-editor/CodeEditor.jsx`: Provides wrappers for advanced code editing, diffing comparisons, and viewing.
*   **Version Control (VCS):** `/src/components/repo/*`: Tools dedicated to visualizing Git history, managing commits, and reviewing PRs.
*   **Project Context:** `/src/components/project/*`: Components defining project identification, metadata selection, and structural listing.
*   **Collaboration & Workflow:** `/src/components/kanban/*`: Full module for task board visualization and customizable workflow management.

### ⚙️ Specialized Configuration & Data Handling
Modules dedicated to advanced settings, external data integration, and system resources.
*   **AI Settings:** `/src/components/ai_settings/*`: Dedicated modules controlling LLM connections (providers, models, agents) and API configuration.
*   **Data Management:** `/src/components/data/*`: Components for displaying structured records, search results, and data-intensive lists.
*   **Knowledge Base:** `/src/components/knowledge/settings/*`, `src/views/KnowledgeView.vue`: Logic for indexing external knowledge sources and managing retrieval patterns.
*   **User & Auth:** `/src/components/user/*`, `/src/components/security/*`: Handles user login, profile visualization, authorization details, and role management.

### 🏗️ Utilities and Layout Components
Reusable building blocks providing universal structure, navigation, and viewing utility across all modules.
*   **Layout:** `/src/components/*Modal*.vue`, `/src/components/*Splitter*.vue`: Dialog boxes, context menus, and flexible layout dividers.
*   **Navigation/Menu:** `/src/components/main-menu/*`, `/src/components/sidebar/*`: Manages global application navigation structures (sidebars, tabs, main menus).
*   **File System:** `/src/views/FileBrowserView.vue`, `/src/components/filebrowser/FileFinder.vue`: Core view for traversing and selecting files within a structured directory system.