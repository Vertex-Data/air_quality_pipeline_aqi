"""
validate_clean.py — Vérifie que clean/aqi_clean.csv respecte le contrat de
données du projet avant chargement dans le warehouse.
"""
import os
import sys

import pandas as pd

from config import CITIES, HOURLY_VARS

CLEAN_FILE = os.path.join(os.path.dirname(__file__), "..", "clean", "aqi_clean.csv")
REQUIRED_COLUMNS = ["city", "country", "latitude", "longitude", "timestamp_utc"] + HOURLY_VARS
EXPECTED_CITIES = {c["name"] for c in CITIES}


def fail(msg: str):
    print(f"[ÉCHEC] {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    if not os.path.exists(CLEAN_FILE):
        fail(f"{CLEAN_FILE} introuvable. Lancez build_clean.py d'abord.")

    df = pd.read_csv(CLEAN_FILE, parse_dates=["timestamp_utc"])

    missing_cols = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing_cols:
        fail(f"Colonnes manquantes : {missing_cols}")

    if df.empty:
        fail("clean/aqi_clean.csv est vide.")

    missing_cities = EXPECTED_CITIES - set(df["city"].unique())
    if missing_cities:
        fail(f"Villes manquantes dans clean/ : {missing_cities}")

    dupes = df.duplicated(subset=["city", "timestamp_utc"]).sum()
    if dupes > 0:
        fail(f"{dupes} doublons (ville, heure) détectés.")

    for city in EXPECTED_CITIES:
        sub = df[df["city"] == city]
        if not sub["timestamp_utc"].is_monotonic_increasing:
            fail(f"{city} : les lignes ne sont pas triées chronologiquement.")

    if df[["latitude", "longitude"]].isnull().any().any():
        fail("Coordonnées manquantes.")

    print("[OK] clean/aqi_clean.csv est valide.")
    print(f"  Lignes totales   : {len(df)}")
    print(f"  Villes           : {sorted(df['city'].unique())}")
    print(f"  Période couverte : {df['timestamp_utc'].min()} -> {df['timestamp_utc'].max()}")
    print("  Lignes par ville :")
    print(df.groupby("city").size().to_string())


if __name__ == "__main__":
    main()
