# 🛒 Amazon Reviews Scraper

Un scraper d'avis Amazon robuste et configurable avec résilience, rotation de proxies, et export multi-format.

[![CI/CD](https://github.com/your-username/amazon-scraper/workflows/CI/CD%20Pipeline/badge.svg)](https://github.com/your-username/amazon-scraper/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## ⚠️ Avertissement de conformité

**IMPORTANT** : Le scraping peut contrevenir aux Conditions Générales d'Utilisation d'Amazon. Ce projet est fourni à des fins éducatives et de recherche uniquement. L'utilisateur est responsable de l'utilisation conforme et légale de cet outil.

### Bonnes pratiques recommandées :
- Respectez une cadence raisonnable (2-4 secondes entre les requêtes)
- Limitez le nombre de pages par ASIN (5-10 maximum)
- Utilisez des proxies rotatifs pour éviter la détection
- Ne collectez pas de données personnelles non nécessaires
- Respectez les robots.txt et les CGU d'Amazon

## 🚀 Fonctionnalités

- **Scraping robuste** : Gestion des erreurs, retry automatique, détection anti-bot
- **Rotation de proxies** : Support de pools de proxies pour éviter la détection
- **Pagination robuste** : Next + fallback URL si nécessaire, scrape jusqu’à la fin
- **Base de données** : Stockage SQLite (défaut) ou PostgreSQL
- **Export multi-format** : CSV, Parquet, NDJSON
- **CLI ergonomique** : Interface en ligne de commande intuitive
- **Tests complets** : Couverture de tests >90%
- **Docker ready** : Conteneurisation complète
- **CI/CD** : Pipeline d'intégration continue

## 📋 Prérequis

- Python 3.11+
- Playwright (navigateurs installés automatiquement)
- Base de données SQLite (incluse) ou PostgreSQL (optionnel)

## 🛠️ Installation

### Installation locale

1. **Cloner le repository**
```bash
git clone https://github.com/your-username/amazon-scraper.git
cd amazon-scraper
```

2. **Créer l'environnement virtuel**
```bash
make venv
# ou
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. **Installer les dépendances**
```bash
make dev
# ou
pip install -r requirements.txt
python -m playwright install chromium
```

4. **Configuration**
```bash
cp env.example .env
# Éditer .env selon vos besoins
```

### Installation avec Docker

1. **Construction de l'image**
```bash
make docker-build
# ou
docker build -t amazon-scraper .
```

2. **Lancement avec docker-compose (recommandé)**
```bash
make docker-compose-up
# ou
docker-compose up -d
```

## ⚙️ Configuration

### Variables d'environnement (.env)

```bash
# Proxies (optionnel)
PROXY_POOL=http://user:pass@proxy1:8000,http://user:pass@proxy2:8000

# Navigateur
HEADLESS=true
TIMEOUT_MS=45000
MAX_CONTEXTS=2

# Scraping
MAX_PAGES_PER_ASIN=5
SLEEP_MIN=2.0
SLEEP_MAX=4.0
LANGUAGE=fr_FR
SORT=recent

# Base de données
DB_URL=sqlite:///./reviews.db
# ou pour PostgreSQL:
# DB_URL=postgresql+psycopg://user:pass@host:5432/dbname
```

### Configuration des proxies

Le scraper supporte la rotation de proxies pour éviter la détection :

```bash
# Format : http://user:pass@host:port
PROXY_POOL=http://user1:pass1@proxy1.example.com:8080,http://user2:pass2@proxy2.example.com:8080
```

## 🎯 Utilisation

### Interface en ligne de commande

#### Scraping d'un ASIN unique
```bash
# Scraping basique
python -m app.cli crawl --asin B123456789

# Avec options
python -m app.cli crawl --asin B123456789 --max-pages 10 --verbose

# Avec Makefile
make run ASIN=B123456789
```

#### Scraping en lot
```bash
# Depuis un fichier
python -m app.cli crawl-batch --file scripts/examples_asins.txt --concurrency 2

# Avec Makefile
make run-batch FILE=scripts/examples_asins.txt
```

#### Export des données
```bash
# Export CSV
python -m app.cli export --asin B123456789 --output reviews.csv --format csv

# Export Parquet
python -m app.cli export --asin B123456789 --output reviews.parquet --format parquet

# Export de tous les avis
python -m app.cli export --output all_reviews.csv --format csv

# Avec Makefile
make export ASIN=B123456789 OUTPUT=reviews.csv
```

#### Vérification du système
```bash
# Health check
python -m app.cli health-check

# Avec Makefile
make health
```

### Utilisation programmatique

```python
import asyncio
from app.scrape import AmazonScraper

async def main():
    scraper = AmazonScraper()
    
    # Scraping d'un ASIN
    stats = await scraper.scrape_asin("B123456789", max_pages=5)
    print(f"Récupéré {stats['total_reviews']} avis")
    
    # Récupération des avis
    reviews = scraper.get_reviews_for_asin("B123456789")
    for review in reviews:
        print(f"Rating: {review['rating']}, Auteur: {review['reviewer_name']}")

asyncio.run(main())
```

## 📊 Structure des données

### Modèle de données

Chaque avis contient les champs suivants :

| Champ | Type | Description |
|-------|------|-------------|
| `id` | Integer | ID unique auto-incrémenté |
| `asin` | String(20) | ASIN du produit |
| `review_id` | String(64) | ID unique de l'avis |
| `review_title` | String(500) | Titre de l'avis |
| `review_body` | Text | Corps de l'avis |
| `rating` | Float | Note de 1.0 à 5.0 |
| `review_date` | String(10) | Date au format YYYY-MM-DD |
| `verified_purchase` | Boolean | Achat vérifié |
| `helpful_votes` | Integer | Nombre de votes utiles |
| `reviewer_name` | String(255) | Nom du reviewer |
| `variant` | String(255) | Variante du produit (taille, couleur) |
| `created_at` | DateTime | Date de création en base |
| `updated_at` | DateTime | Date de mise à jour |

### Exemple de données exportées

```csv
asin,review_id,review_title,review_body,rating,review_date,verified_purchase,helpful_votes,reviewer_name,variant
B123456789,R123456789,"Excellent produit","Très satisfait de cet achat",4.5,2024-01-15,true,3,"Jean Dupont","Taille: L, Couleur: Bleu"
B123456789,R987654321,"Bon produit","Correct pour le prix",3.0,2024-01-14,false,1,"Marie Martin",
```

## 🧪 Tests

### Lancement des tests

```bash
# Tests complets avec couverture
make test

# Tests rapides
make test-fast

# Tests spécifiques
pytest tests/test_normalize.py -v
```

### Couverture de code

```bash
# Génération du rapport de couverture
pytest --cov=app --cov-report=html

# Affichage du rapport
open htmlcov/index.html
```

## 🔧 Développement

### Configuration de l'environnement de développement

```bash
# Installation complète
make dev

# Installation des hooks pre-commit
make pre-commit

# Vérifications de qualité
make ci
```

### Commandes de développement

```bash
# Formatage du code
make format

# Vérification du code
make lint

# Vérification des types
make typecheck

# Nettoyage
make clean
```

## 🐳 Docker

### Construction et exécution

```bash
# Construction de l'image
make docker-build

# Exécution simple
make docker-run

# Exécution interactive
make docker-run-interactive

# Avec docker-compose (PostgreSQL inclus)
make docker-compose-up
```

### Services Docker

Le `docker-compose.yml` inclut :
- **amazon-scraper** : Service principal
- **postgres** : Base de données PostgreSQL
- **pgadmin** : Interface d'administration (optionnel)

```bash
# Lancement de tous les services
docker-compose up -d

# Affichage des logs
docker-compose logs -f

# Arrêt des services
docker-compose down
```

## 📁 Structure du projet
## 🔒 Déduplication & intégrité

- Unicité en base par `review_id` (contrainte UNIQUE).
- Priorité aux IDs Amazon (`R...`) extraits du DOM; fallback SHA1(titre+corps) si absent.
- Déduplication en insertion par `review_id` ou par contenu `(asin, review_title, review_body, review_date)`.
- Déduplication de secours côté UI pour l’aperçu et les exports.
- Commande CLI de nettoyage:

```bash
python -m app.cli dedupe --dry-run
python -m app.cli dedupe --apply
```

## ☁️ Déploiement Streamlit Cloud (notes)

- Option fiable: exécuter le scraping ailleurs (VM/Render), utiliser Streamlit Cloud pour l’UI uniquement (base partagée).
- Option expérimentale: tenter Playwright sur Cloud avec `apt.txt` et installation de Chromium (`python -m playwright install chromium`).

## 🗂️ Versionning / fichiers ignorés

Voir `.gitignore` pour ignorer `venv/`, `reviews.db`, `pw_profile/`, `debug/`, `htmlcov/`, `streamlit.log`.

## 🧪 Fixtures

Les fichiers HTML d’exemple se trouvent dans `fixtures/`. Conserver un seul exemplaire UTF‑8.

```
amazon-reviews-scraper/
├── app/                    # Code source principal
│   ├── __init__.py
│   ├── config.py          # Configuration Pydantic
│   ├── db.py              # Base de données SQLAlchemy
│   ├── models.py          # Modèles ORM
│   ├── normalize.py       # Normalisation des données
│   ├── selectors.py       # Sélecteurs CSS/XPath
│   ├── parser.py          # Parser des avis
│   ├── fetch.py           # Gestion des requêtes
│   ├── scrape.py          # Logique de scraping
│   ├── cli.py             # Interface CLI
│   └── utils.py           # Utilitaires
├── tests/                 # Tests unitaires et intégration
│   ├── test_normalize.py
│   ├── test_parser.py
│   ├── test_utils.py
│   ├── test_models.py
│   └── test_integration.py
├── scripts/               # Scripts utilitaires
│   ├── examples_asins.txt
│   └── init_db.sql
├── .github/workflows/     # CI/CD
│   └── ci.yml
├── requirements.txt       # Dépendances Python
├── pyproject.toml        # Configuration des outils
├── Dockerfile            # Image Docker
├── docker-compose.yml    # Services Docker
├── Makefile             # Commandes de développement
└── README.md            # Documentation
```

## 🚨 Gestion des erreurs

### Détection anti-bot

Le scraper détecte automatiquement :
- Pages CAPTCHA
- Vérifications de sécurité
- Trafic inhabituel
- Blocages IP

En cas de détection, le scraper :
1. Change de proxy (si disponible)
2. Change de User-Agent
3. Attend avant de réessayer
4. Augmente progressivement le délai

### Gestion des erreurs

```python
# Exemple de gestion d'erreurs
try:
    stats = await scraper.scrape_asin("B123456789")
    if stats["success"]:
        print(f"Succès: {stats['total_reviews']} avis")
    else:
        print(f"Erreurs: {stats['errors']}")
except Exception as e:
    print(f"Erreur fatale: {e}")
```

## 📈 Performance

### Optimisations

- **Concurrence contrôlée** : Limitation du nombre de contextes simultanés
- **Rotation de proxies** : Évite la détection et les blocages
- **Pagination intelligente** : Arrêt automatique si pas de page suivante
- **Cache de base de données** : Évite les doublons
- **Pauses aléatoires** : Simule un comportement humain

### Monitoring

```bash
# Vérification de l'état
make health

# Logs détaillés
python -m app.cli crawl --asin B123456789 --verbose
```

## 🤝 Contribution

### Workflow de contribution

1. Fork le repository
2. Créer une branche feature (`git checkout -b feature/amazing-feature`)
3. Commit les changements (`git commit -m 'Add amazing feature'`)
4. Push vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrir une Pull Request

### Standards de code

- **Python 3.11+** avec type hints
- **Black** pour le formatage
- **Ruff** pour le linting
- **MyPy** pour la vérification des types
- **Pytest** pour les tests
- **Couverture >90%**

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 🙏 Remerciements

- [Playwright](https://playwright.dev/) pour l'automatisation du navigateur
- [SQLAlchemy](https://www.sqlalchemy.org/) pour l'ORM
- [Typer](https://typer.tiangolo.com/) pour l'interface CLI
- [Pydantic](https://pydantic-docs.helpmanual.io/) pour la validation des données

## 📞 Support

- **Issues** : [GitHub Issues](https://github.com/your-username/amazon-scraper/issues)
- **Discussions** : [GitHub Discussions](https://github.com/your-username/amazon-scraper/discussions)
- **Email** : support@amazon-scraper.com

---

**⚠️ Rappel** : Respectez les CGU d'Amazon et utilisez cet outil de manière responsable et légale.
