# Codx Junior UI Project Summary

A comprehensive AI-powered digital workspace Single Page Application (SPA) providing advanced tools—including code editing, multi-window desktop simulation, real-time chat with LLMs, version control visualization, and sophisticated project management workflows—all within a unified interface.

## Core Infrastructure & State Management
Manages application state, routing, and external service communication.
*   `src/store/*`: Centralized persistent data systems (`chats.js`, `users.js`, `profiles.js`, `project.js`, `session.js`, `ui.js`, `logs.js`).
*   `src/router/*`, `src/service/*`: Global navigation flows and business logic services (`chat.js`, `project.js`, `wiki.js`).
*   `src/api/*`: External communication layer (`socket.js` for WebSocket, `connection.js`, `chatManager.js`, `api.js`).

## Main Workspaces & Views
Container components representing primary operational environments.
*   `src/views/ChatView.vue`: Core chat interface.
*   `src/views/DesktopView.vue`: Multi-window desktop simulation.
*   `src/views/AgentPlanView.vue`: Agent planning and workflow visualization.
*   `src/views/GlobalSettings.vue`, `src/views/AISettings.vue`, `src/views/KnowledgeSettings.vue`: Configuration hubs.
*   `src/views/HomeView.vue`, `src/views/ProjectSettings.vue`, `src/views/ProfileView.vue`, `src/views/WikiView.vue`, `src/views/KnowledgeView.vue`: Additional views.

## Chat & Messaging
Chat logic, input handling, file/image management, and LLM integration.
*   `src/components/chat/Chat.vue`: Main chat component.
*   `src/components/chat/ChatInput*.vue`: Input handling and toolbar.
*   `src/components/chat/ChatFile*.vue`: File management and preview.
*   `src/components/chat/ChatImage*.vue`: Image display and carousel.
*   `src/components/chat/ChatIntelliSense.vue`, `src/components/chat/LLMModelSelector.vue`: LLM integration.
*   `src/components/chat/ChatMentionBar.vue`, `src/components/chat/EmojiPicker.vue`, `src/components/chat/ExportChat.vue`: Additional chat features.

## Code Editing & Version Control
Professional code editing, diff viewing, and Git workflow visualization.
*   `src/components/monaco/*`: Code editor wrappers (`Editor.vue`, `DiffViewer.vue`).
*   `src/components/code-editor/CodeEditor.jsx`: React-based code editor.
*   `src/components/repo/PRView.vue`: Pull request visualization.
*   `src/components/repo/PRFile.vue`, `src/components/repo/PRCommitSelector.vue`, `src/components/repo/PRReport.vue`: PR file details, commit selection, and reports.
*   `src/components/repo/CommitTreeView.vue`, `src/components/repo/BranchSelector.vue`: Git history and branch management.
*   `src/components/code/GitDiffViewer.vue`: File version comparison.

## Project Management & Task Boards
Project organization and task workflow management.
*   `src/components/project/*`: Project metadata and navigation (`ProjectCard.vue`, `ProjectOverview.vue`, `ProjectScripts.vue`, `NewProject.vue`).
*   `src/components/kanban/*`: Task board with columns, cards, tree hierarchy, and multiple view modes (`Kanban.vue`, `KanbanColumnView.vue`, `TaskCard.vue`, `KanbanSettings.vue`).

## AI Configuration & Settings
LLM connection parameters, model selection, and agent configuration.
*   `src/components/ai_settings/AIModels.vue`, `src/components/ai_settings/AIProviders.vue`: Model and provider management.
*   `src/components/ai_settings/AIModelSettings.vue`, `src/components/ai_settings/AIProviderSettings.vue`, `src/components/ai_settings/AgentSettings.vue`: Configuration forms.

## Analytics, Logs & Monitoring
Data visualization, usage patterns, and activity tracking.
*   `src/components/analytics/DailyChart.vue`, `src/components/analytics/MetricsDashboard.vue`: Analytics visualization.
*   `src/components/logs/LogsTable.vue`, `src/components/logs/LogEntryDetail.vue`: Log display and details.
*   `src/components/logs/LogsAnalytics.vue`, `src/components/logs/LogsAnalyzerDashboard.vue`, `src/components/logs/LogsFilterBar.vue`, `src/components/logs/LogsLiveMetrics.vue`: Analysis and filtering.

## User Management & Security
Identity management, authentication, and security configuration.
*   `src/components/user/Login.vue`, `src/components/user/UserProfile.vue`: Authentication and profiles.
*   `src/components/user/UserAvatar.vue`, `src/components/user/UserSelector.vue`: User display and selection.
*   `src/components/security/AccountSettings.vue`, `src/components/security/SecurityUserList.vue`, `src/components/security/UserSecurityDetail.vue`, `src/components/security/UserSecuritySettings.vue`, `src/components/security/UserWalletSettings.vue`: Security and user configuration.
*   `src/components/roles/RoleSelector.vue`: Role selection and management.

## Data & Knowledge Management
Data exploration and knowledge base configuration.
*   `src/components/data/DataExplorer.vue`, `src/components/data/DataDetails.vue`: Data browsing and inspection.
*   `src/components/knowledge/KnowledgeSearch.vue`: Knowledge base search.
*   `src/components/knowledge/settings/KnowledgeIndex.vue`, `src/components/knowledge/settings/KnowledgeIgnorePatterns.vue`, `src/components/knowledge/settings/KnowledgeIndexStats.vue`: Knowledge configuration.

## Navigation & Layout
Navigation structures, menus, and layout utilities.
*   `src/components/main-menu/MainMenu.vue`, `src/components/main-menu/MenubarItem.vue`: Sidebar and menu items.
*   `src/components/main-menu/ProjectsMenu.vue`, `src/components/main-menu/WorkspacesMenu.vue`, `src/components/main-menu/ViewsMenu.vue`: Context-specific menus.
*   `src/components/NavigationBar.vue`, `src/components/Toolbar.vue`: Top-level navigation.
*   `src/components/*Splitter*.vue`, `src/components/TabView.vue`, `src/components/Modal.vue`: Layout containers.

## Document & Content Viewing
Document editing, markup rendering, and content display.
*   `src/components/document/Document.vue`, `src/components/document/TipTapDocument.vue`: Document management.
*   `src/components/MarkdownViewer.vue`, `src/components/HTMLViewer.vue`, `src/components/MermaidViewer.vue`: Content renderers.
*   `src/components/CodeViewer.vue`, `src/components/ConsoleViewer.vue`, `src/components/LogViewer.vue`: Code and output viewers.

## Window Manager & Desktop
Multi-window environment simulation.
*   `src/components/windowManager/VirtualDesktop.vue`: Desktop container.
*   `src/components/windowManager/Window.vue`, `src/components/windowManager/AppWindow.vue`: Window implementations.
*   `src/components/windowManager/Workspace.vue`, `src/components/windowManager/Navigator.vue`: Workspace and navigation.

## Utility Components
Atomic reusable components and generic utilities.
*   `src/components/TreeView.vue`, `src/components/Collapsible.vue`: Tree navigation and disclosure.
*   `src/components/ThemeSelector.vue`, `src/components/NotificationControl.vue`: Settings and notifications.
*   `src/components/autocomplete/AutoComplete.vue`, `src/components/bar/SearchBar.vue`: Input components.
*   `src/components/ProfileCard.vue`, `src/components/UserInfo.vue`, `src/components/ProjectChip.vue`: Display components.

## External Integrations & Plugins
OAuth, plugins, and third-party services.
*   `src/components/oauth_settings/OAuthSettings.vue`: OAuth configuration.
*   `src/components/global_settings/plugins/PluginsEditor.vue`, `src/components/global_settings/plugins/PluginCard.vue`, `src/components/global_settings/plugins/LoadPluginModal.vue`: Plugin management.
*   `src/components/global_settings/EnvVariablesEditor.vue`: Environment configuration.

## File Browser
File system navigation and discovery.
*   `src/views/FileBrowserView.vue`: Main file browser view.
*   `src/components/filebrowser/FileFinder.vue`: File search and discovery.