# Makefile pour le scraper Amazon
.PHONY: help venv dev install test lint typecheck format clean run build docker-build docker-run docker-stop

# Variables
PYTHON := python3
PIP := pip
VENV_DIR := venv
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/pip

# Couleurs pour l'affichage
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Affiche l'aide
	@echo "$(GREEN)Amazon Reviews Scraper - Commandes disponibles:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

venv: ## Crée l'environnement virtuel
	@echo "$(GREEN)Création de l'environnement virtuel...$(NC)"
	$(PYTHON) -m venv $(VENV_DIR)
	@echo "$(GREEN)✓ Environnement virtuel créé$(NC)"

dev: venv install playwright-install ## Installe les dépendances de développement
	@echo "$(GREEN)✓ Installation de développement terminée$(NC)"

install: ## Installe les dépendances Python
	@echo "$(GREEN)Installation des dépendances...$(NC)"
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r requirements.txt
	@echo "$(GREEN)✓ Dépendances installées$(NC)"

playwright-install: ## Installe les navigateurs Playwright
	@echo "$(GREEN)Installation des navigateurs Playwright...$(NC)"
	$(VENV_PYTHON) -m playwright install chromium
	$(VENV_PYTHON) -m playwright install-deps chromium
	@echo "$(GREEN)✓ Navigateurs Playwright installés$(NC)"

test: ## Lance les tests
	@echo "$(GREEN)Lancement des tests...$(NC)"
	$(VENV_PYTHON) -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)✓ Tests terminés$(NC)"

test-fast: ## Lance les tests sans couverture
	@echo "$(GREEN)Lancement des tests rapides...$(NC)"
	$(VENV_PYTHON) -m pytest tests/ -v
	@echo "$(GREEN)✓ Tests rapides terminés$(NC)"

lint: ## Vérifie le code avec ruff
	@echo "$(GREEN)Vérification du code avec ruff...$(NC)"
	$(VENV_PYTHON) -m ruff check app/ tests/
	@echo "$(GREEN)✓ Vérification ruff terminée$(NC)"

typecheck: ## Vérifie les types avec mypy
	@echo "$(GREEN)Vérification des types avec mypy...$(NC)"
	$(VENV_PYTHON) -m mypy app/
	@echo "$(GREEN)✓ Vérification mypy terminée$(NC)"

format: ## Formate le code avec black et ruff
	@echo "$(GREEN)Formatage du code...$(NC)"
	$(VENV_PYTHON) -m black app/ tests/
	$(VENV_PYTHON) -m ruff check --fix app/ tests/
	@echo "$(GREEN)✓ Code formaté$(NC)"

clean: ## Nettoie les fichiers temporaires
	@echo "$(GREEN)Nettoyage...$(NC)"
	rm -rf $(VENV_DIR)
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf *.db
	rm -rf data/
	rm -rf logs/
	@echo "$(GREEN)✓ Nettoyage terminé$(NC)"

run: ## Lance le scraper avec un ASIN (usage: make run ASIN=B123456789)
	@if [ -z "$(ASIN)" ]; then \
		echo "$(RED)Erreur: Veuillez spécifier un ASIN avec ASIN=B123456789$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Lancement du scraper pour l'ASIN: $(ASIN)$(NC)"
	$(VENV_PYTHON) -m app.cli crawl --asin $(ASIN)

run-batch: ## Lance le scraper en lot (usage: make run-batch FILE=scripts/examples_asins.txt)
	@if [ -z "$(FILE)" ]; then \
		echo "$(RED)Erreur: Veuillez spécifier un fichier avec FILE=path/to/file.txt$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Lancement du scraper en lot avec le fichier: $(FILE)$(NC)"
	$(VENV_PYTHON) -m app.cli crawl-batch --file $(FILE)

export: ## Exporte les avis (usage: make export ASIN=B123456789 OUTPUT=reviews.csv)
	@if [ -z "$(ASIN)" ]; then \
		echo "$(RED)Erreur: Veuillez spécifier un ASIN avec ASIN=B123456789$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Export des avis pour l'ASIN: $(ASIN)$(NC)"
	$(VENV_PYTHON) -m app.cli export --asin $(ASIN) --output $(OUTPUT)

health: ## Vérifie l'état du système
	@echo "$(GREEN)Vérification de l'état du système...$(NC)"
	$(VENV_PYTHON) -m app.cli health-check

# Commandes Docker
docker-build: ## Construit l'image Docker
	@echo "$(GREEN)Construction de l'image Docker...$(NC)"
	docker build -t amazon-scraper .
	@echo "$(GREEN)✓ Image Docker construite$(NC)"

docker-run: ## Lance le conteneur Docker
	@echo "$(GREEN)Lancement du conteneur Docker...$(NC)"
	docker run --rm -it amazon-scraper

docker-run-interactive: ## Lance le conteneur Docker en mode interactif
	@echo "$(GREEN)Lancement du conteneur Docker en mode interactif...$(NC)"
	docker run --rm -it -v $(PWD)/data:/app/data amazon-scraper bash

docker-compose-up: ## Lance les services avec docker-compose
	@echo "$(GREEN)Lancement des services avec docker-compose...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Services lancés$(NC)"

docker-compose-down: ## Arrête les services docker-compose
	@echo "$(GREEN)Arrêt des services docker-compose...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Services arrêtés$(NC)"

docker-compose-logs: ## Affiche les logs des services
	@echo "$(GREEN)Affichage des logs...$(NC)"
	docker-compose logs -f

# Commandes de développement
pre-commit: ## Installe les hooks pre-commit
	@echo "$(GREEN)Installation des hooks pre-commit...$(NC)"
	$(VENV_PIP) install pre-commit
	$(VENV_PYTHON) -m pre_commit install
	@echo "$(GREEN)✓ Hooks pre-commit installés$(NC)"

ci: lint typecheck test ## Lance toutes les vérifications CI
	@echo "$(GREEN)✓ Toutes les vérifications CI terminées$(NC)"

# Commandes de base de données
db-init: ## Initialise la base de données
	@echo "$(GREEN)Initialisation de la base de données...$(NC)"
	$(VENV_PYTHON) -c "from app.db import create_tables; create_tables(); print('Base de données initialisée')"
	@echo "$(GREEN)✓ Base de données initialisée$(NC)"

db-reset: ## Réinitialise la base de données
	@echo "$(GREEN)Réinitialisation de la base de données...$(NC)"
	$(VENV_PYTHON) -c "from app.db import drop_tables, create_tables; drop_tables(); create_tables(); print('Base de données réinitialisée')"
	@echo "$(GREEN)✓ Base de données réinitialisée$(NC)"

# Aide détaillée
help-detailed: ## Affiche l'aide détaillée
	@echo "$(GREEN)Amazon Reviews Scraper - Aide détaillée$(NC)"
	@echo ""
	@echo "$(YELLOW)Installation et configuration:$(NC)"
	@echo "  make venv          - Crée l'environnement virtuel"
	@echo "  make dev           - Installation complète de développement"
	@echo "  make install       - Installe les dépendances Python"
	@echo "  make playwright-install - Installe les navigateurs Playwright"
	@echo ""
	@echo "$(YELLOW)Tests et qualité:$(NC)"
	@echo "  make test          - Lance tous les tests avec couverture"
	@echo "  make test-fast     - Lance les tests sans couverture"
	@echo "  make lint          - Vérifie le code avec ruff"
	@echo "  make typecheck     - Vérifie les types avec mypy"
	@echo "  make format        - Formate le code"
	@echo "  make ci            - Lance toutes les vérifications"
	@echo ""
	@echo "$(YELLOW)Utilisation:$(NC)"
	@echo "  make run ASIN=B123456789 - Scrape un ASIN spécifique"
	@echo "  make run-batch FILE=file.txt - Scrape plusieurs ASINs"
	@echo "  make export ASIN=B123456789 OUTPUT=reviews.csv - Exporte les avis"
	@echo "  make health        - Vérifie l'état du système"
	@echo ""
	@echo "$(YELLOW)Docker:$(NC)"
	@echo "  make docker-build  - Construit l'image Docker"
	@echo "  make docker-run    - Lance le conteneur"
	@echo "  make docker-compose-up - Lance tous les services"
	@echo ""
	@echo "$(YELLOW)Base de données:$(NC)"
	@echo "  make db-init       - Initialise la base de données"
	@echo "  make db-reset      - Réinitialise la base de données"
	@echo ""
	@echo "$(YELLOW)Nettoyage:$(NC)"
	@echo "  make clean         - Nettoie tous les fichiers temporaires"
