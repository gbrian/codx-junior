# VNC Application Deployment Tool

## Overview
This utility is designed for the deployment and operational maintenance of applications requiring a virtual display environment. It automates the initiation of VNC streaming sessions for specified applications.

## Usage
The script requires three mandatory parameters to function correctly. Execute the script using the following command structure:

`./vnc_app.sh -c|--command <command> -n|--name <name> -d|--display <display_number>`

### Parameters
*   **-c | --command**: Specifies the command to be executed for the application.
*   **-n | --name**: Defines the name of the application being deployed.
*   **-d | --display**: Sets the virtual display number (e.g., passing '1' will result in display `:1`).

## Operational Workflow
1.  **Input Parsing**: The script processes the provided arguments to identify the application name, execution command, and target display.
2.  **Validation**: It verifies that all required parameters are provided before proceeding.
3.  **Environment Setup**: It exports the `DISPLAY` variable using the provided display number.
4.  **Execution**: It initializes the `vncserver` with the following configuration:
    *   `-localhost yes`: Restricts VNC access to the local machine.
    *   `-xstartup`: Configures the server to run the specified application command upon startup.
5.  **Confirmation**: Upon successful execution, the script outputs the application name, the display utilized, and the associated window ID.

## Requirements
*   The script must be provided with a command, an application name, and a display number to prevent termination. 
*   If any required parameter is missing, the script will output the correct usage syntax and exit with a status of 1.

---

### References
*   Document Project: `codx-junior`
*   Category: `Deployment and Operations`
*   Keywords: `deployment`, `operations`, `scripts`, `maintenance`

[https://github.com/codx-junior/scripts/blob/main/tools/vnc_app.sh](https://github.com/codx-junior/scripts/blob/main/tools/vnc_app.sh)