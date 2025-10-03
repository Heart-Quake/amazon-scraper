## Roadmap et suivi de projet

Ce document suit l’avancement du projet Amazon Reviews Scraper. Il est synchronisé avec la roadmap JSON (`docs/roadmap.json`).

### En cours
- Dédoublonner les avis par `review_id` avant aperçu/export (`ui-dedup-review-id`)
- Barre de progression basée sur le total d’avis entête (`ui-progress-total-header`)
- Afficher et exploiter le total d’avis (entête) dans l’UI (`ui-show-total-reviews-header`)

### A faire
- Parser total d’avis depuis l’entête (multi-sélecteurs, multi-locales) (`parser-total-reviews-header`)
- Tests unitaires: parser total + dédup UI (`tests-unit-parser-dedup`)
- Tests d’intégration: pagination complète + exports (`tests-integration-pagination-export`)
- Charts récap (distribution des notes, timeline) avant export (`ui-charts-before-export`)
- Documentation utilisateur pas-à-pas avec captures Streamlit (`docs-user-guide`)
- CI: lint + tests + build Docker (`ci-cd-basic`)
- Docker: image exécutable avec dépendances Playwright (`docker-image-playwright`)
- Exposer réglages proxy et User-Agent dans l’UI (`ui-proxy-ua-settings`)
- Upsert DB sur `review_id` (éviter erreurs de duplicat) (`db-upsert-review-id`)

### Terminées
- Export du détail de pagination depuis l’UI (`ui-export-pagination-details`)
- Indicateur « Pagination complète » fiable (`ui-pagination-complete-indicator`)
- Tri par sentiment (Positif/Neutre/Négatif) dans l’UI (`ui-sentiment-sorting`)
- Correction TypeError: 'function' object is not iterable (`bugfix-typeerror-description`)
- Augmenter pages max à 100 (UI + config) (`limit-pages-100`)
- Extraction avis + pagination via Playwright (warm-up + next) (`scrape-playwright-core`)
- Auth Amazon (CLI + Streamlit) avec `storage_state.json` (`auth-storage-state`)
- Anti-bot: rotation UA, blocage ressources, cookies régionaux (`antibot-ua-cookies-blocking`)
- Fallback User-Agent mobile si blocage (`fetch-mobile-ua-fallback`)
- Retry/backoff robuste (tenacity) (`retry-backoff`)
- Migration pydantic-settings (`pydantic-settings-migration`)
- Fix conflit tenacity/streamlit dans requirements (`deps-tenacity-fix`)

### Historique
- 2025-10-01: Création du suivi de projet (ROADMAP.md + roadmap.json) et synchronisation avec la todo interne.


