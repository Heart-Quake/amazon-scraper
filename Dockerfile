liore t# Dockerfile pour le scraper Amazon
FROM python:3.11-slim

# Métadonnées
LABEL maintainer="Amazon Scraper Team"
LABEL description="Scraper d'avis Amazon avec résilience et rotation de proxies"

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Installation de Node.js (requis pour Playwright)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Création du répertoire de travail
WORKDIR /app

# Copie des fichiers de dépendances
COPY requirements.txt pyproject.toml ./

# Installation des dépendances Python
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Installation des navigateurs Playwright
RUN playwright install chromium \
    && playwright install-deps chromium

# Copie du code source
COPY app/ ./app/
COPY scripts/ ./scripts/

# Création du répertoire pour les données
RUN mkdir -p /app/data

# Utilisateur non-root pour la sécurité
RUN useradd --create-home --shell /bin/bash scraper \
    && chown -R scraper:scraper /app
USER scraper

# Point d'entrée par défaut
ENTRYPOINT ["python", "-m", "app.cli"]

# Commande par défaut
CMD ["--help"]
