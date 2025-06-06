import os
import yaml

import threading
from utils.config import Config

thread_started = False

class ConfigYamlManager:
    def __init__(self, config_path, yaml_path):
        self.config_path = config_path
        self.yaml_path = yaml_path
        self._config: Config = None
        self._yaml = None
        self._config_mtime = None
        self._yaml_mtime = None
        self._lock = threading.Lock()
        self._load_files()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._watch_files, daemon=True)
        global thread_started
        if not thread_started:
            self._thread.start()
            thread_started = True

    def _load_files(self):
        with self._lock:
            # Load config.json
            self._config = Config(self.config_path)
            self._config_mtime = os.path.getmtime(self.config_path)

            # Load data.yml
            with open(self.yaml_path, encoding="utf-8") as f:
                self._yaml = yaml.safe_load(f)
            self._yaml_mtime = os.path.getmtime(self.yaml_path)


    def _watch_files(self):
        while not self._stop_event.is_set():
            # Wait up to 60 seconds, but return early if stop event is set
            self._stop_event.wait(timeout=60)
            if self._stop_event.is_set():
                break
            reload_needed = False
            if os.path.exists(self.config_path):
                mtime = os.path.getmtime(self.config_path)
                if mtime != self._config_mtime:
                    reload_needed = True
            if os.path.exists(self.yaml_path):
                mtime = os.path.getmtime(self.yaml_path)
                if mtime != self._yaml_mtime:
                    reload_needed = True
            if reload_needed:
                self._load_files()

    def get_config(self):
        with self._lock:
            return self._config

    def get_yaml(self):
        with self._lock:
            return self._yaml.copy() if self._yaml else {}

    def stop(self):
        self._stop_event.set()
        self._thread.join()

# Example usage:
# manager = ConfigYamlManager("config.json", "data.yml")
# config = manager.get_config()
# yaml_data = manager.get_yaml()