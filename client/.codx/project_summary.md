# Codx Junior UI Project

Codx Junior UI is a Vue 3 application designed for AI-driven workspace management, team collaboration, and communication.

## Configuration & Setup
- `.eslintrc.cjs`: ESLint configuration.
- `.prettierrc.json`: Prettier settings.
- `postcss.config.js`: PostCSS configuration.
- `tailwind.config.js`: Tailwind CSS configuration.
- `vite.config.ts`: Vite build configuration.
- `package.json`: Project dependencies and scripts.
- `tsconfig.json`: TypeScript project configuration.
- `tsconfig.app.json`: TypeScript app-specific configuration.
- `tsconfig.node.json`: TypeScript Node.js-specific configuration.

## Documentation
- `README.md`: Project overview and setup guide.
- `api-examples.md`: Examples for API usage.
- `markdown-examples.md`: Markdown usage examples.

## Core Application Files
- `index.html`: Main web entry point.
- `src/App.vue`: Root Vue component.
- `src/main.ts`: Main project entry file.

## API Management
- `src/api/api.js`: General API functionalities.
- `src/api/chatManager.js`: Manages chat operations.
- `src/api/connection.js`: Manages connections.

## Services
- `src/service/chat.js`: Chat service functionalities.
- `src/service/project.js`: Project service functionalities.

## State Management
- `src/store/index.js`: Main store management.
- `src/store/chats.js`: Manages chat-related state data.
- `src/store/logs.js`: Manages log-related state data.

## Models
- `src/model/chat.ts`: Chat data model management.

## Components

### Main Menu & Navigation
- `src/components/main-menu/MainMenu.vue`: Central navigation interface.
- `src/components/NavigationBar.vue`: Navigation bar component.

### Chat Interface
- `src/components/chat/Chat.vue`: Core chat interface.

### Project Management
- `src/components/project/ProjectOverview.vue`: Overview of projects.

### Profile Management
- `src/components/profiles/ProfileViewer.vue`: Viewing user profiles.

### Media Management
- `src/components/media/MediaGallery.vue`: Handles media files.

### AI Settings
- `src/components/ai_settings/AIModelSettings.vue`: Configures AI models.

### Security & OAuth
- `src/components/oauth_settings/OAuthSettings.vue`: OAuth configuration.

### UI Components
- `src/components/ui/ColorPicker.vue`: UI for selecting colors.

## Routing
- `src/router/index.ts`: Handles application routing logic.

## Views
- `src/views/AboutView.vue`: About page view component.
- `src/views/ChatView.vue`: Interface for chat functionalities.
- `src/views/HomeView.vue`: Desktop home view component.

## Wizards
- `src/wizards/gitIssue.js`: Handles git issue management.