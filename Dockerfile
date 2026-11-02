# 1. Image de base légère
FROM python:3.12-slim

# 2. Empêcher Python d'écrire des fichiers .pyc et forcer l'affichage des logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Installer uv et les outils système (curl pour le healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# 4. Définir le répertoire de travail
WORKDIR /app

# 5. Copier UNIQUEMENT les fichiers de dépendances (Optimisation du cache)
# Le projet utilise uv, donc on copie pyproject.toml et uv.lock
COPY pyproject.toml uv.lock ./

# 6. Installer les dépendances dans un environnement virtuel
# --frozen : installe exactement ce qui est dans le lock
# --no-dev : exclut les dépendances de dev (comme pytest)
# On utilise UV_PROJECT_ENVIRONMENT pour forcer uv à utiliser /opt/venv
RUN UV_PROJECT_ENVIRONMENT=/opt/venv uv sync --frozen --no-dev --no-install-project --extra-index-url https://download.pytorch.org/whl/cpu

# 7. Ajouter l'environnement virtuel au PATH
ENV PATH="/opt/venv/bin:$PATH"

# 8. Copier le reste du code source
COPY . .

# 9. Créer un utilisateur non-root pour la sécurité
RUN useradd -m -r appuser && chown -R appuser:appuser /app
USER appuser

# 10. Collecter les fichiers statiques (pour Nginx)
# Note: Il faut que STATIC_ROOT soit défini dans settings.py
RUN python manage.py collectstatic --noinput

# 11. Exposer le port (8000 pour Gunicorn)
EXPOSE 8000

# 12. Lancer le serveur de production (Gunicorn)
# - config.wsgi:application : le point d'entrée de ton projet
# - workers : nombre de processus (2 * nombre de cœurs + 1)
# - bind : écoute sur toutes les interfaces au port 8000
CMD ["gunicorn", "config.wsgi:application", "--workers", "3", "--bind", "0.0.0.0:8000", "--timeout", "120"]