"""Tests pour le module utils."""

import pytest

from app.utils import (
    UserAgentPool,
    ProxyPool,
    validate_asin,
    generate_review_url,
    detect_anti_bot,
    detect_error_page,
)


class TestUserAgentPool:
    """Tests pour le pool de User-Agents."""
    
    def test_user_agent_pool_initialization(self):
        """Test de l'initialisation du pool."""
        ua_list = ["UA1", "UA2", "UA3"]
        pool = UserAgentPool(ua_list)
        
        assert pool.user_agents == ua_list
        assert pool.current_index == 0
    
    def test_user_agent_pool_default(self):
        """Test avec les User-Agents par défaut."""
        pool = UserAgentPool()
        
        assert len(pool.user_agents) > 0
        assert all(isinstance(ua, str) for ua in pool.user_agents)
    
    def test_get_random_ua(self):
        """Test de récupération d'un User-Agent aléatoire."""
        ua_list = ["UA1", "UA2", "UA3"]
        pool = UserAgentPool(ua_list)
        
        # Test plusieurs fois pour s'assurer que tous les UAs peuvent être retournés
        results = set()
        for _ in range(100):
            ua = pool.get_random_ua()
            results.add(ua)
        
        assert len(results) > 0
        assert all(ua in ua_list for ua in results)
    
    def test_get_next_ua_cycling(self):
        """Test du cycle des User-Agents."""
        ua_list = ["UA1", "UA2", "UA3"]
        pool = UserAgentPool(ua_list)
        
        # Test du cycle complet
        expected_cycle = ["UA1", "UA2", "UA3", "UA1", "UA2", "UA3"]
        actual_cycle = [pool.get_next_ua() for _ in range(6)]
        
        assert actual_cycle == expected_cycle


class TestProxyPool:
    """Tests pour le pool de proxies."""
    
    def test_proxy_pool_initialization(self):
        """Test de l'initialisation du pool."""
        proxy_list = ["proxy1", "proxy2", "proxy3"]
        pool = ProxyPool(proxy_list)
        
        assert pool.proxies == proxy_list
        assert pool.current_index == 0
    
    def test_proxy_pool_empty(self):
        """Test avec une liste vide de proxies."""
        pool = ProxyPool()
        
        assert pool.proxies == []
        assert pool.current_index == 0
    
    def test_get_random_proxy(self):
        """Test de récupération d'un proxy aléatoire."""
        proxy_list = ["proxy1", "proxy2", "proxy3"]
        pool = ProxyPool(proxy_list)
        
        # Test plusieurs fois
        results = set()
        for _ in range(100):
            proxy = pool.get_random_proxy()
            results.add(proxy)
        
        assert len(results) > 0
        assert all(proxy in proxy_list for proxy in results)
    
    def test_get_random_proxy_empty(self):
        """Test avec un pool vide."""
        pool = ProxyPool()
        
        proxy = pool.get_random_proxy()
        assert proxy is None
    
    def test_get_next_proxy_cycling(self):
        """Test du cycle des proxies."""
        proxy_list = ["proxy1", "proxy2", "proxy3"]
        pool = ProxyPool(proxy_list)
        
        # Test du cycle complet
        expected_cycle = ["proxy1", "proxy2", "proxy3", "proxy1", "proxy2", "proxy3"]
        actual_cycle = [pool.get_next_proxy() for _ in range(6)]
        
        assert actual_cycle == expected_cycle
    
    def test_has_proxies(self):
        """Test de vérification de présence de proxies."""
        # Avec proxies
        pool_with_proxies = ProxyPool(["proxy1", "proxy2"])
        assert pool_with_proxies.has_proxies() is True
        
        # Sans proxies
        pool_without_proxies = ProxyPool()
        assert pool_without_proxies.has_proxies() is False


class TestValidateAsin:
    """Tests pour la validation d'ASIN."""
    
    def test_validate_asin_valid(self):
        """Test avec des ASINs valides."""
        valid_asins = [
            "B123456789",
            "1234567890",
            "ABCDEFGHIJ",
            "B0C1234567",
        ]
        
        for asin in valid_asins:
            assert validate_asin(asin) is True, f"ASIN {asin} should be valid"
    
    def test_validate_asin_invalid(self):
        """Test avec des ASINs invalides."""
        invalid_asins = [
            "",
            None,
            "123456789",  # Trop court
            "12345678901",  # Trop long
            "123456789-",  # Caractère non alphanumérique
            "123456789 ",  # Espace
            "123456789\n",  # Caractère de contrôle
        ]
        
        for asin in invalid_asins:
            assert validate_asin(asin) is False, f"ASIN {repr(asin)} should be invalid"


class TestGenerateReviewUrl:
    """Tests pour la génération d'URLs d'avis."""
    
    def test_generate_review_url_basic(self):
        """Test de génération d'URL de base."""
        asin = "B123456789"
        url = generate_review_url(asin)
        
        assert "amazon.fr" in url
        assert asin in url
        assert "product-reviews" in url
        assert "reviewerType=all_reviews" in url
    
    def test_generate_review_url_with_page(self):
        """Test de génération d'URL avec numéro de page."""
        asin = "B123456789"
        url = generate_review_url(asin, page=3)
        
        assert "pageNumber=3" in url
    
    def test_generate_review_url_page_one(self):
        """Test de génération d'URL pour la page 1."""
        asin = "B123456789"
        url = generate_review_url(asin, page=1)
        
        # La page 1 ne doit pas avoir de paramètre pageNumber
        assert "pageNumber" not in url


class TestDetectAntiBot:
    """Tests pour la détection anti-bot."""
    
    def test_detect_anti_bot_positive_cases(self):
        """Test avec des contenus contenant des éléments anti-bot."""
        positive_cases = [
            "Please complete the captcha",
            "Enter the characters you see",
            "Saisissez les caractères que vous voyez",
            "Robot verification required",
            "Vérification robot",
            "Security check",
            "Vérification de sécurité",
            "Unusual traffic detected",
            "Trafic inhabituel détecté",
        ]
        
        for content in positive_cases:
            assert detect_anti_bot(content) is True, f"Should detect anti-bot in: {content}"
    
    def test_detect_anti_bot_negative_cases(self):
        """Test avec des contenus normaux."""
        negative_cases = [
            "",
            None,
            "Normal page content",
            "Product reviews",
            "Avis produits",
            "Customer feedback",
        ]
        
        for content in negative_cases:
            assert detect_anti_bot(content) is False, f"Should not detect anti-bot in: {content}"
    
    def test_detect_anti_bot_case_insensitive(self):
        """Test de détection insensible à la casse."""
        content = "CAPTCHA REQUIRED"
        assert detect_anti_bot(content) is True


class TestDetectErrorPage:
    """Tests pour la détection de pages d'erreur."""
    
    def test_detect_error_page_positive_cases(self):
        """Test avec des contenus d'erreur."""
        positive_cases = [
            "Page not found",
            "Page non trouvée",
            "Product not available",
            "Produit non disponible",
            "No reviews available",
            "Aucun avis disponible",
            "Error 404",
            "Erreur 500",
        ]
        
        for content in positive_cases:
            assert detect_error_page(content) is True, f"Should detect error in: {content}"
    
    def test_detect_error_page_negative_cases(self):
        """Test avec des contenus normaux."""
        negative_cases = [
            "",
            None,
            "Product reviews",
            "Avis produits",
            "Customer feedback",
            "Normal page content",
        ]
        
        for content in negative_cases:
            assert detect_error_page(content) is False, f"Should not detect error in: {content}"
    
    def test_detect_error_page_case_insensitive(self):
        """Test de détection insensible à la casse."""
        content = "ERROR 404"
        assert detect_error_page(content) is True
