"""Tests d'intégration pour le scraper Amazon."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.scrape import AmazonScraper


class TestAmazonScraperIntegration:
    """Tests d'intégration pour le scraper."""
    
    @pytest.fixture
    def scraper(self):
        """Fixture pour créer un scraper."""
        return AmazonScraper()
    
    @pytest.fixture
    def mock_reviews_data(self):
        """Fixture avec des données d'avis mock."""
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
    
    @pytest.mark.asyncio
    async def test_scrape_asin_success(self, scraper, mock_reviews_data):
        """Test de scraping d'un ASIN avec succès."""
        # Mock du fetcher
        mock_page = AsyncMock()
        scraper.fetcher.fetch_reviews_page = AsyncMock(return_value=mock_page)
        
        # Mock du parser
        scraper.parser.parse_reviews_from_page = AsyncMock(return_value=mock_reviews_data)
        scraper.parser.extract_review_id = AsyncMock(side_effect=lambda x: f"R{hash(str(x))}")
        
        # Mock de la vérification de pagination
        scraper._has_next_page = AsyncMock(return_value=False)
        
        # Mock de la sauvegarde
        scraper._save_reviews = AsyncMock(return_value=2)
        
        # Test
        result = await scraper.scrape_asin("B123456789", max_pages=1)
        
        # Vérifications
        assert result["asin"] == "B123456789"
        assert result["total_reviews"] == 2
        assert result["total_pages"] == 1
        assert result["success"] is True
        assert len(result["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_scrape_asin_no_reviews(self, scraper):
        """Test de scraping d'un ASIN sans avis."""
        # Mock du fetcher
        mock_page = AsyncMock()
        scraper.fetcher.fetch_reviews_page = AsyncMock(return_value=mock_page)
        
        # Mock du parser - aucun avis
        scraper.parser.parse_reviews_from_page = AsyncMock(return_value=[])
        
        # Test
        result = await scraper.scrape_asin("B123456789", max_pages=1)
        
        # Vérifications
        assert result["asin"] == "B123456789"
        assert result["total_reviews"] == 0
        assert result["total_pages"] == 0
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_scrape_asin_fetch_error(self, scraper):
        """Test de scraping avec erreur de récupération."""
        # Mock du fetcher - erreur
        scraper.fetcher.fetch_reviews_page = AsyncMock(return_value=None)
        
        # Test
        result = await scraper.scrape_asin("B123456789", max_pages=1)
        
        # Vérifications
        assert result["asin"] == "B123456789"
        assert result["total_reviews"] == 0
        assert result["total_pages"] == 0
        assert result["success"] is True  # Pas d'erreur fatale
    
    @pytest.mark.asyncio
    async def test_scrape_asin_parser_error(self, scraper):
        """Test de scraping avec erreur de parsing."""
        # Mock du fetcher
        mock_page = AsyncMock()
        scraper.fetcher.fetch_reviews_page = AsyncMock(return_value=mock_page)
        
        # Mock du parser - erreur
        scraper.parser.parse_reviews_from_page = AsyncMock(side_effect=Exception("Parser error"))
        
        # Test
        result = await scraper.scrape_asin("B123456789", max_pages=1)
        
        # Vérifications
        assert result["asin"] == "B123456789"
        assert result["total_reviews"] == 0
        assert result["total_pages"] == 0
        assert result["success"] is True  # Erreur gérée
    
    @pytest.mark.asyncio
    async def test_scrape_batch_success(self, scraper, mock_reviews_data):
        """Test de scraping en lot avec succès."""
        asins = ["B123456789", "B987654321"]
        
        # Mock du scraping individuel
        async def mock_scrape_asin(asin, max_pages=None):
            return {
                "asin": asin,
                "total_reviews": 2,
                "total_pages": 1,
                "errors": [],
                "success": True,
            }
        
        scraper.scrape_asin = mock_scrape_asin
        
        # Test
        results = await scraper.scrape_batch(asins, concurrency=1)
        
        # Vérifications
        assert len(results) == 2
        assert all(r["success"] for r in results)
        assert all(r["total_reviews"] == 2 for r in results)
    
    @pytest.mark.asyncio
    async def test_scrape_batch_with_errors(self, scraper):
        """Test de scraping en lot avec erreurs."""
        asins = ["B123456789", "B987654321"]
        
        # Mock du scraping individuel avec erreur
        async def mock_scrape_asin(asin, max_pages=None):
            if asin == "B123456789":
                return {
                    "asin": asin,
                    "total_reviews": 2,
                    "total_pages": 1,
                    "errors": [],
                    "success": True,
                }
            else:
                raise Exception("Test error")
        
        scraper.scrape_asin = mock_scrape_asin
        
        # Test
        results = await scraper.scrape_batch(asins, concurrency=1)
        
        # Vérifications
        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert "Test error" in results[1]["errors"][0]
    
    def test_get_reviews_for_asin(self, scraper):
        """Test de récupération des avis d'un ASIN."""
        # Mock de la base de données
        with patch('app.scrape.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = iter([mock_db])
            
            # Mock des avis
            mock_review1 = MagicMock()
            mock_review1.to_dict.return_value = {"review_id": "R1", "asin": "B123456789"}
            
            mock_review2 = MagicMock()
            mock_review2.to_dict.return_value = {"review_id": "R2", "asin": "B123456789"}
            
            mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_review1, mock_review2]
            
            # Test
            reviews = scraper.get_reviews_for_asin("B123456789", limit=10)
            
            # Vérifications
            assert len(reviews) == 2
            assert reviews[0]["review_id"] == "R1"
            assert reviews[1]["review_id"] == "R2"
    
    def test_get_all_reviews(self, scraper):
        """Test de récupération de tous les avis."""
        # Mock de la base de données
        with patch('app.scrape.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = iter([mock_db])
            
            # Mock des avis
            mock_review = MagicMock()
            mock_review.to_dict.return_value = {"review_id": "R1", "asin": "B123456789"}
            
            mock_db.query.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_review]
            
            # Test
            reviews = scraper.get_all_reviews(limit=10)
            
            # Vérifications
            assert len(reviews) == 1
            assert reviews[0]["review_id"] == "R1"
    
    @pytest.mark.asyncio
    async def test_has_next_page_true(self, scraper):
        """Test de détection de page suivante."""
        mock_page = AsyncMock()
        
        # Mock des éléments de pagination
        next_button = AsyncMock()
        mock_page.query_selector.return_value = next_button
        
        # Test
        result = await scraper._has_next_page(mock_page)
        
        # Vérifications
        assert result is True
    
    @pytest.mark.asyncio
    async def test_has_next_page_false(self, scraper):
        """Test de détection d'absence de page suivante."""
        mock_page = AsyncMock()
        
        # Mock - pas de bouton suivant
        mock_page.query_selector.return_value = None
        
        # Test
        result = await scraper._has_next_page(mock_page)
        
        # Vérifications
        assert result is False
    
    @pytest.mark.asyncio
    async def test_save_reviews_success(self, scraper, mock_reviews_data):
        """Test de sauvegarde des avis avec succès."""
        # Mock de la base de données
        with patch('app.scrape.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = iter([mock_db])
            
            # Test
            saved_count = await scraper._save_reviews(mock_reviews_data)
            
            # Vérifications
            assert saved_count == 2
            assert mock_db.add.call_count == 2
            assert mock_db.commit.call_count == 2
    
    @pytest.mark.asyncio
    async def test_save_reviews_integrity_error(self, scraper, mock_reviews_data):
        """Test de sauvegarde avec erreur d'intégrité (doublon)."""
        from sqlalchemy.exc import IntegrityError
        
        # Mock de la base de données avec erreur d'intégrité
        with patch('app.scrape.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = iter([mock_db])
            
            # Premier appel réussi, deuxième avec erreur d'intégrité
            mock_db.add.side_effect = [None, IntegrityError("Duplicate key", None, None)]
            
            # Test
            saved_count = await scraper._save_reviews(mock_reviews_data)
            
            # Vérifications
            assert saved_count == 1  # Un seul sauvé
            assert mock_db.rollback.call_count == 1
