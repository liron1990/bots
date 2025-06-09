from whatsapp_api_client_python import API

from .message_dispatcher import MessageDispatcher
from .appointment_fetcher import AppointmentFetcher
from app.common.iservice import IService
from app.common.config_yaml_manager import ConfigYamlManager


class Tor4YouService(IService):
    def __init__(self, config_yaml_manager: ConfigYamlManager):
        self.config_yaml_manager = config_yaml_manager
        self.dispatcher = None
        self.fetcher = None

    def start(self):
        config = self.config_yaml_manager.get_config()
        api = API.GreenAPI(config.GREEN_API_INSTANCE_ID, config.GREEN_API_TOKEN_ID)
        self.dispatcher = MessageDispatcher(api, self.config_yaml_manager)
        self.fetcher = AppointmentFetcher(on_new_appointments=self.dispatcher.handle_new_appointments)

    def stop(self):
        if self.fetcher:
            self.fetcher.stop()
        
        if self.dispatcher:
            self.dispatcher.stop() 