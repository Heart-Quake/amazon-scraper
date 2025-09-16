"""Sélecteurs CSS et XPath centralisés pour le scraping Amazon."""

from typing import Dict


class AmazonSelectors:
    """Sélecteurs centralisés pour les éléments Amazon."""
    
    # Sélecteurs pour les avis
    REVIEW_BLOCK = '[data-hook="review"]'
    REVIEW_TITLE = '[data-hook="review-title"]'
    REVIEW_BODY = '[data-hook="review-body"]'
    REVIEW_RATING = '[data-hook="review-star-rating"]'
    REVIEW_DATE = '[data-hook="review-date"]'
    VERIFIED_BADGE = '[data-hook="avp-badge"]'
    HELPFUL_VOTES = '[data-hook="helpful-vote-statement"]'
    REVIEWER_NAME = '.a-profile-name'
    REVIEWER_VARIANT = '[data-hook="format-strip"]'
    
    # Sélecteurs pour la pagination
    PAGINATION_NEXT = 'li.a-last a'
    PAGINATION_DISABLED = 'li.a-disabled'
    
    # Sélecteurs pour la détection anti-bot
    CAPTCHA_INDICATORS = [
        'captcha',
        'enter the characters you see',
        'saisissez les caractères que vous voyez',
        'robot verification',
        'vérification robot',
        'security check',
        'vérification de sécurité',
    ]
    
    # Sélecteurs pour les erreurs
    ERROR_INDICATORS = [
        'page not found',
        'page non trouvée',
        'product not available',
        'produit non disponible',
        'no reviews',
        'aucun avis',
    ]


class ReviewSelectors:
    """Sélecteurs spécifiques pour l'extraction des avis."""
    
    @staticmethod
    def get_all_selectors() -> Dict[str, str]:
        """Retourne tous les sélecteurs pour les avis."""
        return {
            "block": AmazonSelectors.REVIEW_BLOCK,
            "title": AmazonSelectors.REVIEW_TITLE,
            "body": AmazonSelectors.REVIEW_BODY,
            "rating": AmazonSelectors.REVIEW_RATING,
            "date": AmazonSelectors.REVIEW_DATE,
            "verified": AmazonSelectors.VERIFIED_BADGE,
            "helpful": AmazonSelectors.HELPFUL_VOTES,
            "reviewer": AmazonSelectors.REVIEWER_NAME,
            "variant": AmazonSelectors.REVIEWER_VARIANT,
        }
    
    @staticmethod
    def get_pagination_selectors() -> Dict[str, str]:
        """Retourne les sélecteurs pour la pagination."""
        return {
            "next": AmazonSelectors.PAGINATION_NEXT,
            "disabled": AmazonSelectors.PAGINATION_DISABLED,
        }
    
    @staticmethod
    def get_anti_bot_indicators() -> list:
        """Retourne les indicateurs de détection anti-bot."""
        return AmazonSelectors.CAPTCHA_INDICATORS
    
    @staticmethod
    def get_error_indicators() -> list:
        """Retourne les indicateurs d'erreur."""
        return AmazonSelectors.ERROR_INDICATORS
