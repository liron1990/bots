from whatsapp_api_client_python import API


# from config_yaml_manager import ConfigYamlManager
from .message_dispatcher import MessageDispatcher
from .appointment_fetcher import AppointmentFetcher
from .webhook_handler import WebhookHandler


class Tor4YouService:
    def __init__(self, config_yaml_manager):
        config = config_yaml_manager.get_config()
        api = API.GreenAPI(config.GREEN_API_INSTANCE_ID, config.GREEN_API_TOKEN_ID)
        self.dispatcher = MessageDispatcher(api, config_yaml_manager)
        self.fetcher = AppointmentFetcher(on_new_appointments=self.dispatcher.handle_new_appointments)
        self.webhook = WebhookHandler(self.dispatcher, config_yaml_manager)

    def handle_webhook(self, data):
        return self.webhook.handle(data)

    def stop(self):
        self.fetcher.stop()