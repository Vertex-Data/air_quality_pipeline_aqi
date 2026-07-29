import os
import sys

import pandas as pd
import psycopg2
import psycopg2.extras

CLEAN_FILE = os.path.join(os.path.dirname(__file__), "..", "clean", "aqi_clean.csv")
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "..", "sql", "schema.sql")

DAY_NAMES_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]


def get_connection():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("[ERREUR] Variable d'environnement DATABASE_URL absente.", file=sys.stderr)
        sys.exit(1)
    return psycopg2.connect(dsn)


def apply_schema(conn):
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        ddl = f.read()
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()


def upsert_cities(conn, df: pd.DataFrame) -> dict:
    cities = df[["city", "country", "latitude", "longitude"]].drop_duplicates(subset=["city"])
    city_id_map = {}
    with conn.cursor() as cur:
        for _, row in cities.iterrows():
            cur.execute(
                """
                INSERT INTO dim_city (city_name, country, latitude, longitude)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (city_name) DO UPDATE
                    SET country = EXCLUDED.country,
                        latitude = EXCLUDED.latitude,
                        longitude = EXCLUDED.longitude
                RETURNING city_id, city_name;
                """,
                (row["city"], row["country"], row["latitude"], row["longitude"]),
            )
            city_id, city_name = cur.fetchone()
            city_id_map[city_name] = city_id
    conn.commit()
    return city_id_map


def upsert_time(conn, df: pd.DataFrame) -> dict:
    timestamps = pd.to_datetime(df["timestamp_utc"]).drop_duplicates().sort_values()
    time_id_map = {}
    with conn.cursor() as cur:
        for ts in timestamps:
            dow = ts.weekday()  # 0 = lundi
            cur.execute(
                """
                INSERT INTO dim_time (full_timestamp, date, hour, day_of_week,
                                       day_name, is_weekend, month, year)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (full_timestamp) DO NOTHING
                RETURNING time_id;
                """,
                (ts.to_pydatetime(), ts.date(), ts.hour, dow, DAY_NAMES_FR[dow], dow >= 5, ts.month, ts.year),
            )
            result = cur.fetchone()
            if result is None:
                cur.execute("SELECT time_id FROM dim_time WHERE full_timestamp = %s;", (ts.to_pydatetime(),))
                result = cur.fetchone()
            time_id_map[ts] = result[0]
    conn.commit()
    return time_id_map


def upsert_facts(conn, df: pd.DataFrame, city_id_map: dict, time_id_map: dict):
    df = df.copy()
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])
    rows = []
    for _, r in df.iterrows():
        rows.append((
            city_id_map[r["city"]],
            time_id_map[r["timestamp_utc"]],
            r.get("pm10"), r.get("pm2_5"), r.get("carbon_monoxide"),
            r.get("nitrogen_dioxide"), r.get("sulphur_dioxide"), r.get("ozone"),
            r.get("european_aqi"), r.get("us_aqi"),
        ))

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO fact_aqi (city_id, time_id, pm10, pm2_5, carbon_monoxide,
                                   nitrogen_dioxide, sulphur_dioxide, ozone,
                                   european_aqi, us_aqi)
            VALUES %s
            ON CONFLICT (city_id, time_id) DO UPDATE
                SET pm10 = EXCLUDED.pm10,
                    pm2_5 = EXCLUDED.pm2_5,
                    carbon_monoxide = EXCLUDED.carbon_monoxide,
                    nitrogen_dioxide = EXCLUDED.nitrogen_dioxide,
                    sulphur_dioxide = EXCLUDED.sulphur_dioxide,
                    ozone = EXCLUDED.ozone,
                    european_aqi = EXCLUDED.european_aqi,
                    us_aqi = EXCLUDED.us_aqi;
            """,
            rows,
        )
    conn.commit()


def main():
    if not os.path.exists(CLEAN_FILE):
        print(f"[ERREUR] {CLEAN_FILE} introuvable. Lancez build_clean.py d'abord.", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(CLEAN_FILE, parse_dates=["timestamp_utc"])
    if df.empty:
        print("[ERREUR] clean/aqi_clean.csv est vide.", file=sys.stderr)
        sys.exit(1)

    conn = get_connection()
    try:
        apply_schema(conn)
        city_id_map = upsert_cities(conn, df)
        time_id_map = upsert_time(conn, df)
        upsert_facts(conn, df, city_id_map, time_id_map)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM fact_aqi;")
            total = cur.fetchone()[0]
        print(f"[OK] Warehouse chargé. fact_aqi contient désormais {total} lignes.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
