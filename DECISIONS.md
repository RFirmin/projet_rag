# Journal des décisions techniques — Projet RAG

Ce document retrace les décisions majeures prises tout au long du projet,
avec leur contexte, les alternatives considérées, et les impacts observés.

---

## Phase 1 : Fondations et choix technologiques

### D1 — Refus de LangChain et des frameworks monolithiques
**Date** : Début du projet
**Contexte** : Recherche d'une solution pour construire un RAG avec Django.
Les tutoriels LangChain étaient séduisants mais les dépendances cassaient à chaque mise à jour.
**Décision** : Construire le pipeline avec des briques stables et indépendantes.
**Alternatives** : LangChain, LlamaIndex, ChromaDB.
**Raison** : Les frameworks monolithiques ont des cycles de release trop rapides,
ce qui rend les tutoriels obsolètes en quelques semaines. Les dépendances en cascade
créent des conflits impossibles à résoudre.
**Impact** : Pipeline modulaire, dépendances stables, code maîtrisé de bout en bout.

---

### D2 — Choix de pymupdf pour l'extraction PDF
**Date** : Premières expérimentations
**Contexte** : Besoin d'extraire du texte depuis des PDF volumineux (100 à 500+ pages).
**Décision** : Utiliser pymupdf (fitz).
**Alternatives** : PyPDF2, pdfplumber, pdfminer, unstructured.
**Raison** :
- pymupdf est le plus rapide et le plus fiable pour l'ordre de lecture
- PyPDF2 échoue sur les PDF complexes (colonnes, tableaux)
- pdfplumber est excellent mais plus lent
**Impact** : Extraction fiable, gestion des gros volumes, progression affichée en console.

---

### D3 — Ajout de pymupdf4llm pour le markdown
**Date** : Après échec de `get_text("markdown")`
**Contexte** : La méthode `get_text("markdown")` n'existe pas dans pymupdf standard.
**Décision** : Utiliser pymupdf4llm pour la conversion PDF → Markdown.
**Raison** : Le markdown préserve la structure (titres, listes, tableaux),
ce qui améliore la compréhension du LLM.
**Impact** : Meilleure qualité de chunks, structure préservée.

---

### D4 — Choix de PostgreSQL + pgvector pour le stockage vectoriel
**Date** : Phase de conception
**Contexte** : Besoin d'une base vectorielle pour stocker les embeddings.
**Décision** : Utiliser PostgreSQL avec l'extension pgvector.
**Alternatives** : ChromaDB, Pinecone, Weaviate, Qdrant, FAISS.
**Raison** :
- pgvector vit dans PostgreSQL (pas de serveur supplémentaire)
- Géré par les migrations Django
- Transactionnel, backup standard
- Pas de dépendance externe
**Impact** : Stockage fiable, pas de serveur à maintenir.

---

## Phase 2 : Extraction et découpage

### D5 — Extraction multi-formats (PDF, Excel, Word, CSV, TXT)
**Date** : Après validation du pipeline PDF
**Contexte** : Besoin d'indexer d'autres types de documents.
**Décision** : Créer un extracteur unifié avec dispatch par type de fichier.
**Alternatives** : Convertir manuellement en PDF avant indexation.
**Raison** : Anticiper les besoins futurs (Excel notamment).
**Impact** : `extractor/` avec modules séparés par type.

---

### D6 — Choix de pandas pour Excel
**Date** : Phase multi-formats
**Contexte** : Extraction des données Excel.
**Décision** : Utiliser pandas avec `to_markdown()`.
**Alternatives** : openpyxl brut, xlrd.
**Raison** : pandas est standard, gère les cellules fusionnées, convertit en markdown.
**Impact** : Extraction fiable, nettoyage des colonnes `Unnamed`.

---

### D7 — Gestion des en-têtes fusionnés Excel
**Date** : Tests sur le tableau Canal+
**Contexte** : Les colonnes étaient nommées `Unnamed: 1`, `Unnamed: 3`, etc.
**Décision** : Charger avec `header=1` (deuxième ligne) au lieu de `header=0`.
**Raison** : La première ligne contient des en-têtes fusionnés, la deuxième
contient les vrais noms de colonnes.
**Impact** : Colonnes correctement nommées, extraction propre.

---

### D8 — Découpage par `RecursiveTextSplitter`
**Date** : Phase de chunking
**Contexte** : Besoin de découper le texte en chunks cohérents.
**Décision** : Implémenter un splitter récursif from scratch.
**Alternatives** : LangChain's RecursiveCharacterTextSplitter.
**Raison** : Contrôle total, pas de dépendance, compréhension du fonctionnement.
**Paramètres** :
- PDF/Word : chunk_size=1000, overlap=200
- Excel/CSV : chunk_size=1500, overlap=300
**Impact** : Découpage propre, sémantique préservée, chevauchement efficace.

---

## Phase 3 : Enrichissement

### D9 — Enrichissement avec métadonnées
**Date** : Phase d'enrichissement
**Contexte** : Les chunks bruts manquaient de contexte.
**Décision** : Ajouter des métadonnées (source, page, chapitre, résumé, mots-clés).
**Raison** : Le LLM comprend mieux quand il sait d'où vient le texte.
**Impact** : Meilleure compréhension, sources traçables.

---

### D10 — Enrichissements adaptés au type de fichier
**Date** : Après ajout Excel
**Contexte** : Les enrichissements PDF ne conviennent pas à l'Excel.
**Décision** : Adapter les enrichissements au type :
- PDF : source, page, chapter, summary, keywords
- Excel : source, page, keywords (pas de chapitre)
**Impact** : Pertinence des métadonnées.

---

## Phase 4 : Embedding

### D11 — Choix de all-MiniLM-L6-v2
**Date** : Phase d'embedding
**Contexte** : Besoin d'un modèle d'embedding local, gratuit, rapide.
**Décision** : Utiliser `sentence-transformers/all-MiniLM-L6-v2`.
**Alternatives** : all-mpnet-base-v2 (768 dim), modèles multilingues.
**Raison** :
- 384 dimensions (léger)
- 80 Mo (rapide à charger)
- Excellent rapport qualité/vitesse
- Local (pas d'API)
- Licence Apache 2.0
**Impact** : Embeddings rapides, gratuits, hors ligne.

---

### D12 — Cohérence obligatoire de l'embedder
**Date** : Après question sur les modèles différents
**Règle** : Le modèle d'embedding utilisé à l'indexation doit être
**exactement** celui utilisé pour vectoriser les questions.
**Raison** : Les vecteurs doivent vivre dans le même espace vectoriel.
**Impact** : Si changement d'embedder → réindexation obligatoire.

---

## Phase 5 : Recherche et reranking

### D13 — Choix de BAAI/bge-reranker-base
**Date** : Après tests comparatifs
**Contexte** : Les scores du ms-marco-MiniLM-L-6-v2 étaient négatifs même sur
des questions précises.
**Décision** : Utiliser `BAAI/bge-reranker-base`.
**Alternatives** : ms-marco-MiniLM-L-6-v2, L-12-v2.
**Raison** :
- Scores positifs et cohérents
- Meilleur sur les questions larges
- Multilingue
- Meilleure discrimination
**Impact** : Reranking fiable, scores exploitables.

---

### D14 — Normalisation conditionnelle des scores
**Date** : Après diagnostic du bug des scores à 1.0
**Contexte** : Le BGE retourne des scores dans [0, 1], mais la sigmoïde
les écrasait tous à 1.0.
**Décision** : Détecter automatiquement le type de modèle :
- BGE → pas de transformation
- ms-marco → sigmoïde
**Impact** : Scores exploitables, discrimination réelle.

---

### D15 — Seuil de rerank avec fallback
**Date** : Après tests de seuils
**Décision** : Appliquer un seuil (0.3) avec fallback sur les 3 meilleurs.
**Raison** : Éliminer le bruit sans risquer de perdre le contexte.
**Impact** : Réponses plus propres.

---

## Phase 6 : Traduction

### D16 — Traduction FR→EN avant embedding
**Date** : Après tests multilingues
**Contexte** : Les scores de rerank étaient très faibles sur les questions
en français avec des documents en anglais.
**Décision** : Traduire les questions FR en EN avant la recherche.
**Raison** : Le modèle d'embedding est principalement entraîné sur l'anglais.
**Impact** : Scores ×38 sur les questions FR (0.026 → 0.997).

---

### D17 — Détection automatique de la langue
**Date** : Après ajout traduction
**Décision** : Détecter la langue et ne traduire que si nécessaire.
**Raison** : Éviter de traduire des questions déjà en anglais.
**Impact** : Économie de tokens, rapidité.

---

### D18 — Limite de traduction pour textes longs
**Date** : Après bug de traduction vide
**Contexte** : Le modèle retournait une chaîne vide sur les textes longs.
**Décision** : Limiter à 1000 caractères avant traduction, avec fallback.
**Impact** : Robustesse accrue.

---

## Phase 7 : Génération

### D19 — Choix de Groq comme fournisseur LLM
**Date** : Après échec OpenAI
**Contexte** : Pas de clé OpenAI, besoin d'un LLM gratuit.
**Décision** : Utiliser Groq.
**Alternatives** : OpenAI, HuggingFace, Mistral.
**Raison** :
- Tier gratuit généreux
- API compatible OpenAI
- Rapide (LPU)
- Modèles performants disponibles
**Impact** : Génération gratuite, rapide.

---

### D20 — Fallback multi-modèles
**Date** : Après erreurs 429 (rate limit)
**Décision** : Essayer plusieurs modèles en cascade.
**Ordre** : gpt-oss-120b → gpt-oss-20b → qwen → allam
**Raison** : Chaque modèle a son propre quota.
**Impact** : Robustesse, pas d'interruption.

---

### D21 — max_tokens adapté par modèle
**Date** : Après erreurs OTPM
**Décision** : Configurer max_tokens selon le modèle :
- gpt-oss-120b : 1500
- qwen : 900
- autres : 1024
**Raison** : Éviter l'erreur "Request too large" du tier gratuit.
**Impact** : Pas d'interruption, réponses complètes.

---

### D22 — Nettoyage des balises `<think>`
**Date** : Après observation de Qwen
**Contexte** : Qwen expose son raisonnement interne.
**Décision** : Nettoyer les balises `<think>` avec fallback si non fermées.
**Impact** : Réponses propres, pas de raisonnement visible.

---

## Phase 8 : Prompt

### D23 — Prompt système avec contraintes
**Date** : Phase de génération
**Décision** : Définir des contraintes claires :
- Répondre uniquement avec le contexte
- Ne pas mentionner les noms de fichiers
- Répondre dans la langue de la question
- Être concis
**Impact** : Réponses contrôlées.

---

### D24 — Règle d'agrégation
**Date** : Après problème CRTV
**Contexte** : Le LLM ne citait qu'un seul numéro.
**Décision** : Ajouter une règle d'agrégation explicite.
**Impact** : Amélioration partielle (~50%).

---

### D25 — Génération d'un guide descriptif
**Date** : Solution finale au problème CRTV
**Contexte** : L'agrégation est une tâche algorithmique, pas linguistique.
**Décision** : Générer un fichier texte descriptif à partir du tableau Excel.
**Raison** : Le LLM lit une phrase déjà agrégée au lieu de devoir agréger.
**Impact** : Réponses stables et complètes (3/3 essais concluants).
**Pattern** : Déplacer les tâches structurées du LLM vers le code.

---

## Phase 9 : Architecture

### D26 — Séparation séquentiel / POO
**Date** : Phase de refactoring
**Décision** :
- Fonctions pures → séquentiel (`extract_to_markdown`, `cosine_similarity`)
- État à conserver → POO (`Embedder`, `Reranker`, `PipelineResources`)
**Raison** : Utiliser la POO uniquement quand nécessaire.
**Impact** : Code clair, responsabilités bien définies.

---

### D27 — Singleton PipelineResources
**Date** : Après tests de performance
**Contexte** : Les modèles étaient rechargés à chaque question.
**Décision** : Charger les ressources une seule fois.
**Impact** : Économie de 3-5 secondes par question.

---

### D28 — Structure modulaire `rag/`
**Date** : Refactoring final
**Décision** : Organiser le code en modules par phase :
- `indexation/`
- `recherche/`
- `generation/`
**Raison** : Séparation des responsabilités, maintenabilité.
**Impact** : Code organisé, testable, évolutif.

---

## Phase 10 : Extensions

### D29 — Mémoire conversationnelle
**Date** : Après tests de discussion
**Décision** : Buffer fenêtré (5 tours) avec `ConversationMemory`.
**Raison** : Simple, efficace, suffisant pour des conversations courtes.
**Impact** : Suivi du contexte conversationnel.

---

### D30 — Séparation question / historique
**Date** : Après bug de recherche diluée
**Contexte** : La recherche se faisait sur la question enrichie avec l'historique.
**Décision** : Rechercher sur la question pure, injecter l'historique
uniquement dans le prompt.
**Impact** : Recherche précise, contexte conversationnel préservé.

---

### D31 — Audio en console (SpeechRecognition + pyttsx3)
**Date** : Phase audio
**Décision** :
- `SpeechRecognition` pour voix → texte
- `pyttsx3` 2.91 pour texte → voix
**Raison** : Fonctionnent en local, gratuits.
**Impact** : Assistant vocal fonctionnel.

---

### D32 — Interface Streamlit avec gTTS
**Date** : Après conflit pyttsx3 / Streamlit
**Contexte** : pyttsx3 bloque le thread Streamlit.
**Décision** : Utiliser `gTTS` (Google TTS) au lieu de pyttsx3.
**Raison** : Pas de conflit, qualité audio supérieure.
**Impact** : Interface web fonctionnelle.

---

## Phase 11 : Organisation

### D33 — Documentation systématique
**Date** : Continu
**Décision** : Documenter chaque décision technique.
**Raison** : Mémoire des choix, justification, transmission.
**Impact** : Projet compréhensible dans le temps.

---

### D34 — Méthode Bottom-Up
**Date** : Continu
**Principe** : Tester chaque brique isolément avant de l'intégrer.
**Raison** : Isolation des bugs, compréhension profonde.
**Impact** : Pipeline stable, code maîtrisé.

---

## Résumé des principes directeurs

1. **Briques stables plutôt que frameworks monolithiques**
2. **Tester chaque composant isolément avant de l'intégrer**
3. **Déplacer les tâches structurées du LLM vers le code**
4. **Traduire avant de vectoriser (si langues différentes)**
5. **Charger les ressources une seule fois (singleton)**
6. **Documenter chaque décision technique**
7. **Séparer les responsabilités (modules, classes, fonctions)**
8. **Utiliser la POO quand il y a un état à conserver**


Voici la mise à jour de `DECISIONS.md` avec les décisions récentes (Django, HTMX, SSE, etc.).

---

## `DECISIONS.md` — Mise à jour

Ajoutez ces nouvelles sections à la fin du document existant.

```markdown
---

## Phase 12 : Intégration Django

### D35 — Création d'un nouveau projet Django propre

**Date** : 2026-10-13
**Contexte** : Le pipeline RAG était stable en console. Il fallait l'intégrer
dans une application web complète.
**Décision** : Créer un nouveau projet Django propre plutôt que d'adapter
l'ancien projet Django (qui avait servi aux premiers tests avec LangChain).
**Raison** :
- L'ancien projet contenait du code obsolète (LangChain)
- Un projet neuf part sur des bases saines
- Le pipeline RAG est déjà modulaire, il suffit de le copier
**Impact** : Projet propre, structure claire, pas de dette technique.

---

### D36 — Choix du package local pour le pipeline RAG

**Date** : 2026-10-13
**Contexte** : Comment intégrer le pipeline RAG dans Django ?
**Décision** : Copier `rag/` tel quel dans le projet Django (package local).
**Alternatives** :
- Package installable (`pip install -e ./rag`) → plus complexe
- Sous-module Git → complexe pour un solo dev
- Réécrire dans Django → gaspillage
**Raison** : Le pipeline est déjà un package Python. On le copie, on l'importe.
**Impact** : Le pipeline fonctionne à l'identique, sans modification.

---

### D37 — Modèles `Conversation` et `Message`

**Date** : 2026-10-13
**Contexte** : Besoin de stocker les conversations et messages.
**Décision** :
- `Conversation` : UUID, user (FK), title, timestamps
- `Message` : UUID, conversation (FK), role, content, sources (JSON), timestamp
**Raison** :
- UUID : évite l'énumération des conversations par un attaquant
- `user` FK : isolation par utilisateur
- `role` : distingue user/assistant
- `sources` JSON : stocke les sources sans table supplémentaire
**Impact** : Modèles simples, isolation garantie, extensible.

---

### D38 — Isolation par `user_id` plutôt que `django-tenants`

**Date** : 2026-10-13
**Contexte** : Comment isoler les données entre utilisateurs ?
**Décision** : Filtrage par `user_id` dans les vues.
**Alternatives** : `django-tenants` (schémas PostgreSQL séparés).
**Raison** :
- `django-tenants` est surdimensionné pour un projet multi-utilisateurs simple
- L'authentification Django standard fonctionne directement
- Pas de migrations multiples
- L'isolation par `user_id` est garantie par l'ORM
**Impact** : Simplicité, scalabilité jusqu'à des milliers d'utilisateurs.
**Note** : Si le projet devient un SaaS multi-entreprises, migrer vers
`django-tenants` sera une configuration, pas une refonte.

---

### D39 — Authentification Django standard

**Date** : 2026-10-13
**Contexte** : Besoin d'authentification pour l'accès aux conversations.
**Décision** : Utiliser `django.contrib.auth` avec les vues `LoginView` et
`LogoutView`.
**Raison** :
- Standard, testé, sécurisé
- Gère les sessions, les mots de passe hashés, le CSRF
- Pas de dépendance externe
**Impact** : Authentification robuste en quelques lignes.

---

## Phase 13 : Interface utilisateur

### D40 — Choix de HTMX dès le début

**Date** : 2026-10-13
**Contexte** : Comment construire l'interface de chat ?
**Décision** : Utiliser HTMX dès le départ.
**Alternatives** :
- JavaScript manuel → plus de code, plus de bugs
- React/Vue → surdimensionné pour un chat simple
- Full Django (rechargement) → mauvaise UX
**Raison** :
- Simplicité : ~5 attributs HTML vs ~50 lignes de JS
- Gestion CSRF automatique
- Mise à jour partielle sans rechargement
- Pas de framework JS à apprendre
**Impact** : Interface moderne, code minimal, maintenable.
**Pattern** : La vue retourne un fragment HTML, pas du JSON.

---

### D41 — Structure des templates

**Date** : 2026-10-13
**Contexte** : Comment organiser les templates ?
**Décision** :
```
templates/
├── base.html              # Layout commun
├── home.html              # Liste des conversations
├── conversation.html      # Vue d'une conversation
└── partials/
    └── messages.html      # Fragment réutilisable

**Raison** :
- `base.html` : évite la duplication (header, CSS, HTMX)
- `partials/` : fragments utilisés par HTMX
**Impact** : Réutilisabilité, lisibilité.

---

### D42 — CSS centralisé dans `static/css/style.css`

**Date** : 2026-10-13
**Contexte** : Le CSS était initialement inline dans les templates.
**Décision** : Centraliser tout le CSS dans un seul fichier.
**Raison** :
- Lisibilité : les templates ne sont plus pollués
- Réutilisabilité : une classe définie une fois, utilisée partout
- Cache navigateur : le CSS est téléchargé une seule fois
**Impact** : Templates plus légers, CSS maintenable.

---

### D43 — Utilisation des template filters Django

**Date** : 2026-10-13
**Contexte** : Besoin de formater les données dans les templates.
**Décision** : Utiliser les filtres natifs (`linebreaks`, `date`, `truncatechars`).
**Raison** :
- Évite d'écrire du Python dans les templates
- Standard Django
**Impact** : Templates expressifs, code Python dans les vues uniquement.

---

## Phase 14 : Streaming

### D44 — Choix de SSE pour le streaming

**Date** : 2026-10-14
**Contexte** : Comment afficher la réponse du LLM mot par mot ?
**Décision** : Utiliser SSE (Server-Sent Events).
**Alternatives** :
- WebSockets → bidirectionnel, surdimensionné
- Long polling → inefficace
- Attendre la fin → mauvaise UX
**Raison** :
- SSE est **unidirectionnel** (serveur → client), exactement notre besoin
- Basé sur HTTP, pas de protocole spécial
- Reconnexion automatique gérée par le navigateur
- Standard pour le streaming de LLM
**Impact** : Réponse affichée mot par mot, UX type ChatGPT.

---

### D45 — Désactivation de HTMX pour le streaming

**Date** : 2026-10-14
**Contexte** : HTMX gère les mises à jour simples, mais pas le streaming
temps réel.
**Décision** : Utiliser `fetch` + `ReadableStream` en JavaScript pour le streaming.
**Raison** :
- HTMX SSE est conçu pour des notifications, pas pour un chat
- `fetch` permet un contrôle précis des chunks
- On peut parser les événements SSE manuellement
**Impact** : Deux mécanismes coexistent :
- HTMX pour les mises à jour simples (navigation, liste)
- JS pour le streaming (chat)
**Note** : C'est un compromis. HTMX reste utilisé pour le reste.

---

### D46 — Format des messages SSE

**Date** : 2026-10-14
**Contexte** : Comment structurer les messages SSE ?
**Décision** : Utiliser un format JSON avec un champ `type` :
```json
{"type": "user", "content": "..."}
{"type": "chunk", "content": "..."}
{"type": "done"}
{"type": "error", "content": "..."}
```
**Raison** :
- Le `type` permet de distinguer les événements
- Extensible (on peut ajouter `sources` plus tard)
- Standard JSON
**Impact** : Protocole clair, extensible.

---

### D47 — Nettoyage des balises `<think>` en streaming

**Date** : 2026-10-14
**Contexte** : Certains modèles (Qwen) exposent leur raisonnement interne.
**Décision** : Détecter et filtrer les balises `<think>` en temps réel
dans le générateur.
**Raison** :
- En streaming, on ne peut pas attendre la fin pour nettoyer
- Il faut filtrer au fur et à mesure
**Impact** : L'utilisateur ne voit jamais le raisonnement interne.

---

## Phase 15 : Consolidation

### D48 — Tests automatisés avec Django TestCase

**Date** : 2026-10-14
**Contexte** : Besoin de garantir la stabilité du code.
**Décision** : Écrire des tests pour les modèles et les vues.
**Raison** :
- Détecter les régressions immédiatement
- Refactorer sereinement
- Documenter le comportement attendu
**Structure** :
```
chat/tests/
├── test_models.py
└── test_views.py
```
**Impact** : 8 tests passent en 6 secondes. Confiance pour la suite.

---

### D49 — Outils de qualité de code

**Date** : 2026-10-14
**Contexte** : Le code doit être propre et cohérent.
**Décision** : Utiliser 4 outils :
- `black` : formatage automatique
- `isort` : tri des imports
- `flake8` : vérification du style
- `autoflake` : suppression des imports inutilisés
**Raison** :
- `black` : pas de débat sur le style
- `isort` : imports cohérents
- `flake8` : détecte les erreurs
- `autoflake` : nettoie le code mort
**Impact** : Code propre, standardisé.
**Attention** : `isort` a causé une importation circulaire dans `groq`.
Il faut configurer `isort` avec `profile = black` et exclure les fichiers
sensibles.

---

### D50 — Configuration de sécurité pour la production

**Date** : 2026-10-14
**Contexte** : Le projet doit être sécurisé en production.
**Décision** : Ajouter les configurations suivantes quand `DEBUG=False` :
```python
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```
**Raison** : Standard Django pour la production.
**Impact** : Application sécurisée en HTTPS.

---

### D51 — Documentation structurée

**Date** : 2026-10-14
**Contexte** : Le projet doit être compréhensible dans le temps.
**Décision** : Créer 3 documents :
- `README.md` : vue d'ensemble, installation, utilisation
- `DECISIONS.md` : journal des décisions techniques (ce fichier)
- `rag/README.md` : documentation du pipeline RAG
**Raison** :
- `README.md` : point d'entrée pour un nouveau développeur
- `DECISIONS.md` : mémoire des choix et justifications
- `rag/README.md` : documentation technique du pipeline
**Impact** : Projet documenté, transmissible.

---

## Phase 16 : Gestion avancée des documents (Data Engineering)

### D52 — Création d'un pipeline de nettoyage (ETL)
**Date** : 2026-10-26
**Contexte** : Les documents Canal+ (PDF) posaient des problèmes d'indexation (tableaux mal formatés, balises `<br/>` résiduelles, caractères invisibles).
**Décision** : Créer un script Python (`clean_canal_channels.py`) pour transformer les PDF bruts en fichiers `.md` propres et structurés.
**Raison** : Le RAG ne doit pas lire les tableaux bruts. Il a besoin de phrases linéaires et sémantiques (ex: "La chaîne CRTV est de genre Généraliste...").
**Impact** : Amélioration drastique des scores de rerank (passage de 0.2 à 1.0 sur les requêtes ciblées).

### D53 — Normalisation du format d'entrée
**Date** : 2026-10-26
**Décision** : Privilégier les fichiers `.md` ou `.txt` nettoyés plutôt que les PDF ou Excel bruts pour les données complexes.
**Impact** : Le pipeline d'extraction a été mis à jour pour accepter nativement les fichiers `.md` (les traitant comme du texte).

---

## Phase 17 : Tests de robustesse et Comportement du LLM

### D54 — Résultats des tests de robustesse
**Date** : 2026-10-27
**Contexte** : Tests sur les documents Canal+ nettoyés (fausses prémisses, hors sujet, croisement de données).
**Décisions/Constats** :
- Le LLM **ne succombe pas aux fausses prémisses** (ex: il a démenti que CRTV était uniquement dans TOUT CANAL+).
- Le LLM **refuse de répondre** quand l'information n'est pas dans le contexte (pas d'hallucination).
- **Limite identifiée** : Le croisement d'informations entre deux documents distincts (ex: le genre dans le Guide + la formule dans le Tableau Excel) reste complexe pour une recherche vectorielle simple.

---

## Phase 18 : Architecture du projet et Gestion des versions

### D55 — Séparation des environnements (Console vs Django)
**Date** : 2026-10-27
**Décision** : Maintenir deux versions distinctes du système.
1.  **Version Console / Streamlit** : Pour les tests rapides, l'analyse de données, et les prototypes.
2.  **Version Django** : Pour l'application web finale, la gestion des utilisateurs et le déploiement.
**Impact** : Les deux versions partagent le même moteur (`rag/`), mais ont leur propre documentation (`README.md`) et leur propre mode d'exécution.

### D56 — Unification du journal de décisions
**Date** : 2026-10-27
**Décision** : Le fichier `DECISIONS.md` est unique et centralise toutes les décisions techniques du moteur RAG, indépendamment de l'interface (Console, Streamlit ou Django) qui l'utilise.

### D57 — Adoption de `uv` pour la gestion des dépendances
**Date** : 2026-10-27
**Décision** : Utiliser `uv` au lieu de `pip` pour la gestion des paquets et des environnements virtuels.
**Raison** :
- Vitesse d'installation nettement supérieure (crucial avec PyTorch et sentence-transformers).
- Génération d'un fichier `uv.lock` garantissant la reproductibilité exacte des environnements.
- Simplification des commandes (`uv add`, `uv sync`).
**Impact** : Le déploiement futur sera plus fiable et plus rapide.

---

## Phase 19 : Documentations et Perspectives

### D58 — Nécessité d'une documentation technique
**Date** : 2026-10-27
**Contexte** : Distinguer le `README.md` (installation/utilisation) de la documentation technique (architecture, API interne, base de données).
**Décision** : Prévoir la création d'un dossier `docs/` contenant des fichiers comme `architecture.md`, `pipeline.md`, et `django_models.md`.

### D59 — Préparation au déploiement (Rappel)
**Date** : 2026-10-27
**Décision** : Le déploiement se fera via Docker (Gunicorn + Nginx + Certbot pour le HTTPS). L'accent sera mis sur la sécurité (isolation des conversations, gestion des secrets, rate limiting).

## Résumé des principes directeurs (mis à jour)

1. **Briques stables plutôt que frameworks monolithiques**
2. **Tester chaque composant isolément avant de l'intégrer**
3. **Déplacer les tâches structurées du LLM vers le code**
4. **Traduire avant de vectoriser (si langues différentes)**
5. **Charger les ressources une seule fois (singleton)**
6. **Documenter chaque décision technique**
7. **Séparer les responsabilités (modules, classes, fonctions)**
8. **Utiliser la POO quand il y a un état à conserver**
9. **HTMX pour les mises à jour simples, JS pour le streaming**
10. **Isolation par `user_id` plutôt que multi-tenant complexe**
11. **Tests avant fonctionnalités (TDD quand possible)**
12. **Outils de qualité dès le début (black, isort, flake8)**
```

---

## Récapitulatif des décisions

| Phase | Décisions | Thème |
|-------|-----------|-------|
| 1-11 | D1 à D34 | Fondations, extraction, recherche, génération |
| 12 | D35 à D39 | Intégration Django |
| 13 | D40 à D43 | Interface utilisateur |
| 14 | D44 à D47 | Streaming |
| 15 | D48 à D51 | Consolidation |

**Total : 51 décisions documentées.**

---

## Ce que ce document apporte

| Bénéfice | Détail |
|----------|--------|
| **Mémoire** | Vous n'oublierez pas pourquoi vous avez fait tel choix |
| **Justification** | Si on vous demande "pourquoi pas X ?", vous avez la réponse |
| **Transmission** | Un nouveau développeur comprend le projet en 30 minutes |
| **Debug** | Si un problème réapparaît, vous savez ce qui a été tenté |
| **Apprentissage** | Vous voyez votre progression |

---
