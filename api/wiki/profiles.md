# Profiles

This section provides details and structured guidance on profiles and functionalities within the Codx-Jr project, assisting in efficient automation and task management.

## Updated Profiles

New updates include the addition of the **Browser** profile to enhance the project's capabilities in web automation. Furthermore, we have added a new profile related to handling Vue components, expanding the automation and task management features of the Codx-Jr project.

### Profile: Browser

The **Browser** profile serves as the browser assistant within the Codx-Jr project. It instructs on using browser automation to aid users in navigating the internet effectively. This profile is particularly focused on extracting pertinent information directly from current web pages.

#### Key Functions:

- **Navigation**: The primary goal is to assist users in navigating web pages and finding the best answers to their requests. This must be done using information available from the "Current Page HTML" section of the user's query. 
- **Response Script**: If relevant information is not found in the "Current Page HTML," a navigation script should be returned for the user.

#### Usage Example:

To illustrate practical usage, consider the script below for navigating GitHub to find repositories:

```python
# Navigate to find the best repositories for the gbrian profile
navigate("https://github.com/gbrian?tab=repositories")
# Optionally, execute a script to retrieve needed information from the webpage
execute_script("return document.querySelector('.stars').innerText")
```

This script uses Python commands to navigate web pages and extract necessary data when the automatic retrieval from the current page is insufficient.

### Profile: Vue

The new **Vue** profile is designed to support tasks and functions specifically related to Vue.js components—one of the modern web frameworks. 

#### Key Functions:

- **File Recognition**: This profile identifies files with a `.vue` extension, ensuring they are recognized and can be handled appropriately within the project setup.

#### Usage Hints:

Developers can rely on this profile to automate tasks and scripts that involve Vue.js components, ensuring seamless integration and execution within the Codx-Jr environment. Automating processes such as build tasks, testing, and component exploration can significantly help streamlining development.

```json
{
    "vue": {
        "expression": "\\.vue$",
        "profile": ""
    }
}
```

This JSON snippet illustrates the setup for recognizing Vue files based on their `.vue` extension, which is crucial for accurate file management and task execution.

### Profiles Overview:

The assortment of profiles within the Codx-Jr project facilitates various roles and tasks, ensuring comprehensive and efficient handling of project task management and definition. Profiles include definitions for Project, Software Developer, Analyst, and Agent Coding Task roles, each contributing uniquely to the project's lifecycle.

## Repository

For full access to the project's files, scripts, and further insight into the profiles and their functions, visit the [codx-junior repository](https://github.com/gbrian/codx-junior.git).

This update ensures the Codx-Jr wiki reflects the latest developments, enhancing the utility and implementation of its automation and task management strategies.