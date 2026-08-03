# Codx Junior UI Project

Codx Junior UI is a Vue 3 application focused on AI-driven workspace management, team collaboration, and communication.

## Configuration & Setup
- `.eslintrc.cjs`: ESLint configuration.
- `.prettierrc.json`: Prettier settings.
- `tailwind.config.js`: Tailwind CSS configuration.
- `vite.config.ts`: Vite build configuration.
- `package.json`: Project dependencies and scripts.
- `tsconfig.json`: TypeScript project configuration.

## Documentation
- `README.md`: Project overview and setup guide.
- `api-examples.md`: API usage examples.

## Core Application Files
- `index.html`: Main web entry point.
- `src/App.vue`: Root Vue component.
- `src/main.ts`: Main project entry file.

## API and Services
- `src/api/api.js`: General API functionalities.
- `src/api/chatManager.js`: Manages chat operations.
- `src/service/chat.js`: Chat service functionalities.
- `src/service/project.js`: Project service functionalities.

## State Management
- `src/store/index.js`: Main store management.
- `src/store/chats.js`: Manages chat-related state data.

## Models
- `src/model/chat.ts`: Chat data model management.

## Components

### Navigation & UI
- `src/components/main-menu/MainMenu.vue`: Central navigation interface.
- `src/components/NavigationBar.vue`: Navigation bar component.
- `src/components/ui/ColorPicker.vue`: UI for selecting colors.

### Chat Interface
- `src/components/chat/Chat.vue`: Core chat interface.
- `src/components/chat/ChatMessageEditor.vue`: Editor for chat messages.

### Project & File Management
- `src/components/project/ProjectOverview.vue`: Overview of projects.
- `src/components/filebrowser/FileExplorerPanel.vue`: Panel for file explorer in file browser.

### Workspace Management
- `src/components/workspaces/WorkspaceManager.vue`: Manages overall workspace functionality.
- `src/components/workspaces/WorkspacesList.vue`: Displays list of workspaces.

### Profile & Media
- `src/components/profiles/ProfileViewer.vue`: Viewing user profiles.
- `src/components/media/MediaGallery.vue`: Handles media files.

### AI Settings
- `src/components/ai_settings/AIModelSettings.vue`: Configures AI models.

## Routing
- `src/router/index.ts`: Handles application routing logic.

## Views
- `src/views/AboutView.vue`: About page view component.
- `src/views/ChatView.vue`: Interface for chat functionalities.
- `src/views/HomeView.vue`: Desktop home view component.

## Utilities
- `src/utils/codeBlockExtractor.js`: Extracts code blocks from text content.

## Wizards
- `src/wizards/gitIssue.js`: Handles git issue management.

## Configuration
- `src/config/appComponentsMap.js`: Maps application components.