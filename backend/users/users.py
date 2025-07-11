import json
from pathlib import Path
from filelock import FileLock
from typing import Dict
from jsonschema import validate
import uuid

from app.common.config_yaml_manager import ConfigYamlManager
from .user_paths import Tor4Paths, BotPaths
from app.bot.bot_service import BotService
from app.common.tor4u.tor4u_service import Tor4YouService


class Users:
    def __init__(self):
        current_dir = Path(__file__).parent
        self.users_data_path: Path = current_dir / ".." / ".." / "users_data"
        self.users_list_path: Path = self.users_data_path / "users.json"
        self.users_schema_path: Path = self.users_data_path / "users_schema.json"
        self.users_lock_path: Path = self.users_list_path.with_suffix(".json.lock")
        self.users = {}
        self.guid_to_user = {}

    def _read_locked(self, path: Path):
        with FileLock(self.users_lock_path):
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)

    def _write_locked(self, path: Path, data: Dict):
        with FileLock(self.users_lock_path):
            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_users(self):
        if not self.users_list_path.exists():
            self.users = {}
            self.guid_to_user = {}
            return

        data = self._read_locked(self.users_list_path)
        self.users = {}
        self.guid_to_user = {}
        for user in data.get("users", []):
            user_name = user.get("name") or user.get("guid")
            services_dict = {
                s["type"]: {"active": s.get("active", False)}
                for s in user.get("services", [])
            }
            self.users[user_name] = {
                "guid": user["guid"],
                "active": user.get("active", False),
                "admin": user.get("admin", False),
                "services": services_dict
            }
            self.guid_to_user[user["guid"]] = user_name

    def save(self):
        users_list = []
        for user_name, user_data in self.users.items():
            services = [
                {"type": name, "active": service.get("active", False)}
                for name, service in user_data.get("services", {}).items()
            ]
            users_list.append({
                "guid": user_data["guid"],
                "name": user_name,
                "active": user_data["active"],
                "admin": user_data["admin"],
                "services": services
            })

        self.users_data_path.mkdir(parents=True, exist_ok=True)
        self._write_locked(self.users_list_path, {"users": users_list})

    def get_users_list(self):
        self._load_users()
        return list(self.users.keys())

    def get_guid(self, user_name):
        self._load_users()
        return self.users.get(user_name, {}).get("guid")

    def get_user(self, guid: str):
        self._load_users()
        user_name = self.guid_to_user.get(guid)
        if not user_name:
            raise ValueError("User not exists")
        return user_name

    def get_config_yaml_manager(self, guid: str) -> ConfigYamlManager:
        self._load_users()
        user_name = self.get_user(guid)
        cfg = Tor4Paths(user_name)
        return ConfigYamlManager(cfg.config_path, cfg.data_yaml_path)

    def get_services(self, user_name: str):
        self._load_users()
        user = self.users.get(user_name)
        if not user:
            raise ValueError("User not found")
        return user.get("services", {})

    def enable_user(self, user_name: str):
        self._load_users()
        if user_name in self.users:
            self.users[user_name]["active"] = True
            self.save()
        else:
            raise ValueError("User not found")

    def disable_user(self, user_name: str):
        self._load_users()
        if user_name in self.users:
            self.users[user_name]["active"] = False
            self.save()
        else:
            raise ValueError("User not found")

    def enable_service(self, user_name: str, service_name: str):
        self._load_users()
        if user_name not in self.users:
            raise ValueError("User not found")
        self.users[user_name].setdefault("services", {})[service_name] = {"active": True}
        self.save()

    def disable_service(self, user_name: str, service_name: str):
        self._load_users()
        if user_name not in self.users:
            raise ValueError("User not found")
        services = self.users[user_name].setdefault("services", {})
        if service_name in services:
            services[service_name]["active"] = False
            self.save()
        else:
            raise ValueError("Service not found")

    def get_active_services(self):
        self._load_users()
        SERVICE_CLASS_MAP = {
            "tor4u": (Tor4YouService, Tor4Paths),
            "bot": (BotService, BotPaths),
        }
        active_services = []

        for user_name, user_data in self.users.items():
            if not user_data.get("active"):
                continue
            for service_name, service_data in user_data.get("services", {}).items():
                if not service_data.get("active"):
                    continue
                if service_name not in SERVICE_CLASS_MAP:
                    continue
                cls, cfg_cls = SERVICE_CLASS_MAP[service_name]
                active_services.append((user_name, service_name, cls, cfg_cls(user_name)))
        return active_services

    def is_admin(self, user_name: str) -> bool:
        self._load_users()
        return self.users.get(user_name, {}).get("admin", False)

    def get_users_data(self) -> Dict:
        return self._read_locked(self.users_list_path)

    def get_users_schema(self) -> Dict:
        with self.users_schema_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def update_users_data(self, data: Dict):
        schema = self.get_users_schema()
        validate(instance=data, schema=schema)
        self._write_locked(self.users_list_path, data)

    def add_user(self, user_name: str, admin: bool = False):
            self._load_users()

            if user_name in self.users:
                raise ValueError("User already exists")

            user_guid = str(uuid.uuid4())
            self.users[user_name] = {
                "guid": user_guid,
                "active": True,
                "admin": admin,
                "services": {}
            }
            self.guid_to_user[user_guid] = user_name
            self.save()
            return user_guid

    def add_service_to_user(self, user_name: str, service_name: str, active: bool = False):
        self._load_users()

        if user_name not in self.users:
            raise ValueError("User not found")

        self.users[user_name].setdefault("services", {})[service_name] = {"active": active}
        self.save()