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
    if len(cols) < 4:
        continue

    home = cols[1]
    away = cols[2]
    date = cols[3]

    events.append((home, away, date))

with open("calendar.ics", "w") as f:

    f.write("BEGIN:VCALENDAR\n")
    f.write("VERSION:2.0\n")

    for e in events:

        uid = e[0].replace(" ","")+"-"+e[1].replace(" ","")

        f.write("BEGIN:VEVENT\n")
        f.write(f"UID:{uid}@jaguar\n")
        f.write(f"SUMMARY:{e[0]} - {e[1]}\n")
        f.write("END:VEVENT\n")

    f.write("END:VCALENDAR\n")
