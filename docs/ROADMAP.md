# Roadmap

Ziel: ein Portfolio-Projekt, das Backend-Handwerk und Datenanalyse mit Luftfahrt-Fachwissen verbindet.
Halte jeden Meilenstein klein und lauffähig, bevor du den nächsten beginnst.

## Meilenstein 1: Backend-Grundgerüst (Wochen 1 bis 3)

Bereits im Repository:

- [x] Projektstruktur, `pyproject.toml`, Docker, Docker Compose
- [x] Ingestion: OpenSky abrufen, parsen, ohne Duplikate speichern
- [x] API: `/states/latest`, `/aircraft/{icao24}/track`
- [x] Tests (Parser, Storage, API) und CI

Deine Aufgaben, in dieser Reihenfolge:

1. [ ] **Git einrichten:** `git init`, erster Commit, Repository auf GitHub anlegen, pushen
2. [ ] **Lint beim ersten Mal:** `ruff check --fix .` und `ruff format .`, Ergebnis committen
3. [ ] **Alles einmal laufen lassen:** `docker compose up --build`, in `/docs` ausprobieren, Logs lesen
4. [ ] **Code lesen:** Warum `ON CONFLICT DO NOTHING`? Warum SQL nur in `storage.py`? Warum ein eigener Parser?
5. [ ] **Erste eigene Funktion** (Branch `feature/latest-endpoint`): `GET /aircraft/{icao24}/latest` mit Test, danach Pull Request an dich selbst
6. [ ] **Fehlerfall testen:** Was passiert bei HTTP 429 oder ungültigem JSON? Schreibe einen Test für `run_forever` oder `run_once` mit einem Fake-Client
7. [ ] **Alembic** statt `create_all` für Schema-Änderungen einführen
8. [ ] **Einfache Absicherung:** API-Key per Header für die Endpunkte

## Meilenstein 2: Datenaufbereitung und Zustandsschätzung (Wochen 4 bis 6)

Hier spielt dein Studium seine Stärke aus.

- [ ] Notebook: Rohdaten laden, Lücken, Ausreißer und Duplikate untersuchen
- [ ] Koordinaten in ein lokales kartesisches System (ENU) umrechnen
- [ ] Kalman-Filter (Modell mit konstanter Geschwindigkeit), Vergleich Rohdaten gegen gefilterte Spur
- [ ] Filter als wiederverwendbares Modul mit Tests (`src/flightdata/filtering/`)
- [ ] Endpunkt für geglättete Tracks

## Meilenstein 3: Analyse und ML (Wochen 7 bis 9)

- [ ] Flugphasen erkennen (Climb, Cruise, Descent, Approach), erst regelbasiert, dann datengetrieben
- [ ] Anomalien: Holding Patterns, Durchstarten (Go-arounds)
- [ ] Vorhersage (zum Beispiel Ankunftszeit) mit scikit-learn, sauberer Train/Test-Split nach Zeit
- [ ] Modelle über die API ausliefern, Evaluation dokumentieren

## Meilenstein 4: Produktreife und Branchenbrücke (Wochen 10 bis 12)

- [ ] Optional TimescaleDB für Zeitreihen
- [ ] Dashboard (Streamlit oder kleine Web-Oberfläche)
- [ ] Deployment (Server oder Cloud) mit laufender Demo
- [ ] Zweite Datenquelle (IMU- oder Fahrzeugtelemetrie), gleiche Pipeline
- [ ] README mit Ergebnisbeispielen und Screenshots, Architekturdiagramm aktuell halten

## Arbeitsweise mit Git

- Ein Branch pro Aufgabe: `git switch -c feature/kurzer-name`
- Kleine Commits mit verständlicher Nachricht im Imperativ: `Add latest-position endpoint`
- Vor jedem Commit: `git status` und `git diff` ansehen
- `.env` und Zugangsdaten gehören nie ins Repository (steht in `.gitignore`)
- Pull Request öffnen, CI abwarten, dann mergen

## Bewerbung

Ab etwa Woche 6 kannst du dich mit dem Projekt als "in Arbeit, Zwischenstand hier" bewerben.
Wichtiger als Umfang sind Tests, lesbarer Code und eine verständliche README.
