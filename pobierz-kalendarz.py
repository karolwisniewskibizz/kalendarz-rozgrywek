import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import hashlib
import json
import math

### NEW
from geopy.distance import geodesic

URL = "https://www.pomorskifutbol.pl/mecze.php?id=4623&id_klub=7470"

### NEW – wczytanie stadionów
with open("stadiums.json", encoding="utf-8") as f:
    stadiums = json.load(f)

HOME_TEAM = "Jaguar"
HOME_COORD = (stadiums["Jaguar Gdańsk"]["lat"], stadiums["Jaguar Gdańsk"]["lon"])

html = requests.get(URL).content
soup = BeautifulSoup(html, "html.parser")

tables = soup.find_all("table")

months_list = ["stycznia","lutego","marca","kwietnia","maja","czerwca",
               "lipca","sierpnia","września","października","listopada","grudnia"]

match_table = None

for t in tables:
    if any(m in t.get_text().lower() for m in months_list):
        match_table = t
        break

if match_table is None:
    print("Nie znaleziono tabeli z meczami")
    exit()

rows = match_table.find_all("tr")

months = {
    "stycznia":1,"lutego":2,"marca":3,"kwietnia":4,"maja":5,"czerwca":6,
    "lipca":7,"sierpnia":8,"września":9,"października":10,"listopada":11,"grudnia":12
}

events = []

### NEW
def round_quarter(minutes):
    return math.ceil(minutes/15)*15

### NEW – szacowanie czasu jazdy
def travel_minutes(coord1, coord2):

    dist = geodesic(coord1, coord2).km

    avg_speed = 70  # km/h – średnia dla tras regionalnych

    minutes = dist/avg_speed*60

    return round_quarter(minutes)

for r in rows:

    cols = [c.get_text(strip=True) for c in r.find_all("td")]

    if len(cols) < 6:
        continue

    home = cols[1].strip()
    away = cols[3].strip()
    date_text = cols[5].strip()

    if not date_text:
        continue

    m = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})", date_text)

    if not m:
        continue

    day = int(m.group(1))
    month_name = m.group(2).lower()
    year = int(m.group(3))

    if month_name not in months:
        continue

    month = months[month_name]

    t = re.search(r"(\d{2}):(\d{2})", date_text)

    if t:
        time = t.group(0)
    else:
        time = "12:00"

    start = datetime.strptime(f"{year}-{month:02d}-{day:02d} {time}", "%Y-%m-%d %H:%M")

    end = start + timedelta(minutes=120)

    uid_src = f"{year}-{month}-{day}-{home}-{away}".lower()
    uid = hashlib.md5(uid_src.encode()).hexdigest()

    location = ""

    ### NEW – ustalenie stadionu
    if home in stadiums:
        st = stadiums[home]
        location = st["address"]

    events.append({
        "uid": uid,
        "title": f"{home} - {away}",
        "start": start,
        "end": end,
        "location": location
    })

    ### NEW – wyjazd jeśli Jaguar gra na wyjeździe
    if HOME_TEAM in away and home in stadiums:

        coord = (stadiums[home]["lat"], stadiums[home]["lon"])

        travel = travel_minutes(HOME_COORD, coord)

        depart = start - timedelta(minutes=travel+30)

        events.append({
            "uid": uid+"-travel",
            "title": f"Wyjazd na mecz: {home}",
            "start": depart,
            "end": depart + timedelta(minutes=travel),
            "location": stadiums[home]["address"]
        })

        print(f"Wyjazd: {home}, dystans ~{travel} min")

print(f"Znalezione wydarzenia: {len(events)}")

with open("calendar.ics","w",encoding="utf-8") as f:

    f.write("BEGIN:VCALENDAR\n")
    f.write("VERSION:2.0\n")
    f.write("PRODID:-//Jaguar Calendar//PL\n")

    for e in events:

        f.write("BEGIN:VEVENT\n")
        f.write(f"UID:{e['uid']}@jaguar\n")
        f.write(f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}\n")
        f.write(f"DTSTART:{e['start'].strftime('%Y%m%dT%H%M00')}\n")
        f.write(f"DTEND:{e['end'].strftime('%Y%m%dT%H%M00')}\n")
        f.write(f"SUMMARY:{e['title']}\n")

        if e["location"]:
            f.write(f"LOCATION:{e['location']}\n")

        f.write("END:VEVENT\n")

    f.write("END:VCALENDAR\n")

print("calendar.ics utworzony")
