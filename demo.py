#!/usr/bin/env python3
"""
Script de démonstration pour le scraper Amazon.
Ce script montre comment utiliser le scraper de manière programmatique.
"""

import asyncio
import os
import logging
from pathlib import Path

from app.scrape import AmazonScraper
from app.utils import setup_logging
from app.config import settings
from app.fetch import AmazonFetcher

# Configuration du logging
setup_logging("INFO")
logger = logging.getLogger(__name__)


async def demo_single_asin():
    """Démonstration du scraping d'un ASIN unique."""
    print("🔍 Démonstration: Scraping d'un ASIN unique")
    print("=" * 50)
    
    scraper = AmazonScraper()
    
    # ASIN d'exemple (remplacez par un vrai ASIN)
    asin = "B08N5WRWNW"  # Exemple d'ASIN Amazon
    
    try:
        print(f"Scraping de l'ASIN: {asin}")
        stats = await scraper.scrape_asin(asin, max_pages=2)
        
        print(f"✅ Résultats:")
        print(f"  - Avis récupérés: {stats['total_reviews']}")
        print(f"  - Pages traitées: {stats['total_pages']}")
        print(f"  - Succès: {stats['success']}")
        
        if stats['errors']:
            print(f"  - Erreurs: {len(stats['errors'])}")
            for error in stats['errors']:
                print(f"    • {error}")
        
        # Récupération des avis pour affichage
        reviews = scraper.get_reviews_for_asin(asin, limit=3)
        if reviews:
            print(f"\n📝 Aperçu des avis:")
            for i, review in enumerate(reviews[:3], 1):
                print(f"  {i}. {review.get('review_title', 'Sans titre')}")
                print(f"     Rating: {review.get('rating', 'N/A')}/5")
                print(f"     Auteur: {review.get('reviewer_name', 'Anonyme')}")
                print(f"     Date: {review.get('review_date', 'N/A')}")
                print()
        
    except Exception as e:
        print(f"❌ Erreur lors du scraping: {e}")


async def ensure_amazon_session_for_demo() -> bool:
    """Vérifie/obtient une session Amazon utilisable pour le scraping côté démo.

    - Si un `storage_state.json` existe, on l'utilise tel quel.
    - Sinon, si `AMZ_EMAIL` et `AMZ_PASSWORD` sont définis, tentative de connexion headless
      et sauvegarde de l'état dans `settings.storage_state_path`.
    - Retourne True si une session valide est détectée, False sinon.
    """
    print("\n🔐 Préparation de la session Amazon (démo)")
    print("=" * 50)
    storage_state_path = getattr(settings, "storage_state_path", "./storage_state.json")
    if os.path.exists(storage_state_path):
        print(f"✓ Session existante détectée: {storage_state_path}")
        # Vérifier que la session est encore valide
        fetcher = AmazonFetcher()
        await fetcher.start_browser()
        ctx = await fetcher.create_context()
        ok = await fetcher.is_session_valid(ctx)
        await ctx.close()
        await fetcher.stop_browser()
        if ok:
            print("✓ Session valide")
            return True
        print("⚠️  Session existante invalide — tentative de reconnexion si identifiants fournis")

    email = settings.amz_email
    password = settings.amz_password
    if not email or not password:
        print("ℹ️  Identifiants Amazon non fournis (AMZ_EMAIL/AMZ_PASSWORD). Le scraping tentera sans login.")
        return False

    fetcher = AmazonFetcher()
    # Forcer headless pour robustesse
    try:
        settings.headless = True
    except Exception:
        pass
    await fetcher.start_browser()
    ctx = await fetcher.create_context()
    try:
        await fetcher.ensure_logged_in(ctx)
        ok = await fetcher.is_session_valid(ctx)
        if ok:
            await ctx.storage_state(path=storage_state_path)
            print(f"✓ Session enregistrée: {storage_state_path}")
            return True
        print("❌ Connexion non détectée — captcha/2FA possible.")
        return False
    finally:
        await ctx.close()
        await fetcher.stop_browser()


async def demo_batch_scraping():
    """Démonstration du scraping en lot."""
    print("\n📦 Démonstration: Scraping en lot")
    print("=" * 50)
    
    scraper = AmazonScraper()
    
    # Liste d'ASINs d'exemple
    asins = ["B08N5WRWNW", "B07FZ8S74R"]
    
    try:
        print(f"Scraping de {len(asins)} ASINs")
        results = await scraper.scrape_batch(asins, concurrency=1)
        
        print(f"✅ Résultats du lot:")
        total_reviews = 0
        successful = 0
        
        for result in results:
            status = "✅" if result['success'] else "❌"
            print(f"  {status} {result['asin']}: {result['total_reviews']} avis")
            total_reviews += result['total_reviews']
            if result['success']:
                successful += 1
        
        print(f"\n📊 Résumé global:")
        print(f"  - Total avis: {total_reviews}")
        print(f"  - ASINs réussis: {successful}/{len(asins)}")
        
    except Exception as e:
        print(f"❌ Erreur lors du scraping en lot: {e}")


def demo_export():
    """Démonstration de l'export des données."""
    print("\n📤 Démonstration: Export des données")
    print("=" * 50)
    
    scraper = AmazonScraper()
    
    try:
        # Récupération de tous les avis
        all_reviews = scraper.get_all_reviews(limit=10)
        
        if not all_reviews:
            print("ℹ️  Aucun avis trouvé en base de données")
            return
        
        print(f"📊 {len(all_reviews)} avis trouvés en base")
        
        # Statistiques par ASIN
        asin_stats = {}
        for review in all_reviews:
            asin = review['asin']
            if asin not in asin_stats:
                asin_stats[asin] = {'count': 0, 'avg_rating': 0}
            asin_stats[asin]['count'] += 1
            if review['rating']:
                asin_stats[asin]['avg_rating'] += review['rating']
        
        # Calcul des moyennes
        for asin in asin_stats:
            count = asin_stats[asin]['count']
            asin_stats[asin]['avg_rating'] = asin_stats[asin]['avg_rating'] / count
        
        print(f"\n📈 Statistiques par ASIN:")
        for asin, stats in asin_stats.items():
            print(f"  - {asin}: {stats['count']} avis, rating moyen: {stats['avg_rating']:.1f}/5")
        
        # Exemple d'export CSV
        import csv
        output_file = "demo_export.csv"
        
        if all_reviews:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = all_reviews[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_reviews)
            
            print(f"\n💾 Export CSV créé: {output_file}")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'export: {e}")


def demo_health_check():
    """Démonstration de la vérification du système."""
    print("\n🏥 Démonstration: Vérification du système")
    print("=" * 50)
    
    try:
        # Vérification de la base de données
        from app.db import engine
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        print("✅ Base de données: OK")
    except Exception as e:
        print(f"❌ Base de données: Erreur - {e}")
    
    try:
        # Vérification de Playwright
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        print("✅ Playwright: OK")
    except Exception as e:
        print(f"❌ Playwright: Erreur - {e}")
    
    try:
        # Vérification du réseau
        import requests
        response = requests.get("https://www.amazon.fr", timeout=10)
        if response.status_code == 200:
            print("✅ Réseau: OK")
        else:
            print(f"⚠️  Réseau: Code de statut {response.status_code}")
    except Exception as e:
        print(f"❌ Réseau: Erreur - {e}")


async def main():
    """Fonction principale de démonstration."""
    print("🛒 Amazon Reviews Scraper - Démonstration")
    print("=" * 60)
    print("⚠️  Note: Ceci est une démonstration. Respectez les CGU d'Amazon.")
    print("=" * 60)
    
    # Vérification du système
    demo_health_check()
    
    # Préparer/valider la session Amazon pour fiabiliser les exemples
    try:
        ok_session = await ensure_amazon_session_for_demo()
        if not ok_session:
            print("ℹ️  Poursuite sans session authentifiée (accès limité aux contenus publics).")
    except Exception as e:
        print(f"⚠️  Préparation session ignorée: {e}")
    
    # Démonstrations
    await demo_single_asin()
    await demo_batch_scraping()
    demo_export()
    
    print("\n🎉 Démonstration terminée!")
    print("💡 Pour plus d'informations, consultez le README.md")


if __name__ == "__main__":
    asyncio.run(main())
