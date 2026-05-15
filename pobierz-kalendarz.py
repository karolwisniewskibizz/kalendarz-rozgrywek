import argparse
import hashlib
import json
import math
import re
from datetime import datetime, timedelta
from urllib.parse import urlencode, urlparse

import pytz
import requests
from bs4 import BeautifulSoup
from geopy.distance import geodesic

DEFAULT_URL = "https://www.pomorskifutbol.pl/mecze.php?id=4623&id_klub=7470"

HOME_TEAM = "Jaguar"
HOME_KEY = "Jaguar Gdańsk"

with open("stadiums.json", encoding="utf-8") as f:
    stadiums = json.load(f)

HOME_COORD = (stadiums[HOME_KEY]["lat"], stadiums[HOME_KEY]["lon"])
HOME_ADDRESS = stadiums[HOME_KEY]["address"]
POLAND = pytz.timezone("Europe/Warsaw")

months = {
    "stycznia": 1,
    "lutego": 2,
    "marca": 3,
    "kwietnia": 4,
    "maja": 5,
    "czerwca": 6,
    "lipca": 7,
    "sierpnia": 8,
    "września": 9,
    "października": 10,
    "listopada": 11,
    "grudnia": 12,
}


def parse_args():
    parser = argparse.ArgumentParser(description="Generuje kalendarz meczów do pliku ICS")
    parser.add_argument("--url", default=DEFAULT_URL, help="URL terminarza")
    return parser.parse_args()


def travel_minutes(coord1, coord2):
    dist_km = geodesic(coord1, coord2).km
    avg_speed = 70
    minutes = dist_km / avg_speed * 60
    return int(math.ceil(minutes / 15.0) * 15)


def directions_url(origin, destination):
    params = urlencode({"api": 1, "origin": origin, "destination": destination, "travelmode": "driving"})
    return f"https://www.google.com/maps/dir/?{params}"


def fetch_html(url):
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_polish_datetime(date_text):
    m = re.search(r"(\d{1,2})(?:/\d{1,2})?\.?\s+(\w+)\s+(\d{4})", date_text)
    if not m:
        return None

    day = int(m.group(1))
    month_name = m.group(2).lower()
    year = int(m.group(3))

    if month_name not in months:
        return None

    month = months[month_name]
    t = re.search(r"(\d{2}):(\d{2})", date_text)
    time_str = t.group(0) if t else "12:00"

    naive_start = datetime.strptime(f"{year}-{month:02d}-{day:02d} {time_str}", "%Y-%m-%d %H:%M")
    return POLAND.localize(naive_start)


def parse_matches_from_table(soup):
    tables = soup.find_all("table")
    if not tables:
        return []

    rows = tables[0].find_all("tr")
    matches = []

    for row in rows:
        cols = [c.get_text(strip=True) for c in row.find_all("td")]
        if len(cols) < 6:
            continue

        home = cols[1].strip()
        away = cols[3].strip()
        date_text = cols[5].strip()

        match_start = parse_polish_datetime(date_text)
        if not match_start:
            continue

        matches.append({"home": home, "away": away, "match_start": match_start})

    return matches


def parse_matches_from_json_ld(soup):
    matches = []
    scripts = soup.find_all("script", {"type": "application/ld+json"})

    for script in scripts:
        raw = script.string
        if not raw:
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("@type") != "SportsEvent":
                continue

            home = (item.get("homeTeam") or {}).get("name")
            away = (item.get("awayTeam") or {}).get("name")
            start = item.get("startDate")
            if not (home and away and start):
                continue

            match_start = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(POLAND)
            matches.append({"home": home, "away": away, "match_start": match_start})

    return matches


def parse_matches(url, html):
    soup = BeautifulSoup(html, "html.parser")
    host = urlparse(url).netloc

    if "pomorskifutbol.pl" in host:
        matches = parse_matches_from_table(soup)
        print(f"Źródło: tabela HTML ({len(matches)} meczów)")
        return matches

    json_ld_matches = parse_matches_from_json_ld(soup)
    if json_ld_matches:
        print(f"Źródło: JSON-LD ({len(json_ld_matches)} meczów)")
        return json_ld_matches

    table_matches = parse_matches_from_table(soup)
    if table_matches:
        print(f"Źródło: tabela HTML fallback ({len(table_matches)} meczów)")
        return table_matches

    return []


def main():
    args = parse_args()
    url = args.url

    html = fetch_html(url)
    matches = parse_matches(url, html)

    if not matches:
        print("Nie znaleziono meczów na stronie")
        return

    events = []
    for match in matches:
        home = match["home"]
        away = match["away"]
        match_start = match["match_start"]
        match_end = match_start + timedelta(minutes=120)

        event_start = match_start - timedelta(minutes=45)

        uid_src = f"{match_start.date()}-{home}-{away}".lower()
        uid = hashlib.md5(uid_src.encode()).hexdigest()

        location = stadiums[home]["address"] if home in stadiums else home
        desc = (
            f"Mecz: {home} - {away}\\n"
            f"Rozgrzewka: {event_start.strftime('%H:%M')}\\n"
            f"Start: {match_start.strftime('%H:%M')}\\n"
            f"Koniec: {match_end.strftime('%H:%M')}\\n"
            f"Link: {url}"
        )

        events.append({
            "uid": uid,
            "title": f"{home} - {away}",
            "start": event_start,
            "end": match_end,
            "location": location,
            "url": url,
            "description": desc,
        })

        is_away = HOME_TEAM.lower() in away.lower()

        if is_away:
            if home in stadiums and stadiums[home]["address"] == HOME_ADDRESS:
                continue

            if home in stadiums:
                coord = (stadiums[home]["lat"], stadiums[home]["lon"])
                travel = travel_minutes(HOME_COORD, coord)
            else:
                travel = 60

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
                ),
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
                ),
            })

    with open("calendar.ics", "w", encoding="utf-8") as f:
        f.write("BEGIN:VCALENDAR\n")
        f.write("VERSION:2.0\n")
        f.write("PRODID:-//Jaguar Calendar//PL\n")
        f.write("X-WR-CALNAME:Jaguar Gdańsk - Terminarz\n")
        f.write("X-WR-TIMEZONE:Europe/Warsaw\n")
        f.write(f"X-WR-CALDESC:Wygenerowano {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

        for event in events:
            f.write("BEGIN:VEVENT\n")
            f.write(f"UID:{event['uid']}@jaguar\n")
            f.write(f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}\n")
            f.write(f"DTSTART;TZID=Europe/Warsaw:{event['start'].strftime('%Y%m%dT%H%M%S')}\n")
            f.write(f"DTEND;TZID=Europe/Warsaw:{event['end'].strftime('%Y%m%dT%H%M%S')}\n")
            f.write(f"SUMMARY:{event['title']}\n")

            if event.get("location"):
                f.write(f"LOCATION:{event['location']}\n")

            if event.get("url"):
                f.write(f"URL:{event['url']}\n")

            if event.get("description"):
                f.write(f"DESCRIPTION:{event['description']}\n")

            f.write("END:VEVENT\n")

        f.write("END:VCALENDAR\n")

    print(f"Plik calendar.ics utworzony z {len(events)} wydarzeniami.")


if __name__ == "__main__":
    main()
