# Codx Junior UI Project Summary

A comprehensive AI-powered digital workspace SPA built with Vue 3 and TypeScript, featuring code editing, desktop simulation, chat, version control, project management, and team collaboration.

## Project Configuration
- `package.json`: Project dependencies and scripts
- `vite.config.ts`: Build configuration for Vite
- `tsconfig.json`: TypeScript configuration
- `tailwind.config.js`: Tailwind CSS styling configuration
- `.eslintrc.cjs`: ESLint linting rules
- `.prettierrc.json`: Code formatting configuration
- `postcss.config.js`: PostCSS processing configuration
- `index.html`: HTML entry point

## Application Entry Point
- `src/main.ts`: Application initialization and mount
- `src/App.vue`: Root Vue component and layout structure

## API & Backend Integration
- `src/api/api.js`: Main API client and request handling
- `src/api/chatManager.js`: Chat API management
- `src/api/socket.js`: WebSocket connection handling
- `src/api/connection.js`: Connection utilities

## State Management (Vuex Store)
- `src/store/index.js`: Root state management store
- `src/store/chats.js`: Chat state and messages
- `src/store/session.js`: User session state
- `src/store/teams.js`: Team collaboration state
- `src/store/ui.js`: UI state and themes
- `src/store/profiles.js`: User profiles state
- `src/store/users.js`: Users list state
- `src/store/logs.js`: Logs and events state
- `src/store/media.js`: Media assets state
- `src/store/project.js`: Project management state

## Core Services
- `src/service/service.js`: Main service layer
- `src/service/chat.js`: Chat service and utilities
- `src/service/project.js`: Project service and utilities
- `src/service/wiki.js`: Wiki service and utilities

## Routing & Navigation
- `src/router/index.ts`: Vue Router configuration
- `src/router/navigate.js`: Navigation utilities
- `src/mixins/index.js`: Shared Vue mixins
- `src/model/chat.ts`: Chat data model types

## Core Views
- `src/views/HomeView.vue`: Main dashboard
- `src/views/HomeMobile.vue`: Mobile dashboard variant
- `src/views/ChatView.vue`: Chat interface
- `src/views/CodxJunior.vue`: Codx Junior assistant interface
- `src/views/GlobalSettings.vue`: Global application settings
- `src/views/AISettings.vue`: AI model and provider configuration
- `src/views/ProjectSettings.vue`: Project configuration
- `src/views/ProjectProfile.vue`: Project details page
- `src/views/ProjectScripts.vue`: Project script management
- `src/views/KnowledgeView.vue`: Knowledge base browser
- `src/views/KnowledgeSettings.vue`: Knowledge base configuration
- `src/views/TeamView.vue`: Team collaboration interface
- `src/views/DesktopView.vue`: Virtual desktop environment
- `src/views/VibeCodingView.vue`: Vibe coding interface
- `src/views/FileBrowserView.vue`: File system browser
- `src/views/WikiView.vue`: Wiki documentation viewer
- `src/views/ProfileView.vue`: User profile page
- `src/views/StatusView.vue`: System status dashboard
- `src/views/AgentPlanView.vue`: Agent planning interface
- `src/views/SharedView.vue`: Shared content viewer
- `src/views/SplitView.vue`: Split screen view
- `src/views/LiveEdit.vue`: Live editing interface
- `src/views/DocsView.vue`: Documentation viewer
- `src/views/AboutView.vue`: About page
- `src/views/CodxWelcomeView.vue`: Welcome screen

## Chat Components
- `src/components/chat/Chat.vue`: Main chat interface
- `src/components/chat/ChatInputBox.vue`: Message input handling
- `src/components/chat/ChatMessageList.vue`: Message display
- `src/components/chat/ChatFileList.vue`: File attachment management
- `src/components/chat/ChatImageCarousel.vue`: Image preview carousel
- `src/components/chat/ChatImagePreviewModal.vue`: Image preview dialog
- `src/components/chat/LLMModelSelector.vue`: Model selection dropdown
- `src/components/chat/EmojiPicker.vue`: Emoji insertion tool
- `src/components/chat/ExportChat.vue`: Chat export utility
- `src/components/chat/ChatFileSelectorModal.vue`: File selection dialog
- `src/components/chat/ChatIntelliSense.vue`: Intelligent autocomplete
- `src/components/chat/UserSelector.vue`: User mention selection
- `src/components/chat/ChatMentionBar.vue`: Mention suggestions
- `src/components/chat/ChatInputToolbar.vue`: Input formatting toolbar
- `src/components/chat/ChatBrowser.vue`: Chat browsing interface
- `src/components/chat/ChatIcon.vue`: Chat icon display
- `src/components/chat/CheckLists.vue`: Checklist management
- `src/components/chat/AddFileDialog.vue`: File addition modal
- `src/components/chat/ChatFilePreview.vue`: File preview display
- `src/components/chat/ChatSelector.vue`: Chat selection interface
- `src/components/chats/RecentChatsQuickAccess.vue`: Recent chats access

## Code Editor & Viewing
- `src/components/code-editor/CodeEditor.jsx`: Monaco-based code editor
- `src/components/CodeEditor.vue`: Vue wrapper for code editor
- `src/components/Code.vue`: Code display component
- `src/components/CodeViewer.vue`: Read-only code viewer
- `src/components/DiffViewer.vue`: Diff visualization
- `src/components/monaco/Editor.vue`: Monaco editor integration
- `src/components/monaco/DiffViewer.vue`: Monaco diff viewer
- `src/components/code/GitDiffViewer.vue`: Git diff viewer

## AI & Agent Configuration
- `src/components/ai_settings/AIProviders.vue`: AI provider management
- `src/components/ai_settings/AIProviderSettings.vue`: AI provider setup
- `src/components/ai_settings/AIModels.vue`: AI models list
- `src/components/ai_settings/AIModels2.vue`: AI models list variant
- `src/components/ai_settings/AIModelSettings.vue`: AI model configuration interface
- `src/components/ai_settings/AgentSettings.vue`: Agent configuration
- `src/components/ai_settings/ModelSelector.vue`: Model selection component
- `src/components/codx-junior/Assistant.vue`: Codx Junior assistant
- `src/components/codx-junior/AssistantChat.vue`: Assistant chat interface
- `src/components/apps/AgentStudio.vue`: Agent development studio
- `src/components/assistant/codxjunior.vue`: Codx Junior component

## Project Management
- `src/components/project/ProjectCard.vue`: Project display cards
- `src/components/project/NewProject.vue`: Project creation wizard
- `src/components/project/ProjectScripts.vue`: Script management
- `src/components/project/ProjectOverview.vue`: Overview display
- `src/components/project/ProjectIconSelector.vue`: Icon selection
- `src/components/project/ProjectInlineNavigator.vue`: Inline navigation
- `src/components/project/QuickBar.vue`: Quick action bar
- `src/components/project/ProjectBadge.vue`: Project badge display
- `src/components/project/CodxDropdown.vue`: Codx dropdown selector
- `src/components/project/BarButton.vue`: Bar button component
- `src/components/project/ProjectIconSquare.vue`: Square icon variant
- `src/components/ProjectDetailt.vue`: Project detail component
- `src/components/ProjectScriptSettings.vue`: Project script settings

## Kanban & Task Management
- `src/components/kanban/Kanban.vue`: Kanban board interface
- `src/components/kanban/KanbanColumnView.vue`: Column view
- `src/components/kanban/KanbanList.vue`: List view
- `src/components/kanban/KanbanGridView.vue`: Grid view
- `src/components/kanban/KanbanFilesView.vue`: Files view
- `src/components/kanban/TaskCard.vue`: Individual task cards
- `src/components/kanban/TaskCardLite.vue`: Lightweight task card
- `src/components/kanban/TaskSettings.vue`: Task configuration
- `src/components/kanban/KanbanSettings.vue`: Kanban configuration
- `src/components/kanban/NewEditBoardModal.vue`: Board creation/edit
- `src/components/kanban/KanbanContainer.vue`: Kanban container
- `src/components/kanban/KanbanTreeNode.vue`: Tree node display
- `src/components/kanban/ChatHistory.vue`: Chat history in kanban
- `src/components/kanban/Badge.vue`: Badge component

## Team & Collaboration
- `src/components/teams/TeamChannel.vue`: Team channel interface
- `src/components/teams/TeamSelector.vue`: Team selection dropdown
- `src/components/teams/TeamBar.vue`: Team navigation bar
- `src/components/teams/TeamSettings.vue`: Team configuration
- `src/components/teams/TeamDM.vue`: Team direct messaging
- `src/components/teams/TeamMediaLibrary.vue`: Team media assets
- `src/components/teams/TeamChannelsSidebar.vue`: Channel list sidebar
- `src/components/teams/AddMemberDialog.vue`: Member addition modal
- `src/components/teams/CreateTeamDialog.vue`: Team creation dialog
- `src/components/teams/CreateChannelDialog.vue`: Channel creation dialog
- `src/components/teams/MemberAvatar.vue`: Member avatar display
- `src/components/teams/MemberSettings.vue`: Member configuration
- `src/components/teams/CategorySettings.vue`: Category configuration
- `src/components/teams/ChannelSettings.vue`: Channel configuration
- `src/components/teams/TeamQuickBar.vue`: Team quick actions

## Settings & Configuration
- `src/components/global_settings/GeneralSettings.vue`: General application settings
- `src/components/global_settings/EnvVariablesEditor.vue`: Environment variables configuration
- `src/components/global_settings/plugins/PluginsEditor.vue`: Plugin management
- `src/components/global_settings/plugins/PluginsGrid.vue`: Plugin grid view
- `src/components/global_settings/plugins/PluginCard.vue`: Plugin card display
- `src/components/global_settings/plugins/PluginModal.vue`: Plugin detail modal
- `src/components/global_settings/plugins/LoadPluginModal.vue`: Plugin loading dialog
- `src/components/security/AccountSettings.vue`: Account configuration
- `src/components/security/SecurityUserList.vue`: Security user list
- `src/components/security/UserSecuritySettings.vue`: User security settings
- `src/components/security/UserWalletSettings.vue`: Wallet configuration
- `src/components/oauth_settings/OAuthSettings.vue`: OAuth configuration
- `src/components/ThemeSelector.vue`: Theme selection component

## Analytics & Logs
- `src/components/analytics/DailyChart.vue`: Daily metrics chart
- `src/components/analytics/MetricsDashboard.vue`: Metrics and analytics dashboard
- `src/components/analytics/PriceEditor.vue`: Price configuration
- `src/components/analytics/index.vue`: Analytics module index
- `src/components/logs/LogsAnalyzerDashboard.vue`: Log analysis interface
- `src/components/logs/LogsTable.vue`: Logs table display
- `src/components/logs/LogsFilterBar.vue`: Logs filtering interface
- `src/components/logs/LogsLiveMetrics.vue`: Live metrics display
- `src/components/logs/LogEntryDetail.vue`: Log entry details
- `src/components/logs/LogsAnalytics.vue`: Logs analytics view
- `src/components/metrics/MetricsViewer.vue`: Metrics visualization
- `src/components/metrics/HeatMap.vue`: Heat map visualization
- `src/components/metrics/RequestMetrics.vue`: Request metrics display

## Version Control
- `src/components/repo/PRView.vue`: Pull request viewer
- `src/components/repo/PRFile.vue`: PR file viewer
- `src/components/repo/PRReport.vue`: PR analysis report
- `src/components/repo/CommitTreeView.vue`: Commit history visualization
- `src/components/repo/CodeComment.vue`: Code comment component
- `src/components/repo/BranchSelector.vue`: Branch selection component
- `src/components/repo/PRBranchSelectoor.vue`: PR branch selector
- `src/components/repo/PRCommitSelector.vue`: PR commit selector
- `src/components/repo/PRFileViewModeSelector.vue`: PR file view mode selector
- `src/components/git/BranchSelector.vue`: Git branch selection
- `src/components/repository/RepositoryBar.vue`: Repository toolbar

## Knowledge & Documentation
- `src/components/knowledge/KnowledgeSearch.vue`: Knowledge base search
- `src/components/knowledge/settings/KnowledgeIndex.vue`: Knowledge indexing
- `src/components/knowledge/settings/KnowledgeFileList.vue`: Knowledge file list
- `src/components/knowledge/settings/KnowledgeIndexStats.vue`: Index statistics
- `src/components/knowledge/settings/KnowledgeIgnorePatterns.vue`: Ignore patterns configuration
- `src/components/knowledge/settings/KnowledgeSearch.vue`: Knowledge search settings
- `src/components/wiki/WikiSections.vue`: Wiki page sections
- `src/components/wiki/WikiTree.vue`: Wiki tree navigation
- `src/components/wiki/WikiSettings.vue`: Wiki configuration

## Board & Community
- `src/components/board/Achievements.vue`: Achievements display
- `src/components/board/ContributionActivity.vue`: Contribution activity
- `src/components/board/ContributionGraph.vue`: Contribution visualization
- `src/components/board/LinkedProjects.vue`: Linked projects display
- `src/components/board/ProjectSettings.vue`: Project board settings
- `src/components/board/SettingsAndCustomization.vue`: Board customization

## Workspaces & Desktop
- `src/components/workspaces/WorkspacesViewer.vue`: Workspaces viewer
- `src/components/workspaces/Workspaces.vue`: Workspaces interface
- `src/components/workspaces/WorkspacesSelector.vue`: Workspace selection
- `src/components/workspaces/WorkspaceSettings.vue`: Workspace configuration
- `src/components/desktop/Desktop.vue`: Desktop environment
- `src/components/desktop/VibeDesktop.vue`: Vibe desktop variant
- `src/components/desktop/Window.vue`: Window component
- `src/components/desktop/EmptyStateWelcome.vue`: Empty state welcome
- `src/components/desktop/Tab.vue`: Desktop tab component

## Window Management & Applications
- `src/components/windowManager/AppWindow.vue`: App window container
- `src/components/windowManager/Window.vue`: Window manager component
- `src/components/windowManager/VirtualDesktop.vue`: Virtual desktop
- `src/components/windowManager/Workspace.vue`: Workspace container
- `src/components/windowManager/Navigator.vue`: Window navigator
- `src/components/apps/AppBar.vue`: Application bar
- `src/components/apps/AppIcon.vue`: App icon display
- `src/components/apps/Coder.vue`: Code application
- `src/components/apps/Files.vue`: File manager application
- `src/components/apps/Preview.vue`: Preview application

## Content Viewers & Editors
- `src/components/HTMLViewer.vue`: HTML content viewer
- `src/components/MarkdownViewer.vue`: Markdown renderer
- `src/components/Markdown.vue`: Markdown component
- `src/components/MermaidViewer.vue`: Mermaid diagram viewer
- `src/components/YoutubeViewer.vue`: YouTube player
- `src/components/Iframe.vue`: IFrame wrapper
- `src/components/ConsoleViewer.vue`: Console output viewer
- `src/components/LogViewer.vue`: Log file viewer
- `src/components/document/Document.vue`: Document viewer
- `src/components/document/DocumentSummary.vue`: Document summary
- `src/components/document/TipTapDocument.vue`: TipTap document editor
- `src/components/document/Word.vue`: Word document viewer
- `src/components/tiptap/SimpleEditor.vue`: Simple TipTap editor
- `src/components/tiptap/MentionList.vue`: Mention list for TipTap
- `src/components/tiptap/suggestion.js`: TipTap suggestion utilities

## Media & Files
- `src/components/media/MediaGallery.vue`: Media gallery display
- `src/components/media/MediaLibrary.vue`: Media library manager
- `src/components/media/MediaManager.vue`: Media management interface
- `src/components/media/MediaPreview.vue`: Media preview component
- `src/components/media/MediaUploadDialog.vue`: Media upload dialog
- `src/components/filebrowser/FileFinder.vue`: File finder/search
- `src/components/browser/Browser.vue`: Web browser component

## Search & Autocomplete
- `src/components/bar/SearchBar.vue`: Search bar component
- `src/components/autocomplete/AutoComplete.vue`: Autocomplete component
- `src/components/autocomplete/Editable.vue`: Editable autocomplete
- `src/components/autocomplete/ProjectResourcesAutoComplete.vue`: Project resources autocomplete
- `src/components/search/SearchForm.vue`: Search form interface
- `src/components/search/ResultViewer.vue`: Search results viewer

## Vibe Coding Components
- `src/components/vibe/ChatPanel.vue`: Vibe chat panel
- `src/components/vibe/ChatPanelHeader.vue`: Chat panel header
- `src/components/vibe/VibeCodingHeader.vue`: Vibe coding header
- `src/components/vibe/modals/SubtaskModal.vue`: Subtask modal dialog
- `src/components/vibe/modals/SubtasksModal.vue`: Multiple subtasks modal
- `src/components/vibe/modals/TagModal.vue`: Tag modal dialog
- `src/components/vibe/panels/BranchSelector.vue`: Branch selection panel
- `src/components/vibe/panels/ChangesPanel.vue`: Changes display panel
- `src/components/vibe/panels/PreviewPanel.vue`: Preview panel

## UI Layout & Navigation
- `src/components/Modal.vue`: Modal dialog component
- `src/components/Toolbar.vue`: Toolbar UI element
- `src/components/TopBar.vue`: Top navigation bar
- `src/components/NavigationBar.vue`: Navigation component
- `src/components/Menu.vue`: Menu system
- `src/components/MenuDropDown.vue`: Menu dropdown component
- `src/components/TabNavigation.vue`: Tab-based navigation
- `src/components/TabView.vue`: Tab view container
- `src/components/Splitter.vue`: Resizable splitter
- `src/components/TreeView.vue`: Tree view component
- `src/components/TreeItem.vue`: Individual tree item
- `src/components/Collapsible.vue`: Collapsible section component
- `src/components/Row.vue`: Row layout component
- `src/components/EventBar.vue`: Event display bar
- `src/components/StatuBar.vue`: Status bar component
- `src/components/layout/VerticalSplitter.vue`: Vertical splitter layout

## Main Menu Components
- `src/components/main-menu/MainMenu.vue`: Main application menu
- `src/components/main-menu/MenubarItem.vue`: Menu bar item
- `src/components/main-menu/MenubarSub.vue`: Menu bar submenu
- `src/components/main-menu/MenuDivider.vue`: Menu divider
- `src/components/main-menu/ProjectsMenu.vue`: Projects menu section
- `src/components/main-menu/ViewsMenu.vue`: Views menu section
- `src/components/main-menu/WorkspacesMenu.vue`: Workspaces menu section
- `src/components/main-menu/SettingsMenu.vue`: Settings menu section
- `src/components/main-menu/ViewProperties.vue`: View properties display
- `src/components/main-menu/ProjectLabel.vue`: Project label component

## User & Profile Management
- `src/components/user/UserAvatar.vue`: User avatar display
- `src/components/user/UserProfile.vue`: User profile page
- `src/components/user/UserSelector.vue`: User selection dropdown
- `src/components/user/ChatBar.vue`: User chat bar
- `src/components/user/Login.vue`: Login interface
- `src/components/profile/ProfileAvatar.vue`: Profile avatar component
- `src/components/profile/ProfileSelector.vue`: Profile selection
- `src/components/profiles/ProfileViewer.vue`: Profile viewer
- `src/components/EditProfile.vue`: Profile editing interface
- `src/components/UserInfo.vue`: User info display
- `src/components/UserList.vue`: User list component
- `src/components/ProfileCard.vue`: Profile card display

## Miscellaneous Components
- `src/components/CodxJuniorLogo.vue`: Codx Junior logo
- `src/components/Logo.vue`: Application logo
- `src/components/ProjectChip.vue`: Project chip display
- `src/components/ProjectDropdown.vue`: Project dropdown selector
- `src/components/ProjectIcon.vue`: Project icon display
- `src/components/IssuePreview.vue`: Issue preview component
- `src/components/NotificationControl.vue`: Notification control
- `src/components/TimeSelector.vue`: Time selection component
- `src/components/TagsComponent.vue`: Tags display
- `src/components/MetricRow.vue`: Metric row display
- `src/components/VSwatches.vue`: Color swatches picker
- `src/components/MobileMenu.vue`: Mobile navigation menu
- `src/components/LogAIView.vue`: AI log viewer
- `src/components/ExportImportButton.vue`: Export/import utility
- `src/components/EmbeddedCodxJunior.vue`: Embedded assistant
- `src/components/NoVNC.vue`: NoVNC remote viewer
- `src/components/CodxMenu.vue`: Codx menu component
- `src/components/ChatEntry.vue`: Chat entry component
- `src/components/ChatEntryMobile.vue`: Mobile chat entry
- `src/components/ChatEntrySlack.vue`: Slack-style chat entry
- `src/components/ChatProjectIcon.vue`: Chat project icon
- `src/components/HelloWorld.vue`: Hello world example
- `src/components/data/DataExplorer.vue`: Data exploration interface
- `src/components/data/DataDetails.vue`: Data details viewer
- `src/components/data/DataRow.vue`: Data row component
- `src/components/events/EventList.vue`: Event list display
- `src/components/mentions/MentionSelector.vue`: Mention selection
- `src/components/roles/RoleSelector.vue`: Role selection
- `src/components/wall/Wall.vue`: Wall display interface
- `src/components/wall/ChatPreview.vue`: Chat preview on wall
- `src/components/wizards/Wizard.vue`: Wizard dialog component
- `src/components/ui/ColorPicker.vue`: Color picker component
- `src/components/mobile/MenuBar.vue`: Mobile menu bar
- `src/components/dummy.vue`: Dummy component
- `src/components/icons/*`: Icon components for UI elements