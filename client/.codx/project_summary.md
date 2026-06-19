# Codx Junior UI Project Summary

**Description:** A comprehensive AI-powered digital workspace Single Page Application (SPA) providing advanced tools—including code editing, multi-window desktop simulation, real-time chat with LLMs, version control visualization, and sophisticated project management workflows—all within a unified interface.

### ⚙️ Core Infrastructure & State Management
Manages application state, routing, and abstracting external service communication.
*   `src/store/*`: Centralized persistent data systems (`chats.js`, `users.js`, `profiles.js`).
*   `src/router/*`, `/src/service/*`: Defines global navigation flows and business logic services (e.g., `chat.js`, `project.js`).
*   `src/api/socket.js`: Handles real-time WebSocket connections for live data updates.

### 🖥️ Main Workspaces & Views
Container components representing the primary operational environments or dedicated system modules.
*   **Chat Hub:** `/src/views/ChatView.vue`, `src/components/chat/*`: Core chat logic (messages, input, file selectors).
*   **Workspace Simulation:** `/src/views/DesktopView.vue`, `/src/components/windowManager/*`: Simulates a multi-window desktop environment.
*   **Settings Hubs:** 
    *   `/src/viewsv/GlobalSettings.vue`: General application and system configuration.
    *   `/src/views/KnowledgeSettings.vue` & `/src/views/DocsView.vue`: Dedicated modules for Knowledge Base indexing (RAG) setup.

### ✨ AI, Code, and Collaboration Workflow Components
Specialized components handling complex interactions like coding, version control, and project management.
*   **Code Editor & VCS:** 
    *   `src/components/monaco/*`, `src/components/code-editor/CodeEditor.*`: Professional code editing environment wrappers.
    *   `src/components/repo/*`: Modules for visualizing Git history, commits, and Pull Requests (`PRView.vue`).
    *   `src/components/diffviewer/*`: Tools for comparing file versions (Monaco, general).
*   **Project Management:** `/src/components/project/*`: Components managing project grouping, metadata display, and navigation bar elements.
*   **Kanban Board:** `src/components/kanban/*`: Full task board implementation for visual workflow management.

### 📊 Settings & Identity Modules (Configuration Areas)
Dedicated components controlling external integrations, user data, or complex settings like LLMs.
*   **AI Configuration:** `/src/components/ai_settings/*`: Controls connection parameters, model selection, and agent behaviors for the underlying LLM.
*   **User & Security:** `/src/components/user/*`, `/src/components/security/*`: Handles identity management, user selection, and authentication details.
*   **Data Modeling:** `src/components/data/*`: Components designed for displaying structured search results or data exploration records.

### 🧱 Utility & Layout Toolkit (Reusability)
Atomic, highly reusable building blocks providing structure, navigation, and flexible layout within views.
*   **Layout & Dividers:** `src/components/*Splitter*.vue`, `Modal.vue`, `TabBar.vue`.
*   **Navigation & Menus:** `/src/components/main-menu/*`: Sidebars, main menu items, and workspace selectors.
*   **View Helpers:** `/src/views/FileBrowserView.vue`, `src/components/filebrowser/FileFinder.vue`: Core structure for file system navigation.
*   **Generic Components:** `src/components/utils/*.vue` group (Includes general helpers like `README.md`, icons, etc.).