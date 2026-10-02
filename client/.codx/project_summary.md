# Codx Junior UI Project

Codx Junior UI is a Vue 3 application for AI-driven workspace management, team collaboration, and real-time communication with integrated chat, project management, and knowledge systems.

## Configuration & Setup
- `.eslintrc.cjs`: ESLint configuration.
- `.prettierrc.json`: Prettier code formatting settings.
- `tailwind.config.js`: Tailwind CSS styling configuration.
- `vite.config.ts`: Vite build and development server configuration.
- `package.json`: Project dependencies and npm scripts.
- `tsconfig.json`: TypeScript compiler configuration.

## Documentation
- `README.md`: Project overview and setup guide.
- `api-examples.md`: API usage examples and integration patterns.

## Core Application
- `index.html`: Main web entry point.
- `src/main.ts`: Application entry and initialization.
- `src/App.vue`: Root Vue component.

## API & Services
- `src/api/api.js`: General API client and request handling.
- `src/api/chatManager.js`: Chat operations and message management.
- `src/api/connection.js`: Connection lifecycle and state management.
- `src/api/socket.js`: WebSocket communication layer.
- `src/api/model/ChatSearchRequest.js`: Chat search request model and validation.
- `src/api/model/ChatSearchResponse.js`: Chat search response model and data structures.
- `src/api/model/analytics.ts`: Analytics data models and types.
- `src/api/modules/analytics.js`: Analytics API operations.
- `src/api/modules/chats.js`: Chat API operations and endpoints.
- `src/api/modules/files.js`: File upload and management API operations.
- `src/api/modules/globalSettings.js`: Global application settings API operations.
- `src/api/modules/logs.js`: Logs API operations and retrieval.
- `src/api/modules/views.js`: Views API operations and management.
- `src/service/chat.js`: Chat business logic and utilities.
- `src/service/project.js`: Project management services.
- `src/service/service.js`: General service utilities.
- `src/service/wiki.js`: Wiki and knowledge base services.

## State Management
- `src/store/index.js`: Vuex store configuration and setup.
- `src/store/chats.js`: Chat state and messages.
- `src/store/project.js`: Project data and settings state.
- `src/store/session.js`: User session and authentication state.
- `src/store/ui.js`: UI state and layout preferences.
- `src/store/users.js`: User profiles and list state.
- `src/store/teams.js`: Team and collaboration state.
- `src/store/media.js`: Media library and uploads state.
- `src/store/logs.js`: Application logs and monitoring state.
- `src/store/profiles.js`: User profile preferences state.
- `src/store/entityStatuses.js`: Entity status tracking and management.
- `src/store/views.js`: Views and layout state management.

## Data Models
- `src/model/chat.ts`: Chat message and conversation data structures.
- `src/models/MCPServer.js`: MCP server configuration model and validation.

## Chat Components
- `src/components/chat/Chat.vue`: Main chat interface and container.
- `src/components/chat/ChatViewHeader.vue`: Chat view header with title and controls.
- `src/components/chat/ChatBreadcrumb.vue`: Navigation breadcrumb in chat context.
- `src/components/chat/ChatMessageList.vue`: Displays chat message history.
- `src/components/chat/ChatMessageEditor.vue`: Editor for composing and editing messages.
- `src/components/chat/ChatInputBox.vue`: Input field for new messages.
- `src/components/chat/ChatInputToolbar.vue`: Toolbar with formatting and actions.
- `src/components/chat/ChatMentionBar.vue`: Mention and tag autocomplete.
- `src/components/chat/ChatModeSelector.vue`: Select chat mode and conversation type.
- `src/components/chat/ChatProfileSelector.vue`: Select chat profile and context.
- `src/components/chat/ChatFileList.vue`: File attachments display and management.
- `src/components/chat/ChatFilePreview.vue`: Preview uploaded files.
- `src/components/chat/ChatFileSelectorModal.vue`: File selection dialog.
- `src/components/chat/ChatFileUploadConfirmModal.vue`: Confirmation modal for file uploads.
- `src/components/chat/ChatIntelliSense.vue`: Smart context and suggestions.
- `src/components/chat/ChatImageCarousel.vue`: Image attachment carousel display.
- `src/components/chat/ChatImagePreviewModal.vue`: Image preview modal.
- `src/components/chat/ChatHistoryViewer.vue`: Browse chat history and archives.
- `src/components/chat/ChatSelector.vue`: Select between multiple chats.
- `src/components/chat/Selector.vue`: Generic selector component for chat context.
- `src/components/chat/ChatIcon.vue`: Chat visual identifier icon.
- `src/components/chat/ChatBrowser.vue`: Chat browsing interface.
- `src/components/chat/ChatChildrenTree.vue`: Display chat hierarchy and child conversations.
- `src/components/chat/ChatNavigatorDrawer.vue`: Drawer for chat navigation and selection.
- `src/components/chat/ChatNavigatorNode.vue`: Individual node in chat navigator tree.
- `src/components/chat/ChatSearch.vue`: Search chats and messages.
- `src/components/chat/ChatSidebar.vue`: Sidebar for chat navigation and quick access.
- `src/components/chat/ChatSidebarNode.vue`: Individual node in chat sidebar tree.
- `src/components/chat/ChatTreeNode.vue`: Hierarchical tree node for chat navigation.
- `src/components/chat/AddFileDialog.vue`: Add files to chat dialog.
- `src/components/chat/CheckLists.vue`: Task and checklist management.
- `src/components/chat/EmojiPicker.vue`: Emoji selection picker.
- `src/components/chat/ExportChat.vue`: Export chat to various formats.
- `src/components/chat/FileActionMenu.vue`: Context menu for file actions in chat.
- `src/components/chat/LLMModelSelector.vue`: Select AI model for chat.
- `src/components/chat/ChatLLMModelSelector.vue`: Chat-specific LLM model selector.
- `src/components/chat/MessageFileView.vue`: Display file information in messages.
- `src/components/chat/MessagePRView.vue`: Display PR information in messages.
- `src/components/chat/ParentContentIndicator.vue`: Display parent chat content reference.
- `src/components/chat/UserSelector.vue`: Select users for chat/mentions.
- `src/components/chat/ProfileDrawer.vue`: Profile management drawer for chat context.
- `src/components/chats/RecentChatsQuickAccess.vue`: Recent chats sidebar.

## Chat Entry Components
- `src/components/ChatEntry.vue`: Individual chat message entry wrapper.
- `src/components/ChatEntryDrawer.vue`: Drawer component for chat entry details.
- `src/components/ChatEntryEvent.vue`: Event-based chat entry handler.
- `src/components/ChatEntryEventCard.vue`: Event-based chat entry card display.
- `src/components/ChatEntryMetadata.vue`: Chat entry metadata display and management.
- `src/components/ChatEntryMobile.vue`: Mobile-optimized chat entry display.
- `src/components/ChatEntrySelectionMenu.vue`: Selection menu for chat entries.
- `src/components/ChatEntrySlack.vue`: Slack-formatted chat entry display.
- `src/components/ChatEntryTimeline.vue`: Timeline visualization of chat entries.
- `src/components/ChatEntryToolCard.vue`: Tool card display for chat entry tools.
- `src/components/ChatEntryTools.vue`: Tools panel for chat entry actions and utilities.
- `src/components/QuickChatSelector.vue`: Quick chat selection component.

## Navigation & Search
- `src/components/main-menu/MainMenu.vue`: Central navigation and menu system.
- `src/components/main-menu/MenubarItem.vue`: Individual menu item component.
- `src/components/main-menu/MenubarSub.vue`: Submenu handler.
- `src/components/main-menu/MenuDivider.vue`: Menu divider component.
- `src/components/main-menu/ProjectsMenu.vue`: Projects submenu.
- `src/components/main-menu/ViewsMenu.vue`: Views and layouts submenu.
- `src/components/main-menu/SettingsMenu.vue`: Settings submenu.
- `src/components/main-menu/WorkspacesMenu.vue`: Workspaces submenu.
- `src/components/main-menu/ProjectLabel.vue`: Project label display.
- `src/components/main-menu/ViewProperties.vue`: View properties and options.
- `src/components/NavigationBar.vue`: Top navigation bar.
- `src/components/TopBar.vue`: Top application bar.
- `src/components/TopBarSearch.vue`: Search interface in top bar.
- `src/components/MobileMenu.vue`: Mobile navigation menu.
- `src/components/Menu.vue`: Generic menu component.
- `src/components/MenuDropDown.vue`: Dropdown menu wrapper.
- `src/components/SelectionMenu.vue`: Selection menu for list items.
- `src/components/ThemeSelector.vue`: Theme selection interface.
- `src/components/TabNavigation.vue`: Tab-based navigation component.
- `src/components/bar/SearchBar.vue`: Search input bar.
- `src/components/search/SearchForm.vue`: General search interface.
- `src/components/search/ResultViewer.vue`: Display search results.

## Project & File Management
- `src/components/project/ProjectOverview.vue`: Project summary and statistics.
- `src/components/project/ProjectCard.vue`: Project card display component.
- `src/components/project/NewProject.vue`: Create new project interface.
- `src/components/project/ProjectSettings.vue`: Project configuration panel.
- `src/components/project/ProjectScripts.vue`: Project automation scripts.
- `src/components/project/ProjectIconSelector.vue`: Project icon picker.
- `src/components/project/ProjectBadge.vue`: Project status badge.
- `src/components/project/ProjectInlineNavigator.vue`: Inline project navigation.
- `src/components/project/ProjectLoadingOverlay.vue`: Loading overlay for projects.
- `src/components/project/QuickBar.vue`: Quick actions toolbar.
- `src/components/project/CodxDropdown.vue`: Codx-specific dropdown.
- `src/components/project/ProjectIconSquare.vue`: Square project icon display.
- `src/components/project/BarButton.vue`: Button component for toolbars.
- `src/components/ProjectChip.vue`: Compact project display.
- `src/components/ProjectDetailt.vue`: Project detail view.
- `src/components/ProjectDropdown.vue`: Project selection dropdown.
- `src/components/ProjectIcon.vue`: Project icon component.
- `src/components/ProjectList.vue`: List all projects.
- `src/components/ProjectScriptSettings.vue`: Project script configuration.
- `src/components/ProjectSelector.vue`: Select and display projects.
- `src/components/ProjectSelectorContent.vue`: Project selector content panel.
- `src/components/filebrowser/FileExplorer.vue`: File browsing interface.
- `src/components/filebrowser/FileExplorerPanel.vue`: File explorer sidebar panel.
- `src/components/filebrowser/FileViewer.vue`: File content viewer.
- `src/components/filebrowser/TabManager.vue`: Manage open file tabs in editor.

## Project Settings
- `src/components/project_settings/MCPServerListEditor.vue`: MCP server configuration and management.
- `src/components/project_settings/MCPServerSettings.vue`: Individual MCP server settings and configuration.

## Workspace Management
- `src/components/workspaces/WorkspacesManager.vue`: Overall workspace operations.
- `src/components/workspaces/WorkspacesList.vue`: List all workspaces.
- `src/components/workspaces/WorkspaceCard.vue`: Individual workspace card.
- `src/components/workspaces/WorkspaceCreate.vue`: Create new workspace.
- `src/components/workspaces/WorkspaceCreateContent.vue`: Workspace creation content panel.
- `src/components/workspaces/WorkspaceCreateSidebar.vue`: Workspace creation sidebar.
- `src/components/workspaces/WorkspaceSettings.vue`: Workspace configuration.
- `src/components/workspaces/WorkspaceStatusBadge.vue`: Workspace status indicator.
- `src/components/workspaces/WorkspaceTemplateSelector.vue`: Workspace template selection.
- `src/components/workspaces/WorkspacesSelector.vue`: Select active workspace.
- `src/components/workspaces/WorkspacesViewer.vue`: Workspace viewing interface.
- `src/components/workspaces/WorkspaceActions.vue`: Workspace action buttons and controls.
- `src/components/workspaces/WorkspaceAppBuilder.vue`: Workspace app configuration builder.
- `src/components/workspaces/WorkspaceLogs.vue`: Workspace activity logs.
- `src/components/workspaces/WorkspaceProjectSelector.vue`: Project selection within workspace.
- `src/components/workspaces/Workspaces.vue`: Main workspaces interface.

## Code & Diff Viewing
- `src/components/Code.vue`: Generic code display component.
- `src/components/CodeViewer.vue`: Read-only code viewer.
- `src/components/CodeEditor.vue`: Editable code editor wrapper.
- `src/components/DiffViewer.vue`: Diff view component.
- `src/components/code-editor/CodeEditor.jsx`: Monaco editor integration.
- `src/components/monaco/Editor.vue`: Monaco editor Vue wrapper.
- `src/components/monaco/DiffViewer.vue`: Monaco-based diff viewer.
- `src/components/code/GitDiffViewer.vue`: Git diff visualization.

## Profile & User Management
- `src/components/user/UserProfile.vue`: User profile display.
- `src/components/user/UserAvatar.vue`: User avatar component.
- `src/components/user/UserSelector.vue`: Select user from list.
- `src/components/user/Login.vue`: Authentication login interface.
- `src/components/user/ChatBar.vue`: Chat bar with user context.
- `src/components/profile/ProfileViewer.vue`: Profile viewing interface.
- `src/components/profile/ProfileAvatar.vue`: Profile avatar display.
- `src/components/profile/ProfileSelector.vue`: Profile selection dropdown.
- `src/components/profiles/ProfileViewer.vue`: Advanced profile viewer.
- `src/components/ProfileChatEditor.vue`: Profile chat editor interface.
- `src/components/EditProfile.vue`: Profile editing interface.
- `src/components/ProfileCard.vue`: User profile card display.
- `src/components/security/AccountSettings.vue`: Account configuration.
- `src/components/security/UserSecuritySettings.vue`: Security preferences.
- `src/components/security/UserWalletSettings.vue`: Wallet and billing settings.
- `src/components/security/SecurityUserList.vue`: User security management list.

## Team & Collaboration
- `src/components/teams/TeamBar.vue`: Team selection and display bar.
- `src/components/teams/TeamSelector.vue`: Team selection interface.
- `src/components/teams/TeamSettings.vue`: Team configuration panel.
- `src/components/teams/TeamChannel.vue`: Team channel display.
- `src/components/teams/TeamChannelsSidebar.vue`: Channels navigation sidebar.
- `src/components/teams/TeamDM.vue`: Direct messaging interface.
- `src/components/teams/TeamQuickBar.vue`: Team quick actions toolbar.
- `src/components/teams/CreateTeamDialog.vue`: Create new team dialog.
- `src/components/teams/CreateChannelDialog.vue`: Create channel dialog.
- `src/components/teams/AddMemberDialog.vue`: Add team members dialog.
- `src/components/teams/MemberSettings.vue`: Team member configuration.
- `src/components/teams/MemberAvatar.vue`: Team member avatar component.
- `src/components/teams/ChannelSettings.vue`: Channel configuration.
- `src/components/teams/CategorySettings.vue`: Channel category settings.
- `src/components/teams/TeamMediaLibrary.vue`: Team shared media library.

## AI & Agent Components
- `src/components/ai_settings/AIModelSettings.vue`: AI model configuration.
- `src/components/ai_settings/AIModels.vue`: List and manage AI models.
- `src/components/ai_settings/AIModels2.vue`: Alternative AI models view.
- `src/components/ai_settings/AIProviderSettings.vue`: AI provider setup.
- `src/components/ai_settings/AIProviders.vue`: List and configure providers.
- `src/components/ai_settings/AIProvidersAndModels.vue`: Combined AI providers and models management.
- `src/components/ai_settings/AIProvidersAndModels_CardGrid.vue`: Card grid view for AI providers and models.
- `src/components/ai_settings/AgentSettings.vue`: Agent configuration panel.
- `src/components/ai_settings/ModelSelector.vue`: Select AI model dropdown.
- `src/components/apps/AgentStudio.vue`: Agent creation and editing interface.
- `src/components/assistant/codxjunior.vue`: Codx Junior assistant interface.
- `src/components/codx-junior/Assistant.vue`: Assistant wrapper component.
- `src/components/codx-junior/AssistantChat.vue`: Assistant chat interface.

## Analytics & Monitoring
- `src/components/analytics/DailyChart.vue`: Daily metrics chart.
- `src/components/analytics/MetricsDashboard.vue`: Metrics overview dashboard.
- `src/components/analytics/PriceEditor.vue`: Pricing configuration.
- `src/components/analytics/index.vue`: Analytics entry point.
- `src/components/logs/LogViewer.vue`: View application logs.
- `src/components/logs/LogsTable.vue`: Logs in table format.
- `src/components/logs/LogsFilterBar.vue`: Filter logs by criteria.
- `src/components/logs/LogsLiveMetrics.vue`: Real-time metrics display.
- `src/components/logs/LogsAnalytics.vue`: Logs analytics and insights.
- `src/components/logs/LogsAnalyzerDashboard.vue`: Advanced logs analysis dashboard.
- `src/components/logs/LogEntryDetail.vue`: Individual log entry details.
- `src/components/logs/LlmRequestsViewer.vue`: LLM API requests and responses viewer.
- `src/components/metrics/MetricsViewer.vue`: Metrics visualization.
- `src/components/metrics/RequestMetrics.vue`: Request performance metrics.
- `src/components/metrics/HeatMap.vue`: Heatmap visualization.

## Knowledge & Search
- `src/components/knowledge/KnowledgeSearch.vue`: Search knowledge base.
- `src/components/knowledge/settings/KnowledgeIndex.vue`: Knowledge index management.
- `src/components/knowledge/settings/KnowledgeIndexStats.vue`: Index statistics.
- `src/components/knowledge/settings/KnowledgeFileList.vue`: Files in knowledge base.
- `src/components/knowledge/settings/KnowledgeIgnorePatterns.vue`: Exclude patterns configuration.
- `src/components/knowledge/settings/KnowledgeSearch.vue`: Advanced search settings.

## Document & Content
- `src/components/document/Document.vue`: Document viewer and editor.
- `src/components/document/DocumentSummary.vue`: Document summary display.
- `src/components/document/ChapterBlock.vue`: Chapter section component for documents.
- `src/components/document/TipTapDocument.vue`: TipTap-based rich editor.
- `src/components/document/Word.vue`: Word document handler.
- `src/components/Markdown.vue`: Markdown renderer component.
- `src/components/MarkdownViewer.vue`: Standalone markdown viewer.
- `src/components/HTMLPreview.vue`: HTML content preview component.
- `src/components/HTMLViewer.vue`: HTML content viewer.

## Media & Gallery
- `src/components/media/MediaManager.vue`: Media file management.
- `src/components/media/MediaGallery.vue`: Media gallery display.
- `src/components/media/MediaLibrary.vue`: Media library browser.
- `src/components/media/MediaPreview.vue`: Media file preview.
- `src/components/media/MediaUploadDialog.vue`: Upload media dialog.

## Kanban & Task Management
- `src/components/kanban/Kanban.vue`: Kanban board interface.
- `src/components/kanban/KanbanList.vue`: Kanban as list view.
- `src/components/kanban/KanbanColumnView.vue`: Kanban column display.
- `src/components/kanban/KanbanGridView.vue`: Kanban grid layout view.
- `src/components/kanban/KanbanFilesView.vue`: Files attached to tasks.
- `src/components/kanban/KanbanTreeNode.vue`: Hierarchical task node.
- `src/components/kanban/KanbanContainer.vue`: Kanban container wrapper.
- `src/components/kanban/TaskCard.vue`: Individual task card.
- `src/components/kanban/TaskCardLite.vue`: Lightweight task card.
- `src/components/kanban/TaskSettings.vue`: Task configuration panel.
- `src/components/kanban/KanbanSettings.vue`: Kanban board settings.
- `src/components/kanban/NewEditBoardModal.vue`: Create/edit board dialog.
- `src/components/kanban/KanbanBoardModal.vue`: Kanban board modal.
- `src/components/kanban/ChatHistory.vue`: Chat history in kanban context.
- `src/components/kanban/Badge.vue`: Status badge component.

## Git & Repository
- `src/components/git/BranchSelector.vue`: Git branch selection.
- `src/components/repo/BranchSelector.vue`: Repository branch selector.
- `src/components/repo/PRView.vue`: Pull request viewer.
- `src/components/repo/PRReport.vue`: PR analysis and report.
- `src/components/repo/PRFile.vue`: Individual PR file changes.
- `src/components/repo/PRFileViewModeSelector.vue`: PR view mode options.
- `src/components/repo/PRBranchSelectoor.vue`: PR branch selection.
- `src/components/repo/PRCommitSelector.vue`: PR commit selection.
- `src/components/repo/PRViewer.vue`: Advanced pull request viewer and navigation.
- `src/components/repo/CommitTreeView.vue`: Commit history tree view.
- `src/components/repo/CodeComment.vue`: Code review comments.
- `src/components/repository/RepositoryBar.vue`: Repository information bar.

## Data & Table Management
- `src/components/data/DataExplorer.vue`: Data browsing and exploration.
- `src/components/data/DataDetails.vue`: Detailed data view.
- `src/components/data/DataRow.vue`: Individual data row component.
- `src/components/InteractiveTable.vue`: Interactive table component.

## Desktop & Window Management
- `src/components/desktop/Desktop.vue`: Desktop workspace view.
- `src/components/desktop/VibeDesktop.vue`: Vibe mode desktop interface.
- `src/components/desktop/Window.vue`: Draggable window component.
- `src/components/desktop/Tab.vue`: Window tab component.
- `src/components/desktop/EmptyStateWelcome.vue`: Welcome empty state.
- `src/components/desktop/GroupHeaderActions.vue`: Group header action controls.
- `src/components/windowManager/VirtualDesktop.vue`: Virtual desktop environment.
- `src/components/windowManager/Workspace.vue`: Workspace window container.
- `src/components/windowManager/Window.vue`: Window wrapper.
- `src/components/windowManager/AppWindow.vue`: Application window.
- `src/components/windowManager/Navigator.vue`: Window navigation.

## Vibe Mode Panels
- `src/components/vibe/ChatPanel.vue`: Chat panel for Vibe mode.
- `src/components/vibe/ChatPanelHeader.vue`: Vibe chat panel header.
- `src/components/vibe/VibeCodingHeader.vue`: Vibe coding mode header.
- `src/components/vibe/panels/BranchSelector.vue`: Vibe branch selection panel.
- `src/components/vibe/panels/ChangesPanel.vue`: Vibe changes display panel.
- `src/components/vibe/panels/PreviewPanel.vue`: Vibe preview panel.
- `src/components/vibe/panels/PRChangesPanel.vue`: Pull request changes panel for Vibe mode.
- `src/components/vibe/panels/PRSearchPanel.vue`: Pull request search panel for Vibe mode.
- `src/components/vibe/modals/SubtaskModal.vue`: Subtask dialog.
- `src/components/vibe/modals/SubtasksModal.vue`: Subtasks management dialog.
- `src/components/vibe/modals/TagModal.vue`: Tag management dialog.

## UI Components & Utilities
- `src/components/Toolbar.vue`: Generic toolbar component.
- `src/components/StatuBar.vue`: Status bar display.
- `src/components/EventBar.vue`: Event notification bar.
- `src/components/Splitter.vue`: Resizable splitter component.
- `src/components/Row.vue`: Row layout component.
- `src/components/Modal.vue`: Modal dialog wrapper.
- `src/components/Collapsible.vue`: Collapsible section component.
- `src/components/TreeView.vue`: Tree view component.
- `src/components/TreeItem.vue`: Individual tree item.
- `src/components/TagsComponent.vue`: Tags display and management.
- `src/components/VSwatches.vue`: Color swatches picker.
- `src/components/ConsoleViewer.vue`: Console output display.
- `src/components/NotificationControl.vue`: Notification management.
- `src/components/Iframe.vue`: Iframe wrapper component.
- `src/components/MermaidViewer.vue`: Mermaid diagram renderer.
- `src/components/YoutubeViewer.vue`: YouTube video embed.
- `src/components/NoVNC.vue`: VNC remote desktop viewer.
- `src/components/layout/VerticalSplitter.vue`: Vertical splitter layout.

## Autocomplete & Input
- `src/components/autocomplete/AutoComplete.vue`: Generic autocomplete input.
- `src/components/autocomplete/Editable.vue`: Editable autocomplete field.
- `src/components/autocomplete/ProjectResourcesAutoComplete.vue`: Project resources autocomplete.
- `src/components/tiptap/SimpleEditor.vue`: Simple rich text editor.
- `src/components/tiptap/MentionList.vue`: Mention autocomplete list.
- `src/components/tiptap/suggestion.js`: Mention suggestion utilities.
- `src/components/mentions/MentionSelector.vue`: Mention selection dialog.
- `src/components/ui/ColorPicker.vue`: Color selection picker.

## Global Settings
- `src/views/GlobalSettings.vue`: Global application settings page.
- `src/components/global_settings/GeneralSettings.vue`: General application settings.
- `src/components/global_settings/EnvVariablesEditor.vue`: Environment variables configuration.
- `src/components/global_settings/ChatGlobalPrompts.vue`: Global chat prompts.
- `src/components/global_settings/plugins/PluginsEditor.vue`: Plugin management interface.
- `src/components/global_settings/plugins/PluginsGrid.vue`: Plugins grid display.
- `src/components/global_settings/plugins/PluginCard.vue`: Individual plugin card.
- `src/components/global_settings/plugins/PluginModal.vue`: Plugin details modal.
- `src/components/global_settings/plugins/LoadPluginModal.vue`: Load plugin dialog.
- `src/components/oauth_settings/OAuthSettings.vue`: OAuth provider configuration.

## Apps & Preview
- `src/components/apps/AppBar.vue`: App toolbar.
- `src/components/apps/AppIcon.vue`: Application icon.
- `src/components/apps/Coder.vue`: Code application interface.
- `src/components/apps/Preview.vue`: Preview application interface.
- `src/components/browser/Browser.vue`: Browser component wrapper.

## Other Components
- `src/components/CodxJuniorLogo.vue`: Codx Junior branding logo.
- `src/components/CodxMenu.vue`: Codx-specific menu component.
- `src/components/EmbeddedCodxJunior.vue`: Embedded assistant mode.
- `src/components/IssuePreview.vue`: GitHub/issue preview.
- `src/components/LogAIView.vue`: AI logging view.
- `src/components/Logo.vue`: Generic logo component.
- `src/components/MetricRow.vue`: Metric row display.
- `src/components/TimeSelector.vue`: Time picker component.
- `src/components/UserInfo.vue`: User information display.
- `src/components/UserList.vue`: List of users.
- `src/components/HelloWorld.vue`: Demo component.
- `src/components/dummy.vue`: Placeholder component.
- `src/components/wall/Wall.vue`: Wall/feed interface.
- `src/components/wall/ChatPreview.vue`: Chat preview in wall.
- `src/components/wiki/WikiSections.vue`: Wiki sections display.
- `src/components/wiki/WikiSettings.vue`: Wiki configuration.
- `src/components/wiki/WikiTree.vue`: Wiki hierarchy tree.
- `src/components/mobile/MenuBar.vue`: Mobile bottom menu bar.

## Views
- `src/views/ChatView.vue`: Chat interface view.
- `src/views/HomeView.vue`: Desktop home page.
- `src/views/HomeMobile.vue`: Mobile home page.
- `src/views/AboutView.vue`: About page.
- `src/views/ProjectSettings.vue`: Project settings page.
- `src/views/ProjectProfile.vue`: Project profile page.
- `src/views/ProjectScripts.vue`: Project scripts management.
- `src/views/ProfileView.vue`: User profile page.
- `src/views/TeamView.vue`: Team page.
- `src/views/KnowledgeView.vue`: Knowledge base page.
- `src/views/KnowledgeSettings.vue`: Knowledge base configuration.
- `src/views/CodxJunior.vue`: Codx Junior main interface.
- `src/views/CodxWelcomeView.vue`: Codx Junior welcome screen.
- `src/views/DesktopView.vue`: Desktop workspace view.
- `src/views/VibeCodingView.vue`: Vibe coding mode interface.
- `src/views/WikiView.vue`: Wiki and knowledge management.
- `src/views/AgentPlanView.vue`: Agent planning interface.
- `src/views/DocsView.vue`: Documentation viewer.
- `src/views/SplitView.vue`: Split screen layout view.
- `src/views/SharedView.vue`: Shared content view.
- `src/views/StatusView.vue`: System status overview.
- `src/views/LiveEdit.vue`: Live editing interface.

## Routing
- `src/router/index.ts`: Application route definitions.
- `src/router/navigate.js`: Navigation utilities and helpers.

## Utilities & Helpers
- `src/utils/codeBlockExtractor.js`: Extract code blocks from text.
- `src/utils/markdownParser.js`: Parse and process markdown content.
- `src/wizards/gitIssue.js`: Git issue creation wizard.
- `src/config/appComponentsMap.js`: Component registration and mapping.
- `src/mixins/index.js`: Vue mixins collection.