"""Configuration de la base de données avec SQLAlchemy."""

from sqlalchemy import create_engine, Index
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings

# Création du moteur de base de données
connect_args = {}
if settings.db_url.startswith("sqlite"):
    # Streamlit Cloud exécute dans un environnement multi-threads: nécessaire pour SQLite
    connect_args = {"check_same_thread": False}

engine: Engine = create_engine(
    settings.db_url,
    echo=False,  # Mettre à True pour debug SQL
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args=connect_args,
)

# Factory pour les sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base pour les modèles ORM
Base = declarative_base()


def get_db():
    """Générateur de session de base de données."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Crée toutes les tables dans la base de données."""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Supprime toutes les tables de la base de données."""
    Base.metadata.drop_all(bind=engine)
