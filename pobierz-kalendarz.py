import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

URL = "https://www.pomorskifutbol.pl/mecze.php?id=4623&id_klub=7470"

html = requests.get(URL).text
soup = BeautifulSoup(html, "html.parser")

rows = soup.select("table tr")

events = []

for r in rows:
    cols = [c.text.strip() for c in r.find_all("td")]

    if len(cols) < 5:
        continue

    date_str = cols[0]      # np. 08.03.2026
    time_str = cols[1]      # np. 11:00
    home = cols[2]
    away = cols[3]

    if not time_str or time_str == "-":
        continue

    try:
        start = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
    except:
        continue

    end = start + timedelta(minutes=120)

    events.append({
        "home": home,
        "away": away,
        "start": start,
        "end": end
    })

with open("calendar.ics", "w", encoding="utf-8") as f:

    f.write("BEGIN:VCALENDAR\n")
    f.write("VERSION:2.0\n")
    f.write("PRODID:-//Jaguar Calendar//PL\n")

    for e in events:

        uid = f"{e['start'].strftime('%Y%m%d')}-{e['home']}-{e['away']}".replace(" ", "")

        dtstart = e["start"].strftime("%Y%m%dT%H%M00")
        dtend = e["end"].strftime("%Y%m%dT%H%M00")

        f.write("BEGIN:VEVENT\n")
        f.write(f"UID:{uid}@jaguar\n")
        f.write(f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}\n")
        f.write(f"DTSTART:{dtstart}\n")
        f.write(f"DTEND:{dtend}\n")
        f.write(f"SUMMARY:{e['home']} - {e['away']}\n")
        f.write("END:VEVENT\n")

    f.write("END:VCALENDAR\n")
