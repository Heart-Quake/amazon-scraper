"""Tests pour le module de normalisation."""

import pytest

from app.normalize import (
    clean_text,
    extract_review_id_from_url,
    normalize_date_fr,
    normalize_helpful_votes,
    normalize_rating,
    normalize_verified_purchase,
)


class TestNormalizeRating:
    """Tests pour la normalisation des ratings."""
    
    def test_normalize_rating_valid_formats(self):
        """Test avec différents formats de rating valides."""
        test_cases = [
            ("4.0 sur 5 étoiles", 4.0),
            ("4,0 sur 5 étoiles", 4.0),
            ("4 sur 5", 4.0),
            ("4.5", 4.5),
            ("4,5", 4.5),
            ("5", 5.0),
            ("1.0", 1.0),
        ]
        
        for input_text, expected in test_cases:
            result = normalize_rating(input_text)
            assert result == expected, f"Failed for input: {input_text}"
    
    def test_normalize_rating_invalid_formats(self):
        """Test avec des formats de rating invalides."""
        test_cases = [
            "",
            None,
            "invalid text",
            "6.0",  # Hors plage
            "0.5",  # Hors plage
            "sur 5 étoiles",  # Pas de nombre
        ]
        
        for input_text in test_cases:
            result = normalize_rating(input_text)
            assert result is None, f"Should return None for: {input_text}"


class TestNormalizeDateFr:
    """Tests pour la normalisation des dates françaises."""
    
    def test_normalize_date_fr_valid_formats(self):
        """Test avec différents formats de dates françaises valides."""
        test_cases = [
            ("le 15 janvier 2024", "2024-01-15"),
            ("15 janvier 2024", "2024-01-15"),
            ("le 1er février 2024", "2024-02-01"),
            ("1er février 2024", "2024-02-01"),
            ("15/01/2024", "2024-01-15"),
            ("1/12/2024", "2024-12-01"),
            ("2024-01-15", "2024-01-15"),
        ]
        
        for input_text, expected in test_cases:
            result = normalize_date_fr(input_text)
            assert result == expected, f"Failed for input: {input_text}"
    
    def test_normalize_date_fr_invalid_formats(self):
        """Test avec des formats de dates invalides."""
        test_cases = [
            "",
            None,
            "invalid date",
            "15 invalid 2024",
            "32 janvier 2024",  # Jour invalide
            "15 janvier 13",  # Année invalide
        ]
        
        for input_text in test_cases:
            result = normalize_date_fr(input_text)
            assert result is None, f"Should return None for: {input_text}"


class TestNormalizeHelpfulVotes:
    """Tests pour la normalisation des votes utiles."""
    
    def test_normalize_helpful_votes_valid_formats(self):
        """Test avec différents formats de votes valides."""
        test_cases = [
            ("3 personnes ont trouvé cela utile", 3),
            ("1 personne a trouvé cela utile", 1),
            ("3 people found this helpful", 3),
            ("3 utile", 3),
            ("3", 3),
            ("0", 0),
        ]
        
        for input_text, expected in test_cases:
            result = normalize_helpful_votes(input_text)
            assert result == expected, f"Failed for input: {input_text}"
    
    def test_normalize_helpful_votes_invalid_formats(self):
        """Test avec des formats de votes invalides."""
        test_cases = [
            "",
            None,
            "invalid text",
            "aucun vote",
            "no votes",
        ]
        
        for input_text in test_cases:
            result = normalize_helpful_votes(input_text)
            assert result == 0, f"Should return 0 for: {input_text}"


class TestNormalizeVerifiedPurchase:
    """Tests pour la détection d'achat vérifié."""
    
    def test_normalize_verified_purchase_positive_cases(self):
        """Test avec des indicateurs d'achat vérifié."""
        test_cases = [
            "Achat vérifié",
            "Verified Purchase",
            "vérifié",
            "verified",
            "ACHAT VÉRIFIÉ",
        ]
        
        for input_text in test_cases:
            result = normalize_verified_purchase(input_text)
            assert result is True, f"Should return True for: {input_text}"
    
    def test_normalize_verified_purchase_negative_cases(self):
        """Test avec des cas non vérifiés."""
        test_cases = [
            "",
            None,
            "pas vérifié",
            "not verified",
            "autre texte",
        ]
        
        for input_text in test_cases:
            result = normalize_verified_purchase(input_text)
            assert result is False, f"Should return False for: {input_text}"


class TestExtractReviewIdFromUrl:
    """Tests pour l'extraction d'ID d'avis depuis une URL."""
    
    def test_extract_review_id_valid_urls(self):
        """Test avec des URLs valides."""
        test_cases = [
            ("https://www.amazon.fr/reviews/R123456789", "R123456789"),
            ("/reviews/R987654321", "R987654321"),
            ("https://amazon.com/reviews/R111111111", "R111111111"),
        ]
        
        for url, expected in test_cases:
            result = extract_review_id_from_url(url)
            assert result == expected, f"Failed for URL: {url}"
    
    def test_extract_review_id_invalid_urls(self):
        """Test avec des URLs invalides."""
        test_cases = [
            "",
            None,
            "https://www.amazon.fr/product/123",
            "https://www.google.com",
            "invalid url",
        ]
        
        for url in test_cases:
            result = extract_review_id_from_url(url)
            assert result is None, f"Should return None for: {url}"


class TestCleanText:
    """Tests pour le nettoyage de texte."""
    
    def test_clean_text_normal_cases(self):
        """Test avec des cas normaux."""
        test_cases = [
            ("  hello world  ", "hello world"),
            ("hello\nworld", "hello world"),
            ("hello\tworld", "hello world"),
            ("hello\r\nworld", "hello world"),
            ("", ""),
            (None, ""),
        ]
        
        for input_text, expected in test_cases:
            result = clean_text(input_text)
            assert result == expected, f"Failed for input: {repr(input_text)}"
    
    def test_clean_text_control_characters(self):
        """Test avec des caractères de contrôle."""
        input_text = "hello\x00world\x1f"
        expected = "hello world"
        result = clean_text(input_text)
        assert result == expected
