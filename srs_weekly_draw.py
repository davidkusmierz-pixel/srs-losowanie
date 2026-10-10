#!/usr/bin/env python3
import json
import os
import random
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo

DB_URL = os.environ["FIREBASE_DATABASE_URL"].rstrip("/")
DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]
TZ = ZoneInfo("Europe/Warsaw")

TRACKS = [
    "Autodrome Lago Maggiore", "Autopolis", "Blue Moon Bay Speedway", "Brands Hatch",
    "Circuit de Barcelona-Catalunya", "Circuit de la Sarthe", "Circuit de Spa-Francorchamps",
    "Daytona Road Course", "Deep Forest Raceway", "Dragon Trail - Seaside",
    "Fuji International Speedway", "Goodwood Motor Circuit", "Grand Valley",
    "High Speed Ring", "Interlagos", "Kyoto Driving Park", "Monza Circuit",
    "Mount Panorama", "Nürburgring GP", "Nürburgring Nordschleife", "Nürburgring 24h",
    "Red Bull Ring", "Road Atlanta", "Sardegna Road Track", "Sardegna Windmills",
    "Suzuka Circuit", "Tokyo Expressway", "Trial Mountain Circuit", "Watkins Glen",
    "WeatherTech Raceway Laguna Seca"
]

# Plausible, intentionally restrained race presets; only Gr.1–Gr.4.
PRESETS = {
    "Gr.1": [
        {"laps": 20, "qualifying": "10 minut", "tires": "Racing Hard + Racing Medium", "fuel": "×3", "wear": "×4", "pit": "1 obowiązkowy PIT STOP", "start": "Start lotny", "bop": "Włączony"},
        {"laps": 25, "qualifying": "10 minut", "tires": "Racing Hard + Racing Medium", "fuel": "×4", "wear": "×5", "pit": "1 obowiązkowy PIT STOP", "start": "Start lotny", "bop": "Włączony"},
    ],
    "Gr.2": [
        {"laps": 25, "qualifying": "10 minut", "tires": "Racing Hard + Racing Medium", "fuel": "×2", "wear": "×4", "pit": "1 obowiązkowy PIT STOP", "start": "Start lotny", "bop": "Włączony"},
        {"laps": 30, "qualifying": "10 minut", "tires": "Racing Hard + Racing Medium", "fuel": "×3", "wear": "×5", "pit": "1 obowiązkowy PIT STOP", "start": "Start lotny", "bop": "Włączony"},
    ],
    "Gr.3": [
        {"laps": 20, "qualifying": "10 minut", "tires": "Racing Hard + Racing Medium", "fuel": "×2", "wear": "×4", "pit": "1 obowiązkowy PIT STOP", "start": "Start lotny", "bop": "Włączony"},
        {"laps": 30, "qualifying": "10 minut", "tires": "Racing Hard + Racing Medium", "fuel": "×3", "wear": "×5", "pit": "1 obowiązkowy PIT STOP", "start": "Start lotny", "bop": "Włączony"},
        {"laps": 12, "qualifying": "10 minut", "tires": "Racing Soft", "fuel": "×1", "wear": "×2", "pit": "Brak obowiązkowego PIT STOP", "start": "Start zatrzymany", "bop": "Włączony"},
    ],
    "Gr.4": [
        {"laps": 20, "qualifying": "10 minut", "tires": "Racing Hard + Racing Medium", "fuel": "×2", "wear": "×4", "pit": "1 obowiązkowy PIT STOP", "start": "Start lotny", "bop": "Włączony"},
        {"laps": 25, "qualifying": "10 minut", "tires": "Racing Hard + Racing Medium", "fuel": "×3", "wear": "×5", "pit": "1 obowiązkowy PIT STOP", "start": "Start lotny", "bop": "Włączony"},
        {"laps": 15, "qualifying": "10 minut", "tires": "Racing Soft", "fuel": "×1", "wear": "×2", "pit": "Brak obowiązkowego PIT STOP", "start": "Start zatrzymany", "bop": "Włączony"},
    ],
}

def firebase_request(path, method="GET", payload=None):
    url = f"{DB_URL}/{path.strip('/')}.json"
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else None

def discord_post(message):
    data = json.dumps({"content": message}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(DISCORD_WEBHOOK, data=data, method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as response:
        response.read()

def next_due(schedule, now):
    try:
        first_date = date.fromisoformat(schedule["startDate"])
        hour, minute = map(int, schedule.get("time", "18:00").split(":"))
    except (KeyError, ValueError):
        return None, None
    first = datetime.combine(first_date, time(hour, minute), TZ)
    if now < first:
        return first, first.date().isoformat()
    weeks = (now.date() - first.date()).days // 7
    due = first + timedelta(days=7 * weeks)
    if due > now:
        due -= timedelta(days=7)
    return due, due.date().isoformat()

def main():
    now = datetime.now(TZ)
    schedule = firebase_request("srsWeeklySchedule") or {}
    if not schedule.get("enabled"):
        print("Harmonogram zatrzymany.")
        return

    due, run_key = next_due(schedule, now)
    if not due:
        print("Nieprawidłowa data/godzina harmonogramu.")
        return
    if now < due or schedule.get("lastRunKey") == run_key:
        print("Brak nowego terminu do realizacji.")
        return

    pool = firebase_request("srsLobbyTrackPool")
    if not isinstance(pool, list):
        pool = TRACKS[:]
    pool = [t for t in pool if t in TRACKS]
    if not pool:
        pool = TRACKS[:]
        print("Pula torów była pusta — rozpoczęto nowy cykl torów.")

    track = random.choice(pool)
    pool.remove(track)
    car_class = random.choice(["Gr.1", "Gr.2", "Gr.3", "Gr.4"])
    preset = random.choice(PRESETS[car_class])

    # Weather and time are restrained to keep races fair and practical.
    weather = random.choices(
        ["☀️ Bez opadów", "🌤️ Zachmurzenie", "🌦️ Zmienna pogoda"],
        weights=[6, 3, 1], k=1
    )[0]
    time_of_day = random.choice(["🌞 Dzień", "🌇 Popołudnie", "🌅 Zachód słońca"])

    race_date = due.date().strftime("%d.%m.%Y")
    message = (
        "🏁 **SRS WEEKLY RACE — WYLOSOWANY EVENT** 🏁\n"
        f"📅 **Termin:** {race_date}, godz. {due.strftime('%H:%M')} (czas polski)\n"
        f"🛣️ **Tor:** {track}\n"
        f"🏎️ **Klasa:** {car_class}\n"
        f"🔢 **Wyścig:** {preset['laps']} okrążeń\n"
        f"⏱️ **Kwalifikacje:** {preset['qualifying']}\n"
        f"🌦️ **Pogoda:** {weather}\n"
        f"🌅 **Pora dnia:** {time_of_day}\n"
        f"🛞 **Opony:** {preset['tires']}\n"
        f"⛽ **Zużycie paliwa:** {preset['fuel']}\n"
        f"🔧 **Zużycie opon:** {preset['wear']}\n"
        f"🛑 **Pit stop:** {preset['pit']}\n"
        f"🚦 **Start:** {preset['start']}\n"
        f"⚖️ **BOP:** {preset['bop']}\n\n"
        "🏆 Dobór ustawień SRS: wyścig ligowy z naciskiem na uczciwą rywalizację i strategię."
    )

    discord_post(message)
    firebase_request("srsLobbyTrackPool", "PUT", pool)
    schedule["lastRunKey"] = run_key
    schedule["lastRunAt"] = now.strftime("%d.%m.%Y %H:%M")
    schedule["lastTrack"] = track
    schedule["lastClass"] = car_class
    firebase_request("srsWeeklySchedule", "PUT", schedule)
    firebase_request("srsWeeklyLatestResult", "PUT", {
        "track": track, "carClass": car_class, "date": race_date,
        "time": due.strftime("%H:%M"), "message": message, "createdAt": now.isoformat()
    })
    print(f"Opublikowano event: {track} / {car_class} / {run_key}")

if __name__ == "__main__":
    main()
