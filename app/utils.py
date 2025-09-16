"""Utilitaires pour le scraper Amazon."""

import asyncio
import logging
import random
import time
from typing import List, Optional, Tuple, Dict
from urllib.parse import urlparse, parse_qs

from app.config import settings

logger = logging.getLogger(__name__)


MOBILE_USER_AGENTS = [
    # iPhone Safari
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    # Android Chrome
    "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36",
]


class UserAgentPool:
    """Pool de User-Agents pour la rotation."""
    
    def __init__(self, user_agents: Optional[List[str]] = None, mobile_user_agents: Optional[List[str]] = None):
        """Initialise le pool avec la liste de User-Agents."""
        self.user_agents = user_agents or settings.user_agents
        self.mobile_user_agents = mobile_user_agents or MOBILE_USER_AGENTS
        self.current_index = 0
    
    def get_random_ua(self) -> str:
        """Retourne un User-Agent aléatoire."""
        return random.choice(self.user_agents)
    
    def get_next_ua(self) -> str:
        """Retourne le prochain User-Agent dans l'ordre cyclique."""
        ua = self.user_agents[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.user_agents)
        return ua

    def get_random_mobile_ua(self) -> str:
        """Retourne un User-Agent mobile aléatoire."""
        if not self.mobile_user_agents:
            return self.get_random_ua()
        return random.choice(self.mobile_user_agents)


class ProxyPool:
    """Pool de proxies pour la rotation."""
    
    def __init__(self, proxies: Optional[List[str]] = None):
        """Initialise le pool avec la liste de proxies."""
        self.proxies = proxies or []
        self.current_index = 0
    
    def get_random_proxy(self) -> Optional[str]:
        """Retourne un proxy aléatoire."""
        if not self.proxies:
            return None
        return random.choice(self.proxies)
    
    def get_next_proxy(self) -> Optional[str]:
        """Retourne le prochain proxy dans l'ordre cyclique."""
        if not self.proxies:
            return None
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy
    
    def has_proxies(self) -> bool:
        """Vérifie si des proxies sont disponibles."""
        return len(self.proxies) > 0


def random_sleep(min_seconds: Optional[float] = None, max_seconds: Optional[float] = None) -> None:
    """
    Effectue une pause aléatoire entre min_seconds et max_seconds.
    
    Args:
        min_seconds: Durée minimale en secondes
        max_seconds: Durée maximale en secondes
    """
    min_sec = min_seconds or settings.sleep_min
    max_sec = max_seconds or settings.sleep_max
    
    if min_sec >= max_sec:
        sleep_time = min_sec
    else:
        sleep_time = random.uniform(min_sec, max_sec)
    
    logger.debug(f"Pause de {sleep_time:.2f} secondes")
    time.sleep(sleep_time)


async def async_random_sleep(min_seconds: Optional[float] = None, max_seconds: Optional[float] = None) -> None:
    """
    Effectue une pause aléatoire asynchrone.
    
    Args:
        min_seconds: Durée minimale en secondes
        max_seconds: Durée maximale en secondes
    """
    min_sec = min_seconds or settings.sleep_min
    max_sec = max_seconds or settings.sleep_max
    
    if min_sec >= max_sec:
        sleep_time = min_sec
    else:
        sleep_time = random.uniform(min_sec, max_sec)
    
    logger.debug(f"Pause asynchrone de {sleep_time:.2f} secondes")
    await asyncio.sleep(sleep_time)


def setup_logging(level: str = "INFO") -> None:
    """
    Configure le logging pour l'application.
    
    Args:
        level: Niveau de logging (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Réduire le niveau de logging pour Playwright
    logging.getLogger("playwright").setLevel(logging.WARNING)


def validate_asin(asin: str) -> bool:
    """
    Valide le format d'un ASIN Amazon.
    
    Args:
        asin: ASIN à valider
        
    Returns:
        True si l'ASIN est valide, False sinon
    """
    if not asin:
        return False
    
    # ASIN Amazon: 10 caractères alphanumériques
    if len(asin) != 10:
        return False
    
    # Vérifier que ce sont des caractères alphanumériques
    return asin.isalnum()


def generate_review_url(
    asin: str,
    page: int = 1,
    *,
    language: Optional[str] = None,
    sort: Optional[str] = None,
    domain: Optional[str] = None,
    reviewer_type: str = "all_reviews",
) -> str:
    """
    Génère l'URL des avis pour un ASIN donné.
    
    Args:
        asin: ASIN du produit
        page: Numéro de page (commence à 1)
        
    Returns:
        URL des avis Amazon
    """
    base_domain = domain or "www.amazon.fr"
    base_url = f"https://{base_domain}/product-reviews"
    params = {
        "reviewerType": reviewer_type,
        "sortBy": sort or settings.sort,
        "filterByStar": "all_stars",
    }
    # Ajouter le filtre de langue seulement si fourni explicitement
    if language:
        params["filterByLanguage"] = language
    
    if page > 1:
        params["pageNumber"] = str(page)
    
    # Construction de l'URL avec paramètres
    param_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{base_url}/{asin}/?{param_string}"


def generate_product_url(asin: str, *, domain: Optional[str] = None) -> str:
    """Génère une URL produit (dp) stable pour warm-up de session."""
    base_domain = domain or "www.amazon.fr"
    return f"https://{base_domain}/dp/{asin}"


def parse_reviews_url(url: str) -> Optional[Dict[str, Optional[str]]]:
    """
    Parse une URL d'avis Amazon et extrait asin, domaine et paramètres utiles.

    Returns dict with keys: asin, domain, language, sort, reviewer_type
    """
    if not url:
        return None
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc or "www.amazon.fr"
        # asin après /product-reviews/{ASIN}
        asin = None
        parts = parsed.path.split("/")
        for i, part in enumerate(parts):
            if part == "product-reviews" and i + 1 < len(parts):
                asin = parts[i + 1]
                break
        qs = parse_qs(parsed.query)
        language = (qs.get("language") or qs.get("languageLocale") or [None])[0]
        sort = (qs.get("sortBy") or [None])[0]
        reviewer_type = (qs.get("reviewerType") or ["all_reviews"])[0]
        return {
            "asin": asin,
            "domain": netloc,
            "language": language,
            "sort": sort,
            "reviewer_type": reviewer_type,
        }
    except Exception:
        return None


def parse_amazon_url(url: str) -> Optional[Dict[str, Optional[str]]]:
    """
    Parse une URL Amazon générique (page produit ou page d'avis).
    - Supporte /product-reviews/{ASIN}
    - Supporte /dp/{ASIN} et /gp/product/{ASIN}
    Retourne: { asin, domain, language, sort, reviewer_type }
    """
    if not url:
        return None
    # Essayer d'abord comme URL d'avis dédiée
    parsed_reviews = parse_reviews_url(url)
    if parsed_reviews and parsed_reviews.get("asin"):
        return parsed_reviews

    try:
        parsed = urlparse(url)
        netloc = parsed.netloc or "www.amazon.fr"
        asin = None
        parts = [p for p in parsed.path.split("/") if p]
        for i, part in enumerate(parts):
            if part == "dp" and i + 1 < len(parts):
                asin = parts[i + 1]
                break
            if part == "gp" and i + 2 < len(parts) and parts[i + 1] == "product":
                asin = parts[i + 2]
                break

        if not asin:
            return None

        qs = parse_qs(parsed.query)
        language = (qs.get("language") or qs.get("languageLocale") or [None])[0]
        return {
            "asin": asin,
            "domain": netloc,
            "language": language,
            "sort": None,
            "reviewer_type": "all_reviews",
        }
    except Exception:
        return None


def detect_anti_bot(page_content: str) -> bool:
    """
    Détecte la présence d'éléments anti-bot dans le contenu de la page.
    
    Args:
        page_content: Contenu HTML de la page
        
    Returns:
        True si des éléments anti-bot sont détectés, False sinon
    """
    if not page_content:
        return False
    
    content_lower = page_content.lower()
    
    # Vérifier les indicateurs de CAPTCHA
    captcha_indicators = [
        "captcha",
        "enter the characters you see",
        "saisissez les caractères que vous voyez",
        "robot verification",
        "vérification robot",
        "security check",
        "vérification de sécurité",
        "unusual traffic",
        "trafic inhabituel",
    ]
    
    return any(indicator in content_lower for indicator in captcha_indicators)


def detect_error_page(page_content: str) -> bool:
    """
    Détecte si la page contient une erreur.
    
    Args:
        page_content: Contenu HTML de la page
        
    Returns:
        True si une erreur est détectée, False sinon
    """
    if not page_content:
        return True
    
    content_lower = page_content.lower()
    
    # Vérifier des indicateurs d'erreur explicites (éviter les faux positifs)
    error_indicators = [
        "page not found",
        "page non trouvée",
        "product not available",
        "produit non disponible",
        "dogs of amazon",
        "désolé! quelque chose s'est mal passé",
        "sorry! something went wrong",
    ]
    
    return any(indicator in content_lower for indicator in error_indicators)


def detect_login_page(page_content: str) -> bool:
    """Détecte une page de connexion Amazon (sign-in)."""
    if not page_content:
        return False
    c = page_content.lower()
    indicators = [
        "connexion amazon",
        "sign-in",
        "authportal",
        "/ap/signin",
        "identifiez-vous",
        "connectez-vous",
    ]
    return any(s in c for s in indicators)
