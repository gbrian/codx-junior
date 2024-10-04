# Detailed Configuration

## package.json Breakdown

### Scripts
- **dev**: `API_URL=${API_URL:-http://localhost:8000} vite --host 0.0.0.0 --port ${WEB_PORT:-8001}`
  - Starts the development server with a specified API URL and port.
- **build**: `run-p type-check "build-only {@}" --`
  - Performs type checking and builds the project.
- **lint**: `eslint . --ext .vue,.js,.jsx,.cjs,.mjs,.ts,.tsx,.cts,.mts --fix --ignore-path .gitignore`
  - Lints all relevant files and fixes issues automatically.

### Dependencies
- **Vue**: The main framework for building UI components.
- **Pinia**: For state management across the application.
- **Axios** & **Socket.io**: For making HTTP requests and managing real-time communication.

### DevDependencies
- **Vite**: Utilized for fast development and build processes.
- **TypeScript**: Ensures type safety throughout the codebase.
- **ESLint & Prettier**: Maintain code quality and consistency.

## Additional Information
For further details on each dependency and script, consult the respective documentation or the `package.json` file directly.