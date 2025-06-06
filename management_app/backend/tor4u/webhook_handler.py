from utils.config import Config
from utils.logger import logger
from .message_dispatcher import MessageDispatcher
from datetime import datetime
from utils.utils import create_ics_file, normalize_whatsapp_number
from config_yaml_manager import ConfigYamlManager
from .utils import get_template_messages, enrich_appointment_data, should_filter

class WebhookHandler:
    def __init__(self, dispatcher: MessageDispatcher, yaml_manager: ConfigYamlManager):
        self.dispatcher = dispatcher
        self.yaml_manager = yaml_manager

    def handle(self, data):
        if not data:
            logger.warning("No data in webhook")
            return "No JSON", 400

        try:
            config = self.yaml_manager.get_config()
            templates = self.yaml_manager.get_yaml()

            if should_filter(data, config):
                logger.info("Webhook filtered")
                return "Filtered", 200

            data = enrich_appointment_data(data)

            action = {"1": "create", "2": "update", "3": "cancel", "5": "expire"}.get(data.get("action"))
            if not action:
                return "Unknown action", 400

            template = get_template_messages(data, template)
            msg = template[action].format(**data)
            caption = templates["calendar_attachment"].format(**data)

            number = normalize_whatsapp_number(data["customercell"])
            dests = config.DEVLOPERS if config.IS_DEBUG else [number]

            for num in dests:
                jid = f"{num}@c.us"
                self.dispatcher.api.sending.sendMessage(jid, msg)
                if action in {"create", "update"}:
                    path = create_ics_file(data, template["calander"])
                    self.dispatcher.api.sending.sendFileByUpload(jid, path, "escape_room_event.ics", caption=caption)

            return "OK", 200

        except Exception as e:
            logger.exception("Webhook processing failed")
            for num in self.yaml_manager.get_config().DEVLOPERS:
                self.dispatcher.api.sending.sendMessage(f"{num}@c.us", f"❌ Error:\n{e}")
            return "Error", 500
