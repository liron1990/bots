import threading
from datetime import datetime, timedelta

import requests
from .constants import API_URL, TORKEY
from app.utils.logger import logger

class AppointmentFetcher:
    def __init__(self, on_new_appointments, interval=7200):
        self.on_new_appointments = on_new_appointments  # callback function
        self.interval = interval
        self.test_mode = False
        self._stop_event = threading.Event()
        self._lu = None  # Maintain LU in memory, not file
        self._thread = threading.Thread(target=self._fetch_loop, daemon=True, name=self.__class__.__name__)
        self._thread.start()


    def _fetch_loop(self):
        last_day = None
        while not self._stop_event.is_set():
            try:
                now = datetime.now()
                today = now.strftime("%Y%m%d")
                tomorrow = (now + timedelta(days=1)).strftime("%Y%m%d")

                if last_day != today:
                    self._lu = None  # Reset LU in memory
                    last_day = today

                self.fetch(today, tomorrow)
            except Exception as e:
                logger.exception("Error during appointment fetch")
            self._stop_event.wait(self.interval)

    def fetch(self, from_date, to_date):
        headers = {"torkey": TORKEY}
        params = {"from": from_date, "to": to_date, "format": 2}

        if self._lu:
            params["lu"] = self._lu

        logger.info("Fetching appointments from Tor4You API...")
        response = requests.get(API_URL, headers=headers, params=params)
        if response.status_code != 200:
            logger.error(f"Fetch error: {response.status_code} {response.text}")
            return

        data = response.json()
        if data.get("status") != 1:
            logger.warning("Fetch failed: %s", data)
            return

        if data.get("appts") == "no new information":
            logger.info("No new appointments.")
            return

        appointments = data.get("appts", [])
        logger.info("Fetched %d appointments", len(appointments))
        self._lu = data.get("lu")  # Save LU in memory

        # Notify dispatcher with new appointments
        if appointments:
            self.on_new_appointments(appointments)

    def stop(self):
        self._stop_event.set()
        self._thread.join()
