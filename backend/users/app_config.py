from pathlib import Path


class AppConfig:
    def __init__(self, user_name, service_name: str = None):
        current_dir = Path(__file__).parent
        user_dir = current_dir / "users_data" / user_name
        self.user_data_path: Path = user_dir 
        if service_name:
            self.user_data_path = self.user_data_path / service_name

        self.user_data_path.mkdir(parents=True, exist_ok=True)    
        
        self.products_path: Path = user_dir / "products"
        self.products_path.mkdir(parents=True, exist_ok=True)
        
        self.logs_path: Path = self.products_path / "logs"
        self.logs_path.mkdir(parents=True, exist_ok=True)

        self.config_dir: Path = self.user_data_path / "config"

        self.config_path: Path =  self.config_dir / "config.json"
        self.data_yaml_path: Path =  self.config_dir / "data.yml"