-- Script d'initialisation de la base de données PostgreSQL
-- Ce script est exécuté automatiquement lors du premier démarrage du conteneur PostgreSQL

-- Création de la base de données (déjà créée par les variables d'environnement)
-- CREATE DATABASE amazon_reviews;

-- Connexion à la base de données
\c amazon_reviews;

-- Création d'un utilisateur dédié (optionnel, déjà créé par les variables d'environnement)
-- CREATE USER scraper WITH PASSWORD 'scraper123';
-- GRANT ALL PRIVILEGES ON DATABASE amazon_reviews TO scraper;

-- Les tables seront créées automatiquement par SQLAlchemy
-- Ce fichier peut être utilisé pour des configurations supplémentaires
