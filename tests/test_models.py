"""Tests pour les modèles de données."""

import pytest
from datetime import datetime

from app.models import Review


class TestReviewModel:
    """Tests pour le modèle Review."""
    
    def test_review_creation(self):
        """Test de création d'un avis."""
        review = Review(
            asin="B123456789",
            review_id="R123456789",
            review_title="Excellent produit",
            review_body="Très satisfait de cet achat",
            rating=4.5,
            review_date="2024-01-15",
            verified_purchase=True,
            helpful_votes=3,
            reviewer_name="Jean Dupont",
            variant="Taille: L, Couleur: Bleu",
        )
        
        assert review.asin == "B123456789"
        assert review.review_id == "R123456789"
        assert review.review_title == "Excellent produit"
        assert review.review_body == "Très satisfait de cet achat"
        assert review.rating == 4.5
        assert review.review_date == "2024-01-15"
        assert review.verified_purchase is True
        assert review.helpful_votes == 3
        assert review.reviewer_name == "Jean Dupont"
        assert review.variant == "Taille: L, Couleur: Bleu"
    
    def test_review_minimal_creation(self):
        """Test de création d'un avis minimal."""
        review = Review(
            asin="B123456789",
            review_id="R123456789",
        )
        
        assert review.asin == "B123456789"
        assert review.review_id == "R123456789"
        assert review.review_title is None
        assert review.review_body is None
        assert review.rating is None
        assert review.review_date is None
        assert review.verified_purchase is False
        assert review.helpful_votes == 0
        assert review.reviewer_name is None
        assert review.variant is None
    
    def test_review_repr(self):
        """Test de la représentation string de l'avis."""
        review = Review(
            asin="B123456789",
            review_id="R123456789",
            rating=4.5,
        )
        
        repr_str = repr(review)
        assert "Review" in repr_str
        assert "B123456789" in repr_str
        assert "R123456789" in repr_str
        assert "4.5" in repr_str
    
    def test_review_to_dict(self):
        """Test de conversion en dictionnaire."""
        review = Review(
            asin="B123456789",
            review_id="R123456789",
            review_title="Excellent produit",
            review_body="Très satisfait de cet achat",
            rating=4.5,
            review_date="2024-01-15",
            verified_purchase=True,
            helpful_votes=3,
            reviewer_name="Jean Dupont",
            variant="Taille: L, Couleur: Bleu",
        )
        
        # Simuler des timestamps
        review.created_at = datetime(2024, 1, 15, 10, 30, 0)
        review.updated_at = datetime(2024, 1, 15, 10, 30, 0)
        
        data = review.to_dict()
        
        assert data["asin"] == "B123456789"
        assert data["review_id"] == "R123456789"
        assert data["review_title"] == "Excellent produit"
        assert data["review_body"] == "Très satisfait de cet achat"
        assert data["rating"] == 4.5
        assert data["review_date"] == "2024-01-15"
        assert data["verified_purchase"] is True
        assert data["helpful_votes"] == 3
        assert data["reviewer_name"] == "Jean Dupont"
        assert data["variant"] == "Taille: L, Couleur: Bleu"
        assert data["created_at"] == "2024-01-15T10:30:00"
        assert data["updated_at"] == "2024-01-15T10:30:00"
    
    def test_review_to_dict_with_none_timestamps(self):
        """Test de conversion avec des timestamps None."""
        review = Review(
            asin="B123456789",
            review_id="R123456789",
        )
        
        # Timestamps None
        review.created_at = None
        review.updated_at = None
        
        data = review.to_dict()
        
        assert data["created_at"] is None
        assert data["updated_at"] is None
    
    def test_review_default_values(self):
        """Test des valeurs par défaut."""
        review = Review(
            asin="B123456789",
            review_id="R123456789",
        )
        
        assert review.verified_purchase is False
        assert review.helpful_votes == 0
        assert review.created_at is not None  # Auto-généré
        assert review.updated_at is not None  # Auto-généré
