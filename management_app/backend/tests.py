import requests
from datetime import datetime
import json

API_URL = "https://www.tor4you.co.il/api/apptlist"
TORKEY = "4590-RmKWX2d7NCX9sPsnHJ4xTPBdkJvQdPVf2C6THr2VkmVCVnsDGCQ2QQgGldCrk91u"  
LU_FILE = "last_lu.txt"  # File to persist last LU value
DATA_DUMP_FILE = "appointments_dump.json"  # File to dump all data

def load_last_lu():
    try:
        with open(LU_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def save_lu(lu):
    with open(LU_FILE, "w") as f:
        f.write(lu)

def dump_data(data):
    with open(DATA_DUMP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"📝 Dumped all data to {DATA_DUMP_FILE}")

def fetch_appointments(from_date, to_date):
    headers = {
        "torkey": TORKEY
    }

    params = {
        "from": from_date,
        "to": to_date,
        "format": 2  # Use detailed format
    }

    # Include last LU if available
    last_lu = load_last_lu()
    last_lu = None
    if last_lu:
        params["lu"] = last_lu

    print("Fetching appointments...")
    response = requests.get(API_URL, headers=headers, params=params)

    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return

    data = response.json()

    # Dump all data to file
    dump_data(data)

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

    if new_lu:
        save_lu(new_lu)
        print(f"🔄 Saved LU: {new_lu}")

if __name__ == "__main__":
    # Example date range: today
    today = datetime.now().strftime("%Y%m%d")
    fetch_appointments(from_date=today, to_date=today)
