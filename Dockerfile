# Utiliser une image de base Python slim
FROM python:3.13.1-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Installer les dépendances système nécessaires pour les packages Python
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Mettre à jour pip
RUN pip install --upgrade pip

# Copier le fichier de dépendances Python et installer les dépendances
COPY requirements.txt .
RUN pip install -r requirements.txt

# Exposer le port 5000 pour l'application Flask
EXPOSE 5000

# Définir la variable d'environnement pour Flask
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Démarrer l'application Flask lors du lancement du conteneur
CMD ["flask", "run"]