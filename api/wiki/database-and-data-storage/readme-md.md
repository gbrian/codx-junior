The `ProjectWatcher` class monitors file changes within project directories using the `watchdog` library. It executes specified callback functions when file modifications are detected.

### Project Watcher

The `ProjectWatcher` class is responsible for monitoring file changes in the project directories. It uses the `watchdog` library to observe changes and trigger callbacks when files are modified.

#### Usage

To start watching a directory:

```python
# /README.md
watcher = ProjectWatcher()
watcher.start_watching('/path/to/project', callback_function)
```

To stop watching a directory:

```python
# /README.md
watcher.stop_watching('/path/to/project')
```