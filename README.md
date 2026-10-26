# Assistant RAG

> Un système RAG (Retrieval-Augmented Generation) complet, modulaire et documenté.
> Posez des questions sur vos documents, l'assistant répond en se basant uniquement
> sur le contenu indexé.

---

## Table des matières

- [Fonctionnalités](#fonctionnalités)
- [Architecture](#architecture)
- [Stack technique](#stack-technique)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [Structure du projet](#structure-du-projet)
- [Commandes utiles](#commandes-utiles)
- [Tests](#tests)
- [Documentation](#documentation)
- [Roadmap](#roadmap)
- [Licence](#licence)

---

## Fonctionnalités

| Fonctionnalité | Description |
|----------------|-------------|
| **Extraction multi-formats** | PDF, Excel, Word, CSV, TXT, images (OCR) |
| **Recherche sémantique** | Embeddings locaux (all-MiniLM-L6-v2) + pgvector |
| **Reranking** | Cross-encoder BGE pour affiner les résultats |
| **Traduction automatique** | FR → EN avant vectorisation |
| **Interface web** | Django + HTMX + SSE (streaming) |
| **Mémoire conversationnelle** | Contexte conservé entre les échanges |
| **Multi-utilisateurs** | Isolation des conversations par utilisateur |
| **Streaming** | Réponse affichée mot par mot (comme ChatGPT) |

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Django                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  Auth    │  │  Chat    │  │   Admin      │  │
│  └──────────┘  └──────────┘  └──────────────┘  │
│                       │                          │
│                       ▼                          │
│              ┌──────────────────┐               │
│              │  Pipeline RAG    │               │
│              │  (rag/)          │               │
│              └──────────────────┘               │
│                       │                          │
│                       ▼                          │
│              ┌──────────────────┐               │
│              │  PostgreSQL      │               │
│              │  + pgvector      │               │
│              └──────────────────┘               │
└─────────────────────────────────────────────────┘
```

### Flux d'une question

```
Utilisateur → Question (texte/image)
                    │
                    ▼
            ┌───────────────┐
            │  Traduction   │  FR → EN
            └───────┬───────┘
                    │
                    ▼
            ┌───────────────┐
            │  Embedding    │  Question → Vecteur
            └───────┬───────┘
                    │
                    ▼
            ┌───────────────┐
            │  Recherche    │  Similarité cosine
            └───────┬───────┘
                    │
                    ▼
            ┌───────────────┐
            │  Reranking    │  Cross-encoder BGE
            └───────┬───────┘
                    │
                    ▼
            ┌───────────────┐
            │  Prompt       │  Contexte + Question
            └───────┬───────┘
                    │
                    ▼
            ┌───────────────┐
            │  LLM (Groq)   │  Streaming
            └───────┬───────┘
                    │
                    ▼
                Réponse
```

---

## Stack technique

| Composant | Technologie | Version |
|-----------|-------------|---------|
| **Framework web** | Django | 5.0+ |
| **Base de données** | PostgreSQL + pgvector | 16+ |
| **Extraction PDF** | pymupdf + pymupdf4llm | 1.28+ |
| **Extraction Excel** | pandas + openpyxl | 2.0+ |
| **Extraction Word** | python-docx | 1.1+ |
| **Extraction image** | EasyOCR + OpenCV | 1.7+ |
| **Embedding** | sentence-transformers | 2.7+ |
| **Reranking** | BAAI/bge-reranker-base | — |
| **LLM** | Groq (gpt-oss-120b) | — |
| **Interface** | HTMX + SSE | 1.9+ |
| **Tests** | Django TestCase | — |

---

## Installation

### Prérequis

- **Python** 3.10 ou supérieur
- **PostgreSQL** 16 avec l'extension pgvector
- **Docker** (optionnel, pour PostgreSQL)
- **Groq API Key** (gratuite sur [console.groq.com](https://console.groq.com))

### Étapes

```bash
# 1. Cloner le projet
git clone <url-du-repo>
cd projet_rag

# 2. Créer l'environnement virtuel
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer l'environnement
cp .env.example .env
# Éditer .env avec vos valeurs

# 5. Lancer PostgreSQL
docker-compose up -d

# 6. Appliquer les migrations
python manage.py migrate

# 7. Créer un superutilisateur
python manage.py createsuperuser

# 8. Placer vos documents dans books_to_index/
# Ex: books_to_index/mon_livre.pdf

# 9. Indexer les documents
python manage.py index_books

# 10. Lancer le serveur
python manage.py runserver
```

L'application est accessible sur `http://localhost:8000`.

---

## Configuration

### Fichier `.env`

```env
# Django
DJANGO_SECRET_KEY=votre-cle-secrete-ici
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Base de données
DB_NAME=rag_db
DB_USER=rag_user
DB_PASSWORD=rag_password
DB_HOST=localhost
DB_PORT=5432

# Groq
GROQ_API_KEY=gsk_votre_cle_groq

# RAG
RAG_INDEX_PATH=chunks_index_all_3.json
```

### Variables importantes

| Variable | Description | Défaut |
|----------|-------------|--------|
| `DJANGO_SECRET_KEY` | Clé secrète Django | — |
| `DJANGO_DEBUG` | Mode debug | `True` |
| `DJANGO_ALLOWED_HOSTS` | Hôtes autorisés | `localhost,127.0.0.1` |
| `DB_NAME` | Nom de la base | `rag_db` |
| `DB_USER` | Utilisateur PostgreSQL | `rag_user` |
| `DB_PASSWORD` | Mot de passe PostgreSQL | `rag_password` |
| `GROQ_API_KEY` | Clé API Groq | — |
| `RAG_INDEX_PATH` | Chemin de l'index RAG | `chunks_index_all.json` |

---

## Utilisation

### 1. Connexion

Rendez-vous sur `http://localhost:8000/login/` et connectez-vous.

### 2. Nouvelle conversation

Cliquez sur **"+ Nouvelle conversation"** pour démarrer un échange.

### 3. Poser une question

Tapez votre question dans le champ et appuyez sur **Entrée**.

La réponse s'affiche **mot par mot** (streaming).

### 4. Historique

Toutes vos conversations sont sauvegardées. Vous pouvez :
- Les consulter depuis la page d'accueil
- Reprendre une conversation
- Voir les messages précédents

### 5. Questions avec image

Vous pouvez envoyer une image contenant du texte (capture d'écran, photo) :
1. L'OCR extrait le texte de l'image
2. Le texte enrichit la question
3. Le pipeline répond en se basant sur ce contexte

---

## Structure du projet

```
projet_rag/
│
├── config/                     # Configuration Django
│   ├── settings.py             # Paramètres
│   ├── urls.py                 # Routes principales
│   ├── asgi.py
│   └── wsgi.py
│
├── chat/                       # App principale
│   ├── models.py               # Conversation, Message
│   ├── views.py                # Vues (home, chat, streaming)
│   ├── urls.py                 # Routes de l'app
│   ├── admin.py                # Admin Django
│   ├── tests/                  # Tests automatisés
│   │   ├── test_models.py
│   │   └── test_views.py
│   └── templates/
│       └── chat/
│           ├── base.html
│           ├── home.html
│           ├── conversation.html
│           └── partials/
│               └── messages.html
│
├── rag/                        # Pipeline RAG
│   ├── indexation/             # Indexation
│   │   ├── extractor.py
│   │   ├── extractor_pdf.py
│   │   ├── extractor_excel.py
│   │   ├── extractor_word.py
│   │   ├── extractor_csv.py
│   │   ├── extractor_text.py
│   │   ├── splitter.py
│   │   ├── enricher.py
│   │   ├── embedder.py
│   │   └── storage.py
│   ├── recherche/              # Recherche
│   │   ├── translator.py
│   │   ├── reranker.py
│   │   ├── image_extractor.py
│   │   └── prompt_builder.py
│   ├── generation/             # Génération
│   │   └── generator.py
│   ├── conversation.py         # Mémoire conversationnelle
│   ├── resources.py            # Singleton des ressources
│   └── pipeline.py             # Orchestration
│
├── static/                     # Fichiers statiques
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── htmx.min.js
│
├── media/                      # Fichiers uploadés
│
├── books_to_index/             # Documents à indexer
│
├── logs/                       # Fichiers de log
│
├── chunks_index_all.json       # Index vectoriel
├── docker-compose.yml          # Configuration PostgreSQL
├── requirements.txt            # Dépendances
├── .env                        # Variables d'environnement
├── .gitignore
└── README.md                   # Ce fichier
```

---

## Commandes utiles

### Django

```bash
# Lancer le serveur
python manage.py runserver

# Vérifier la configuration
python manage.py check

# Créer un superutilisateur
python manage.py createsuperuser

# Shell interactif
python manage.py shell

# Migrations
python manage.py makemigrations
python manage.py migrate
```

### Indexation

```bash
# Indexer tous les documents de books_to_index/
python manage.py index_books
```

### Tests

```bash
# Lancer tous les tests
python manage.py test

# Lancer un fichier de tests
python manage.py test chat.tests.test_models

# Lancer une classe de tests
python manage.py test chat.tests.test_models.ConversationModelTest

# Avec verbosité
python manage.py test --verbosity=2
```

### Qualité du code

```bash
# Formater le code
black .

# Trier les imports
isort .

# Vérifier le style
flake8 . --max-line-length=100

# Supprimer les imports inutilisés
autoflake --in-place --remove-all-unused-imports --recursive .
```

### Docker

```bash
# Démarrer PostgreSQL
docker-compose up -d

# Voir les logs
docker-compose logs -f

# Arrêter
docker-compose down

# Arrêter et supprimer les volumes
docker-compose down -v
```

---

## Tests

### Lancer les tests

```bash
python manage.py test
```

### Résultat attendu

```
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
........
----------------------------------------------------------------------
Ran 8 tests in 6.194s

OK
Destroying test database for alias 'default'...
```

### Ce qui est testé

| Fichier | Ce qui est testé |
|---------|-----------------|
| `test_models.py` | Création, ordre, isolation des modèles |
| `test_views.py` | Authentification, redirections, isolation |
| `test_pipeline.py` | Pipeline RAG (optionnel) |

---

## Documentation

| Fichier | Contenu |
|---------|---------|
| `README.md` | Vue d'ensemble et installation (ce fichier) |
| `DECISIONS.md` | Journal des décisions techniques |
| `rag/README.md` | Documentation du pipeline RAG |

---

## Roadmap

### Fait

- [x] Pipeline RAG complet (extraction, chunking, embedding, reranking)
- [x] Extraction multi-formats (PDF, Excel, Word, CSV, TXT)
- [x] Extraction d'images (OCR)
- [x] Traduction automatique FR→EN
- [x] Interface Django avec HTMX
- [x] Streaming SSE
- [x] Mémoire conversationnelle
- [x] Tests automatisés

### En cours

- [ ] Logging structuré
- [ ] Configuration de production

### Prévu

- [ ] API FastAPI (pour l'app mobile)
- [ ] Serveur MCP (communication avec services externes)
- [ ] Scraper (récupération de données externes)
- [ ] Déploiement (Docker, Nginx, Gunicorn)
- [ ] Interface mobile (Flutter/React Native)

---

## Contribution

Ce projet est en développement actif. Si vous souhaitez contribuer :

1. Fork le projet
2. Créez une branche (`git checkout -b feature/nouvelle-fonctionnalite`)
3. Committez vos changements (`git commit -m 'Ajout nouvelle fonctionnalité'`)
4. Pushez (`git push origin feature/nouvelle-fonctionnalite`)
5. Ouvrez une Pull Request

---

## Licence

Ce projet est sous licence **MIT**. Voir le fichier [`LICENSE`](LICENSE) pour plus de détails.

La licence MIT permet :
- ✅ Usage commercial
- ✅ Modification
- ✅ Distribution
- ✅ Usage privé

Elle exige :
- 📄 Conservation de la notice de copyright
- 📄 Conservation de la licence

Elle interdit :
- ❌ Toute responsabilité de l'auteur en cas de problème

---

## Auteur

Ce projet a été développé dans le cadre d'un apprentissage approfondi du génie logiciel
et des systèmes RAG.

Pour toute question ou suggestion, ouvrez une [issue](../../issues).

---

## Remerciements

- [Django](https://www.djangoproject.com/) pour le framework web
- [Groq](https://groq.com/) pour l'API LLM gratuite
- [HuggingFace](https://huggingface.co/) pour les modèles d'embedding et de reranking
- [HTMX](https://htmx.org/) pour la simplicité du frontend
- Tous les contributeurs open source dont les bibliothèques ont rendu ce projet possible
```