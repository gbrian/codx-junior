# Codx Junior UI Project Summary

A comprehensive AI-powered digital workspace Single Page Application (SPA) providing advanced tools—including code editing, multi-window desktop simulation, real-time chat with LLMs, version control visualization, and sophisticated project management workflows—all within a unified interface.

## Core Infrastructure & State Management
*   `src/store/chats.js`, `users.js`, `profiles.js`, `project.js`, `session.js`, `ui.js`, `logs.js`, `media.js`, `teams.js`: Centralized persistent data and state.
*   `src/router/index.ts`, `navigate.js`: Global navigation routing.
*   `src/service/chat.js`, `project.js`, `wiki.js`, `service.js`: Business logic and service layer.
*   `src/api/socket.js`, `connection.js`, `chatManager.js`, `api.js`: External communication and WebSocket management.

## Main Views & Workspaces
*   `src/views/ChatView.vue`: Core chat interface.
*   `src/views/DesktopView.vue`: Multi-window desktop simulation.
*   `src/views/AgentPlanView.vue`: Agent planning and workflows.
*   `src/views/GlobalSettings.vue`, `AISettings.vue`, `KnowledgeSettings.vue`: Configuration hubs.
*   `src/views/HomeView.vue`, `ProjectSettings.vue`, `ProfileView.vue`, `WikiView.vue`, `KnowledgeView.vue`, `FileBrowserView.vue`, `TeamView.vue`: Additional views.

## Chat & Messaging
*   `src/components/chat/Chat.vue`: Main chat component.
*   `src/components/chat/ChatInput.vue`, `ChatInputBox.vue`, `ChatInputToolbar.vue`: Input handling and toolbar.
*   `src/components/chat/ChatFile*.vue`: File management and preview.
*   `src/components/chat/ChatImage*.vue`: Image display and carousel.
*   `src/components/chat/ChatIntelliSense.vue`, `LLMModelSelector.vue`: LLM integration.
*   `src/components/chat/ChatMentionBar.vue`, `EmojiPicker.vue`, `ExportChat.vue`: Additional chat features.

## Code Editing & Version Control
*   `src/components/monaco/Editor.vue`, `DiffViewer.vue`: Code editor wrappers.
*   `src/components/code-editor/CodeEditor.jsx`: React-based code editor.
*   `src/components/repo/PRView.vue`, `PRFile.vue`, `PRCommitSelector.vue`, `PRReport.vue`: Pull request visualization.
*   `src/components/repo/CommitTreeView.vue`, `BranchSelector.vue`: Git history and branches.
*   `src/components/code/GitDiffViewer.vue`: File version comparison.

## Project Management & Task Boards
*   `src/components/project/*`: Project metadata, navigation, and creation (`ProjectCard.vue`, `ProjectOverview.vue`, `ProjectScripts.vue`, `NewProject.vue`).
*   `src/components/kanban/*`: Task board with columns, cards, and views (`Kanban.vue`, `KanbanColumnView.vue`, `TaskCard.vue`, `KanbanSettings.vue`, `KanbanGridView.vue`, `KanbanList.vue`).

## Workspaces & Teams
*   `src/components/workspaces/*`: Workspace organization and selection (`Workspaces.vue`, `WorkspacesSelector.vue`, `WorkspacesViewer.vue`, `WorkspaceSettings.vue`).
*   `src/components/teams/*`: Team and channel management (`TeamSettings.vue`, `ChannelSettings.vue`, `MemberSettings.vue`, `CreateTeamDialog.vue`, `CreateChannelDialog.vue`).

## AI Configuration & Settings
*   `src/components/ai_settings/AIModels.vue`, `AIProviders.vue`: Model and provider management.
*   `src/components/ai_settings/AIModelSettings.vue`, `AIProviderSettings.vue`, `AgentSettings.vue`, `ModelSelector.vue`: Configuration forms.

## Analytics, Logs & Monitoring
*   `src/components/analytics/DailyChart.vue`, `MetricsDashboard.vue`: Analytics visualization.
*   `src/components/logs/LogsTable.vue`, `LogEntryDetail.vue`: Log display and details.
*   `src/components/logs/LogsAnalytics.vue`, `LogsAnalyzerDashboard.vue`, `LogsFilterBar.vue`, `LogsLiveMetrics.vue`: Analysis and filtering.

## Media Management
*   `src/components/media/MediaGallery.vue`, `MediaLibrary.vue`, `MediaManager.vue`: Media browsing and organization.
*   `src/components/media/MediaPreview.vue`, `MediaUploadDialog.vue`: Media display and upload.
*   `src/store/media.js`: Media state management.

## User Management & Security
*   `src/components/user/Login.vue`, `UserProfile.vue`: Authentication and profiles.
*   `src/components/user/UserAvatar.vue`, `UserSelector.vue`, `ChatBar.vue`: User display and selection.
*   `src/components/security/*`: Account settings, user lists, and security configuration.
*   `src/components/roles/RoleSelector.vue`: Role management.
*   `src/components/profile/*`: Profile display and management.

## Data & Knowledge Management
*   `src/components/data/DataExplorer.vue`, `DataDetails.vue`, `DataRow.vue`: Data browsing and inspection.
*   `src/components/knowledge/KnowledgeSearch.vue`: Knowledge base search.
*   `src/components/knowledge/settings/*`: Knowledge index, statistics, and configuration.

## UI & Theming
*   `src/components/ThemeSelector.vue`: Theme switching and customization.
*   `src/components/ui/ColorPicker.vue`: Color selection for theming.
*   `src/components/VSwatches.vue`: Color swatch display.

## Navigation & Layout
*   `src/components/main-menu/MainMenu.vue`, `MenubarItem.vue`, `MenubarSub.vue`: Sidebar and menu navigation.
*   `src/components/main-menu/ProjectsMenu.vue`, `WorkspacesMenu.vue`, `ViewsMenu.vue`: Context-specific menus.
*   `src/components/NavigationBar.vue`, `Toolbar.vue`, `EventBar.vue`: Top-level navigation.
*   `src/components/Splitter.vue`, `layout/VerticalSplitter.vue`: Layout dividers.
*   `src/components/TabView.vue`, `TabNavigation.vue`: Tabbed interfaces.
*   `src/components/Modal.vue`: Modal dialogs.

## Document & Content Viewing
*   `src/components/document/Document.vue`, `TipTapDocument.vue`, `Word.vue`: Document management.
*   `src/components/MarkdownViewer.vue`, `HTMLViewer.vue`, `MermaidViewer.vue`: Content renderers.
*   `src/components/CodeViewer.vue`, `ConsoleViewer.vue`, `LogViewer.vue`: Code and output viewers.

## Window Manager & Desktop
*   `src/components/windowManager/VirtualDesktop.vue`: Desktop container.
*   `src/components/windowManager/Window.vue`, `AppWindow.vue`: Window implementations.
*   `src/components/windowManager/Workspace.vue`, `Navigator.vue`: Workspace and navigation.
*   `src/components/desktop/Desktop.vue`, `Window.vue`, `Tab.vue`: Desktop simulation components.

## Utility Components
*   `src/components/TreeView.vue`, `TreeItem.vue`, `Collapsible.vue`: Tree navigation.
*   `src/components/NotificationControl.vue`: Notification management.
*   `src/components/autocomplete/AutoComplete.vue`, `ProjectResourcesAutoComplete.vue`: Input autocomplete.
*   `src/components/bar/SearchBar.vue`: Search functionality.
*   `src/components/ProfileCard.vue`, `UserInfo.vue`, `ProjectChip.vue`: Display components.

## External Integrations & Plugins
*   `src/components/oauth_settings/OAuthSettings.vue`: OAuth configuration.
*   `src/components/global_settings/plugins/*`: Plugin management and configuration.
*   `src/components/global_settings/EnvVariablesEditor.vue`: Environment configuration.

## File Browser
*   `src/views/FileBrowserView.vue`: Main file browser view.
*   `src/components/filebrowser/FileFinder.vue`: File search and discovery.

## Additional Components
*   `src/components/apps/*`: Application wrappers and interfaces (`AgentStudio.vue`, `Coder.vue`, `Files.vue`, `Preview.vue`).
*   `src/components/board/*`: User dashboard boards (`Achievements.vue`, `ContributionActivity.vue`, `LinkedProjects.vue`, `ProjectSettings.vue`).
*   `src/components/mention*/`, `tiptap/*`: Rich text editor and mention functionality.
*   `src/components/browser/Browser.vue`: Browser component.