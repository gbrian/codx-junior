# Codx Junior UI Project Summary

A comprehensive AI-powered digital workspace Single Page Application (SPA) providing advanced tools—including code editing, multi-window desktop simulation, real-time chat with LLMs, version control visualization, and sophisticated project management workflows—all within a unified interface.

## Core Infrastructure & State Management
*   `src/store/`: Centralized state management for chats, users, profiles, projects, sessions, UI, logs, media, and teams.
*   `src/router/`: Global navigation routing and utilities.
*   `src/service/`: Business logic layer for chat, projects, wikis, and general services.
*   `src/api/`: External communication via WebSocket, connection management, and chat management.

## Main Views & Workspaces
*   `src/views/ChatView.vue`: Core chat interface.
*   `src/views/DesktopView.vue`: Multi-window desktop simulation.
*   `src/views/VibeCodingView.vue`: Vibe coding workspace and environment.
*   `src/views/AgentPlanView.vue`: Agent planning and workflows.
*   `src/views/GlobalSettings.vue`, `AISettings.vue`, `KnowledgeSettings.vue`: Configuration hubs.
*   `src/views/HomeView.vue`, `ProjectSettings.vue`, `ProfileView.vue`, `WikiView.vue`, `KnowledgeView.vue`, `FileBrowserView.vue`, `TeamView.vue`: Additional views.

## Chat & Messaging
*   `src/components/chat/Chat.vue`: Main chat component.
*   `src/components/chat/ChatInput*.vue`, `ChatInputToolbar.vue`: Input handling and toolbar.
*   `src/components/chat/ChatFile*.vue`: File management and preview functionality.
*   `src/components/chat/ChatImage*.vue`: Image display and carousel.
*   `src/components/chat/ChatIntelliSense.vue`, `LLMModelSelector.vue`: LLM integration and model selection.
*   `src/components/chat/ChatMentionBar.vue`, `EmojiPicker.vue`, `ExportChat.vue`: Additional chat features.
*   `src/components/chats/RecentChatsQuickAccess.vue`: Quick access to recent chats.

## Code Editing & Version Control
*   `src/components/monaco/Editor.vue`, `DiffViewer.vue`: Code editor wrappers.
*   `src/components/code-editor/CodeEditor.jsx`: React-based code editor.
*   `src/components/repo/`: Pull request visualization, git history, and code comments.
*   `src/components/git/BranchSelector.vue`: Branch selection and management.
*   `src/components/code/GitDiffViewer.vue`: File version comparison.

## Project Management & Task Boards
*   `src/components/project/`: Project metadata, navigation, creation, and scripting.
*   `src/components/kanban/`: Task board with columns, cards, grid, and file views.

## Workspaces & Teams
*   `src/components/workspaces/`: Workspace organization, selection, and management.
*   `src/components/teams/`: Team, channel, member management, and settings.
*   `src/components/teams/TeamDM.vue`: Team direct messaging interface.
*   `src/components/teams/TeamMediaLibrary.vue`: Team-specific media management.
*   `src/components/teams/TeamQuickBar.vue`: Team quick access toolbar.

## Desktop & Window Management
*   `src/components/desktop/DesktopView.vue`, `Window.vue`, `Tab.vue`: Desktop simulation components.
*   `src/components/desktop/VibeDesktop.vue`: Vibe-themed desktop environment.
*   `src/components/windowManager/`: Virtual desktop, windows, workspaces, and navigation.
*   `src/components/vibe/VibeCodingHeader.vue`: Vibe coding header and workspace UI.

## AI Configuration & Settings
*   `src/components/ai_settings/`: Model and provider configuration, agent settings, and model selection.

## Analytics, Logs & Monitoring
*   `src/components/analytics/`: Analytics visualization, metrics dashboard, and price editing.
*   `src/components/logs/`: Log display, analysis, filtering, and metrics.

## Media Management
*   `src/components/media/`: Media browsing, organization, preview, upload, and gallery.
*   `src/store/media.js`: Media state management.

## User Management & Security
*   `src/components/user/`: Authentication, profiles, avatars, and user selection.
*   `src/components/security/`: Account settings, user security, and wallet settings.
*   `src/components/roles/RoleSelector.vue`: Role management.
*   `src/components/profile/`: Profile display, selection, and viewing.

## Data & Knowledge Management
*   `src/components/data/`: Data exploration and inspection.
*   `src/components/knowledge/`: Knowledge base search and configuration.

## UI & Theming
*   `src/components/ThemeSelector.vue`: Theme switching.
*   `src/components/ui/ColorPicker.vue`: Color selection.
*   `src/components/VSwatches.vue`: Color swatch selector.

## Navigation & Layout
*   `src/components/main-menu/`: Sidebar and menu navigation with project, workspace, and view menus.
*   `src/components/NavigationBar.vue`, `Toolbar.vue`, `EventBar.vue`: Top-level navigation.
*   `src/components/Splitter.vue`, `layout/VerticalSplitter.vue`: Layout dividers.
*   `src/components/TabView.vue`, `TabNavigation.vue`: Tabbed interfaces.
*   `src/components/Modal.vue`: Modal dialogs.

## Document & Content Viewing
*   `src/components/document/`: Document management, editing, and markdown/word support.
*   `src/components/MarkdownViewer.vue`, `HTMLViewer.vue`, `MermaidViewer.vue`: Content renderers.
*   `src/components/CodeViewer.vue`, `ConsoleViewer.vue`, `LogViewer.vue`: Code and output viewers.

## Utility Components
*   `src/components/TreeView.vue`, `TreeItem.vue`, `Collapsible.vue`: Tree navigation.
*   `src/components/NotificationControl.vue`: Notification management.
*   `src/components/autocomplete/`: Input autocomplete and project resource completion.
*   `src/components/bar/SearchBar.vue`: Search functionality.
*   `src/components/ProfileCard.vue`, `UserInfo.vue`, `ProjectChip.vue`: Display components.

## External Integrations & Plugins
*   `src/components/oauth_settings/OAuthSettings.vue`: OAuth configuration.
*   `src/components/global_settings/plugins/`: Plugin management and configuration.
*   `src/components/global_settings/EnvVariablesEditor.vue`: Environment configuration.

## File Browser
*   `src/views/FileBrowserView.vue`: Main file browser view.
*   `src/components/filebrowser/FileFinder.vue`: File search and discovery.

## Additional Components
*   `src/components/apps/`: Application wrappers (AgentStudio, Coder, Files, Preview).
*   `src/components/board/`: User dashboard boards (Achievements, Activity, Projects, Settings).
*   `src/components/mention*/`, `tiptap/`: Rich text editor and mention functionality.
*   `src/components/browser/Browser.vue`: Browser component.
*   `src/components/assistant/`, `codx-junior/`: AI assistant components.
*   `src/components/Markdown.vue`, `IssuePreview.vue`, `NoVNC.vue`, `YoutubeViewer.vue`: Specialized viewers.