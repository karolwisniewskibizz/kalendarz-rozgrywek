import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import hashlib
import json
import math
import pytz
from geopy.distance import geodesic

URL = "https://www.pomorskifutbol.pl/mecze.php?id=4623&id_klub=7470"

HOME_TEAM = "Jaguar"
HOME_KEY = "Jaguar Gdańsk"

# wczytanie stadionów / miast
with open("stadiums.json", encoding="utf-8") as f:
    stadiums = json.load(f)

HOME_COORD = (
    stadiums[HOME_KEY]["lat"],
    stadiums[HOME_KEY]["lon"]
)
HOME_ADDRESS = stadiums[HOME_KEY]["address"]

# strefa czasowa
POLAND = pytz.timezone("Europe/Warsaw")

html = requests.get(URL).content
soup = BeautifulSoup(html, "html.parser")

tables = soup.find_all("table")
if not tables:
    print("Brak tabel na stronie")
    exit()

# Używamy pierwszej tabeli
match_table = tables[0]
print(f"Znaleziono {len(tables)} tabel, używam tabeli 0")

rows = match_table.find_all("tr")
print(f"Liczba wierszy w tabeli: {len(rows)}")

months = {
    "stycznia":1,"lutego":2,"marca":3,"kwietnia":4,"maja":5,"czerwca":6,
    "lipca":7,"sierpnia":8,"września":9,"października":10,"listopada":11,"grudnia":12
}

events = []

def round_quarter(minutes):
    return int(math.ceil(minutes / 15.0) * 15)

def travel_minutes(coord1, coord2):
    dist_km = geodesic(coord1, coord2).km
    avg_speed = 70  # km/h
    minutes = dist_km / avg_speed * 60
    return int(math.ceil(minutes / 15.0) * 15)  # całkowite minuty, zaokrąglone do kwadransa

for r in rows:
    cols = [c.get_text(strip=True) for c in r.find_all("td")]
    if len(cols) < 6:
        continue

    home = cols[1].strip()
    away = cols[3].strip()
    date_text = cols[5].strip()

    if not date_text:
        continue

    # obsługa dat typu "1. maja 2026" i "23/24. maja 2026"
    m = re.search(r"(\d{1,2})(?:/\d{1,2})?\.?\s+(\w+)\s+(\d{4})", date_text)
    if not m:
        print(f"Nie znaleziono daty w: {date_text}")
        continue

    day = int(m.group(1))
    month_name = m.group(2).lower()
    year = int(m.group(3))

    if month_name not in months:
        print(f"Nieznany miesiąc: {month_name}")
        continue

    month = months[month_name]

    # czas w formacie HH:MM
    t = re.search(r"(\d{2}):(\d{2})", date_text)
    if t:
        time = t.group(0)
    else:
        time = "12:00"

    try:
        naive_start = datetime.strptime(f"{year}-{month:02d}-{day:02d} {time}", "%Y-%m-%d %H:%M")
        start = POLAND.localize(naive_start)
    except ValueError as e:
        print(f"Błąd parsowania daty: {date_text}, {e}")
        continue

    end = start + timedelta(minutes=120)

    uid_src = f"{year}-{month}-{day}-{home}-{away}".lower()
    uid = hashlib.md5(uid_src.encode()).hexdigest()

    location = stadiums[home]["address"] if home in stadiums else home

    # wydarzenie meczu
    events.append({
        "uid": uid,
        "title": f"{home} - {away}",
        "start": start,
        "end": end,
        "location": location
        "url": URL
    })

    print(f"Dodano mecz: {home} - {away} ({start})")

    # sprawdzanie gospodarza/gościa
    is_home = HOME_TEAM.lower() in cols[1].lower()
    is_away = HOME_TEAM.lower() in cols[3].lower()

    # WYJAZD i POWRÓT jeśli Jaguar jest gościem
    if is_away:
        # Jeśli mecz jest na tym samym adresie co Jaguar (np. Gardeja), pomijamy dojazd i powrót.
        if home in stadiums and stadiums[home]["address"] == HOME_ADDRESS:
            print(f"Pomijam wyjazd/powrót dla {home}: ten sam adres stadionu co Jaguar")
            continue

        if home in stadiums:
            coord = (stadiums[home]["lat"], stadiums[home]["lon"])
            travel = travel_minutes(HOME_COORD, coord)
        else:
            coord = HOME_COORD  # brak współrzędnych
            travel = 60  # minimalny czas przejazdu w minutach

        depart = start - timedelta(minutes=(travel + 30))  # 30 min przed meczem

        # Wyjazd
        events.append({
            "uid": uid + "-travel",
            "title": f"Wyjazd na mecz: {home}",
            "start": depart,
            "end": depart + timedelta(minutes=travel),
            "location": stadiums[HOME_KEY]["address"]
        })

        # Powrót po meczu
        return_start = end
        return_end = end + timedelta(minutes=travel)
        events.append({
            "uid": uid + "-return",
            "title": f"Powrót z meczu: {home}",
            "start": return_start,
            "end": return_end,
            "location": stadiums[home]["address"] if home in stadiums else home
        })

        print(f"Wyjazd na {home}: {travel} min, powrót po meczu")

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
        if e["location"]:
            f.write(f"LOCATION:{e['location']}\n")
        if "url" in e:
            f.write(f"URL:{e['url']}\n")
        f.write("END:VEVENT\n")

    f.write("END:VCALENDAR\n")

print(f"\nPlik calendar.ics utworzony z {len(events)} wydarzeniami.")
