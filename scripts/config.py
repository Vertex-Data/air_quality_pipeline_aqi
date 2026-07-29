"""
config.py — Configuration partagée par tous les scripts du pipeline.
"""

CITIES = [
    {"name": "Paris", "country": "France", "lat": 48.8566, "lon": 2.3522},
    {"name": "Moscow", "country": "Russie", "lat": 55.7558, "lon": 37.6173},
    {"name": "Nairobi", "country": "Kenya", "lat": -1.2921, "lon": 36.8219},
    {"name": "Berlin", "country": "Allemagne", "lat": 52.5200, "lon": 13.4050},
    {"name": "Tokyo", "country": "Japon", "lat": 35.6762, "lon": 139.6503},
]

# Variables horaires demandées à l'API Open-Meteo Air Quality.
# Documentées avec leurs unités dans README.md.
HOURLY_VARS = [
    "pm10",
    "pm2_5",
    "carbon_monoxide",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "ozone",
    "european_aqi",
    "us_aqi",
]
