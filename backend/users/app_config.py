from pathlib import Path


class AppConfig:
    def __init__(self, user_name, service_name: str = None):
        current_dir = Path(__file__).parent
        user_dir = current_dir / user_name
        self.user_data_path: Path = user_dir / "user_data"
        if service_name:
            self.user_data_path = self.user_data_path / service_name
            
        self.products_path: Path = user_dir / "products"
        self.config_path: Path = self.user_data_path / "config.json"
        self.data_yaml_path: Path = self.user_data_path / "data.yml"