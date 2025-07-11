import os
import json
import threading
from datetime import datetime, timedelta
import glob
import pytz

from whatsapp_api_client_python import API
from app.common.tor4u.config import Config
from app.utils.utils import normalize_whatsapp_number
from app.utils.logger import logger
from .utils import should_filter, enrich_appointment_data, get_template_messages
from app.common.config_yaml_manager import ConfigYamlManager
from users.user_paths import Tor4Paths

class MessageDispatcher:
    def __init__(self, api: API.GreenAPI, yaml_manager: ConfigYamlManager, paths: Tor4Paths):
        self._sent_file_prefix = paths.products_path / "sent_tasks" 
        self.api = api
        self.config_manager = yaml_manager
        self._tasks = {}  # key: "{id}_before"/"{id}_after", value: dict with message, number, send_time, etc.
        self._sent_tasks = self._load_sent_tasks()  # Now a set of sent keys
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._task_loop, daemon=True, name=self.__class__.__name__)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join()

    def _task_loop(self):
        israel_tz = pytz.timezone("Asia/Jerusalem")
        while not self._stop_event.is_set():
            now = datetime.now(israel_tz)
            to_send = []
            with self._lock:
                # Find due tasks, but ignore if more than 10 minutes late
                for key, task in list(self._tasks.items()):
                    if task["send_time"] <= now:
                        # Ignore if more than 10 minutes late
                        if (now - task["send_time"]).total_seconds() > 600:  # 10 minutes
                            logger.info(f"Ignoring overdue task: {key} (was due at {task['send_time']})")
                            self._tasks.pop(key, None)
                            continue
                        to_send.append((key, task))
                # Remove due tasks from _tasks
                for key, _ in to_send:
                    self._tasks.pop(key, None)
            # Send messages outside the lock
            for key, task in to_send:
                self._send_task(key, task)
            self._stop_event.wait(30)

    def _sent_file_for_today(self):
        today = datetime.now().strftime("%Y%m%d")
        return f"{self._sent_file_prefix}_{today}.json"

    def _load_sent_tasks(self):
        # Load all sent_task files and combine keys into a set
        sent_keys = set()
        files = sorted(glob.glob(f"{self._sent_file_prefix}_*.json"))
        for sent_file in files:
            if os.path.exists(sent_file):
                try:
                    with open(sent_file, "r", encoding="utf-8") as f:
                        sent_keys.update(json.load(f))
                except Exception:
                    continue
        return sent_keys

    def _save_sent_tasks(self):
        sent_file = self._sent_file_for_today()
        with open(sent_file, "w", encoding="utf-8") as f:
            json.dump(list(self._sent_tasks), f, ensure_ascii=False, indent=2)
        self._cleanup_old_sent_files()

    def _cleanup_old_sent_files(self):
        # Keep only the 3 most recent sent files
        files = sorted(glob.glob(f"{self._sent_file_prefix}_*.json"))
        if len(files) > 3:
            for old_file in files[:-3]:
                try:
                    os.remove(old_file)
                except Exception as e:
                    logger.warning(f"Failed to remove old sent file {old_file}: {e}")

    def _send_task(self, key, task):
        if key in self._sent_tasks:
            return  # Already sent
        self.send(task["number"], task["message"])
        with self._lock:
            self._sent_tasks.add(key)
            self._save_sent_tasks()

    def send(self, number: str, message: str):
        try:
            number = normalize_whatsapp_number(number)
        except ValueError as e:
            logger.warning(f"Invalid number format: {number} - {e}")
            return

        config = self.config_manager.get_config()
        numbers = config.DEVLOPERS if config.IS_DEBUG else [number]
        for num in numbers:
            jid = f"{num}@c.us"
            logger.info(f"Sending to {jid}, message: {message}")
            self.api.sending.sendMessage(jid, message)


    def handle_new_appointments(self, appointments):
        config = self.config_manager.get_config() 
        logger.info(f"Received new appointments")
        for appt in appointments:
            if appt.get("status", "") == "5":
                logger.info(f"Skipping appointment {appt['id']} due to status 5 (temporary)")
                continue
            
            if should_filter(appt, config):
                continue
            self._schedule(appt, config)
        for key, task in self._tasks.items():
            logger.info(f"Scheduled task: {key} -> {task}")
            

    def _schedule(self, appt, config: Config):
        if appt.get("cancelled"):
            self._remove_tasks(appt["id"])
            return

        appt = enrich_appointment_data(appt)
        try:
            israel_tz = pytz.timezone("Asia/Jerusalem")
            from_dt = israel_tz.localize(datetime.strptime(appt["from"], "%Y%m%d%H%M"))
            to_dt = israel_tz.localize(datetime.strptime(appt["to"], "%Y%m%d%H%M"))
        except Exception as e:
            logger.warning("Invalid datetime in appt: %s", e)
            return

        cell = appt["cell"]
        appt_id = appt["id"]

        before_key = f"{appt_id}_before"
        after_key = f"{appt_id}_after"
        before_time = from_dt - timedelta(hours=config.REMINDER_MSG_TIME_BEFORE_HOURS)
        after_time = to_dt + timedelta(hours=config.THANKS_MSG_TIME_AFTER_HOURS)

        templates = self.config_manager.get_yaml()
        template = get_template_messages(appt, templates)
        before_msg = template['before_msg'].format(**appt)
        after_msg = template['after_msg'].format(**appt)

        with self._lock:
            if before_key not in self._sent_tasks and before_key not in self._tasks:
                self._tasks[before_key] = {
                    "message": before_msg,
                    "number": cell,
                    "send_time": before_time
                }
            if after_key not in self._sent_tasks and after_key not in self._tasks:
                self._tasks[after_key] = {
                    "message": after_msg,
                    "number": cell,
                    "send_time": after_time
                }

    def _remove_tasks(self, appt_id):
        with self._lock:
            self._tasks.pop(f"{appt_id}_before", None)
            self._tasks.pop(f"{appt_id}_after", None)