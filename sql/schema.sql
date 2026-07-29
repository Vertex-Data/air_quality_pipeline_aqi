-- Schéma en étoile pour le data warehouse AQI.
-- Règles respectées : pas de mesure dans les dimensions,
-- pas de colonne descriptive dans la table de faits.

CREATE TABLE IF NOT EXISTS dim_city (
    city_id     SERIAL PRIMARY KEY,
    city_name   VARCHAR(100) NOT NULL UNIQUE,
    country     VARCHAR(100) NOT NULL,
    latitude    DOUBLE PRECISION NOT NULL,
    longitude   DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_time (
    time_id         SERIAL PRIMARY KEY,
    full_timestamp  TIMESTAMP NOT NULL UNIQUE,  -- toujours en UTC
    date            DATE NOT NULL,
    hour            SMALLINT NOT NULL,
    day_of_week     SMALLINT NOT NULL,          -- 0 = lundi ... 6 = dimanche
    day_name        VARCHAR(10) NOT NULL,
    is_weekend      BOOLEAN NOT NULL,
    month           SMALLINT NOT NULL,
    year            SMALLINT NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_aqi (
    fact_id             BIGSERIAL PRIMARY KEY,
    city_id             INTEGER NOT NULL REFERENCES dim_city(city_id),
    time_id             INTEGER NOT NULL REFERENCES dim_time(time_id),
    pm10                DOUBLE PRECISION,
    pm2_5               DOUBLE PRECISION,
    carbon_monoxide     DOUBLE PRECISION,
    nitrogen_dioxide    DOUBLE PRECISION,
    sulphur_dioxide     DOUBLE PRECISION,
    ozone               DOUBLE PRECISION,
    european_aqi        DOUBLE PRECISION,
    us_aqi              DOUBLE PRECISION,
    UNIQUE (city_id, time_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_aqi_city ON fact_aqi (city_id);
CREATE INDEX IF NOT EXISTS idx_fact_aqi_time ON fact_aqi (time_id);
