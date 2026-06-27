# Codx Junior UI Project Summary

A comprehensive AI-powered digital workspace SPA built with Vue 3 and TypeScript, featuring code editing, desktop simulation, chat, version control, project management, and team collaboration.

## Project Configuration
- `package.json`: Project dependencies and scripts.
- `vite.config.ts`: Build configuration for Vite.
- `tsconfig.json`: TypeScript configuration.
- `tailwind.config.js`: Tailwind CSS styling configuration.
- `.eslintrc.cjs`: ESLint linting rules.
- `.prettierrc.json`: Code formatting configuration.
- `postcss.config.js`: PostCSS processing configuration.

## API & Backend Integration
- `src/api/api.js`: Main API client and request handling.
- `src/api/chatManager.js`: Chat API management.
- `src/api/socket.js`: WebSocket connection handling.
- `src/api/connection.js`: Connection utilities.

## State Management
- `src/store/index.js`: Root state management.
- `src/store/chats.js`: Chat state.
- `src/store/project.js`: Project state.
- `src/store/session.js`: User session state.
- `src/store/teams.js`: Team collaboration state.
- `src/store/ui.js`: UI state management.
- `src/store/profiles.js`: User profiles state.
- `src/store/users.js`: Users state.
- `src/store/logs.js`: Logs state.
- `src/store/media.js`: Media assets state.

## Core Services
- `src/service/service.js`: Main service layer.
- `src/service/chat.js`: Chat service.
- `src/service/project.js`: Project service.
- `src/service/wiki.js`: Wiki service.

## Main Application
- `src/main.ts`: Application entry point.
- `src/App.vue`: Root application component.
- `src/router/index.ts`: Vue Router configuration.
- `src/router/navigate.js`: Navigation utilities.

## Views & Layouts
- `src/views/HomeView.vue`: Main dashboard.
- `src/views/CodxJunior.vue`: Codx Junior assistant interface.
- `src/views/ChatView.vue`: Chat messaging interface.
- `src/views/ProjectProfile.vue`: Project details page.
- `src/views/ProjectSettings.vue`: Project configuration.
- `src/views/GlobalSettings.vue`: Global application settings.
- `src/views/AISettings.vue`: AI model and provider configuration.
- `src/views/KnowledgeView.vue`: Knowledge base browser.
- `src/views/KnowledgeSettings.vue`: Knowledge base configuration.
- `src/views/TeamView.vue`: Team collaboration interface.
- `src/views/DesktopView.vue`: Virtual desktop environment.
- `src/views/VibeCodingView.vue`: Vibe coding interface.
- `src/views/FileBrowserView.vue`: File system browser.
- `src/views/WikiView.vue`: Wiki documentation viewer.
- `src/views/ProfileView.vue`: User profile page.
- `src/views/StatusView.vue`: System status dashboard.

## Chat Components
- `src/components/chat/Chat.vue`: Main chat component.
- `src/components/chat/ChatInputBox.vue`: Message input handling.
- `src/components/chat/ChatMessageList.vue`: Message display.
- `src/components/chat/ChatFileList.vue`: File attachment management.
- `src/components/chat/ChatImageCarousel.vue`: Image preview carousel.
- `src/components/chat/LLMModelSelector.vue`: Model selection dropdown.
- `src/components/chat/EmojiPicker.vue`: Emoji insertion tool.
- `src/components/chat/ExportChat.vue`: Chat export utility.
- `src/components/chat/ChatFileSelectorModal.vue`: File selection dialog.
- `src/components/chat/ChatIntelliSense.vue`: Intelligent autocomplete.
- `src/components/chat/UserSelector.vue`: User mention selection.
- `src/components/chat/ChatMentionBar.vue`: Mention suggestions display.
- `src/components/chat/ChatInputToolbar.vue`: Input formatting toolbar.

## Code Editor & Viewing
- `src/components/code-editor/CodeEditor.jsx`: Monaco-based code editor.
- `src/components/CodeEditor.vue`: Vue wrapper for code editor.
- `src/components/Code.vue`: Code display component.
- `src/components/CodeViewer.vue`: Read-only code viewer.
- `src/components/DiffViewer.vue`: Diff visualization.
- `src/components/monaco/Editor.vue`: Monaco editor integration.
- `src/components/code/GitDiffViewer.vue`: Git diff viewer.

## Project Management
- `src/components/kanban/Kanban.vue`: Kanban board interface.
- `src/components/kanban/TaskCard.vue`: Individual task cards.
- `src/components/kanban/KanbanColumnView.vue`: Kanban column view.
- `src/components/kanban/TaskSettings.vue`: Task configuration.
- `src/components/project/ProjectCard.vue`: Project display cards.
- `src/components/project/NewProject.vue`: Project creation wizard.
- `src/components/project/ProjectSettings.vue`: Project configuration.
- `src/components/project/ProjectScripts.vue`: Project script management.

## Team & Collaboration
- `src/components/teams/TeamChannel.vue`: Team channel interface.
- `src/components/teams/TeamSelector.vue`: Team selection dropdown.
- `src/components/teams/AddMemberDialog.vue`: Member addition modal.
- `src/components/teams/TeamBar.vue`: Team navigation bar.
- `src/components/teams/MemberAvatar.vue`: Member display avatar.
- `src/components/teams/TeamSettings.vue`: Team configuration.

## Analytics & Metrics
- `src/components/analytics/MetricsDashboard.vue`: Analytics dashboard with metrics visualization.
- `src/components/analytics/DailyChart.vue`: Daily metrics chart display.
- `src/components/analytics/PriceEditor.vue`: Price configuration.
- `src/components/logs/LogsAnalyzerDashboard.vue`: Log analysis interface.

## AI & Configuration
- `src/components/ai_settings/AIModelSettings.vue`: AI model configuration.
- `src/components/ai_settings/AIProviderSettings.vue`: AI provider setup.
- `src/components/ai_settings/AgentSettings.vue`: Agent configuration.

## Version Control
- `src/components/repo/PRView.vue`: Pull request viewer.
- `src/components/git/BranchSelector.vue`: Git branch selection.
- `src/components/repo/CommitTreeView.vue`: Commit history visualization.

## Knowledge & Documentation
- `src/components/knowledge/KnowledgeSearch.vue`: Knowledge base search.
- `src/components/knowledge/settings/KnowledgeIndex.vue`: Knowledge indexing.
- `src/components/wiki/WikiSections.vue`: Wiki page sections.

## UI Components
- `src/components/Modal.vue`: Modal dialog component.
- `src/components/Toolbar.vue`: Toolbar UI element.
- `src/components/TopBar.vue`: Top navigation bar.
- `src/components/NavigationBar.vue`: Navigation component.
- `src/components/Menu.vue`: Menu system.
- `src/components/TabNavigation.vue`: Tab-based navigation.
- `src/components/Splitter.vue`: Resizable splitter.
- `src/components/TreeView.vue`: Tree view component.
- `src/components/Collapsible.vue`: Collapsible section component.

## Utilities & Helpers
- `src/mixins/index.js`: Vue mixins for shared logic.
- `src/model/chat.ts`: Chat data model types.