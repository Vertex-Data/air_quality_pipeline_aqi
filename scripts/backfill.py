import argparse
import json
import os
import sys
import time
from datetime import date, timedelta

import requests

from config import CITIES, HOURLY_VARS

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "raw")
API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

EARLIEST_AVAILABLE = date(2022, 8, 1)

def month_chunks(start: date, end: date):
    current = start
    while current <= end:
        next_month = (current.replace(day=1) + timedelta(days=32)).replace(day=1)
        chunk_end = min(next_month - timedelta(days=1), end)
        yield current, chunk_end
        current = next_month


def fetch_range(city: dict, start: date, end: date) -> dict:
    params = {
        "latitude": city["lat"],
        "longitude": city["lon"],
        "hourly": ",".join(HOURLY_VARS),
        "timezone": "UTC",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }
    resp = requests.get(API_URL, params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()


def save_raw(city_name: str, payload: dict, start: date, end: date) -> str:
    city_dir = os.path.join(RAW_DIR, city_name)
    os.makedirs(city_dir, exist_ok=True)
    filepath = os.path.join(
        city_dir, f"{city_name}_backfill_{start.isoformat()}_{end.isoformat()}.json"
    )
    if os.path.exists(filepath):
        print(f"[SKIP] {filepath} existe déjà (raw/ n'est jamais réécrit).")
        return filepath
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    return filepath


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--months", type=int, default=12,
        help="Nombre de mois à remonter depuis aujourd'hui (défaut : 12)",
    )
    parser.add_argument("--start", type=str, help="Date de début YYYY-MM-DD (remplace --months)")
    parser.add_argument("--end", type=str, help="Date de fin YYYY-MM-DD (défaut : aujourd'hui)")
    args = parser.parse_args()

    end = date.fromisoformat(args.end) if args.end else date.today()
    start = date.fromisoformat(args.start) if args.start else end - timedelta(days=30 * args.months)
    start = max(start, EARLIEST_AVAILABLE)

    print(f"Backfill de {start} à {end} pour {len(CITIES)} villes.")

    for city in CITIES:
        for chunk_start, chunk_end in month_chunks(start, end):
            try:
                payload = fetch_range(city, chunk_start, chunk_end)
                path = save_raw(city["name"], payload, chunk_start, chunk_end)
                print(f"[OK] {city['name']} {chunk_start}->{chunk_end} -> {path}")
            except Exception as exc:
                print(f"[ERREUR] {city['name']} {chunk_start}->{chunk_end}: {exc}", file=sys.stderr)
            time.sleep(1) 

    print("Backfill terminé. Lancez build_clean.py pour régénérer clean/.")


if __name__ == "__main__":
    main()
