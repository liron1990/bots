from datetime import datetime
from app.common.tor4u.config import Config
from typing import Dict, Any
from app.utils.logger import logger
from app.common.messages import TemplateMerger

def enrich_appointment_data(data):
    """Returns a new dict with date_str, time_str, and stripped staffname."""
    new_data = dict(data)
    # Parse date/time
    from_dt = None
    if "From_date" in data:
        from_dt = __try_parse_date(data["From_date"])
    elif "from" in data:
        from_dt = datetime.strptime(data["from"], "%Y%m%d%H%M")


    if from_dt:
        new_data["date_str"] = from_dt.strftime("%d/%m/%Y")
        new_data["time_str"] = from_dt.strftime("%H:%M")

    # Strip staffname
    if "staffname" in new_data:
        new_data["staffname"] = new_data["staffname"].strip()
    if "first" in data:
        new_data["customerfirst"] = data["first"].strip()
        new_data["customerlast"] = data["last"].strip()

    if "customerfirst" in data:
        new_data["first"] = data["customerfirst"].strip()
        new_data["last"] = data["customerlast"].strip()

    return new_data

def get_template_messages(data, templates: TemplateMerger):
    room = data.get("staffname", "")
    return templates[room]

def should_filter(data: Dict[str, Any], config: Config) -> bool:
    update = '2'
    if data.get("action") == update and 'tmp_expire_date' in data and data['tmp_expire_date']:
        logger.info("Filtered out appointments based on config")
        return True

    for k, v in config.FILTER_WEB_HOOKS.items():
        if k in data and data[k] in v:
            logger.info(f"Filtered out appointment by key {k} with value {data[k]}")
            return True
    return False


def __try_parse_date(dt_str):
    dt_str = dt_str.replace("\\/", "/").replace("\\", "/")
    for fmt in ["%d/%m/%Y %H:%M:%S"]:
        try:
            return datetime.strptime(dt_str, fmt)
        except Exception:
            continue
    raise ValueError(f"Could not parse date string: {dt_str}")
