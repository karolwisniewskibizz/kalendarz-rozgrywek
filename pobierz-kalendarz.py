import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import hashlib

URL = "https://www.pomorskifutbol.pl/mecze.php?id=4623&id_klub=7470"

html = requests.get(URL).text
soup = BeautifulSoup(html, "html.parser")

rows = soup.find_all("tr")

months = {
    "stycznia":1,"lutego":2,"marca":3,"kwietnia":4,"maja":5,"czerwca":6,
    "lipca":7,"sierpnia":8,"września":9,"października":10,"listopada":11,"grudnia":12
}

events = []

for r in rows:

    cols = [c.get_text(strip=True) for c in r.find_all("td")]

    if len(cols) != 6:
        continue

    home = cols[1]
    away = cols[3]
    date_text = cols[5]

    if "pauzuje" in home.lower():
        continue

    # szukanie daty
    m = re.search(r"(\d{1,2}) (\w+) (\d{4})", date_text)

    if not m:
        continue

    day = int(m.group(1))
    month_name = m.group(2)
    year = int(m.group(3))

    if month_name not in months:
        continue

    month = months[month_name]

    # godzina
    t = re.search(r"(\d{2}:\d{2})", date_text)

    if t:
        time = t.group(1)
    else:
        time = "12:00"

    start = datetime.strptime(f"{year}-{month}-{day} {time}", "%Y-%m-%d %H:%M")
    end = start + timedelta(minutes=120)

    uid_src = f"{year}-{month}-{day}-{home}-{away}".lower()
    uid = hashlib.md5(uid_src.encode()).hexdigest()

    events.append((home, away, start, end, uid))

with open("calendar.ics","w",encoding="utf-8") as f:

    f.write("BEGIN:VCALENDAR\n")
    f.write("VERSION:2.0\n")
    f.write("PRODID:-//Jaguar Calendar//PL\n")

    for home, away, start, end, uid in events:

        f.write("BEGIN:VEVENT\n")
        f.write(f"UID:{uid}@jaguar\n")
        f.write(f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}\n")
        f.write(f"DTSTART:{start.strftime('%Y%m%dT%H%M00')}\n")
        f.write(f"DTEND:{end.strftime('%Y%m%dT%H%M00')}\n")
        f.write(f"SUMMARY:{home} - {away}\n")
        f.write("END:VEVENT\n")

    f.write("END:VCALENDAR\n")
    home = cols[1]
    away = cols[3]
    date_text = cols[5]

    if not home or not away:
        continue

    # przykład:
    # "17 sierpnia 2025 - 11:00 (Nd)"
    # lub
    # "17 sierpnia 2025"

    date_match = re.search(r"(\d{1,2}) (\w+) (\d{4})", date_text)
    time_match = re.search(r"(\d{2}:\d{2})", date_text)

    if not date_match:
        continue

    day = date_match.group(1).zfill(2)
    month_name = date_match.group(2)
    year = date_match.group(3)

    if month_name not in months:
        continue

    month = months[month_name]

    # jeśli brak godziny ustaw 12:00
    if time_match:
        time = time_match.group(1)
    else:
        time = "12:00"

    start = datetime.strptime(f"{year}-{month}-{day} {time}", "%Y-%m-%d %H:%M")
    end = start + timedelta(minutes=120)

    # stabilne UID (bez godziny)
    uid_source = f"{year}-{month}-{day}-{home}-{away}".lower()
    uid = hashlib.md5(uid_source.encode()).hexdigest()

    events.append((home, away, start, end, uid))

with open("calendar.ics", "w", encoding="utf-8") as f:

    f.write("BEGIN:VCALENDAR\n")
    f.write("VERSION:2.0\n")
    f.write("PRODID:-//Jaguar Calendar//PL\n")

    for home, away, start, end, uid in events:

        f.write("BEGIN:VEVENT\n")
        f.write(f"UID:{uid}@jaguar\n")
        f.write(f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}\n")
        f.write(f"DTSTART:{start.strftime('%Y%m%dT%H%M00')}\n")
        f.write(f"DTEND:{end.strftime('%Y%m%dT%H%M00')}\n")
        f.write(f"SUMMARY:{home} - {away}\n")
        f.write("END:VEVENT\n")

    f.write("END:VCALENDAR\n")
