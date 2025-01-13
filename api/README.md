CODXJuniorSettings

### Project Watcher

The `ProjectWatcher` class is responsible for monitoring file changes in the project directories. It uses the `watchdog` library to observe changes and trigger callbacks when files are modified.

#### Usage

To start watching a directory:

```python
watcher = ProjectWatcher()
watcher.start_watching('/path/to/project', callback_function)
```

To stop watching a directory:

```python
watcher.stop_watching('/path/to/project')
```