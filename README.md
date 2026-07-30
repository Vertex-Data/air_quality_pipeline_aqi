# README — Pipeline AQI (Open-Meteo)

## Villes suivies

| Ville | Pays | Latitude | Longitude |
|---|---|---|---|
| Paris | France | 48.8566 | 2.3522 |
| Moscow | Russie | 55.7558 | 37.6173 |
| Nairobi | Kenya | -1.2921 | 36.8219 |
| Berlin | Allemagne | 52.5200 | 13.4050 |
| Tokyo | Japon | 35.6762 | 139.6503 |

## Colonnes de `clean/aqi_clean.csv`

| Colonne | Unité | Description |
|---|---|---|
| city | texte | Nom de la ville |
| country | texte | Pays |
| latitude / longitude | degrés (WGS84) | Coordonnées de la ville |
| timestamp_utc | ISO8601, UTC | Horodatage de la mesure (toutes les villes sont normalisées en UTC pour rester comparables entre elles) |
| pm10 | µg/m³ | Particules fines < 10 µm |
| pm2_5 | µg/m³ | Particules fines < 2.5 µm |
| carbon_monoxide | µg/m³ | Monoxyde de carbone |
| nitrogen_dioxide | µg/m³ | Dioxyde d'azote |
| sulphur_dioxide | µg/m³ | Dioxyde de soufre |
| ozone | µg/m³ | Ozone |
| european_aqi | indice (0 à 100+) | Indice de qualité de l'air européen (agrégat du pire polluant) |
| us_aqi | indice (0 à 500) | Indice de qualité de l'air américain (agrégat du pire polluant) |

Source : [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api),
modèles CAMS (Copernicus Atmosphere Monitoring Service — CAMS Europe 11 km
et CAMS Global 45 km).

## Schéma du warehouse (étoile)

- `dim_city(city_id, city_name, country, latitude, longitude)`
- `dim_time(time_id, full_timestamp, date, hour, day_of_week, day_name, is_weekend, month, year)`
- `fact_aqi(fact_id, city_id, time_id, pm10, pm2_5, carbon_monoxide, nitrogen_dioxide, sulphur_dioxide, ozone, european_aqi, us_aqi)`

DDL complet : `sql/schema.sql`.

## Période couverte

- **Backfill historique** : jusqu'à 6 mois avant la date de rendu, limité
  par la disponibilité des données CAMS globales (à partir d'août 2022).
- **Collecte continue** : toutes les heures, via `.github/workflows/collect.yml`.

## Trous connus

- Si le pipeline est mis en place après le début du projet, le backfill ne
  peut couvrir que la période disponible côté Open-Meteo (à partir d'août 2022).
- Un run horaire manqué (panne GitHub Actions) est en principe rattrapé au
  run suivant grâce à la fenêtre de recouvrement de 6h, sauf coupure > 6h.

## Connexion à la base

- Moteur : PostgreSQL hébergé sur **[Supabase](https://supabase.com)**
  (offre gratuite).
- Variable d'environnement : `DATABASE_URL`, stockée en secret GitHub
  Actions, jamais commitée dans le dépôt.
- **Utiliser impérativement le Transaction pooler**, pas la connexion
  directe (voir ci-dessous) : la connexion directe de Supabase est en IPv6
  uniquement, et les runners GitHub Actions ne savent pas router en IPv6 —
  le run échouerait avec une erreur de type *"could not connect"* /
  *"No route to host"*.
- Pour un accès en lecture (ex. pour IA1) : demander les identifiants au
  groupe, transmis hors du dépôt Git.


## Mise en route (une seule fois)

1. Créer un projet gratuit sur [supabase.com](https://supabase.com) →
   **New project** (choisir une région proche, ex. `eu-west` ou
   `eu-central`) et définir le mot de passe de la base.
2. Une fois le projet créé, cliquer sur **Connect** (bouton en haut du
   dashboard) et sélectionner l'onglet **Transaction pooler**. Copier la
   chaîne de connexion, qui ressemble à :
   ```
   postgresql://postgres.<project_ref>:[MOT-DE-PASSE]@aws-0-<région>.pooler.supabase.com:6543/postgres
   ```
   Remplacer `[MOT-DE-PASSE]` par le mot de passe défini à l'étape 1.
   *(Ne pas prendre la "Direct connection" ni la "Session pooler" — le
   Transaction pooler, port `6543`, est le seul mode IPv4 adapté à un job
   GitHub Actions qui se connecte, exécute quelques requêtes, puis se
   déconnecte.)*
3. Dans le dépôt GitHub : **Settings → Secrets and variables → Actions →
   New repository secret**, nommer le secret `DATABASE_URL`, coller la
   chaîne de connexion complète.
4. Vérifier que les workflows sont actifs dans l'onglet **Actions**
   (`Collecte AQI horaire` tourne automatiquement, `Backfill historique AQI`
   se lance manuellement).
5. Lancer une première fois le backfill : **Actions → Backfill historique
   AQI → Run workflow**. Vérifier dans les logs que l'étape "Chargement du
   data warehouse" se termine sur `[OK] Warehouse chargé...`.

### Dépannage rapide

| Symptôme | Cause probable | Solution |
|---|---|---|
| `could not translate host name` / `No route to host` | Connexion directe (IPv6) utilisée au lieu du pooler | Reprendre la chaîne **Transaction pooler** (port 6543) depuis l'étape 2 |
| `password authentication failed` | Mot de passe non remplacé dans la chaîne copiée | Vérifier que `[MOT-DE-PASSE]` a bien été remplacé par le vrai mot de passe |
| `SSL connection required` | Rare avec la chaîne Supabase par défaut | Ajouter `?sslmode=require` à la fin de `DATABASE_URL` |

## Relancer le pipeline manuellement (local)

```bash
pip install -r requirements.txt
export DATABASE_URL="postgresql://..."

python scripts/extract.py          # une collecte immédiate
python scripts/build_clean.py      # reconstruit clean/aqi_clean.csv
python scripts/validate_clean.py   # vérifie le contrat de données
python scripts/load_warehouse.py   # charge le warehouse
```

## Difficultés rencontrées

1. **Lancement automatique du projet**  
   Configuration initiale de GitHub Actions (secrets, permissions `contents: write`, token `GITHUB_TOKEN`) et mise en place du cron fiable. Les runners gratuits peuvent retarder les exécutions planifiées (jusqu'à plusieurs heures de décalage), ce qui a nécessité l'ajout d'une fenêtre de recouvrement de 6h dans `extract.py`.

2. **Utilisation d'Airflow avant migration vers GitHub Actions**  
   Le projet a d'abord été pensé avec Apache Airflow (DAGs, scheduler, base de métadonnées). L'hébergement et la maintenance d'Airflow (serveur, base Postgres dédiée, monitoring) représentaient une surcharge importante pour un pipeline horaire simple. Migration vers GitHub Actions pour : coût nul, intégration native Git, pas d'infrastructure à gérer.

3. **Conflits lors du push (données + code)**  
   Le workflow commit et push `raw/` et `clean/` à chaque run horaire. Si un push manuel (code) arrive en parallèle, le job GitHub Actions échoue avec `rejected non-fast-forward`. Solution : `git pull --rebase` avant push dans le workflow, et séparation des branches (protection `main` + PR pour le code, commits directs du bot pour les données).

4. **Répartition des tâches dans l'équipe**  
   - Un membre : scripts Python (extract, build_clean, validate, load_warehouse, backfill)  
   - Un membre : infrastructure (Supabase, secrets, GitHub Actions, schéma SQL)  
   - Un membre : documentation (README, contrat de données, schéma étoile) et vidéo de démo  
   Synchronisation via issues GitHub et points quotidiens courts (15 min) pour éviter les blocages.

## Backfill historique

```bash
python scripts/backfill.py --months 6
```

Ou depuis GitHub : **Actions → Backfill historique AQI → Run workflow**.
