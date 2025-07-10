import os
import yaml
import threading
from app.common.tor4u.config import Config
from app.utils.logger import logger  # Make sure logger is initialized before using
from app.common.messages import TemplateMerger


class ConfigYamlManager:
    def __init__(self, config_path, yaml_path):
        self.config_path = config_path
        self.yaml_path = yaml_path
        self._config: Config = None
        self._yaml: TemplateMerger = None
        self._config_mtime = None
        self._yaml_mtime = None
        self._lock = threading.Lock()
        self._load_files()

    def _load_files(self):
        """Load both config and YAML files, updating modification times"""
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
                    self._yaml = TemplateMerger(yaml.safe_load(f))
                self._yaml_mtime = os.path.getmtime(self.yaml_path)
            except Exception as e:
                logger.exception(f"Failed to load YAML from {self.yaml_path}")

    def _check_and_reload_config(self):
        """Check if config file has changed and reload if necessary"""
        if not os.path.exists(self.config_path):
            return
            
        try:
            current_mtime = os.path.getmtime(self.config_path)
            if current_mtime != self._config_mtime:
                logger.info(f"Detected change in config file: {self.config_path}")
                self._config = Config(self.config_path)
                self._config_mtime = current_mtime
        except Exception as e:
            logger.exception(f"Failed to reload config from {self.config_path}")

    def _check_and_reload_yaml(self):
        """Check if YAML file has changed and reload if necessary"""
        if not os.path.exists(self.yaml_path):
            return
            
        try:
            current_mtime = os.path.getmtime(self.yaml_path)
            if current_mtime != self._yaml_mtime:
                logger.info(f"Detected change in YAML file: {self.yaml_path}")
                with open(self.yaml_path, encoding="utf-8") as f:
                    self._yaml = TemplateMerger(yaml.safe_load(f))
                self._yaml_mtime = current_mtime
        except Exception as e:
            logger.exception(f"Failed to reload YAML from {self.yaml_path}")

    def get_config(self):
        """Get config, checking for changes first"""
        with self._lock:
            self._check_and_reload_config()
            return self._config

    def get_yaml(self) -> TemplateMerger:
        with self._lock:
            self._check_and_reload_yaml()
            return self._yaml