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
  ("Brands Hatch", 20, "×2", "×4", "Racing Hard + Racing Medium"),
  ("Dragon Trail - Seaside", 16, "×2", "×4", "Racing Hard + Racing Medium"),
  ("Trial Mountain Circuit", 18, "×2", "×4", "Racing Hard + Racing Medium"),
  ("Red Bull Ring", 20, "×2", "×4", "Racing Hard + Racing Medium"),
 ],
}
def fb(path, method="GET", payload=None):
    url = f"{DB_URL}/{path.strip('/')}.json"
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw else None
def post_discord(race):
    """Publikuje ustawienia zgodne z kategoriami opcji w lobby Gran Turismo 7."""
    due = datetime.fromisoformat(race["eventDate"] + "T" + race["eventTime"]).replace(tzinfo=TZ)
    date_pl = due.strftime("%d.%m.%Y")

    def field(name, value, inline=False):
        # Discord limits a single field value to 1024 characters.
        return {"name": name, "value": str(value)[:1024], "inline": inline}

    # Two embeds keep the post readable and within Discord's embed limits.
    embed1 = {
        "title": "🏁 SRS WEEKLY RACE | USTAWIENIA LOBBY GT7",
        "description": (
            f"**Termin:** {date_pl} • **Godzina:** {due.strftime('%H:%M')} (Polska)\n"
            f"**Tor:** {race['track']} • **Kategoria:** {race['className']}\n"
            f"**Dystans:** {race['laps']} okr. • **Kwalifikacje:** {race['qualifying']}\n"
            f"**Szacowany czas jazdy:** ok. {race['estimatedMinutes']} min.\n"
            "Ustawienia poniżej przepisz w odpowiednich sekcjach tworzenia lobby. Nazwy/opcje mogą się różnić zależnie od toru i trybu."
        ),
        "color": 15158332,
        "fields": [
            field("🏁 USTAWIENIA TORU", 
                  f"Tor: {race['track']}\nLiczba okrążeń: {race['laps']}\nLimit czasu wyścigu: {race['raceTimeLimit']}"),
            field("🌦️ CZAS I POGODA",
                  f"Metoda wyboru pogody: {race['weatherMethod']}\n"
                  f"Pogoda ustawiona: {race['weather']}\n"
                  f"Pora dnia: {race['timeOfDay']}\n"
                  f"Przyspieszenie czasu: {race['timeSpeed']}\n"
                  f"Woda na torze na starcie: {race['surfaceWater']}\n"
                  f"Równe warunki: {race['equalConditions']}"),
            field("🚦 USTAWIENIA WYŚCIGU",
                  f"Rodzaj startu: {race['startType']}\n"
                  f"Kolejność na starcie: {race['gridOrder']}\n"
                  f"BoP / zakaz tuningu: {race['bop']}\n"
                  f"Tuning: {race['tuning']}\n"
                  f"Boost: {race['boost']}\n"
                  f"Siła poślizgu aerodynamicznego: {race['slipstream']}\n"
                  f"Uszkodzenia wizualne: {race['visibleDamage']}\n"
                  f"Uszkodzenia mechaniczne: {race['mechanicalDamage']}\n"
                  f"Zużycie opon: {race['tireWear']} • Zużycie paliwa: {race['fuel']}\n"
                  f"Paliwo początkowe: {race['initialFuel']}\n"
                  f"Prędkość tankowania: {race['refuelSpeed']}\n"
                  f"Przyczepność poza torem: {race['offTrackGrip']}\n"
                  f"Opóźnienie końca wyścigu: {race['finishDelay']}\n"
                  f"Minimalna liczba pit stopów: {race['minPitStops']}\n"
                  f"Wymagana zmiana typu opon: {race['requiredTireChange']}\n"
                  f"Mnożnik czasu nitro/systemu wyprzedzania: {race['nitrousMultiplier']}"),
            field("⏱️ KWALIFIKACJE",
                  f"Limit czasu: {race['qualifying']}\n"
                  f"Dodatkowy czas na dokończenie okrążenia: {race['qualifyingContinuation']}\n"
                  f"Zużycie opon w kwalifikacjach: {race['qualifyingTireWear']}\n"
                  f"Zużycie paliwa w kwalifikacjach: {race['qualifyingFuel']}\n"
                  f"Paliwo początkowe: {race['qualifyingInitialFuel']}"),
        ],
    }
    embed2 = {
        "title": "⚙️ SRS WEEKLY RACE | REGULAMIN I KARY",
        "color": 3447003,
        "fields": [
            field("🛞 USTAWIENIA REGULAMINU AUT",
                  f"Filtr kategorii: {race['className']}\n"
                  f"Maks. PP: {race['ppLimit']}\n"
                  f"Maks. moc: {race['maxPower']}\n"
                  f"Minimalna masa: {race['minWeight']}\n"
                  f"Typ opon: {race['tireType']}\n"
                  f"Dozwolone opony: {race['tires']}\n"
                  f"Wymagana zmiana opon: {race['requiredTires']}\n"
                  f"Nitro: {race['nitrous']}\n"
                  f"Użycie kartów: {race['kartUsage']}\n"
                  f"Swap silnika: {race['engineSwap']}\n"
                  f"Części tuningowe: {race['tuningParts']}\n"
                  f"Rok produkcji od–do: {race['yearRange']}\n"
                  f"Napęd: {race['drivetrain']}\n"
                  f"Doładowanie: {race['aspiration']}"),
            field("⚠️ USTAWIENIA KAR",
                  f"Kara za skracanie: {race['shortcutPenalty']}\n"
                  f"Kara za uderzenie w bandę: {race['wallPenalty']}\n"
                  f"Korekta kierunku po uderzeniu w bandę: {race['wallCorrection']}\n"
                  f"Kara za kolizję z autem: {race['carCollisionPenalty']}\n"
                  f"Kara za linię pit lane: {race['pitLanePenalty']}\n"
                  f"Ghosting podczas wyścigu: {race['ghosting']}\n"
                  f"Reguły flag: {race['flagRules']}"),
            field("🎮 OGRANICZENIA ASYST JAZDY",
                  f"Pomoc w kontrze: {race['countersteering']}\n"
                  f"ASM: {race['asm']}\n"
                  f"Linia jazdy: {race['drivingLine']}\n"
                  f"Kontrola trakcji: {race['tractionControl']}\n"
                  f"ABS: {race['abs']}\n"
                  f"Autopilot: {race['autoDrive']}"),
        ],
        "footer": {"text": "SRS • Wartości do przepisania w lobby GT7 • niektóre opcje zależą od toru/trybu"},
    }
    payload = {"content": "🏁 **🏁 SRS | WEEKLY COMBO**", "embeds": [embed1, embed2]}
    data = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(DISCORD_WEBHOOK, data=data, method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "SRS-Weekly-Race/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
            print(f"Discord odpowiedział: HTTP {r.status}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"Discord odrzucił wiadomość: HTTP {e.code}; odpowiedź: {body[:1000]}")
        raise RuntimeError("Nie udało się wysłać wiadomości do Discorda. Sprawdź odpowiedź powyżej.") from None

def make_race_settings(race, cls, track, laps, fuel, wear, tires, weather, timeofday, estimated, due, now, run_key):
    """Ustawienia domyślne, sensowne do ligowego wyścigu SRS Gr.1–Gr.4."""
    race.update({
        "className": cls, "track": track, "laps": laps, "fuel": fuel, "tireWear": wear,
        "tires": tires, "weather": weather, "timeOfDay": timeofday,
        "raceTimeLimit": "Nie dotyczy (wyścig na okrążenia)",
        "estimatedMinutes": estimated,
        "weatherMethod": "Pogoda zaprogramowana (Preset Weather)",
        "timeSpeed": "×5",
        "surfaceWater": "0%",
        "equalConditions": "Włączone",
        "startType": "Start lotny (Rolling Start)",
        "gridOrder": "Najszybsi z przodu (Fastest First)",
        "bop": "Włączony",
        "tuning": "Zabroniony",
        "boost": "Wyłączony",
        "slipstream": "Realistyczny (Real)",
        "visibleDamage": "Włączone",
        "mechanicalDamage": "Lekkie",
        "initialFuel": "Domyślne",
        "refuelSpeed": "20 l/s",
        "offTrackGrip": "Realistyczna",
        "finishDelay": "180 sekund",
        "minPitStops": "1",
        "requiredTireChange": "Włączona",
        "ppLimit": "Brak",
        "maxPower": "Brak",
        "minWeight": "Brak",
        "yearRange": "Bez ograniczeń",
        "drivetrain": "Bez ograniczeń",
        "aspiration": "Bez ograniczeń",
        "tireType": "Wyścigowe",
        "requiredTires": tires,
        "nitrous": "Zabronione",
        "kartUsage": "Wyłączone",
        "engineSwap": "Zabroniony",
        "tuningParts": "Zabronione (BoP włączone)",
        "nitrousMultiplier": "×1",
        "shortcutPenalty": "Silna",
        "wallPenalty": "Wyłączona",
        "wallCorrection": "Włączona",
        "carCollisionPenalty": "Włączona",
        "pitLanePenalty": "Włączona",
        "ghosting": "Wyłączony",
        "flagRules": "Włączone",
        "countersteering": "Wyłączona",
        "asm": "Wyłączone",
        "drivingLine": "Dowolna",
        "tractionControl": "Dowolna",
        "abs": "Dowolne",
        "autoDrive": "Wyłączony",
        "qualifying": "10 minut",
        "qualifyingContinuation": "1 minuta",
        "qualifyingTireWear": wear,
        "qualifyingFuel": fuel,
        "qualifyingInitialFuel": "Domyślne",
        "eventDate": due.date().isoformat(),
        "eventTime": due.strftime("%H:%M"),
        "eventDateTime": int(due.timestamp() * 1000),
        "createdAt": int(now.timestamp() * 1000),
        "scheduleKey": run_key
    })
    return race

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
        # Backfill newly added lobby settings if this race was generated by an older script version.
        race = make_race_settings(
            race,
            race.get("className", "Gr.3"),
            race.get("track", "Trial Mountain Circuit"),
            race.get("laps", 15),
            race.get("fuel", "×2"),
            race.get("tireWear", "×4"),
            race.get("tires", "Racing Hard + Racing Medium"),
            race.get("weather", "S03 — sucho, pochmurno i przyjemnie"),
            race.get("timeOfDay", "Popołudnie"),
            race.get("estimatedMinutes", 40), due, now, run_key
        )
        fb("srsAutoRace", "PUT", race)
        if schedule.get("lastRunKey") == run_key and schedule.get("discordPosted") is True:
            print("Wyścig tygodnia jest już utworzony i ogłoszony na Discordzie.")
            return
        print("Znaleziono już utworzony wyścig. Ponawiam wysyłkę ogłoszenia na Discorda.")
    else:
        last_track = previous.get("track", "")
        cls = random.choice(list(PRESETS))
        options = [x for x in PRESETS[cls] if x[0] != last_track] or PRESETS[cls]
        track, laps, fuel, wear, tires = random.choice(options)
        weather = random.choices(["S01 — sucho, bezchmurnie i przyjemnie", "S03 — sucho, pochmurno i przyjemnie", "S04 — sucho, pochmurno i słonecznie"], [5, 3, 2])[0]
        timeofday = random.choice(["Późny poranek", "Popołudnie", "Zachód słońca"])
        estimated = random.choice([35, 40, 45, 50])
        race = {"id": str(int(now.timestamp() * 1000)), "status": "scheduled"}
        race = make_race_settings(race, cls, track, laps, fuel, wear, tires, weather, timeofday,
                                  estimated, due, now, run_key)
        fb("srsAutoRace", "PUT", race)
        fb("srsAutoRaceHistory/" + race["id"], "PUT", race)
        print("Zapisano wyścig w Firebase:", run_key, track, cls)

    # Only mark the week as completed after Discord confirms the message was accepted.
    post_discord(race)
    fb("srsWeeklyRaceSchedule", "PATCH", {
        "lastRunKey": run_key,
        "lastRunAt": now.isoformat(),
        "discordPosted": True
    })
    print("SUKCES: ogłoszenie wyścigu wysłane na Discorda:", run_key)

if __name__ == "__main__":
    main()
