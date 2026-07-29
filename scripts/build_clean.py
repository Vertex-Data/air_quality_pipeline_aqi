"""
build_clean.py — Reconstruit clean/aqi_clean.csv à partir de TOUS les
fichiers présents dans raw/. Peut être relancé à volonté : ne modifie jamais
raw/, et écrase entièrement clean/aqi_clean.csv à chaque exécution.
"""
import glob
import json
import os

import pandas as pd

from config import CITIES, HOURLY_VARS

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "raw")
CLEAN_DIR = os.path.join(os.path.dirname(__file__), "..", "clean")
CLEAN_FILE = os.path.join(CLEAN_DIR, "aqi_clean.csv")

CITY_LOOKUP = {c["name"]: c for c in CITIES}


def load_all_raw() -> pd.DataFrame:
    rows = []
    pattern = os.path.join(RAW_DIR, "*", "*.json")
    for filepath in sorted(glob.glob(pattern)):
        city_name = os.path.basename(os.path.dirname(filepath))
        city = CITY_LOOKUP.get(city_name)
        if city is None:
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            payload = json.load(f)

        hourly = payload.get("hourly", {})
        times = hourly.get("time", [])
        if not times:
            continue

        for i, ts in enumerate(times):
            row = {
                "city": city_name,
                "country": city["country"],
                "latitude": city["lat"],
                "longitude": city["lon"],
                "timestamp_utc": ts,
            }
            for var in HOURLY_VARS:
                values = hourly.get(var, [])
                row[var] = values[i] if i < len(values) else None
            rows.append(row)

    return pd.DataFrame(rows)


def main():
    os.makedirs(CLEAN_DIR, exist_ok=True)
    df = load_all_raw()

    if df.empty:
        print("Aucune donnée brute trouvée dans raw/. clean/ non modifié.")
        return

    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])

    # Déduplication : même ville + même heure ne doit apparaître qu'une fois.
    # On garde la valeur du fichier lu en dernier (glob trié => l'appel le
    # plus récent l'emporte sur les anciens, utile en cas de recouvrement).
    df = df.sort_values(["city", "timestamp_utc"])
    df = df.drop_duplicates(subset=["city", "timestamp_utc"], keep="last")
    df = df.sort_values(["city", "timestamp_utc"]).reset_index(drop=True)

    # On retire les lignes sans aucune mesure exploitable
    df = df.dropna(subset=["pm10", "pm2_5"], how="all")

    column_order = ["city", "country", "latitude", "longitude", "timestamp_utc"] + HOURLY_VARS
    df = df[column_order]

    df.to_csv(CLEAN_FILE, index=False)
    print(
        f"clean/aqi_clean.csv régénéré : {len(df)} lignes, "
        f"{df['city'].nunique()} villes, "
        f"{df['timestamp_utc'].min()} -> {df['timestamp_utc'].max()}"
    )


if __name__ == "__main__":
    main()
