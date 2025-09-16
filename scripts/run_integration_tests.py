#!/usr/bin/env python3
"""
Script pour lancer les tests d'intégration avec de vrais ASINs Amazon.
⚠️  Utilisez avec précaution et respectez les CGU d'Amazon.
"""

import asyncio
import logging
import sys
from pathlib import Path

from app.scrape import AmazonScraper
from app.utils import setup_logging

# Configuration du logging
setup_logging("INFO")
logger = logging.getLogger(__name__)


async def test_real_asin(asin: str, max_pages: int = 1):
    """Test avec un vrai ASIN Amazon."""
    print(f"\n🔍 Test avec l'ASIN: {asin}")
    print("-" * 50)
    
    scraper = AmazonScraper()
    
    try:
        # Scraping avec une seule page pour le test
        stats = await scraper.scrape_asin(asin, max_pages=max_pages)
        
        print(f"✅ Résultats:")
        print(f"  - Avis récupérés: {stats['total_reviews']}")
        print(f"  - Pages traitées: {stats['total_pages']}")
        print(f"  - Succès: {stats['success']}")
        
        if stats['errors']:
            print(f"  - Erreurs: {len(stats['errors'])}")
            for error in stats['errors']:
                print(f"    • {error}")
        
        # Affichage des premiers avis
        reviews = scraper.get_reviews_for_asin(asin, limit=3)
        if reviews:
            print(f"\n📝 Aperçu des avis:")
            for i, review in enumerate(reviews[:3], 1):
                print(f"  {i}. {review.get('review_title', 'Sans titre')}")
                print(f"     Rating: {review.get('rating', 'N/A')}/5")
                print(f"     Auteur: {review.get('reviewer_name', 'Anonyme')}")
                print(f"     Date: {review.get('review_date', 'N/A')}")
                print()
        
        return stats['success']
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        return False


async def main():
    """Fonction principale."""
    print("🧪 Tests d'intégration avec de vrais ASINs Amazon")
    print("=" * 60)
    print("⚠️  ATTENTION: Ces tests utilisent de vrais ASINs Amazon.")
    print("⚠️  Respectez les CGU d'Amazon et utilisez avec modération.")
    print("=" * 60)
    
    # ASINs de test (remplacez par de vrais ASINs)
    test_asins = [
        "B08N5WRWNW",  # Exemple d'ASIN
        "B07FZ8S74R",  # Exemple d'ASIN
    ]
    
    print(f"📋 ASINs à tester: {', '.join(test_asins)}")
    
    # Confirmation de l'utilisateur
    response = input("\n❓ Voulez-vous continuer? (y/N): ")
    if response.lower() != 'y':
        print("❌ Test annulé par l'utilisateur")
        return
    
    # Tests
    results = []
    for asin in test_asins:
        success = await test_real_asin(asin, max_pages=1)
        results.append((asin, success))
        
        # Pause entre les tests
        if len(test_asins) > 1:
            print("\n⏳ Pause de 5 secondes avant le prochain test...")
            await asyncio.sleep(5)
    
    # Résumé
    print("\n" + "=" * 60)
    print("📊 Résumé des tests:")
    
    successful = 0
    for asin, success in results:
        status = "✅ SUCCÈS" if success else "❌ ÉCHEC"
        print(f"  {status} {asin}")
        if success:
            successful += 1
    
    print(f"\n🎯 Résultat: {successful}/{len(test_asins)} tests réussis")
    
    if successful == len(test_asins):
        print("🎉 Tous les tests d'intégration sont passés!")
    else:
        print("⚠️  Certains tests ont échoué. Vérifiez la configuration.")
    
    print("\n💡 Pour des tests plus approfondis, utilisez:")
    print("  python -m app.cli crawl --asin B123456789 --max-pages 5")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Test interrompu par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        sys.exit(1)