# Codx Junior UI Project Summary

An AI-powered digital workspace SPA built with Vue 3, featuring code editing, chat functionality, project management, analytics, and multi-provider AI integration.

## Project Configuration
- `package.json`: Project dependencies and scripts
- `vite.config.ts`: Vite build configuration
- `tsconfig.json`: TypeScript configuration
- `env.d.ts`: TypeScript environment type definitions
- `tailwind.config.js`: Tailwind CSS configuration
- `postcss.config.js`: PostCSS configuration for Tailwind
- `/.eslintrc.cjs`: ESLint linting configuration
- `/.prettierrc.json`: Code formatting configuration
- `/.vscode/extensions.json`: Recommended VS Code extensions
- `/.repowise/mcp.json`: Repository configuration for MCP integration

## Documentation & Setup
- `index.md`: Project structure and file organization reference
- `README.md`: Project documentation and setup guide
- `api-examples.md`: API usage examples and reference
- `markdown-examples.md`: Markdown usage examples and reference
- `github_issues.html`: GitHub issues documentation
- `setup_workspace.sh`: Workspace initialization script
- `/.claude/CLAUDE.md`: Claude AI integration guidelines

## Application Entry Point
- `src/main.ts`: Application initialization
- `src/App.vue`: Root Vue component and layout structure
- `index.html`: HTML entry point

## Routing & Navigation
- `src/router/index.ts`: Route definitions and configuration
- `src/router/navigate.js`: Navigation utilities

## State Management (Vuex Store)
- `src/store/index.js`: Root state management store
- `src/store/project.js`: Project management state
- `src/store/session.js`: User session state
- `src/store/chats.js`: Chat history and state
- `src/store/ui.js`: UI state and preferences
- `src/store/teams.js`: Team and collaboration state
- `src/store/users.js`: User data state
- `src/store/profiles.js`: User profiles state
- `src/store/media.js`: Media files state
- `src/store/logs.js`: Application logs state

## API & Backend Integration
- `src/api/api.js`: Main API client and request handling
- `src/api/connection.js`: WebSocket/connection management
- `src/api/socket.js`: Socket.io integration
- `src/api/chatManager.js`: Chat-specific API operations

## Services
- `src/service/index.js`: Service layer index
- `src/service/service.js`: Core service utilities
- `src/service/project.js`: Project service operations
- `src/service/chat.js`: Chat service operations
- `src/service/wiki.js`: Wiki service operations

## Core Views
- `src/views/HomeView.vue`: Main dashboard
- `src/views/ChatView.vue`: Chat interface
- `src/views/CodxJunior.vue`: AI assistant interface
- `src/views/GlobalSettings.vue`: Global application settings
- `src/views/ProjectSettings.vue`: Project-specific settings
- `src/views/KnowledgeView.vue`: Knowledge base interface
- `src/views/DesktopView.vue`: Desktop environment
- `src/views/VibeCodingView.vue`: Vibe coding assistant
- `src/views/WikiView.vue`: Wiki documentation
- `src/views/FileBrowserView.vue`: File explorer
- `src/views/TeamView.vue`: Team collaboration
- `src/views/ProfileView.vue`: User profile

## AI Configuration
- `src/components/ai_settings/AIProviders.vue`: AI provider management
- `src/components/ai_settings/AIModels.vue`: AI model configuration
- `src/components/ai_settings/AIProviderSettings.vue`: Provider settings
- `src/components/ai_settings/AIModelSettings.vue`: Model-specific settings
- `src/components/ai_settings/AgentSettings.vue`: Agent configuration
- `src/components/ai_settings/ModelSelector.vue`: Model selection UI

## Chat Components
- `src/components/chat/Chat.vue`: Main chat interface
- `src/components/chat/ChatInputBox.vue`: Message input
- `src/components/chat/ChatMessageList.vue`: Message display
- `src/components/chat/ChatFileList.vue`: File management in chat
- `src/components/chat/ChatFilePreview.vue`: File preview in chat
- `src/components/chat/ChatImageCarousel.vue`: Image gallery in chat
- `src/components/chat/ChatIntelliSense.vue`: Auto-completion
- `src/components/chat/LLMModelSelector.vue`: Model selection
- `src/components/chat/EmojiPicker.vue`: Emoji selection
- `src/components/chat/ExportChat.vue`: Export chat history

## Code Editor & Viewer
- `src/components/CodeEditor.vue`: Vue-based code editor wrapper
- `src/components/code-editor/CodeEditor.jsx`: Monaco-based code editor
- `src/components/monaco/Editor.vue`: Monaco editor component
- `src/components/monaco/DiffViewer.vue`: Code diff viewer
- `src/components/Code.vue`: Code display component
- `src/components/CodeViewer.vue`: Code viewing interface

## Analytics & Monitoring
- `src/components/analytics/MetricsDashboard.vue`: Metrics and analytics dashboard
- `src/components/analytics/DailyChart.vue`: Daily metrics chart
- `src/components/analytics/PriceEditor.vue`: Pricing configuration
- `src/components/logs/LogsTable.vue`: Log table view
- `src/components/logs/LogsAnalyzerDashboard.vue`: Log analysis dashboard
- `src/components/logs/LogsLiveMetrics.vue`: Real-time log metrics
- `src/components/logs/LogsFilterBar.vue`: Log filtering

## Project Management
- `src/components/project/ProjectCard.vue`: Project card display
- `src/components/project/ProjectOverview.vue`: Project overview
- `src/components/project/ProjectSettings.vue`: Project settings modal
- `src/components/project/ProjectScripts.vue`: Project script management
- `src/components/project/NewProject.vue`: Create new project dialog
- `src/components/project/ProjectIconSelector.vue`: Icon selection

## Kanban & Task Management
- `src/components/kanban/Kanban.vue`: Kanban board interface
- `src/components/kanban/KanbanColumnView.vue`: Kanban column
- `src/components/kanban/TaskCard.vue`: Task card component
- `src/components/kanban/TaskSettings.vue`: Task configuration
- `src/components/kanban/KanbanSettings.vue`: Board settings

## Teams & Collaboration
- `src/components/teams/TeamSelector.vue`: Team selection
- `src/components/teams/TeamChannel.vue`: Team channel interface
- `src/components/teams/TeamChannelsSidebar.vue`: Channels list
- `src/components/teams/TeamSettings.vue`: Team settings
- `src/components/teams/AddMemberDialog.vue`: Add team members
- `src/components/teams/CreateTeamDialog.vue`: Create team

## File & Media Management
- `src/components/media/MediaManager.vue`: Media file management
- `src/components/media/MediaGallery.vue`: Media gallery view
- `src/components/media/MediaUploadDialog.vue`: File upload dialog
- `src/components/filebrowser/FileFinder.vue`: File search interface

## Layout & UI Components
- `src/components/NavigationBar.vue`: Top navigation
- `src/components/Menu.vue`: Menu component
- `src/components/TopBar.vue`: Top bar layout
- `src/components/Toolbar.vue`: Toolbar component
- `src/components/Modal.vue`: Modal dialog wrapper
- `src/components/Splitter.vue`: Resizable splitter
- `src/components/TabView.vue`: Tab layout
- `src/components/TabNavigation.vue`: Tab navigation
- `src/components/ThemeSelector.vue`: Theme selection
- `src/components/TreeView.vue`: Tree view component
- `src/components/layout/VerticalSplitter.vue`: Vertical split layout

## Documentation & Wiki
- `src/components/document/Document.vue`: Document viewer
- `src/components/document/TipTapDocument.vue`: TipTap-based editor
- `src/components/wiki/WikiTree.vue`: Wiki navigation tree
- `src/components/wiki/WikiSections.vue`: Wiki sections
- `src/components/wiki/WikiSettings.vue`: Wiki settings

## User & Authentication
- `src/components/user/Login.vue`: Login interface
- `src/components/user/UserProfile.vue`: User profile display
- `src/components/user/UserAvatar.vue`: Avatar component
- `src/components/user/UserSelector.vue`: User selection
- `src/components/security/AccountSettings.vue`: Account security settings
- `src/components/security/UserSecuritySettings.vue`: User security options

## Repository & Version Control
- `src/components/repo/BranchSelector.vue`: Git branch selection
- `src/components/repo/CommitTreeView.vue`: Commit history tree
- `src/components/repo/PRView.vue`: Pull request viewer
- `src/components/code/GitDiffViewer.vue`: Git diff visualization

## Global Settings
- `src/components/global_settings/GeneralSettings.vue`: General settings
- `src/components/global_settings/EnvVariablesEditor.vue`: Environment variables
- `src/components/global_settings/plugins/PluginsEditor.vue`: Plugin management

## Utilities
- `src/mixins/index.js`: Vue mixins
- `src/model/chat.ts`: Chat data models