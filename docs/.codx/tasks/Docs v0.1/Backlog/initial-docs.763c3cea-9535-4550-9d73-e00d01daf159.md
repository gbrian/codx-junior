# [[{"id": "763c3cea-9535-4550-9d73-e00d01daf159", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": [], "profiles": [], "users": ["dime-sazdev", "iva"], "name": "Initial docs", "created_at": "2025-05-14 06:26:22.103693", "updated_at": "2025-05-14T08:56:58.580372", "mode": "task", "kanban_id": "", "column_id": "", "board": "Docs v0.1", "column": "Backlog", "chat_index": 0, "url": "", "branch": "", "file_path": "/home/codx-junior/codx-junior/docs/.codx/tasks/Docs v0.1/Backlog/initial-docs.763c3cea-9535-4550-9d73-e00d01daf159.md", "model": "", "visibility": ""}]]
## [[{"doc_id": "59f061a5-60a3-46c5-bf45-494761780ca4", "role": "user", "task_item": "", "hide": true, "improvement": false, "created_at": "2025-05-14 06:26:22.101535", "updated_at": "2025-05-14 06:26:22.101570", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin"}]]
First version of the docs must show to new uaers how to use cidx-junior from setup to run and make changes in a project


Chapters to cover:
 * Whats cidx-junior
 * Installation
 * Basic setup
 * Load a project
 * Knownledge settings
 * Project settings
 * Global settings 
 * Profiles
 * Tasks  / Kanban
 * Coder
 * Preview
 * Wiki
 
For all chapters we'll add basic info and extend later
 * 
## [[{"doc_id": "295d33cf-e273-4e8a-84fe-a33c743401db", "role": "assistant", "task_item": "analysis", "hide": false, "improvement": false, "created_at": "2025-05-14 06:26:22.101535", "updated_at": "2025-05-14 06:26:22.101570", "images": [], "files": ["/initial-setup.md", "/features.md"], "meta_data": {"time_taken": 7.694307327270508, "first_chunk_time_taken": 7.3390138149261475, "model": "openai/mercury-coder-small"}, "profiles": [], "user": null}]]
# What is codx-junior?

codx-junior is a powerful tool designed to assist with project management, code generation, and collaboration. It provides a comprehensive suite of features to help you manage your projects more efficiently and effectively.

# Installation

To install codx-junior, follow these steps:

1. **Clone the Repository**:
   ```sh
   git clone https://github.com/codx-junior/codx-junior.git
   cd codx-junior
   ```

2. **Install Dependencies**:
   ```sh
   npm install
   ```

3. **Start the Application**:
   ```sh
   npm start
   ```

After installing and running codx-junior, navigate to `http://localhost:19981` or any other port you set in the environment settings.

# Basic Setup

## First Login

Login with the "admin" user for the first time using your chosen password. This password will be set as the admin password. You can change it later from the "Account settings".

# Load a Project

## Adding a Project

After logging in, you'll be presented with the project's dashboard where you'll see all projects that codx-junior is managing. Click on a project to work on it or add a new project.

### Adding a New Project

You can add a new project by cloning from a Git repository or by providing a full path to its folder. Paste the URL or path into the input control and press the "+" button to start.

The new project will become the active project, and you can start working on it.

# Knowledge Settings

To help codx-junior have a better understanding and produce better results, it's important to set up the knowledge settings. Knowledge allows codx-junior and any user to have a better understanding of the project.

# Project Settings

We recommend checking the project settings and adapting them to your needs. By default, all new projects will use the models defined in the global settings.

# Global Settings

Global settings are used to configure the overall behavior of codx-junior. These settings apply to all projects managed by codx-junior.

# Profiles

Profiles are the best way to define how you like your project to be maintained. You can create as many profiles as needed to ensure that your project is maintained according to your preferences.

Profiles can be used in conversations, tasks, file changes, improve new content generation, keep code quality, and more.

# Tasks / Kanban

The Kanban board is a powerful project management section where codx-junior keeps tasks in order. You and your team can start working on tasks here.

> It's possible to create new functionalities without having to write a single line once you manage the Kanban!

For better results, we recommend stopping by the Profiles section and meeting codx-junior assistants.

# Coder

The Coder feature helps with code generation and review. You can automate code generation for repetitive tasks and review code changes efficiently.

# Preview

The Preview feature allows you to see a preview of your changes before committing them to the project.

# Wiki

The Wiki is a place where you can document your project and share knowledge with your team. It's a valuable resource for maintaining a clear and organized project structure.