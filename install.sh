#!/bin/bash

# Script d'installation pour le scraper Amazon
# Usage: ./install.sh [--dev] [--docker]

set -e

# Couleurs pour l'affichage
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Variables
DEV_MODE=false
DOCKER_MODE=false
PYTHON_CMD="python3"

# Fonction d'aide
show_help() {
    echo "Script d'installation pour Amazon Scraper"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dev     Installation en mode développement"
    echo "  --docker  Installation avec Docker"
    echo "  --help    Affiche cette aide"
    echo ""
    echo "Exemples:"
    echo "  $0                # Installation standard"
    echo "  $0 --dev          # Installation développement"
    echo "  $0 --docker       # Installation Docker"
}

# Parsing des arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            DEV_MODE=true
            shift
            ;;
        --docker)
            DOCKER_MODE=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Option inconnue: $1"
            show_help
            exit 1
            ;;
    esac
done

# Fonction de logging
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérification de Python
check_python() {
    log "Vérification de Python..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        log "Python $PYTHON_VERSION trouvé"
        
        # Vérification de la version
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
            log "Version Python compatible (3.11+)"
        else
            error "Python 3.11+ requis. Version actuelle: $PYTHON_VERSION"
            exit 1
        fi
    else
        error "Python 3 non trouvé. Veuillez installer Python 3.11+"
        exit 1
    fi
}

# Installation des dépendances
install_dependencies() {
    log "Installation des dépendances..."
    
    # Création de l'environnement virtuel
    if [ ! -d "venv" ]; then
        log "Création de l'environnement virtuel..."
        $PYTHON_CMD -m venv venv
    fi
    
    # Activation de l'environnement virtuel
    log "Activation de l'environnement virtuel..."
    source venv/bin/activate
    
    # Mise à jour de pip
    log "Mise à jour de pip..."
    pip install --upgrade pip
    
    # Installation des dépendances
    log "Installation des dépendances Python..."
    pip install -r requirements.txt
    
    # Installation de Playwright
    log "Installation des navigateurs Playwright..."
    python -m playwright install chromium
    python -m playwright install-deps chromium
    
    if [ "$DEV_MODE" = true ]; then
        log "Installation des dépendances de développement..."
        pip install pre-commit
        pre-commit install
    fi
    
    log "Dépendances installées avec succès"
}

# Installation Docker
install_docker() {
    log "Installation avec Docker..."
    
    # Vérification de Docker
    if ! command -v docker &> /dev/null; then
        error "Docker non trouvé. Veuillez installer Docker"
        exit 1
    fi
    
    # Vérification de docker-compose
    if ! command -v docker-compose &> /dev/null; then
        error "docker-compose non trouvé. Veuillez installer docker-compose"
        exit 1
    fi
    
    # Construction de l'image
    log "Construction de l'image Docker..."
    docker build -t amazon-scraper .
    
    # Création des répertoires
    mkdir -p data logs
    
    log "Image Docker construite avec succès"
}

# Configuration
setup_config() {
    log "Configuration du projet..."
    
    # Copie du fichier de configuration
    if [ ! -f ".env" ]; then
        log "Création du fichier de configuration..."
        cp env.example .env
        log "Fichier .env créé. Veuillez le modifier selon vos besoins."
    else
        log "Fichier .env existe déjà"
    fi
    
    # Création des répertoires
    mkdir -p data logs
    
    log "Configuration terminée"
}

# Test de l'installation
test_installation() {
    log "Test de l'installation..."
    
    if [ "$DOCKER_MODE" = false ]; then
        # Test avec Python
        source venv/bin/activate
        python test_setup.py
        
        if [ $? -eq 0 ]; then
            log "Tests d'installation réussis"
        else
            warn "Certains tests ont échoué. Vérifiez la configuration."
        fi
    else
        # Test avec Docker
        log "Test de l'image Docker..."
        docker run --rm amazon-scraper --help
        
        if [ $? -eq 0 ]; then
            log "Image Docker fonctionne correctement"
        else
            error "Problème avec l'image Docker"
            exit 1
        fi
    fi
}

# Affichage des instructions finales
show_final_instructions() {
    echo ""
    echo "🎉 Installation terminée!"
    echo ""
    
    if [ "$DOCKER_MODE" = true ]; then
        echo "🐳 Commandes Docker:"
        echo "  docker run --rm amazon-scraper --help"
        echo "  docker-compose up -d"
        echo "  docker-compose logs -f"
    else
        echo "🐍 Commandes Python:"
        echo "  source venv/bin/activate"
        echo "  python -m app.cli --help"
        echo "  make run ASIN=B123456789"
        echo "  python demo.py"
    fi
    
    echo ""
    echo "📚 Documentation:"
    echo "  - README.md pour la documentation complète"
    echo "  - make help pour toutes les commandes disponibles"
    echo ""
    echo "⚠️  Rappel: Respectez les CGU d'Amazon lors de l'utilisation"
}

# Fonction principale
main() {
    echo "🛒 Amazon Reviews Scraper - Installation"
    echo "========================================"
    
    # Vérifications préliminaires
    check_python
    
    # Installation
    if [ "$DOCKER_MODE" = true ]; then
        install_docker
    else
        install_dependencies
    fi
    
    setup_config
    test_installation
    show_final_instructions
}

# Exécution
main "$@"
