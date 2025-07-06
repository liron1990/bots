import json
from pathlib import Path
from app.common.config_yaml_manager import ConfigYamlManager
from .app_config import Tor4uConfig

class Users:
    def __init__(self):
        current_dir = Path(__file__).parent
        self.users_data_path: Path = current_dir / ".." / ".." / "users_data"
        self.users_list_path: Path = self.users_data_path / "users.json"
        self.users = {}
        if self.users_list_path.exists():
            with self.users_list_path.open("r", encoding="utf-8") as f:
                self.users = json.load(f)
        else:
            self.users = {}

    def get_users_list(self):
        return list(self.users.keys())

    def get_guid(self, user_name):
        user = self.users.get(user_name)
        if user:
            return user.get("guid")
        return None
    
    def get_config_yaml_manager(self, guid: str) -> ConfigYamlManager:
        user_name = self.get_user(guid)
        the_maze_app_config = Tor4uConfig(user_name)
        return ConfigYamlManager(the_maze_app_config.config_path, the_maze_app_config.data_yaml_path)
    

    def get_user(self, guid: str):
        for user_name, user_info in self.users.items():
            if user_info.get("guid") == guid:
                return user_name
        raise ValueError("User not exists")