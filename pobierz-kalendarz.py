import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import hashlib
import json
import math
import pytz
from urllib.parse import urlencode
from geopy.distance import geodesic

URL = "https://www.pomorskifutbol.pl/mecze.php?id=4623&id_klub=7470"

HOME_TEAM = "Jaguar"
HOME_KEY = "Jaguar Gdańsk"

with open("stadiums.json", encoding="utf-8") as f:
    stadiums = json.load(f)

HOME_COORD = (
    stadiums[HOME_KEY]["lat"],
    stadiums[HOME_KEY]["lon"]
)
HOME_ADDRESS = stadiums[HOME_KEY]["address"]

POLAND = pytz.timezone("Europe/Warsaw")

html = requests.get(URL).content
soup = BeautifulSoup(html, "html.parser")

tables = soup.find_all("table")
if not tables:
    print("Brak tabel na stronie")
    exit()

match_table = tables[0]
print(f"Znaleziono {len(tables)} tabel, używam tabeli 0")

rows = match_table.find_all("tr")
print(f"Liczba wierszy w tabeli: {len(rows)}")

months = {
    "stycznia":1,"lutego":2,"marca":3,"kwietnia":4,"maja":5,"czerwca":6,
    "lipca":7,"sierpnia":8,"września":9,"października":10,"listopada":11,"grudnia":12
}

events = []

def travel_minutes(coord1, coord2):
    dist_km = geodesic(coord1, coord2).km
    avg_speed = 70
    minutes = dist_km / avg_speed * 60
    return int(math.ceil(minutes / 15.0) * 15)

def directions_url(origin, destination):
    params = urlencode({
        "api": 1,
        "origin": origin,
        "destination": destination,
        "travelmode": "driving"
    })
    return f"https://www.google.com/maps/dir/?{params}"

for r in rows:
    cols = [c.get_text(strip=True) for c in r.find_all("td")]
    if len(cols) < 6:
        continue

    home = cols[1].strip()
    away = cols[3].strip()
    date_text = cols[5].strip()

    if not date_text:
        continue

    m = re.search(r"(\d{1,2})(?:/\d{1,2})?\.?\s+(\w+)\s+(\d{4})", date_text)
    if not m:
        print(f"Nie znaleziono daty w: {date_text}")
        continue

    day = int(m.group(1))
    month_name = m.group(2).lower()
    year = int(m.group(3))

    if month_name not in months:
        continue

    month = months[month_name]

    t = re.search(r"(\d{2}):(\d{2})", date_text)
    time = t.group(0) if t else "12:00"

    naive_start = datetime.strptime(f"{year}-{month:02d}-{day:02d} {time}", "%Y-%m-%d %H:%M")
    match_start = POLAND.localize(naive_start)

    match_end = match_start + timedelta(minutes=120)

    # ✅ wydarzenie zaczyna się 45 min wcześniej
    event_start = match_start - timedelta(minutes=45)
    event_end = match_end

    uid_src = f"{year}-{month}-{day}-{home}-{away}".lower()
    uid = hashlib.md5(uid_src.encode()).hexdigest()

    location = stadiums[home]["address"] if home in stadiums else home

    # ✅ opis z godziną meczu
    desc = (
        f"Mecz: {home} - {away}\\n"
        f"Rozgrzewka: {event_start.strftime('%H:%M')}\\n"
        f"Start: {match_start.strftime('%H:%M')}\\n"
        f"Koniec: {match_end.strftime('%H:%M')}\\n"
        f"Link: {URL}"
    )

    events.append({
        "uid": uid,
        "title": f"{home} - {away}",
        "start": event_start,
        "end": event_end,
        "location": location,
        "url": URL,
        "description": desc
    })

    print(f"Dodano mecz: {home} - {away}")

    is_away = HOME_TEAM.lower() in cols[3].lower()

    if is_away:
        if home in stadiums and stadiums[home]["address"] == HOME_ADDRESS:
            continue

        if home in stadiums:
            coord = (stadiums[home]["lat"], stadiums[home]["lon"])
            travel = travel_minutes(HOME_COORD, coord)
        else:
            travel = 60

        # ✅ przyjazd 45 min przed meczem
        depart = match_start - timedelta(minutes=(travel + 45))

        events.append({
            "uid": uid + "-travel",
            "title": f"Wyjazd na mecz: {home}",
            "start": depart,
            "end": depart + timedelta(minutes=travel),
            "location": f"{HOME_TEAM} - {stadiums[home]['address'] if home in stadiums else home}",
            "url": directions_url(HOME_ADDRESS, stadiums[home]["address"] if home in stadiums else home),
            "description": (
                f"Trasa: {HOME_TEAM} -> {home}\\n"
                f"Czas dojazdu: ok. {travel} min\\n"
                f"Mapy Google: {directions_url(HOME_ADDRESS, stadiums[home]['address'] if home in stadiums else home)}"
            )
        })

        events.append({
            "uid": uid + "-return",
            "title": f"Powrót z meczu: {home}",
            "start": match_end,
            "end": match_end + timedelta(minutes=travel),
            "location": f"{stadiums[home]['address'] if home in stadiums else home} - {HOME_TEAM}",
            "url": directions_url(stadiums[home]["address"] if home in stadiums else home, HOME_ADDRESS),
            "description": (
                f"Trasa: {home} -> {HOME_TEAM}\\n"
                f"Czas powrotu: ok. {travel} min\\n"
                f"Mapy Google: {directions_url(stadiums[home]['address'] if home in stadiums else home, HOME_ADDRESS)}"
            )
        })

        print(f"Wyjazd: {travel} min")

print(f"\nZnalezione wydarzenia: {len(events)}")

with open("calendar.ics","w",encoding="utf-8") as f:
    f.write("BEGIN:VCALENDAR\n")
    f.write("VERSION:2.0\n")
    f.write("PRODID:-//Jaguar Calendar//PL\n")

    for e in events:
        f.write("BEGIN:VEVENT\n")
        f.write(f"UID:{e['uid']}@jaguar\n")
        f.write(f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}\n")
        f.write(f"DTSTART;TZID=Europe/Warsaw:{e['start'].strftime('%Y%m%dT%H%M%S')}\n")
        f.write(f"DTEND;TZID=Europe/Warsaw:{e['end'].strftime('%Y%m%dT%H%M%S')}\n")
        f.write(f"SUMMARY:{e['title']}\n")

        if e.get("location"):
            f.write(f"LOCATION:{e['location']}\n")

        if e.get("url"):
            f.write(f"URL:{e['url']}\n")

        if e.get("description"):
            f.write(f"DESCRIPTION:{e['description']}\n")

        f.write("END:VEVENT\n")

    f.write("END:VCALENDAR\n")

print(f"\nPlik calendar.ics utworzony z {len(events)} wydarzeniami.")
