## Audit de structure — amazon-scraper

Date: 2025-09-16

### Arborescence (hors venv/.git/__pycache__)

- Racine
  - `streamlit_app.py` (UI)
  - `app/` (code applicatif: scraping, parsing, DB)
  - `scripts/` (outils/init/tests intégration)
  - `tests/` (unit tests)
  - `reviews.db` (SQLite locale)
  - `pw_profile/` (profil Playwright persistant — volumineux)
  - `debug/` (dumps HTML/PNG dernière page)
  - `htmlcov/` (rapport de couverture)
  - fichiers de config: `requirements.txt`, `pyproject.toml`, `pytest.ini`, `Dockerfile`, `docker-compose.yml`, `Makefile`, `env.example`
  - docs: `README.md`, `ROADMAP.md`, `AUDIT.md`

### Détails par dossier

- `app/`
  - `config.py`: settings Pydantic v2 (env). OK
  - `db.py`: session SQLAlchemy + `engine`. OK
  - `models.py`: modèle `Review` + contraintes/index. OK (UNIQUE `review_id`)
  - `selectors.py`: sélecteurs Amazon centralisés. OK
  - `normalize.py`: normalisations (rating, dates, etc.). OK
  - `utils.py`: helpers (sleep, UA/proxy pools, parsing URL). OK
  - `fetch.py`: Playwright fetcher (profil persistant/fallback). OK
  - `parser.py`: extraction avis robuste; ID Amazon prioritaire, fallback SHA1. OK
  - `scrape.py`: orchestration; pagination Next + fallback URL; dédup DB; compteurs.
  - `cli.py`: commandes `crawl`, `crawl_batch`, `export`, `auth_login`, `dedupe`. OK

- `scripts/`
  - `init_db.sql` (schéma), `examples_asins.txt`, `test_asins.txt`, `run_integration_tests.py`. OK

- `tests/`
  - couverture basique: models/normalize/parser/utils/integration. OK

### Éléments volumineux / générés

- `pw_profile/`: profil Chromium Playwright. À exclure en git (si pas déjà) → .gitignore.
- `reviews.db`: base de test locale. À exclure du versioning.
- `debug/last_page.*`: pour diagnostic; à conserver localement, exclure en git.
- `htmlcov/`: rapport coverage; à générer à la demande, exclure en git.

### Doublons / redondances

- Fichiers HTML Amazon d’exemple (2 variantes d’encodage) à la racine:
  - `Amazon.fr _Commentaires en ligne_ ... Brevetées - ... Conditionné en France.html`
  - `Amazon.fr _Commentaires en ligne_ ... Brevetées - ... Conditionné en France.html`
  - Recommandé: n’en garder qu’un (UTF-8 correct: “Brevetées/Conditionné” sans accents décomposés) et déplacer vers `debug/` ou `fixtures/`.

### Documentation obsolète

- `ROADMAP.md`: existe mais contenu minimal. Mettre à jour (ou intégrer dans `README.md` + section “Roadmap”).
- `README.md`: OK mais ajouter consignes Streamlit Cloud et limites Playwright.

### Recommandations

1. Ignorer en VCS
   - Ajouter/compléter `.gitignore` pour: `venv/`, `reviews.db`, `pw_profile/`, `debug/`, `htmlcov/`, `streamlit.log`.
2. Déplacer les fixtures HTML
   - Créer `fixtures/` et y déplacer 1 seul fichier HTML d’exemple (UTF-8). Supprimer le doublon.
3. Documentation
   - Mettre à jour `README.md`: déploiement GitHub + Streamlit Cloud (Option A/B), variables d’env, limites scraping.
   - Étendre `ROADMAP.md` (ou fusionner dans README).
4. Maintenance
   - Conserver `cli.py dedupe` pour nettoyage ponctuel.
   - Sur Streamlit, préférer purge ASIN avant run si pas d’historique désiré.

### Commandes utiles

```bash
# Nettoyage doublons
python -m app.cli dedupe --dry-run
python -m app.cli dedupe --apply

# Purge ASIN via UI (checkbox) ou API interne

# Lancement local
streamlit run streamlit_app.py
```

### État global

- Codebase cohérente, pagination renforcée, déduplication bout‑en‑bout, UI clarifiée.
- Actions proposées: .gitignore étendu, consolidation docs, déplacement/choix d’un seul fichier HTML de fixture.


