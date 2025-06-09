import json

class Config:
    def __init__(self, config_path=None):
        with open(config_path, "r", encoding="utf-8") as f:
            self._config = json.load(f)

        # Parse all parameters from config.json
        self.GREEN_API_INSTANCE_ID = self._config.get("GREEN_API_INSTANCE_ID")
        self.GREEN_API_TOKEN_ID = self._config.get("GREEN_API_TOKEN_ID")
        self.TOR_KEY = self._config.get("TOR_KEY")
        self.IS_DEBUG = self._config.get("IS_DEBUG", False)
        self.DEVLOPERS = self._config.get("DEVLOPERS", [])
        self.FILTER_WEB_HOOKS = self._config.get("FILTER_WEB_HOOKS", {})
        self.REMINDER_MSG_TIME_BEFORE_HOURS = float(self._config.get("REMINDER_MSG_TIME_BEFORE_HOURS"))
        self.THANKS_MSG_TIME_AFTER_HOURS = float(self._config.get("THANKS_MSG_TIME_AFTER_HOURS"))
