"""Modèles de données SQLAlchemy pour les avis Amazon."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.db import Base


class Review(Base):
    """Modèle pour les avis Amazon."""
    
    __tablename__ = "reviews"
    
    # Clé primaire
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Identifiants
    asin = Column(String(20), nullable=False, index=True)
    review_id = Column(String(64), nullable=False, unique=True, index=True)
    
    # Contenu de l'avis
    review_title = Column(String(500), nullable=True)
    review_body = Column(Text, nullable=True)
    
    # Métadonnées
    rating = Column(Float, nullable=True)
    review_date = Column(String(10), nullable=True)  # Format YYYY-MM-DD
    verified_purchase = Column(Boolean, default=False, nullable=False)
    helpful_votes = Column(Integer, default=0, nullable=False)
    reviewer_name = Column(String(255), nullable=True)
    variant = Column(String(255), nullable=True)
    domain = Column(String(64), nullable=True)
    canonical_product_url = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Index composites pour optimiser les requêtes
    __table_args__ = (
        Index("idx_asin_review_date", "asin", "review_date"),
        Index("idx_asin_rating", "asin", "rating"),
        UniqueConstraint("review_id", name="uq_review_id"),
    )
    
    def __repr__(self) -> str:
        """Représentation string de l'objet Review."""
        return (
            f"<Review(id={self.id}, asin='{self.asin}', "
            f"review_id='{self.review_id}', rating={self.rating})>"
        )
    
    def to_dict(self) -> dict:
        """Convertit l'avis en dictionnaire."""
        return {
            "id": self.id,
            "asin": self.asin,
            "review_id": self.review_id,
            "review_title": self.review_title,
            "review_body": self.review_body,
            "rating": self.rating,
            "review_date": self.review_date,
            "verified_purchase": self.verified_purchase,
            "helpful_votes": self.helpful_votes,
            "reviewer_name": self.reviewer_name,
            "variant": self.variant,
            "domain": self.domain,
            "canonical_product_url": self.canonical_product_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Assure des valeurs Python par défaut dès l'instanciation (hors DB)."""
        verified = kwargs.pop("verified_purchase", None)
        helpful = kwargs.pop("helpful_votes", None)
        super().__init__(*args, **kwargs)
        # Valeurs par défaut côté objet Python
        if verified is None:
            self.verified_purchase = False
        else:
            self.verified_purchase = bool(verified)
        if helpful is None:
            self.helpful_votes = 0
        else:
            try:
                self.helpful_votes = int(helpful)
            except Exception:
                self.helpful_votes = 0
        # Timestamps par défaut immédiats (sinon uniquement définis côté DB)
        if getattr(self, "created_at", None) is None:
            self.created_at = datetime.utcnow()
        if getattr(self, "updated_at", None) is None:
            self.updated_at = datetime.utcnow()
