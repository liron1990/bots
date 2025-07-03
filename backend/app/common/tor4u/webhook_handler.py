from app.utils.logger import logger
from app.utils.utils import create_ics_file, normalize_whatsapp_number
from app.common.config_yaml_manager import ConfigYamlManager
from .utils import get_template_messages, enrich_appointment_data, should_filter

from whatsapp_api_client_python.API import GreenApi
from whatsapp_api_client_python import API
from app.webapp.config import Config

class WebhookHandler:
    def __init__(self, yaml_manager: ConfigYamlManager):
        config = yaml_manager.get_config()
        self.green_api: GreenApi = API.GreenAPI(config.GREEN_API_INSTANCE_ID, config.GREEN_API_TOKEN_ID)
        self.yaml_manager: ConfigYamlManager = yaml_manager

    def handle(self, data):
        if not data:
            logger.warning("No data in webhook")
            return "No JSON", 400

        try:
            logger.info(f"Received webhook data: {data}")
            config: Config = self.yaml_manager.get_config()
            templates = self.yaml_manager.get_yaml()

            if should_filter(data, config):
                logger.info(f"Webhook filtered")
                return "Filtered", 200

            data = enrich_appointment_data(data)
            logger.debug(f"Enriched data: {data}")

            action = {"1": "create", "2": "update", "3": "cancel", "5": "expire"}.get(data.get("action"))
            update_by = "client" if data.get("updateby").strip() == "99" else "staff"
            logger.info(f"Action: {action}, Update by: {update_by}")

            if not action:
                logger.warning(f"Unknown action: {data.get('action')}")
                return "Unknown action", 400

            template = get_template_messages(data, templates)
            logger.debug(f"Selected template: {template}")
            msg = template[action][update_by].format(**data)
            caption = templates["calendar_attachment"].format(**data)

            number = normalize_whatsapp_number(data["customercell"])
            dests = config.DEVLOPERS if config.IS_DEBUG else [number]

            for num in dests:
                jid = f"{num}@c.us"
                logger.info(f"Preparing to send to {jid}, message: {msg}")
                self.green_api.sending.sendMessage(jid, msg)
                if action in {"create", "update"}:
                    logger.info(f"Creating calendar file for {jid}")
                    path = create_ics_file(data, template["calander"])
                    self.green_api.sending.sendFileByUpload(jid, path, "escape_room_event.ics", caption=caption)

            logger.info("Webhook handled successfully")
            return "OK", 200

        except Exception as e:
            logger.exception("Webhook processing failed")
            for num in self.yaml_manager.get_config().DEVLOPERS:
                logger.error(f"Sending error notification to developer {num}: {e}")
                self.green_api.sending.sendMessage(f"{num}@c.us", f"❌ Error:\n{e}")
            return "Error", 500