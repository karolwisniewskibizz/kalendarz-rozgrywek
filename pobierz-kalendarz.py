import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import hashlib

URL = "https://www.pomorskifutbol.pl/mecze.php?id=4623&id_klub=7470"

html = requests.get(URL).content
soup = BeautifulSoup(html, "html.parser")

tables = soup.find_all("table")

# tabela z meczami to zwykle druga lub trzecia
match_table = None
for t in tables:
    if "kolejka" in t.get_text().lower():
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

for r in rows:
    cols = [c.get_text(strip=True) for c in r.find_all("td")]

    # Pomijamy nagłówki i wiersze z za mało kolumnami
    if len(cols) < 6:
        continue

    home = cols[1].strip()
    away = cols[3].strip()
    date_text = cols[5].strip()

    # Jeśli data jest pusta, pomijamy
    if not date_text:
        continue

    # Szukamy daty w formacie: "dzień miesiąc rok godzina:minuta" lub "dzień miesiąc rok"
    m = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})", date_text)

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

    # Szukamy czasu w formacie "HH:MM"
    t = re.search(r"(\d{2}):(\d{2})", date_text)

    if t:
        time = t.group(0)
    else:
        time = "12:00"

    try:
        start = datetime.strptime(f"{year}-{month:02d}-{day:02d} {time}", "%Y-%m-%d %H:%M")
    except ValueError as e:
        print(f"Błąd parsowania daty: {year}-{month}-{day} {time}, błąd: {e}")
        continue

    end = start + timedelta(minutes=120)

    uid_src = f"{year}-{month}-{day}-{home}-{away}".lower()
    uid = hashlib.md5(uid_src.encode()).hexdigest()

    events.append((home, away, start, end, uid))
    print(f"Dodano mecz: {home} - {away} na dzień {start}")

print(f"\nZnalezione mecze: {len(events)}")

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

print(f"Plik calendar.ics został utworzony z {len(events)} meczami.")
