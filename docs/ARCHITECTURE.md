# Architecture et périmètre

Le prototype utilise FastAPI, SQLAlchemy et PostgreSQL ; l'interface française est servie par le même processus, sans dépendance JavaScript externe. Docker Compose limite la publication à localhost et sépare les volumes de base et de documents. Les documents PDF sont extraits localement avec PyMuPDF ; les pages sans texte et les images sont traitées par Tesseract français. Les champs extraits sont des propositions avec provenance, jamais des données garanties.

La première tranche permet configuration initiale, connexion, import, détection de doublon exact, extraction simple, vérification arithmétique, correction, rejet et journal minimal. Le stockage des champs est actuellement JSON, pas le schéma relationnel final. `create_all` initialise le schéma mais n'est pas un système de migrations. Il faut introduire Alembic avant toute évolution persistante.

Les écritures et exports restent désactivés jusqu'à vérification des sources, validation professionnelle et implémentation de contrôles de sécurité et de tests. Le périmètre complet et les étapes figurent dans DEVELOPMENT_PROGRESS.md.
