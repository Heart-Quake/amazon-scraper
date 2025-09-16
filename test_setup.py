#!/usr/bin/env python3
"""
Script de test pour vérifier l'installation et la configuration du projet.
"""

import sys
import subprocess
import importlib
from pathlib import Path


def test_python_version():
    """Test de la version Python."""
    print("🐍 Test de la version Python...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - Version 3.11+ requise")
        return False


def test_imports():
    """Test des imports des modules principaux."""
    print("\n📦 Test des imports...")
    
    modules_to_test = [
        "app",
        "app.config",
        "app.db",
        "app.models",
        "app.normalize",
        "app.selectors",
        "app.parser",
        "app.fetch",
        "app.scrape",
        "app.cli",
        "app.utils",
    ]
    
    success = True
    for module in modules_to_test:
        try:
            importlib.import_module(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            success = False
    
    return success


def test_dependencies():
    """Test des dépendances externes."""
    print("\n🔧 Test des dépendances...")
    
    dependencies = [
        "playwright",
        "tenacity",
        "sqlalchemy",
        "pydantic",
        "typer",
        "pyarrow",
        "rich",
    ]
    
    success = True
    for dep in dependencies:
        try:
            importlib.import_module(dep)
            print(f"✅ {dep}")
        except ImportError as e:
            print(f"❌ {dep}: {e}")
            success = False
    
    return success


def test_database_connection():
    """Test de la connexion à la base de données."""
    print("\n🗄️  Test de la base de données...")
    
    try:
        from app.db import engine
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        print("✅ Connexion à la base de données - OK")
        return True
    except Exception as e:
        print(f"❌ Connexion à la base de données: {e}")
        return False


def test_playwright_installation():
    """Test de l'installation de Playwright."""
    print("\n🎭 Test de Playwright...")
    
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        print("✅ Playwright - OK")
        return True
    except Exception as e:
        print(f"❌ Playwright: {e}")
        print("💡 Essayez: python -m playwright install chromium")
        return False


def test_file_structure():
    """Test de la structure des fichiers."""
    print("\n📁 Test de la structure des fichiers...")
    
    required_files = [
        "app/__init__.py",
        "app/config.py",
        "app/db.py",
        "app/models.py",
        "app/normalize.py",
        "app/selectors.py",
        "app/parser.py",
        "app/fetch.py",
        "app/scrape.py",
        "app/cli.py",
        "app/utils.py",
        "requirements.txt",
        "pyproject.toml",
        "Dockerfile",
        "Makefile",
        "README.md",
    ]
    
    success = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - Manquant")
            success = False
    
    return success


def test_cli_help():
    """Test de l'aide CLI."""
    print("\n🖥️  Test de l'interface CLI...")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "app.cli", "--help"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Interface CLI - OK")
            return True
        else:
            print(f"❌ Interface CLI: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Interface CLI: {e}")
        return False


def main():
    """Fonction principale de test."""
    print("🧪 Test de configuration du projet Amazon Scraper")
    print("=" * 60)
    
    tests = [
        ("Version Python", test_python_version),
        ("Structure des fichiers", test_file_structure),
        ("Imports des modules", test_imports),
        ("Dépendances externes", test_dependencies),
        ("Base de données", test_database_connection),
        ("Playwright", test_playwright_installation),
        ("Interface CLI", test_cli_help),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}: Erreur inattendue - {e}")
            results.append((test_name, False))
    
    # Résumé
    print("\n" + "=" * 60)
    print("📊 Résumé des tests:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Résultat: {passed}/{total} tests réussis")
    
    if passed == total:
        print("🎉 Tous les tests sont passés! Le projet est prêt à être utilisé.")
        print("\n💡 Commandes utiles:")
        print("  - make dev          # Installation complète")
        print("  - make test         # Lancement des tests")
        print("  - make run ASIN=... # Scraping d'un ASIN")
        print("  - python demo.py    # Démonstration")
        return 0
    else:
        print("⚠️  Certains tests ont échoué. Vérifiez les erreurs ci-dessus.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
