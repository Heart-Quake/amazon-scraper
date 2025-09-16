"""Tests pour le module de parsing."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.parser import ReviewParser


class TestReviewParser:
    """Tests pour le parser d'avis."""
    
    @pytest.fixture
    def parser(self):
        """Fixture pour créer un parser."""
        return ReviewParser()
    
    @pytest.fixture
    def mock_review_element(self):
        """Fixture pour créer un élément d'avis mock."""
        element = AsyncMock()
        
        # Mock des éléments enfants
        title_element = AsyncMock()
        title_element.inner_text.return_value = "Excellent produit"
        element.query_selector.return_value = title_element
        
        return element
    
    @pytest.fixture
    def mock_page(self):
        """Fixture pour créer une page mock."""
        page = AsyncMock()
        page.query_selector_all.return_value = [AsyncMock(), AsyncMock()]
        page.wait_for_selector.return_value = None
        return page
    
    @pytest.mark.asyncio
    async def test_parse_review_block_success(self, parser, mock_review_element):
        """Test du parsing d'un bloc d'avis avec succès."""
        # Mock des éléments de l'avis
        title_element = AsyncMock()
        title_element.inner_text.return_value = "Excellent produit"
        
        body_element = AsyncMock()
        body_element.inner_text.return_value = "Très satisfait de cet achat"
        
        rating_element = AsyncMock()
        rating_element.inner_text.return_value = "4.0 sur 5 étoiles"
        
        date_element = AsyncMock()
        date_element.inner_text.return_value = "le 15 janvier 2024"
        
        verified_element = AsyncMock()
        verified_element.inner_text.return_value = "Achat vérifié"
        
        helpful_element = AsyncMock()
        helpful_element.inner_text.return_value = "3 personnes ont trouvé cela utile"
        
        author_element = AsyncMock()
        author_element.inner_text.return_value = "Jean Dupont"
        
        variant_element = AsyncMock()
        variant_element.inner_text.return_value = "Taille: L, Couleur: Bleu"
        
        # Configuration du mock pour retourner les bons éléments
        async def mock_query_selector(selector):
            selectors_map = {
                '[data-hook="review-title"]': title_element,
                '[data-hook="review-body"]': body_element,
                '[data-hook="review-star-rating"]': rating_element,
                '[data-hook="review-date"]': date_element,
                '[data-hook="avp-badge"]': verified_element,
                '[data-hook="helpful-vote-statement"]': helpful_element,
                '.a-profile-name': author_element,
                '[data-hook="format-strip"]': variant_element,
            }
            return selectors_map.get(selector)
        
        mock_review_element.query_selector = mock_query_selector
        
        # Mock de la page
        mock_page = AsyncMock()
        
        # Test
        result = await parser.parse_review_block(mock_page, mock_review_element)
        
        # Vérifications
        assert result is not None
        assert result["review_title"] == "Excellent produit"
        assert result["review_body"] == "Très satisfait de cet achat"
        assert result["rating"] == 4.0
        assert result["review_date"] == "2024-01-15"
        assert result["verified_purchase"] is True
        assert result["helpful_votes"] == 3
        assert result["reviewer_name"] == "Jean Dupont"
        assert result["variant"] == "Taille: L, Couleur: Bleu"
    
    @pytest.mark.asyncio
    async def test_parse_review_block_missing_elements(self, parser, mock_review_element):
        """Test du parsing avec des éléments manquants."""
        # Mock pour retourner None pour tous les sélecteurs
        mock_review_element.query_selector.return_value = None
        
        mock_page = AsyncMock()
        
        # Test
        result = await parser.parse_review_block(mock_page, mock_review_element)
        
        # Vérifications - doit retourner None car pas de contenu
        assert result is None
    
    @pytest.mark.asyncio
    async def test_parse_review_block_exception(self, parser, mock_review_element):
        """Test du parsing avec une exception."""
        # Mock pour lever une exception
        mock_review_element.query_selector.side_effect = Exception("Test error")
        
        mock_page = AsyncMock()
        
        # Test
        result = await parser.parse_review_block(mock_page, mock_review_element)
        
        # Vérifications
        assert result is None
    
    @pytest.mark.asyncio
    async def test_parse_reviews_from_page_success(self, parser, mock_page):
        """Test du parsing de tous les avis d'une page."""
        # Mock des éléments d'avis
        mock_review1 = AsyncMock()
        mock_review2 = AsyncMock()
        
        # Configuration des mocks pour les avis
        async def mock_parse_review_block(page, element):
            if element == mock_review1:
                return {
                    "review_title": "Avis 1",
                    "review_body": "Contenu 1",
                    "rating": 4.0,
                    "review_date": "2024-01-15",
                    "verified_purchase": True,
                    "helpful_votes": 2,
                    "reviewer_name": "Auteur 1",
                    "variant": "Variant 1",
                }
            elif element == mock_review2:
                return {
                    "review_title": "Avis 2",
                    "review_body": "Contenu 2",
                    "rating": 5.0,
                    "review_date": "2024-01-16",
                    "verified_purchase": False,
                    "helpful_votes": 0,
                    "reviewer_name": "Auteur 2",
                    "variant": None,
                }
            return None
        
        # Mock de la méthode parse_review_block
        parser.parse_review_block = mock_parse_review_block
        
        # Mock de extract_review_id
        async def mock_extract_review_id(element):
            if element == mock_review1:
                return "review_1"
            elif element == mock_review2:
                return "review_2"
            return None
        
        parser.extract_review_id = mock_extract_review_id
        
        # Test
        result = await parser.parse_reviews_from_page(mock_page)
        
        # Vérifications
        assert len(result) == 2
        assert result[0]["review_id"] == "review_1"
        assert result[1]["review_id"] == "review_2"
    
    @pytest.mark.asyncio
    async def test_parse_reviews_from_page_no_reviews(self, parser, mock_page):
        """Test du parsing d'une page sans avis."""
        # Mock pour retourner une liste vide
        mock_page.query_selector_all.return_value = []
        
        # Test
        result = await parser.parse_reviews_from_page(mock_page)
        
        # Vérifications
        assert result == []
    
    @pytest.mark.asyncio
    async def test_parse_reviews_from_page_exception(self, parser, mock_page):
        """Test du parsing avec une exception."""
        # Mock pour lever une exception
        mock_page.wait_for_selector.side_effect = Exception("Test error")
        
        # Test
        result = await parser.parse_reviews_from_page(mock_page)
        
        # Vérifications
        assert result == []
    
    def test_validate_review_data_valid(self, parser):
        """Test de validation avec des données valides."""
        valid_data = {
            "review_title": "Titre",
            "review_body": "Contenu",
            "rating": 4.0,
        }
        
        result = parser._validate_review_data(valid_data)
        assert result is True
    
    def test_validate_review_data_invalid_rating(self, parser):
        """Test de validation avec un rating invalide."""
        invalid_data = {
            "review_title": "Titre",
            "review_body": "Contenu",
            "rating": 6.0,  # Rating invalide
        }
        
        result = parser._validate_review_data(invalid_data)
        assert result is False
    
    def test_validate_review_data_no_content(self, parser):
        """Test de validation sans contenu."""
        invalid_data = {
            "rating": 4.0,
            # Pas de titre ni de corps
        }
        
        result = parser._validate_review_data(invalid_data)
        assert result is False
