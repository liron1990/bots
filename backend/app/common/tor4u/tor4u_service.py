from whatsapp_api_client_python import API

from .message_dispatcher import MessageDispatcher
from .appointment_fetcher import AppointmentFetcher
from app.common.iservice import IService
from app.common.config_yaml_manager import ConfigYamlManager
from users.app_config import AppConfig


class Tor4YouService(IService):
    def __init__(self, app_config: AppConfig):
        self.config_yaml_manager = ConfigYamlManager(app_config.config_path, app_config.data_yaml_path)
        self.dispatcher = None
        self.fetcher = None

    def start(self):
        config = self.config_yaml_manager.get_config()
        api = API.GreenAPI(config.GREEN_API_INSTANCE_ID, config.GREEN_API_TOKEN_ID)
        self.dispatcher = MessageDispatcher(api, self.config_yaml_manager)
        self.fetcher = AppointmentFetcher(on_new_appointments=self.dispatcher.handle_new_appointments, tor4u_key=config.TOR_KEY, interval=7200)

    def stop(self):
        if self.fetcher:
            self.fetcher.stop()
        
        if self.dispatcher:
            self.dispatcher.stop() 