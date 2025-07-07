import jwt, datetime, re
from pathlib import Path

SECRET = "gsdfW#@$@#sdsc34"  # use env var in prod

def create_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")

def decode_token(token):
    return jwt.decode(token, SECRET, algorithms=["HS256"])


def create_ics_file(data: dict, templates, out_path: Path) -> str:
    # Parse dates
    start = datetime.datetime.strptime(data["From_date"], "%d/%m/%Y %H:%M:%S")
    end = datetime.datetime.strptime(data["to_date"], "%d/%m/%Y %H:%M:%S")

    # Format as local time (no Z = not UTC)
    dt_format = "%Y%m%dT%H%M%S"
    dtstart = start.strftime(dt_format)
    dtend = end.strftime(dt_format)

    # Render fields
    summary = templates["summary"].format(**data)
    description = templates["description"].format(**data).replace('\n', '\\n')
    location = templates["location"].format(**data)

    uid = str(data.get("apptid", int(datetime.datetime.now().timestamp())))

    # Create ICS content
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Tor4You//EscapeRoomApp//EN
CALSCALE:GREGORIAN
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{datetime.datetime.utcnow().strftime(dt_format)}
SUMMARY:{summary}
DESCRIPTION:{description}
DTSTART:{dtstart}
DTEND:{dtend}
LOCATION:{location}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR
"""

    # Ensure CRLF line endings
    ics_content = ics_content.replace('\n', '\r\n')
    out_path.write_text(ics_content, encoding="utf-8", newline='')
    
    
def number_to_wa_chat_id(raw_number: str) -> str:
    normalized_number = normalize_whatsapp_number(raw_number)
    return f"{normalized_number}@c.us"

def normalize_whatsapp_number(raw_number):
    # Remove all non-digit characters
    number = re.sub(r'\D', '', raw_number)

    # Replace leading 00 (international call prefix) with nothing
    if number.startswith('00'):
        number = number[2:]

    # Israeli number starting with 0 (e.g., 054...) → replace 0 with 972
    elif number.startswith('0') and len(number) == 10:
        number = '972' + number[1:]

    # If number starts with country code already and has a valid length
    elif len(number) < 8:
        raise ValueError(f"Too short for a phone number: {raw_number}")

    return number