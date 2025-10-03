# Recette fonctionnelle – Amazon Reviews Scraper

## 1. Objectif
Fournir une recette exhaustive et opérationnelle pour scraper, stocker et exporter des avis Amazon, avec résilience anti-bot, rotation de proxies, et interface CLI.

## 2. Périmètre fonctionnel
- Scraping d’avis Amazon par ASIN, pagination automatique, filtrage par étoiles et langue.
- Résilience: détection anti-bot, retry, rotation User-Agent et proxies.
- Persistance: SQLite par défaut ou PostgreSQL.
- Export: CSV et Parquet.
- CLI complète: crawl (asin/urls/batch), export, health-check, auth-login, migration de nettoyage des titres.

## 3. Architecture et composants
- `app/config.py`: configuration via variables d’environnement (Pydantic Settings).
- `app/fetch.py`: récupération des pages (Playwright), rotation UA/proxy, session/login.
- `app/parser.py`: parsing rapide des avis (one-shot evaluate) + fallback, extraction du total d’avis.
- `app/normalize.py`: normalisation (dates FR, rating, votes utiles, achat vérifié, ID canonique).
- `app/models.py`: modèle `Review` (SQLAlchemy) + index et `to_dict()`.
- `app/db.py`: moteur SQLAlchemy, `get_db()`, `create_tables()`.
- `app/selectors.py`: sélecteurs CSS centralisés.
- `app/scrape.py`: orchestrateur `AmazonScraper` (pagination, sauvegarde, stats, batch).
- `app/cli.py`: commandes Typer (crawl, crawl_urls, crawl_batch, export, health_check, auth_login, migrate_clean_titles).

## 4. Pré-requis
- Python 3.11+, Playwright installé (chromium).
- Dépendances: voir `requirements.txt`.
- Optionnel: Docker et docker-compose pour PostgreSQL.

## 5. Configuration (.env)
Variables principales:
- Proxies: `PROXY_POOL=http://user:pass@host:port,http://user:pass@host2:port`
- Navigateur: `HEADLESS=true|false`, `TIMEOUT_MS=45000`, `MAX_CONTEXTS=2`
- Scraping: `MAX_PAGES_PER_ASIN=5`, `SLEEP_MIN=2.0`, `SLEEP_MAX=4.0`, `LANGUAGE=fr_FR`, `SORT=recent`
- Base: `DB_URL=sqlite:///./reviews.db` (ou `postgresql+psycopg://user:pass@host:5432/db`)
- Auth Amazon: `STORAGE_STATE_PATH=./storage_state.json`, `AMZ_EMAIL`, `AMZ_PASSWORD` (facultatif)

## 6. Recette E2E (locale)
1) Installation
- Créer et activer un venv
- `pip install -r requirements.txt`
- `python -m playwright install chromium`
- `cp env.example .env` puis éditer

2) Vérifier l’environnement
- `python -m app.cli health-check -v`

3) Authentification (facultative mais recommandée)
- `python -m app.cli auth-login` (ouvre une fenêtre, se connecter, 2FA si nécessaire)
- À la fin: vérifiez la création de `storage_state.json`

4) Scraper un ASIN (persistant en base)
- Basique: `python -m app.cli crawl B0XXXXXXXX --max-pages 5 -v`
- Par URL d’avis: `python -m app.cli crawl --url "https://www.amazon.fr/product-reviews/ASIN/?reviewerType=all_reviews&sortBy=recent"`

5) Scraper un lot d’URLs avec filtrage d’étoiles
- Fichier `scripts/test_asins.txt` (ou URLs via `crawl-urls`):
  - `python -m app.cli crawl_urls scripts/test_asins.txt --full --stars five --persist`

6) Export des données
- ASIN spécifique CSV: `python -m app.cli export --asin B0XXXXXXXX -o export.csv -f csv`
- Tous les avis Parquet: `python -m app.cli export -o export.parquet -f parquet`

7) Migration de nettoyage des titres
- `python -m app.cli migrate-clean-titles --limit 1000 -v`

## 7. Recette E2E (Docker + PostgreSQL)
1) Construire et lancer
- `docker build -t amazon-scraper .`
- `docker-compose up -d`

2) Exécuter une commande dans le conteneur
- `docker exec -it amazon-scraper python -m app.cli health-check`
- `docker exec -it amazon-scraper python -m app.cli crawl B0XXXXXXXX --max-pages 5`

3) Persistance & exports
- Les volumes `./data` et `./logs` sont montés dans le conteneur.
- Configurez `DB_URL` PostgreSQL via docker-compose (défaut fourni).

## 8. Flux fonctionnels clés
- Génération d’URL: `utils.generate_product_url`, `utils.generate_review_url`.
- Navigation: warm-up via page produit, gestion cookies, headers, scripts d’évasion.
- Anti-bot: `utils.detect_anti_bot`, rotation UA/proxy, `tenacity` retry, pauses aléatoires.
- Parsing: `parser.parse_reviews_from_page` (one-shot + fallback), extraction `review_id` déterministe.
- Déduplication: par `review_id` et contenu canonique.
- Persistance: `scrape._save_reviews` avec gestion d’unicité, index.
- Statistiques: `scrape.scrape_asin` retourne `total_reviews`, `total_pages`, `errors`, `pages_details`.

## 9. Schéma des données `Review`
Champs: `asin`, `review_id` (unique), `review_title`, `review_body`, `rating`, `review_date`, `verified_purchase`, `helpful_votes`, `reviewer_name`, `variant`, `created_at`, `updated_at`.
Index: `idx_asin_review_date`, `idx_asin_rating`, contrainte d’unicité sur `review_id`.

## 10. Bonnes pratiques anti-bot
- Activer `HEADLESS=false` pour debug de blocages.
- Fournir `PROXY_POOL` et varier régions.
- Éviter `full_pagination` en volume; préférer des tranches d’étoiles.
- Respecter `SLEEP_MIN/MAX` (2-4s par défaut) et réduire la verbosité côté réseau.
- Rejouer `auth-login` si redirection login détectée.

## 11. Dépannage
- CAPTCHA / blocage:
  - Vérifier proxies, augmenter délais, tenter UA mobile (automatique au 2e essai).
  - Relancer `auth-login` et vérifier `storage_state.json`.
- Pages vides:
  - Vérifier sélecteurs, langue, ou `filterByStar`; activer `--full` pour parcourir toutes les pages.
- Erreurs DB (doublons):
  - Attendu: unicité sur `review_id`. Les doublons sont ignorés.
- Timeouts:
  - Augmenter `TIMEOUT_MS`, réduire `MAX_PAGES_PER_ASIN`.

## 12. Sécurité et conformité
- Respecter les CGU d’Amazon, ne pas collecter d’informations personnelles non nécessaires.
- Limiter la fréquence et le volume de scraping.

## 13. Indicateurs de réussite
- `health-check` OK (DB, Playwright, réseau).
- Scraping retourne `success=True` avec `total_reviews > 0`.
- Exports présents et lisibles (CSV/Parquet).

## 14. Commandes utiles (exemples)
```bash
python -m app.cli crawl B0XXXXXXXX -p 3 -v
python -m app.cli crawl_urls scripts/test_asins.txt --stars all --persist
python -m app.cli export --output all_reviews.csv -f csv
python -m app.cli health-check -v
python -m app.cli auth-login
python -m app.cli migrate-clean-titles --limit 500
```

## 15. Limites connues
- Layout Amazon variable selon pays/langue; des ajustements de sélecteurs peuvent être requis.
- Les blocages anti-bot peuvent nécessiter des pools de proxies de qualité.
- Le mode headless peut être plus détectable sur certaines périodes.
