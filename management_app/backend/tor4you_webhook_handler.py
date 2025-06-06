import threading
import traceback
from datetime import datetime, timedelta
from utils.config import Config
from utils.utils import create_ics_file, normalize_whatsapp_number
from whatsapp_api_client_python import API
from config_yaml_manager import ConfigYamlManager
import requests
import json
import os

API_URL = "https://www.tor4you.co.il/api/apptlist"
TORKEY = "4590-RmKWX2d7NCX9sPsnHJ4xTPBdkJvQdPVf2C6THr2VkmVCVnsDGCQ2QQgGldCrk91u"
LU_FILE = "last_lu.txt"
DATA_DUMP_FILE = "appointments_dump.json"
SENT_FILE = "sent_appointment_msgs.json"

threads_started = False 

class Tor4YouWebhookHandler:
    def __init__(self, config_yaml_manager: ConfigYamlManager, fetch_interval_sec=7200):
        self.test_mode = False
        self.config_yaml_manager = config_yaml_manager
        config = self.config_yaml_manager.get_config()
        self.green_api = API.GreenAPI(
            idInstance=config.GREEN_API_INSTANCE_ID,
            apiTokenInstance=config.GREEN_API_TOKEN_ID
        )
        self.fetch_interval_sec = fetch_interval_sec
        self._stop_event = threading.Event()
        self._pending_tasks = []  # Now just a list
        self._sent_msgs = self._load_sent_msgs()
        self._task_lock = threading.Lock()
        # Remove LU file at start
        if os.path.exists(LU_FILE):
            os.remove(LU_FILE)
        
        self._fetch_thread = threading.Thread(target=self._fetch_appointments_loop, daemon=True)
        self._send_thread = threading.Thread(target=self._send_task_loop, daemon=True)
        
        global threads_started
        if not threads_started:
            self._fetch_thread.start()
            self._send_thread.start()
            threads_started = True    

    def stop(self):
        self._stop_event.set()
        self._fetch_thread.join()
        self._send_thread.join()

    def _fetch_appointments_loop(self):
        last_fetch_day = None
        while not self._stop_event.is_set():
            try:
                now = datetime.now()
                today = now.strftime("%Y%m%d")
                tomorrow = (now + timedelta(days=1)).strftime("%Y%m%d")
                # Reset LU if new day
                if last_fetch_day != today:
                    if os.path.exists(LU_FILE):
                        os.remove(LU_FILE)
                    last_fetch_day = today
                self.fetch_appointments(from_date=today, to_date=tomorrow)
            except Exception as e:
                print(f"Error in fetch_appointments thread: {e}")
                traceback.print_exc()
            self._stop_event.wait(timeout=self.fetch_interval_sec)

    def _send_task_loop(self):
        while not self._stop_event.is_set():
            now = datetime.now()
            to_send = []
            with self._task_lock:
                # Remove cancelled or outdated tasks
                self._pending_tasks = [
                    task for task in self._pending_tasks
                    if not task.get("cancelled") and task["send_time"] > now - timedelta(minutes=5)
                ]
                # Sort by send_time
                self._pending_tasks.sort(key=lambda t: t["send_time"])
                # Collect all tasks that are due
                while self._pending_tasks and self._pending_tasks[0]["send_time"] <= now:
                    to_send.append(self._pending_tasks.pop(0))
            for task in to_send:
                self._send_task(task)
            self._stop_event.wait(timeout=30)

    def _load_sent_msgs(self):
        if os.path.exists(SENT_FILE):
            try:
                with open(SENT_FILE, "r", encoding="utf-8") as f:
                    # store as set of tuples
                    return set(tuple(x) for x in json.load(f))
            except Exception:
                return set()
        return set()

    def _save_sent_msgs(self):
        with open(SENT_FILE, "w", encoding="utf-8") as f:
            # convert set of tuples to list of lists for json
            json.dump([list(x) for x in self._sent_msgs], f, ensure_ascii=False, indent=2)

    def _send_task(self, task):
        key = (task["appt_id"], task["when"])
        if key in self._sent_msgs:
            print(f"✅ Message for {task['cell']} already sent: {task['message']}. key: {key}")
            return
        try:
            print(f"🔔 Sending task. key {key}")
            print(f"Sending to {task['cell']}: {task['message']}")

            try:
                custumer_number = normalize_whatsapp_number(task['cell'])
            except ValueError as e:
                print(f"❌ Invalid phone number format: {custumer_number} - {e}")
                return

            destination_numbers = [custumer_number]
            config  = self.config_yaml_manager.get_config()
            if config.IS_DEBUG:
                destination_numbers = config.DEVLOPERS

            for number in destination_numbers:
                print(f"Sending to: {number} message: {task['message']}")
                self.green_api.sending.sendMessage(f"{number}@c.us", task["message"])
            print(f"adding to sent messages: {key}")
            
            self._sent_msgs.add(key)
            print(f"sent messages now: {self._sent_msgs}")
            self._save_sent_msgs()  # Save after each send
        except Exception as e:
            print(f"Failed to send message to {task['cell']}: {e}")

    def _msg_key(self, appt_id, when):
        return (appt_id, when)

    def _schedule_appointment_notifications(self, appt):
        # Ignore cancelled appointments
        if appt.get("cancelled"):
            self._remove_tasks_for_appt(appt.get("id"))
            return

        cell = appt.get("cell")
        first = appt.get("first")
        staffname = appt.get("staffname", "").strip()
        appt_id = appt.get("id")
        from_str = appt.get("from")
        to_str = appt.get("to")

        try:
            from_dt = datetime.strptime(from_str, "%Y%m%d%H%M")
            to_dt = datetime.strptime(to_str, "%Y%m%d%H%M")
        except Exception as e:
            print(f"Invalid datetime in appointment: {e}")
            return

        before_dt = from_dt - timedelta(minutes=30)
        after_dt = to_dt + timedelta(minutes=30)

        before_key = self._msg_key(appt_id, "before")
        after_key = self._msg_key(appt_id, "after")

        before_msg = f"שלום {first}, תזכורת: יש לך תור ל{staffname} בשעה {from_dt.strftime('%H:%M')}."
        after_msg = f"שלום {first}, תודה שביקרת ב{staffname}! נשמח לראותך שוב."

        with self._task_lock:
            # Only add if not already sent or scheduled
            if before_key not in self._sent_msgs and not self._task_exists(appt_id, "before"):
                self._pending_tasks.append({
                    "send_time": before_dt,
                    "cell": cell,
                    "message": before_msg,
                    "appt_id": appt_id,
                    "when": "before",
                    "cancelled": False
                })
            if after_key not in self._sent_msgs and not self._task_exists(appt_id, "after"):
                self._pending_tasks.append({
                    "send_time": after_dt,
                    "cell": cell,
                    "message": after_msg,
                    "appt_id": appt_id,
                    "when": "after",
                    "cancelled": False
                })

    def _task_exists(self, appt_id, when):
        for task in self._pending_tasks:
            if task["appt_id"] == appt_id and task["when"] == when:
                return True
        return False

    def _remove_tasks_for_appt(self, appt_id):
        with self._task_lock:
            self._pending_tasks = [
                task for task in self._pending_tasks if task["appt_id"] != appt_id
            ]

    def handle(self, data):
        print("🔔 /webhook endpoint called")
        print(f"Received JSON data: {data}")
        if not data:
            print("❌ No JSON received in request")
            return "No JSON", 400

        try:
            config: Config = self.config_yaml_manager.get_config()
            templates_yaml = self.config_yaml_manager.get_yaml()
            if self.should_filter_webhook(data=data, config=config):
                print("🔕 Webhook filtered out based on configuration")
                return "Filtered", 200

            from_date_raw = data.get("From_date", "")
            dt = datetime.strptime(from_date_raw, "%d/%m/%Y %H:%M:%S")
            data["date_str"] = dt.strftime("%d/%m/%Y")
            data["time_str"] = dt.strftime("%H:%M")

            action = data.get("action")
            print(f"Action received: {action}")

            action_map = {
                "1": "create",
                "2": "update",
                "3": "cancel",
                "5": "expire"
            }

            if action not in action_map:
                print("❓ Unknown action received")
                return "Unknown action", 400

            action_str = action_map[action]

            room = data.get("staffname").strip()
            current_template = templates_yaml.get(room, templates_yaml.get("general"))
            message = current_template[action_str].format(**data)

            calendar_caption = templates_yaml['calendar_attachment'].format(**data)
            print(f"Message to send: {message}")

            if action_str in {"create", "update"}:
                file_path = create_ics_file(data, current_template['calander'])

            customercell = data.get('customercell', '')
            try:
                customercell = normalize_whatsapp_number(customercell)
            except ValueError as e:
                print(f"❌ Invalid phone number format: {customercell} - {e}")

            destination_numbers = [customercell]
            if config.IS_DEBUG:
                destination_numbers = config.DEVLOPERS

            for number in destination_numbers:
                print(f"Sending message to: {number}@c.us")
                self.green_api.sending.sendMessage(f"{number}@c.us", message)

                if action_str in {"create", "update"}:
                    print(f"Sending calendar file to: {number}")
                    self.green_api.sending.sendFileByUpload(
                        f'{number}@c.us', file_path, "escape_room_event.ics", caption=calendar_caption
                    )

        except Exception as e:
            try:
                print("❌ Error processing webhook:", e)
                tb_str = traceback.format_exc()
                print(tb_str)

                config = self.config_yaml_manager.get_config()
                for number in config.DEVLOPERS:
                    print(f"Sending message to: {number}@c.us")
                    self.green_api.sending.sendMessage(f"{number}@c.us", f"❌ Error:\n{tb_str}")
            finally:
                return "Error", 500

        print("✅ Webhook processed successfully")
        return "OK", 200

    def should_filter_webhook(self, data, config: Config) -> bool:
        if 'tmp_expire_date' in data and data['tmp_expire_date']:
            print(f"Filtering out webhook due to tmp_expire_date: {data['tmp_expire_date']}")
            return True
        
        for key, value in config.FILTER_WEB_HOOKS.items():
            if key in data and data[key] in value:
                print(f"Filtering out webhook due to {key}: {data[key]} is one of: {value}")
                return True
        return False

    def load_last_lu(self):
        try:
            with open(LU_FILE, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            return None

    def save_lu(self, lu):
        with open(LU_FILE, "w") as f:
            f.write(lu)

    def dump_data(self, data):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'{DATA_DUMP_FILE}_{timestamp}.json'
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"📝 Dumped all data to {filename}")

    def fetch_appointments(self, from_date, to_date):
        if self.test_mode:
            appointments = self._load_appointments_from_file()
            new_lu = None
        else:
            headers = {
                "torkey": TORKEY
            }
            params = {
                "from": from_date,
                "to": to_date,
                "format": 2
            }
            last_lu = self.load_last_lu()
            if last_lu:
                params["lu"] = last_lu

            print("Fetching appointments...")
            response = requests.get(API_URL, headers=headers, params=params)

            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                print(response.text)
                return

            data = response.json()
            self.dump_data(data)

            if data.get("status") != 1:
                print("API call failed:", data)
                return

            if data.get("appts") == "no new information":
                print("✅ No new information since last check.")
                return

            appointments = data.get("appts", [])
            new_lu = data.get("lu")
            print(f"📅 {len(appointments)} appointments retrieved.")

        for appt in appointments:
            print(f"- {appt['first']} {appt['last']}: {appt['from']} ➡ {appt['to']} ({appt['servicename']})")
            self._schedule_appointment_notifications(appt)

        if not self.test_mode and new_lu:
            self.save_lu(new_lu)
            print(f"🔄 Saved LU: {new_lu}")

    def _load_appointments_from_file(self, file_path="C:\\projects\\the_maze\\web_hooks\\appointments_dump.json_20250531_231420.json"):
        import json
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("appts", [])

