# ARCHITECTURE.md

## Stack retenue

| Composant | Choix | Justification |
|---|---|---|
| Source de données | Open-Meteo Air Quality API | Gratuite et sans clé pour un usage non commercial, couverture mondiale (Paris, Moscow, Nairobi, Berlin, Tokyo), historique CAMS disponible depuis août 2022 — largement suffisant pour un backfill de 12 mois. |
| Orchestrateur | GitHub Actions (workflows planifiés) | Tourne sur l'infrastructure de GitHub : le pipeline continue de fonctionner 24h/24 même quand aucun membre du groupe n'a son PC allumé, ce qui répond à l'exigence « le pipeline doit continuer à tourner après le rendu ». L'onglet **Actions** fournit nativement l'historique de tous les runs (statut, durée, logs), utilisé comme preuve d'exécution automatique. |
| Stockage brut (raw/) | Fichiers JSON versionnés dans le dépôt Git, un fichier par ville et par appel | Conforme à la règle « raw/ jamais modifié » : chaque run *ajoute* des fichiers, n'en réécrit jamais. Git donne gratuitement l'historique complet et l'horodatage de chaque collecte. |
| Stockage propre (clean/) | Un CSV unique, reconstruit à chaque run | Reconstruction complète depuis raw/ à chaque exécution (option recommandée par le sujet) ; la déduplication (même ville + même heure) est gérée par `build_clean.py`. |
| Data warehouse | PostgreSQL hébergé sur **Supabase** (offre gratuite) | Doit rester joignable après la date de rendu pour que IA1 consomme les données au fil de l'eau ; une base locale sur un PC/WSL2 ne peut pas garantir cette disponibilité en continu. Supabase donne en plus un tableau de bord SQL directement utilisable pour la vidéo de démonstration (requête SQL sur le warehouse). |
| Modélisation | Schéma en étoile (`dim_city`, `dim_time`, `fact_aqi`) | Une seule table de faits alimentée par 5 villes ne justifie pas la complexité d'un flocon ; l'étoile suffit et reste simple à interroger en SQL. |
| Secrets | `DATABASE_URL` stocké en secret GitHub Actions | Open-Meteo ne nécessite pas de clé API en usage non commercial. Le seul secret réel du pipeline — les identifiants de connexion à la base — n'apparaît jamais dans le code ni dans l'historique Git. |

## Pourquoi pas Airflow ?

Airflow nécessite un serveur qui tourne en continu (webserver + scheduler),
contraignant à héberger gratuitement et à maintenir disponible après la date
de rendu. GitHub Actions remplit le même rôle d'orchestrateur — déclenchement
planifié, logs, historique d'exécutions — sans infrastructure à gérer, ce qui
correspond à la consigne « ORCHESTRATEUR (au choix du groupe) ».

## Flux du pipeline

```
Open-Meteo Air Quality API
   │  extract.py (toutes les heures, via cron GitHub Actions)
   ▼
raw/<ville>/<ville>_<horodatage>.json   (jamais modifié)
   │  build_clean.py (reconstruction complète à chaque run)
   ▼
clean/aqi_clean.csv   (un fichier unique, dédupliqué, trié)
   │  validate_clean.py (contrôle du contrat de données)
   ▼
load_warehouse.py (UPSERT idempotent)
   ▼
PostgreSQL — dim_city / dim_time / fact_aqi
```

## Limites connues

- **Connexion Supabase depuis GitHub Actions** : la connexion directe de
  Supabase (`db.<ref>.supabase.co:5432`) est en IPv6 uniquement, et les
  runners GitHub Actions n'ont pas de sortie IPv6. Il faut donc utiliser le
  **Transaction pooler** de Supabase (Supavisor, port `6543`,
  `aws-0-<région>.pooler.supabase.com`), qui est en IPv4 — adapté à un client
  éphémère comme un job GitHub Actions. Voir README.md pour la procédure.
- Les cron GitHub Actions sont *best effort* : un run peut être retardé de
  quelques minutes en cas de forte charge sur l'infrastructure GitHub
  (contrairement à un scheduler Airflow dédié). On compense avec une fenêtre
  de recouvrement (`past_hours=6`) à chaque extraction, pour ne pas perdre de
  données en cas de léger retard ou d'échec ponctuel d'un run.
- Un workflow planifié est automatiquement désactivé après 60 jours
  d'inactivité sur le dépôt. Comme notre workflow *commite* les nouvelles
  données à chaque run, le dépôt reste actif et ce risque est évité tant que
  le pipeline tourne.
