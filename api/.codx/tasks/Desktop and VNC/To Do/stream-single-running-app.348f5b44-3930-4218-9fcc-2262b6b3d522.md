# [[{"id": "348f5b44-3930-4218-9fcc-2262b6b3d522", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": [], "check_lists": [], "profiles": [], "users": ["admin"], "name": "Stream single running app", "description": "The user requested a script to stream a single window using VNC with specific parameters for command, app name, and display number. The proposed shell script automates setting up a virtual display, launching the application, obtaining the window ID, and starting the VNC server using `x11vnc`. Key steps include running `vncserver` to create a display, exporting the display variable, and using `xwininfo` to find the window ID. The script assumes necessary tools (`vncserver`, `xwininfo`, `x11vnc`) are installed. Instructions for saving, making the script executable, and executing it with parameters were also provided.", "created_at": "2025-08-18 14:55:45.842210", "updated_at": "2025-08-19T07:04:13.554515", "mode": "task", "kanban_id": "", "column_id": "", "board": "Desktop and VNC", "column": "To Do", "chat_index": 0, "url": "", "branch": "", "file_path": "/shared/codx-junior/api/.codx/tasks/Desktop and VNC/To Do/stream-single-running-app.348f5b44-3930-4218-9fcc-2262b6b3d522.md", "llm_model": "", "visibility": "", "remote_url": "", "knowledge_topics": []}]]
## [[{"doc_id": "9e28bb72-1892-4140-9efc-d62eb2fc8c0e", "role": "user", "task_item": "", "think": "", "hide": false, "improvement": false, "created_at": "2025-08-18 14:55:45.840102", "updated_at": "2025-08-18 14:55:45.840128", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
Based on the comments below, we must create a script to call with different parameters and stream a single window.
Parameters will be:
-c --command :To run a new app
-n --name: Running app name to use their id to stream
-d --display: Display number


```references
To VNC stream a single window, use the x11vnc server with its -id option, which allows you to select a specific window by its ID to share over the network. First, you'll need to create a virtual display, run your desired application on it, export the display to your terminal, use the xwininfo -root -children command to find the specific window ID, and then start x11vnc -id {window_id} source to begin streaming that single window. 
Steps to stream a single VNC window: 
1. Create a Virtual Display:
Start by setting up a virtual display. You can do this by starting an application on a dedicated virtual display, for example, using vncserver.
2. Export the Display:
In your terminal, set the DISPLAY environment variable to the virtual display number you created, such as export DISPLAY=:33.
3. Launch Your Application:
Start the application you want to share on this virtual display.
4. Get the Window ID:
On the same terminal, run the xwininfo -root -children command to list all the windows and find the ID of your application's window.
5. Start the VNC Server with the Window ID:
Execute the following command, replacing {window_id} with the ID you found in the previous step:
x11vnc -id {window_id} source. 
This command tells x11vnc to share only the content of that specific window over the VNC protocol. You can then connect to the VNC session from your VNC client to view the single application window
```
## [[{"doc_id": "8b54e8b2-1055-4197-a8ba-9bb5183b4c5a", "role": "assistant", "task_item": "", "think": null, "hide": false, "improvement": false, "created_at": "2025-08-18 14:55:45.840102", "updated_at": "2025-08-18 14:55:45.840128", "images": [], "files": [], "meta_data": {"time_taken": 9.489594459533691, "first_chunk_time_taken": 0.00022411346435546875, "model": "gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": null, "disable_knowledge": false, "read_by": []}]]
To achieve streaming of a single window via VNC using the parameters mentioned, you can create a shell script that automates these steps. Below is the script to accomplish this:

```bash /scripts/vnc_single_window_stream.sh
#!/bin/bash

# Parse input arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -c|--command) command_to_run="$2"; shift ;;
        -n|--name) app_name="$2"; shift ;;
        -d|--display) virtual_display=":$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

# Check if required parameters are provided
if [ -z "$command_to_run" ] || [ -z "$app_name" ] || [ -z "$virtual_display" ]; then
    echo "Usage: $0 -c|--command <command> -n|--name <name> -d|--display <display_number>"
    exit 1
fi

# Step 1: Create a Virtual Display
vncserver $virtual_display

# Step 2: Export the Display Environment Variable
export DISPLAY=$virtual_display

# Step 3: Launch the Application
$command_to_run &

# Allow some time for the application to start
sleep 5

# Step 4: Get the Window ID
window_id=$(xwininfo -root -children | grep "$app_name" | awk '{print $1}')

# Check if window_id is empty
if [ -z "$window_id" ]; then
    echo "Could not find window ID for application name: $app_name"
    exit 1
fi

# Step 5: Start the VNC Server with the Window ID
x11vnc -display $virtual_display -id $window_id -loop &

echo "VNC streaming started for $app_name on display $virtual_display with window ID $window_id."
```

### Instructions to Use the Script:

1. **Save the Script**: Save this script on your system under the filename `vnc_single_window_stream.sh` in a directory of your choice, e.g., `/scripts`.

2. **Make the Script Executable**: Run `chmod +x /scripts/vnc_single_window_stream.sh` to make the script executable.

3. **Run the Script with Parameters**: 
   - `-c, --command`: The command to launch your application.
   - `-n, --name`: The name of your application to uniquely identify it.
   - `-d, --display`: The virtual display number.

   Example usage:
   ```bash
   ./vnc_single_window_stream.sh -c "your_application" -n "Application Window Name" -d 33
   ```

This script will set up a virtual display, launch the specified application on it, retrieve the window ID and start streaming that window via VNC. Adjust sleep time if your application needs more time to start. Also, ensure that tools like `vncserver`, `xwininfo`, and `x11vnc` are installed on your system.