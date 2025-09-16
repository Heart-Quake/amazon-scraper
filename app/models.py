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
    verified_purchase = Column(Boolean, default=False)
    helpful_votes = Column(Integer, default=0)
    reviewer_name = Column(String(255), nullable=True)
    variant = Column(String(255), nullable=True)
    
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
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
