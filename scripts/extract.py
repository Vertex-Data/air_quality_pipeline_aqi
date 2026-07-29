"""
extract.py — Collecte horaire des données de qualité de l'air (Open-Meteo)
pour les 5 villes du projet.

Chaque exécution produit UN fichier brut par ville dans raw/<ville>/.
Les fichiers bruts ne sont jamais modifiés ni supprimés (raw/ = sauvegarde).
"""
import json
import os
import sys
from datetime import datetime, timezone

import requests

from config import CITIES, HOURLY_VARS

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "raw")
API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

# Fenêtre de recouvrement : si un run est manqué ou en retard, le run suivant
# récupère quand même les heures manquantes. La déduplication (même ville +
# même heure = une seule ligne) est faite ensuite par build_clean.py.
PAST_HOURS = 6
FORECAST_HOURS = 1


def fetch_city(city: dict) -> dict:
    params = {
        "latitude": city["lat"],
        "longitude": city["lon"],
        "hourly": ",".join(HOURLY_VARS),
        "timezone": "UTC",
        "past_hours": PAST_HOURS,
        "forecast_hours": FORECAST_HOURS,
    }
    resp = requests.get(API_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def save_raw(city_name: str, payload: dict, run_ts: str) -> str:
    city_dir = os.path.join(RAW_DIR, city_name)
    os.makedirs(city_dir, exist_ok=True)
    filepath = os.path.join(city_dir, f"{city_name}_{run_ts}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    return filepath


def main():
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ok, failed = 0, []

    for city in CITIES:
        try:
            payload = fetch_city(city)
            path = save_raw(city["name"], payload, run_ts)
            print(f"[OK] {city['name']} -> {path}")
            ok += 1
        except Exception as exc:
            print(f"[ERREUR] {city['name']}: {exc}", file=sys.stderr)
            failed.append(city["name"])

    print(f"Terminé : {ok}/{len(CITIES)} villes collectées.")
    if failed:
        print(f"Échecs : {', '.join(failed)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
