#!/usr/bin/env python3
import json, os, random, urllib.request, urllib.error
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo

DB_URL = os.environ["FIREBASE_DATABASE_URL"].rstrip("/")
DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]
TZ = ZoneInfo("Europe/Warsaw")

# Race formats aimed at roughly 35–50 minutes of racing, plus 10-minute qualifying.
PRESETS = {
 "Gr.1": [
  ("Circuit de la Sarthe", 8, "×2", "×3", "Racing Hard + Racing Medium"),
  ("Suzuka Circuit", 10, "×2", "×3", "Racing Hard + Racing Medium"),
  ("Mount Panorama", 8, "×2", "×3", "Racing Hard + Racing Medium"),
 ],
 "Gr.2": [
  ("Autopolis", 12, "×2", "×3", "Racing Medium + Racing Soft"),
  ("Fuji International Speedway", 12, "×2", "×3", "Racing Medium + Racing Soft"),
  ("Monza Circuit", 12, "×2", "×3", "Racing Medium + Racing Soft"),
 ],
 "Gr.3": [
  ("Circuit de Spa-Francorchamps", 8, "×2", "×3", "Racing Hard + Racing Medium"),
  ("Red Bull Ring", 16, "×2", "×4", "Racing Medium + Racing Soft"),
  ("Deep Forest Raceway", 16, "×2", "×4", "Racing Medium + Racing Soft"),
  ("Watkins Glen", 14, "×2", "×3", "Racing Hard + Racing Medium"),
  ("Dragon Trail - Seaside", 14, "×2", "×4", "Racing Medium + Racing Soft"),
 ],
 "Gr.4": [
  ("Brands Hatch", 20, "×2", "×4", "Sports Hard + Sports Medium"),
  ("Dragon Trail - Seaside", 16, "×2", "×4", "Sports Hard + Sports Medium"),
  ("Trial Mountain Circuit", 18, "×2", "×4", "Sports Hard + Sports Medium"),
  ("Red Bull Ring", 20, "×2", "×4", "Sports Hard + Sports Medium"),
 ],
}
def fb(path, method="GET", payload=None):
    url = f"{DB_URL}/{path.strip('/')}.json"
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw else None
def post_discord(message):
    data = json.dumps({"content": message}, ensure_ascii=False).encode()
    req = urllib.request.Request(DISCORD_WEBHOOK, data=data, method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "SRS-Weekly-Race/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
            print(f"Discord odpowiedział: HTTP {r.status}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        # Do not print the webhook URL or its token.
        print(f"Discord odrzucił wiadomość: HTTP {e.code}; odpowiedź: {body[:1000]}")
        raise RuntimeError("Nie udało się wysłać wiadomości do Discorda. Sprawdź odpowiedź powyżej.") from None

def make_message(race):
    due = datetime.fromisoformat(race["eventDate"] + "T" + race["eventTime"]).replace(tzinfo=TZ)
    date_pl = due.strftime("%d.%m.%Y")
    return (
      "🏁 **SRS WEEKLY RACE — NOWY WYŚCIG** 🏁\\n"
      f"📅 **Termin:** {date_pl}, godz. {due.strftime('%H:%M')} (czas polski)\\n"
      f"🛣️ **Tor:** {race['track']}\\n🏎️ **Klasa:** {race['className']}\\n"
      f"🔢 **Dystans:** {race['laps']} okrążeń\\n"
      f"⌛ **Szacowany czas jazdy:** {race['estimatedMinutes']} min + kwalifikacje 10 min\\n"
      f"🌦️ **Pogoda:** {race['weather']}\\n🌅 **Pora dnia:** {race['timeOfDay']}\\n"
      f"🛞 **Opony:** {race['tires']}\\n🔧 **Pit stop:** 1 obowiązkowy\\n"
      f"⛽ **Paliwo:** {race['fuel']}\\n🛞 **Zużycie opon:** {race['tireWear']}\\n"
      "🚦 **Start:** lotny\\n⚖️ **BOP:** włączony\\n\\n"
      "ℹ️ Czas jest orientacyjny i zależy od tempa kierowców."
    )

def main():
    now = datetime.now(TZ)
    schedule = fb("srsWeeklyRaceSchedule") or {}
    if not schedule.get("enabled"):
        print("Harmonogram nieaktywny.")
        return
    try:
        first_date = date.fromisoformat(schedule["startDate"])
        hh, mm = map(int, schedule.get("time", "18:00").split(":"))
    except (KeyError, ValueError):
        raise RuntimeError("Harmonogram ma nieprawidłową datę lub godzinę.")
    first = datetime.combine(first_date, time(hh, mm), TZ)
    if now < first:
        print("Pierwszy termin jeszcze nie nadszedł.")
        return
    weeks = (now.date() - first.date()).days // 7
    due = first + timedelta(days=7 * weeks)
    if due > now:
        due -= timedelta(days=7)
    run_key = due.date().isoformat()

    previous = fb("srsAutoRace") or {}
    # If this week's race exists but Discord failed earlier, retry posting that same race.
    if previous.get("scheduleKey") == run_key:
        race = previous
        if schedule.get("lastRunKey") == run_key and schedule.get("discordPosted") is True:
            print("Wyścig tygodnia jest już utworzony i ogłoszony na Discordzie.")
            return
        print("Znaleziono już utworzony wyścig. Ponawiam wysyłkę ogłoszenia na Discorda.")
    else:
        last_track = previous.get("track", "")
        cls = random.choice(list(PRESETS))
        options = [x for x in PRESETS[cls] if x[0] != last_track] or PRESETS[cls]
        track, laps, fuel, wear, tires = random.choice(options)
        weather = random.choices(["Słonecznie", "Lekko pochmurno", "Zmienna pogoda"], [6, 3, 1])[0]
        timeofday = random.choice(["Dzień", "Popołudnie", "Zachód słońca"])
        estimated = random.choice([35, 40, 45, 50])
        race = {
          "id": str(int(now.timestamp() * 1000)), "status": "scheduled",
          "eventDate": due.date().isoformat(), "eventTime": due.strftime("%H:%M"),
          "eventDateTime": int(due.timestamp() * 1000), "className": cls, "track": track,
          "laps": laps, "fuel": fuel, "tireWear": wear, "tires": tires, "weather": weather,
          "timeOfDay": timeofday, "pit": "1 obowiązkowy PIT STOP", "startType": "Start lotny",
          "qualifying": "10 minut", "bop": "BOP włączony", "estimatedMinutes": estimated,
          "createdAt": int(now.timestamp() * 1000), "scheduleKey": run_key
        }
        fb("srsAutoRace", "PUT", race)
        fb("srsAutoRaceHistory/" + race["id"], "PUT", race)
        print("Zapisano wyścig w Firebase:", run_key, track, cls)

    # Only mark the week as completed after Discord confirms the message was accepted.
    post_discord(make_message(race))
    fb("srsWeeklyRaceSchedule", "PATCH", {
        "lastRunKey": run_key,
        "lastRunAt": now.isoformat(),
        "discordPosted": True
    })
    print("SUKCES: ogłoszenie wyścigu wysłane na Discorda:", run_key)

if __name__ == "__main__":
    main()
