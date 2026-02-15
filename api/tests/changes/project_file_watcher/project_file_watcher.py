import asyncio
from watchfiles import awatch
from concurrent.futures import ThreadPoolExecutor
from codx.junior.knowledge.knowledge_milvus import Knowledge

class ProjectFileWatcher:
    def __init__(self, project_settings, stop_event, call_back):
        self.project_settings = project_settings
        self.stop_event = stop_event
        self.call_back = call_back
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.knowledge = Knowledge(settings=self.project_settings)
        self._start_watching()

    async def _watch_files(self):
        async for changes in awatch(self.project_settings['project_path'], stop_event=self.stop_event):
            valid_changes = [change for change in changes if self.knowledge.is_valid_file(change[1])]
            if valid_changes:
                self.executor.submit(self.call_back, valid_changes)

    def _start_watching(self):
        asyncio.run(self._watch_files())