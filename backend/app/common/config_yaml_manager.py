import os
import yaml
import threading
from app.utils.config import Config
from app.utils.logger import logger  # Make sure logger is initialized before using

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
        self._thread.start()

    def _load_files(self):
        with self._lock:
            try:
                # Load config.json
                logger.info(f"Loading config from {self.config_path}")
                self._config = Config(self.config_path)
                self._config_mtime = os.path.getmtime(self.config_path)
            except Exception as e:
                logger.exception(f"Failed to load config from {self.config_path}")

            try:
                # Load data.yml
                logger.info(f"Loading YAML from {self.yaml_path}")
                with open(self.yaml_path, encoding="utf-8") as f:
                    self._yaml = yaml.safe_load(f)
                self._yaml_mtime = os.path.getmtime(self.yaml_path)
            except Exception as e:
                logger.exception(f"Failed to load YAML from {self.yaml_path}")

    def _watch_files(self):
        logger.info(f"startting ConfigYamlManager thread")
        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=60)
            if self._stop_event.is_set():
                break
            reload_needed = False
            
            if os.path.exists(self.config_path):
                mtime = os.path.getmtime(self.config_path)
                if mtime != self._config_mtime:
                    logger.info(f"Detected change in config file: {self.config_path}")
                    reload_needed = True
            
            if os.path.exists(self.yaml_path):
                mtime = os.path.getmtime(self.yaml_path)
                if mtime != self._yaml_mtime:
                    logger.info(f"Detected change in YAML file: {self.yaml_path}")
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
        logger.info(f"stopping ConfigYamlManager thread")
        self._stop_event.set()
        self._thread.join()