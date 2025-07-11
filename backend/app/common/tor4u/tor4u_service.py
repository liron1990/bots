from whatsapp_api_client_python import API

from .message_dispatcher import MessageDispatcher
from .appointment_fetcher import AppointmentFetcher
from app.common.iservice import IService
from app.common.config_yaml_manager import ConfigYamlManager
from users.user_paths import Tor4Paths
from app.common.green_api import GreenApiFactory


class Tor4YouService(IService):
    def __init__(self, app_paths: Tor4Paths):
        self.app_paths: Tor4Paths = app_paths
        self.config_yaml_manager = ConfigYamlManager(app_paths.config_path, app_paths.data_yaml_path)
        self.dispatcher = None
        self.fetcher = None

    def start(self):
        config = self.config_yaml_manager.get_config()
        api: API.GreenAPI = GreenApiFactory.create(config.GREEN_API_INSTANCE_ID, config.GREEN_API_TOKEN_ID)
        self.dispatcher = MessageDispatcher(api, self.config_yaml_manager, self.app_paths)
        self.fetcher = AppointmentFetcher(on_new_appointments=self.dispatcher.handle_new_appointments, tor4u_key=config.TOR_KEY, interval=1800)

    def stop(self):
        if self.fetcher:
            self.fetcher.stop()
        
        if self.dispatcher:
            self.dispatcher.stop() 