# Developer Settings Configuration

This documentation outlines specific configurations applied to the coding environment settings.

## General Editor Behavior

*   **Auto-Save Delay:** The automatic delay before files are saved is set to 60000 milliseconds (Referenced by `files.autoSaveDelay`).
*   **Color Theme:** The primary workspace color theme is configured to "Default Dark+" (Referenced by `workbench.colorTheme`).

## AI and Chat Functionality

*   **Disable AI Features:** AI features within the chat functionality are disabled, ensuring that these advanced features are not active upon startup (Referenced by `chat.disableAIFeatures`).

## Language-Specific Settings

Settings for Vue files (`[vue]`) dictate specialized formatting rules:

*   **Default Formatter:** For any file identified as Vue, the specified default formatter is "Vue.volar" (Referenced by `editor.defaultFormatter` within the `[vue]` block).