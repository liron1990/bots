import threading
import multiprocessing
import time
from app.common.iservice import IService
from users.app_config import BotConfig
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path

import importlib.util
import sys

def run_bot_py(path_to_bot_py: Path):
    module_name = "bot_dynamic"
    spec = importlib.util.spec_from_file_location(module_name, str(path_to_bot_py))
    if spec is None:
        raise ImportError(f"Could not load spec from {path_to_bot_py}")
    
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    if hasattr(module, "main"):
        module.main()
    else:
        raise AttributeError("No 'main' function in the bot module")

class PromptChangeHandler(FileSystemEventHandler):
    def __init__(self, prompt_file, restart_event):
        super().__init__()
        self.prompt_file = str(prompt_file.resolve())
        self.restart_event = restart_event

    def on_modified(self, event):
        if str(event.src_path) == self.prompt_file:
            print(f"Detected change in {self.prompt_file}. Restarting main process...")
            self.restart_event.set()

class BotService(IService):
    def __init__(self, bot_config: BotConfig):
        self.bot_config = bot_config
        self._main_proc = None
        self._watcher_thread = None
        self._stop_event = multiprocessing.Event()
        self._restart_event = multiprocessing.Event()

    def _run_main(self):
        while not self._stop_event.is_set():
            bot_path = self.bot_config.programs_dir / "bot.py"
            self._main_proc = multiprocessing.Process(
                target=run_bot_py, args=(bot_path,), name="BotMainProcess"
            )
            self._main_proc.start()
            # Wait for either stop or restart
            while not (self._stop_event.is_set() or self._restart_event.is_set()):
                time.sleep(0.5)
            # If restart requested, terminate and restart
            if self._restart_event.is_set():
                self._restart_event.clear()
                if self._main_proc.is_alive():
                    self._main_proc.terminate()
                    self._main_proc.join(timeout=10)
            else:
                # Stop requested
                if self._main_proc.is_alive():
                    self._main_proc.terminate()
                    self._main_proc.join(timeout=10)
                break

    def _prompt_watcher(self, prompt_file, main_proc_thread):
        event_handler = PromptChangeHandler(prompt_file, self._restart_event)
        observer = Observer()
        observer.schedule(event_handler, str(prompt_file.parent), recursive=False)
        observer.start()
        try:
            while not self._stop_event.is_set():
                self._stop_event.wait(1)
        finally:
            observer.stop()
            observer.join()

    def start(self) -> None:
        prompt_file = self.bot_config.prompt_path
        # Start main process in a separate thread
        main_proc_thread = threading.Thread(target=self._run_main, args=(), daemon=True, name="BotMainProcessThread")
        main_proc_thread.start()

        # Start prompt watcher in a separate thread
        self._watcher_thread = threading.Thread(target=self._prompt_watcher, args=(prompt_file, main_proc_thread), daemon=True, name="PromptWatcherThread")
        self._watcher_thread.start()

        return main_proc_thread  # Return the thread running the main process

    def stop(self) -> None:
        self._stop_event.set()
        self._restart_event.set()
        if self._main_proc and self._main_proc.is_alive():
            self._main_proc.terminate()
            self._main_proc.join(timeout=5)