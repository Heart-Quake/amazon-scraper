"""Fonctions de normalisation des données extraites."""

import re
from datetime import datetime
from typing import Optional, Tuple
import hashlib


def normalize_rating(rating_text: str) -> Optional[float]:
    """
    Normalise le texte de rating en nombre flottant.
    
    Args:
        rating_text: Texte contenant le rating (ex: "4.0 sur 5 étoiles")
        
    Returns:
        Rating normalisé (1.0-5.0) ou None si non trouvé
    """
    if not rating_text:
        return None
    
    # Recherche de pattern comme "4.0", "4,0", "4 sur 5"
    patterns = [
        r"(\d+)[.,](\d+)\s*sur\s*5",  # "4.0 sur 5"
        r"(\d+)[.,](\d+)",  # "4.0" ou "4,0"
        r"(\d+)\s*sur\s*5",  # "4 sur 5"
        r"^(?:[1-5](?:[.,]0)?)$",  # entier simple 1..5 ou x.0
    ]
    
    for pattern in patterns:
        match = re.search(pattern, rating_text)
        if match:
            if match.lastindex and match.lastindex == 2:
                # Format avec décimales
                whole, decimal = match.groups()
                rating = float(f"{whole}.{decimal}")
            else:
                # Format entier (pattern 3) ou entier simple (pattern 4)
                # Extraire le premier nombre trouvé
                num = re.search(r"\d+(?:[.,]\d+)?", rating_text)
                if not num:
                    continue
                rating = float(num.group(0).replace(",", "."))
            
            # Validation de la plage
            if 1.0 <= rating <= 5.0:
                return rating
    
    return None


def normalize_date_fr(date_text: str) -> Optional[str]:
    """
    Normalise une date française en format YYYY-MM-DD.
    
    Args:
        date_text: Date en français (ex: "le 15 janvier 2024")
        
    Returns:
        Date normalisée au format YYYY-MM-DD ou None si non trouvé
    """
    if not date_text:
        return None
    
    # Mapping des mois français
    months_fr = {
        "janvier": "01", "février": "02", "fevrier": "02", "mars": "03",
        "avril": "04", "mai": "05", "juin": "06", "juillet": "07",
        "août": "08", "aout": "08", "septembre": "09", "octobre": "10",
        "novembre": "11", "décembre": "12", "decembre": "12"
    }
    
    # Patterns de dates françaises
    # Supporte aussi "1er" pour le jour 1
    patterns = [
        r"le\s+(\d{1,2}|1er)\s+(\w+)\s+(\d{4})",  # "le 15 janvier 2024" ou "le 1er février 2024"
        r"(\d{1,2}|1er)\s+(\w+)\s+(\d{4})",  # "15 janvier 2024" ou "1er février 2024"
        r"(\d{1,2})/(\d{1,2})/(\d{4})",  # "15/01/2024"
        r"(\d{4})-(\d{1,2})-(\d{1,2})",  # "2024-01-15"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, date_text.lower())
        if match:
            groups = match.groups()
            
            if len(groups) == 3:
                if pattern.endswith(r"/(\d{4})"):  # Format DD/MM/YYYY
                    day, month, year = groups
                    try:
                        day_i = int(day)
                        month_i = int(month)
                        year_i = int(year)
                        if 1 <= day_i <= 31 and 1 <= month_i <= 12:
                            return f"{year_i}-{str(month_i).zfill(2)}-{str(day_i).zfill(2)}"
                    except Exception:
                        continue
                elif pattern.endswith(r"-(\d{1,2})"):  # Format YYYY-MM-DD
                    year, month, day = groups
                    try:
                        day_i = int(day)
                        month_i = int(month)
                        year_i = int(year)
                        if 1 <= day_i <= 31 and 1 <= month_i <= 12:
                            return f"{year_i}-{str(month_i).zfill(2)}-{str(day_i).zfill(2)}"
                    except Exception:
                        continue
                else:  # Format avec mois en français
                    day_raw, month_fr, year = groups
                    day = "1" if str(day_raw).lower() == "1er" else str(day_raw)
                    month = months_fr.get(month_fr.lower())
                    if month:
                        try:
                            day_i = int(day)
                            if 1 <= day_i <= 31:
                                return f"{year}-{month}-{str(day_i).zfill(2)}"
                        except Exception:
                            continue
    
    return None


def normalize_helpful_votes(votes_text: str) -> int:
    """
    Normalise le texte de votes utiles en nombre entier.
    
    Args:
        votes_text: Texte contenant les votes (ex: "3 personnes ont trouvé cela utile")
        
    Returns:
        Nombre de votes utiles ou 0 si non trouvé
    """
    if not votes_text:
        return 0
    
    # Recherche de patterns comme "3 personnes", "3 people", "3"
    patterns = [
        r"(\d+)\s+personnes?\s+ont\s+trouvé\s+cela\s+utile",
        r"(\d+)\s+people?\s+found\s+this\s+helpful",
        r"(\d+)\s+utile",
        r"(\d+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, votes_text.lower())
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    
    return 0


def normalize_verified_purchase(badge_text: str) -> bool:
    """
    Détermine si l'achat est vérifié basé sur le texte du badge.
    
    Args:
        badge_text: Texte du badge de vérification
        
    Returns:
        True si achat vérifié, False sinon
    """
    if not badge_text:
        return False
    
    t = badge_text.lower()
    # Négations explicites
    negative = [
        "pas vérifié",
        "not verified",
    ]
    if any(n in t for n in negative):
        return False
    verified_indicators = [
        "achat vérifié",
        "verified purchase",
        " vérifié",
        " verified",
        "vérifié",
        "verified",
    ]
    return any(ind in t for ind in verified_indicators)


def extract_review_id_from_url(url: str) -> Optional[str]:
    """
    Extrait l'ID de l'avis depuis une URL Amazon.
    
    Args:
        url: URL de l'avis Amazon
        
    Returns:
        ID de l'avis ou None si non trouvé
    """
    if not url:
        return None
    
    # Pattern pour extraire l'ID depuis l'URL
    pattern = r"/reviews/([A-Z0-9]+)"
    match = re.search(pattern, url)
    return match.group(1) if match else None


def clean_text(text: str) -> str:
    """
    Nettoie le texte en supprimant les espaces excessifs et caractères indésirables.
    
    Args:
        text: Texte à nettoyer
        
    Returns:
        Texte nettoyé
    """
    if not text:
        return ""
    
    # Remplace les caractères de contrôle par des espaces, puis compacte les espaces
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", text)
    text = re.sub(r"\s+", " ", text.strip())
    return text


def generate_canonical_review_id(title: Optional[str], body: Optional[str]) -> str:
    """Génère un ID déterministe SHA-1 à partir du titre + corps normalisés.
    Retourne une chaîne du type "sha1_<hex>".
    """
    t = clean_text(title or "")
    b = clean_text(body or "")
    blob = (t + "|" + b).encode("utf-8")
    digest = hashlib.sha1(blob).hexdigest()
    return f"sha1_{digest}"


def strip_rating_from_title(text: str) -> str:
    """Retire les mentions de notation (ex: "5,0 sur 5 étoiles", "5 out of 5 stars",
    ainsi que les symboles ★/☆) d'un titre d'avis.
    """
    if not text:
        return ""
    t = text
    # Retirer préfixes FR/EN du type "5,0 sur 5 étoiles" / "5 out of 5 stars"
    patterns = [
        r"^\s*\d+[\.,]?\d*\s*sur\s*5\s*étoiles?\s*[-–—]*\s*",
        r"^\s*\d+[\.,]?\d*\s*out\s*of\s*5\s*stars?\s*[-–—]*\s*",
    ]
    for pat in patterns:
        t = re.sub(pat, "", t, flags=re.IGNORECASE)
    # Retirer les étoiles unicode éventuelles en tête
    t = re.sub(r"^[★☆\s]+", "", t)
    return clean_text(t)
