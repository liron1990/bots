from pathlib import Path


class Paths:
    def __init__(self, user_name: str, service_name: str = None, make_dirs: bool = False):
        current_dir = Path(__file__).parent
        self.programs_dir: Path = current_dir / "users_programs" / user_name
        self.user_data_path: Path = current_dir/ ".." / '..' / "users_data" / user_name 
        self.products_path: Path = current_dir/ ".." / '..' / "users_products" / user_name 
        
        if service_name:
            self.user_data_path = self.user_data_path / service_name
            self.programs_dir = self.programs_dir / service_name
        
        self.logs_path: Path = self.products_path / "logs"
        self.config_dir: Path = self.user_data_path / "config"
        self.config_path: Path =  self.config_dir / "config.json"
        self.data_yaml_path: Path =  self.config_dir / "messages.yaml"
        if make_dirs:
            self.__make_dirs()  

    def __make_dirs(self):
        """Ensure all necessary directories exist."""
        self.user_data_path.mkdir(parents=True, exist_ok=True)
        self.programs_dir.mkdir(parents=True, exist_ok=True)
        self.products_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        

class BotPaths(Paths):
    def __init__(self, user_name: str, make_dirs: bool = False):
        super().__init__(user_name, service_name="bot", make_dirs=make_dirs)
        self.prompt_path: Path =  self.config_dir / "prompt.txt"


class Tor4Paths(Paths):
    def __init__(self, user_name: str, make_dirs: bool = False):
        super().__init__(user_name, service_name="tor4u", make_dirs=make_dirs)
        self.appointemets_db: Path =  self.products_path / "appointments.db"
