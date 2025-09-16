"""Configuration pytest pour les tests."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from app.db import engine, Base, SessionLocal
from app.config import settings


@pytest.fixture(scope="session")
def test_db_url():
    """URL de base de données de test."""
    return "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_settings(test_db_url):
    """Configuration de test."""
    # Sauvegarde de la configuration originale
    original_db_url = settings.db_url
    
    # Configuration de test
    settings.db_url = test_db_url
    settings.headless = True
    settings.max_pages_per_asin = 1
    settings.sleep_min = 0.1
    settings.sleep_max = 0.2
    
    yield settings
    
    # Restauration de la configuration originale
    settings.db_url = original_db_url


@pytest.fixture(scope="function")
def db_session(test_settings):
    """Session de base de données pour les tests."""
    # Création des tables
    Base.metadata.create_all(bind=engine)
    
    # Création de la session
    session = SessionLocal()
    
    yield session
    
    # Nettoyage
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_playwright_page():
    """Page Playwright mockée pour les tests."""
    page = AsyncMock()
    
    # Mock des méthodes de base
    page.goto = AsyncMock()
    page.content = AsyncMock(return_value="<html><body>Test content</body></html>")
    page.wait_for_selector = AsyncMock()
    page.query_selector = AsyncMock(return_value=None)
    page.query_selector_all = AsyncMock(return_value=[])
    page.close = AsyncMock()
    
    return page


@pytest.fixture
def mock_playwright_browser():
    """Navigateur Playwright mocké pour les tests."""
    browser = AsyncMock()
    context = AsyncMock()
    page = AsyncMock()
    
    # Configuration des mocks
    browser.new_context = AsyncMock(return_value=context)
    context.new_page = AsyncMock(return_value=page)
    browser.close = AsyncMock()
    
    return browser


@pytest.fixture
def mock_playwright():
    """Playwright mocké pour les tests."""
    playwright = AsyncMock()
    browser = AsyncMock()
    
    # Configuration des mocks
    playwright.chromium.launch = AsyncMock(return_value=browser)
    playwright.stop = AsyncMock()
    
    return playwright


@pytest.fixture
def sample_review_data():
    """Données d'avis d'exemple pour les tests."""
    return {
        "asin": "B123456789",
        "review_id": "R123456789",
        "review_title": "Excellent produit",
        "review_body": "Très satisfait de cet achat",
        "rating": 4.5,
        "review_date": "2024-01-15",
        "verified_purchase": True,
        "helpful_votes": 3,
        "reviewer_name": "Jean Dupont",
        "variant": "Taille: L, Couleur: Bleu",
    }


@pytest.fixture
def sample_reviews_data():
    """Liste de données d'avis d'exemple pour les tests."""
    return [
        {
            "asin": "B123456789",
            "review_id": "R123456789",
            "review_title": "Excellent produit",
            "review_body": "Très satisfait de cet achat",
            "rating": 4.5,
            "review_date": "2024-01-15",
            "verified_purchase": True,
            "helpful_votes": 3,
            "reviewer_name": "Jean Dupont",
            "variant": "Taille: L, Couleur: Bleu",
        },
        {
            "asin": "B123456789",
            "review_id": "R987654321",
            "review_title": "Bon produit",
            "review_body": "Correct pour le prix",
            "rating": 3.0,
            "review_date": "2024-01-14",
            "verified_purchase": False,
            "helpful_votes": 1,
            "reviewer_name": "Marie Martin",
            "variant": None,
        },
    ]


@pytest.fixture
def temp_file():
    """Fichier temporaire pour les tests."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("B123456789\nB987654321\n")
        temp_path = f.name
    
    yield temp_path
    
    # Nettoyage
    os.unlink(temp_path)


@pytest.fixture
def temp_dir():
    """Répertoire temporaire pour les tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture(autouse=True)
def setup_test_environment(test_settings):
    """Configuration automatique de l'environnement de test."""
    # Configuration des variables d'environnement de test
    os.environ["HEADLESS"] = "true"
    os.environ["MAX_PAGES_PER_ASIN"] = "1"
    os.environ["SLEEP_MIN"] = "0.1"
    os.environ["SLEEP_MAX"] = "0.2"
    
    yield
    
    # Nettoyage des variables d'environnement de test
    for key in ["HEADLESS", "MAX_PAGES_PER_ASIN", "SLEEP_MIN", "SLEEP_MAX"]:
        os.environ.pop(key, None)
