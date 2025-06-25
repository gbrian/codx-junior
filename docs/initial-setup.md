After installing and running **codx-junior**, navigate to `http://localhost:19981` or any other port defined in your environment settings.

## First Login

Log in using the `admin` user and your chosen password. This password will be set as the admin password and can later be changed in **Account Settings**.

## Projects

Once logged in, the dashboard will display all projects managed by codx-junior. You can select an existing project or add a new one.

### Adding a New Project

New projects can be added in one of two ways:

- Clone a project from a Git repository
- Provide a full path to an existing folder

Paste the URL or local path into the input field and click the `+` button. The added project becomes the active project.

### Project Settings

Review the **Project Settings** to configure options specific to the project.  
By default, all new projects inherit the settings from the **Global Settings**.

## Global Settings

Global settings define the behavior of codx-junior across all projects. These include model configurations, access rules, and environment preferences.

## Knowledge Setup

To improve codx-junior’s understanding of your codebase, configure the **Knowledge Settings**.

### Profiles

Profiles define how codx-junior should interact with your project. You can create multiple profiles to:

- Enforce coding standards
- Control code generation
- Guide change suggestions

Profiles are used across tasks, file updates, content generation, and code review.

## Quick Tour

### Tasks

The **Kanban board** organizes project tasks. Use it to:

- Manage backlog and priorities
- Create and track new features
- Collaborate with the team

Tasks can drive code generation and content creation without writing manual code.

### Changes Review

The **Changes** view displays all tracked file modifications.

- View diffs for committed and uncommitted changes
- Ask codx-junior for explanations or improvement suggestions

### Coder

The **Coder** tool is a web-based IDE based on Visual Studio Code, integrated into the codx-junior environment.

#### Features

- Full-featured VS Code interface
- Support for all standard VS Code extensions
- Container support via Docker (if configured)

#### Requirements

Docker must be installed and set up during installation to support containerized environments.

### Mentions

You can mention `@codx` in any project file. This triggers codx-junior to:

- Modify the file
- Explain specific parts of the code
- Suggest improvements

### Preview

The **Preview** feature opens a desktop-like environment that allows you to inspect changes before committing them.

### Wiki (Optional)

The **Wiki** lets you document the project and share technical details with the team.

> The Wiki must be enabled in the Project Settings to be available.

### User and Global Settings

Configure user-specific or global options to personalize the codx-junior environment.