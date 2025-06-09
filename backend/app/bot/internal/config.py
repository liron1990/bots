import json
from typing import Optional, List

class Config:
    def __init__(
        self,
        user_id: str,
        api_token_id: str,
        crm_api_token: str,
        open_ai_key: Optional[str] = None,
        answer_only: Optional[List[str]] = None,
        notify_numbers: Optional[List[str]] = None,
        ignore_numbers: Optional[List[str]] = None,
        reminder_timeout: int = 120,
        notify_on_non_kids_events: bool = False
    ):
        self.user_id = user_id
        self.api_token_id = api_token_id
        self.open_ai_key = open_ai_key
        self.answer_only = answer_only
        self.notify_numbers = notify_numbers
        self.ignore_numbers = ignore_numbers
        self.reminder_timeout = reminder_timeout
        self.crm_api_token = crm_api_token
        self.notify_on_non_kids_events = notify_on_non_kids_events

    @staticmethod
    def from_dict(data: dict) -> 'Config':
        return Config(
            user_id=data["USER_ID"],
            api_token_id=data["API_TOKEN_ID"],
            crm_api_token=data["CRM_API_TOKEN"],
            open_ai_key=data.get("OPEN_AI_KEY"),
            answer_only=data.get("ANSWER_ONLY"),
            notify_numbers=data.get("NOTIFY_NUMBERS"),
            ignore_numbers=data.get("IGNORE_NUMBERS"),
            reminder_timeout=data.get("REMINDER_TIMEOUT", 120),
            notify_on_non_kids_events=data.get("NOTIFY_ON_NON_KIDS_EVENTS", False)
        )


def load_config(path: str) -> Config:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Config.from_dict(data)
