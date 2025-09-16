"""Fonctions de normalisation des données extraites."""

import re
from datetime import datetime
from typing import Optional, Tuple


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
        r"(\d+)",  # "4"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, rating_text)
        if match:
            if len(match.groups()) == 2:
                # Format avec décimales
                whole, decimal = match.groups()
                rating = float(f"{whole}.{decimal}")
            else:
                # Format entier
                rating = float(match.group(1))
            
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
    patterns = [
        r"le\s+(\d{1,2})\s+(\w+)\s+(\d{4})",  # "le 15 janvier 2024"
        r"(\d{1,2})\s+(\w+)\s+(\d{4})",  # "15 janvier 2024"
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
                        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    except ValueError:
                        continue
                elif pattern.endswith(r"-(\d{1,2})"):  # Format YYYY-MM-DD
                    year, month, day = groups
                    try:
                        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    except ValueError:
                        continue
                else:  # Format avec mois en français
                    day, month_fr, year = groups
                    month = months_fr.get(month_fr.lower())
                    if month:
                        try:
                            return f"{year}-{month}-{day.zfill(2)}"
                        except ValueError:
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
    
    verified_indicators = [
        "achat vérifié",
        "verified purchase",
        "vérifié",
        "verified",
    ]
    
    return any(indicator in badge_text.lower() for indicator in verified_indicators)


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
    
    # Supprime les espaces multiples et les caractères de contrôle
    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)
    
    return text
