# État du développement — 16 novembre 2026

## Correction des doublons et retraitement

L'ancien traitement vérifiait le hash avant l'extraction et associait un doublon au document trouvé, dont les champs pouvaient être vides. Le code n'excluait pas explicitement le document du même identifiant lors d'une reprise. Sans accès aux données de l'utilisateur, il n'est pas possible de déterminer si les cinq fichiers existaient déjà ou pourquoi leurs anciens champs étaient vides.

Chaque nouvel élément est maintenant extrait même si son hash existe. Le document portant le même identifiant est exclu de la recherche de doublons ; les correspondances exactes signalent le document original, le lot d'origine lorsqu'il est connu et le type (même lot ou import précédent). Les champs extraits, dont les montants, sont affichés et inclus dans le rapport. Le bouton « Retraiter ce lot » crée un nouveau lot audité à partir des fichiers conservés, sans supprimer ni modifier les anciens lots. Les doublons restent bloqués pour les écritures ; aucune écriture comptable n'est créée par ce code. La recherche de référence manquante ne doit plus consommer la ligne suivante.

Tests disponibles exécutés : 10 réussis, 3 tests d'intégration ignorés faute de dépendances backend accessibles dans l'environnement de l'agent. Les tests d'intégration créent une base SQLite temporaire et simulent l'extraction ; ils couvrent cinq fichiers distincts, doublons intra/inter-lots, retraitement et auto-comparaison. Le contrôle de total sur texte OCR simulé a réussi ; un vrai scan/OCR n'a pas été testé. Syntaxe Python et JavaScript vérifiée. L'installation locale des dépendances a échoué à cause de la résolution DNS de PyPI. Aucun test PostgreSQL ou navigateur exécuté dans cette session.

## Changement demandé : traitement par lots

### Tranche suivante

Ajout de tables `batches` et `batch_items` par création additive au démarrage (aucune suppression ou modification de table existante), import authentifié jusqu'à 100 fichiers, traitement local séquentiel en arrière-plan, reprise des éléments en attente après redémarrage, progression et liste des exceptions. Les doublons exacts et les références fournisseur/facture déjà présentes sont signalés. Le module `batch_validation` est connecté au traitement. Un rapport XLSX d'anomalies est construit et rouvert pour vérifier les lignes et l'absence de formules avant téléchargement. Aucun export d'écritures validées n'est proposé.

Limites : une seule instance du processus applicatif est prise en charge ; pas de verrouillage interprocessus, de reprise automatique des échecs, de migrations Alembic, de validation des règles fiscales et comptables, de moteur de correspondance ou de génération/vérification d'écritures. Toutes les factures sont donc exclues des écritures et envoyées en exception. Le statut est transactionnel, mais les fichiers orphelins après interruption pendant l'envoi ne sont pas nettoyés automatiquement. Les vérifications de dates, périodes, TVA, provenance, lignes et les tests de charge restent incomplets. La base de données et les volumes existants ne sont pas réinitialisés. ZIP non pris en charge. Il s'agit d'un prototype à utiliser uniquement avec des données fictives.

Pour déployer depuis PowerShell, dans ce dossier : `docker compose up -d --build` puis `docker compose ps` ; ouvrir `http://localhost:8081`. Pour tester : se connecter, ouvrir « Traitement par lots », sélectionner `tests/fixtures/facture-fictive.pdf`, lancer le lot, attendre la fin et télécharger les anomalies. Relancer `docker compose restart app` et vérifier que le lot reste visible. Les volumes ne doivent pas être supprimés. Ce test n'a pas été exécuté dans l'environnement de l'agent.

Le nouveau flux vise la validation automatique des seuls cas couverts par des règles et correspondances vérifiées ; les exceptions restent exclues. `backend/batch_validation.py` effectue des contrôles préliminaires conservateurs et refuse toute éligibilité tant qu'aucune règle n'est vérifiée. Il ne constitue pas un moteur comptable. La commande `docker compose ps` avait échoué avec permission refusée sur le moteur Docker depuis l'environnement de l'agent, même si l'utilisateur indique que l'application fonctionne sur le port 8081 ; cela ne démontre pas une panne de l'application. Aucun test de bout en bout ni test de charge n'a été effectué pour ce changement.

## Résultat actuel

Première tranche de code, **MVP incomplet et non validé pour des données réelles**. Le dossier était vide ; Git a été initialisé localement sans publication ni commit. Source : `backend/`, `frontend/`, Compose, scripts PowerShell et documentation. L'interface est HTML/CSS/JavaScript sans construction, choix volontaire pour réduire les dépendances dans cette tranche ; elle ne satisfait pas encore les exigences de composants et tests React du brief.

Implémenté dans le code : création initiale d'un administrateur local, connexion Argon2 et session, tableau de bord, import PDF/JPEG/PNG, hash de doublon exact, stockage aléatoire, extraction PDF et OCR français, extraction de quelques champs avec provenance, contrôle arithmétique, aperçu, correction, rejet, audit minimal, page de références. Pas encore vérifié de bout en bout. Les fonctions non disponibles sont désactivées à l'écran. Aucun taux fiscal ni code de compte inventé ; aucune proposition comptable n'est activée.

## Contrôles exécutés

- Python 3.15 local : `python -m unittest discover -s tests -v` : 4 tests d'extraction et arithmétique réussis.
- `node --check frontend/app.js` : réussi.
- `python -m compileall -q backend tests` : réussi, contrôle syntaxique seulement.
- `docker compose --env-file .env.example config --quiet` : configuration syntaxiquement valide.
- `docker info` : échec « permission denied » sur `dockerDesktopLinuxEngine`. Images non construites, services non démarrés ; intégration PostgreSQL, OCR, interface, sécurité, persistance, lancement Windows et scénario d'acceptation non testés. Le Python local ne contient pas FastAPI, PyMuPDF, Pillow ou SQLAlchemy.

## Problèmes et risques ouverts

La création initiale peut être concurrencée. Sessions non révocables individuellement, pas de limitation des tentatives, protection CSRF/DNS rebinding incomplète, droits de rôles incomplets, audit sans anciennes/nouvelles valeurs, OCR synchrone et isolation insuffisante des fichiers non fiables. Les vérifications de sécurité ne sont pas complètes. `create_all` doit être remplacé par des migrations Alembic. Absence de sauvegardes/restaurations et de gestion de rétention. L'OCR n'a pas été exercé sur des fichiers. Les champs couverts sont limités ; pas de lignes de facture ni de détection de doublons sémantiques. Aucun contrôle fiscal n'est effectué.

Les sources officielles ont été identifiées, mais l'analyse des textes consolidés, des modifications et des situations transactionnelles est incomplète. La revue par un professionnel reste nécessaire ; aucun schéma comptable n'est activé. Voir `regulatory/`.

## Étapes suivantes

1. Rendre Docker Desktop accessible, exécuter `./run.ps1`, corriger toute erreur de construction et tester le cycle complet sur données fictives. Éviter les données réelles.
2. Renforcer configuration initiale, sessions, autorisations, protection CSRF/DNS rebinding, limitations et isolation OCR ; ajouter tests d'intégration et de sécurité.
3. Introduire Alembic et le schéma relationnel demandé ; tester persistance et sauvegarde/restauration.
4. Générer et tester tous les cas synthétiques PDF et scans, extraction, doublons et contrôles ; améliorer l'interface de revue et provenance.
5. Compléter et faire valider les recherches réglementaires ; concevoir règles versionnées et comptes configurables, sans activer les cas non vérifiés.
6. Implémenter lignes équilibrées, approbation humaine, modèles d'export XLSX/CSV, protection contre injection et historique, puis couvrir l'acceptation de bout en bout.
7. Finaliser la gestion utilisateurs/fournisseurs, paramètres, documentation française et tests navigateur/accessibilité. Exécuter et consigner chaque critère d'acceptation.
