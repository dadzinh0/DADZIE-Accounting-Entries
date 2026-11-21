# PROHEAT Accounting Entry

**État : première implémentation en développement, non prête pour des données réelles.** Les règles comptables, les écritures, l'approbation, les exports, la gestion des utilisateurs et les sauvegardes restaurables ne sont pas encore implémentés. Ne pas utiliser pour une comptabilité réelle. Voir [l'état détaillé](docs/DEVELOPMENT_PROGRESS.md).

## Démarrage prévu sous Windows

1. Démarrer Docker Desktop avec les conteneurs Linux.
2. Dans PowerShell, ouvrir ce dossier et exécuter `./run.ps1`.
3. Ouvrir http://localhost:8080 si le navigateur ne s'ouvre pas. Créer le premier administrateur avec un mot de passe d'au moins 8 caractères, puis se connecter.
4. Importer uniquement une facture fictive PDF, JPG ou PNG. Vérifier les champs et l'arithmétique ; les corrections et rejets sont enregistrés.
5. Pour arrêter : `./stop.ps1`. Les volumes Docker persistent après l'arrêt. Ne pas utiliser `docker compose down -v` : cela supprime les volumes.

Le premier lancement télécharge des images et des dépendances depuis des registres publics. Le traitement des documents n'appelle aucun service externe. La configuration Compose publie seulement le port 8080 sur 127.0.0.1 et le réseau des conteneurs est interne. `.env`, créé localement avec des secrets aléatoires, doit rester privé et être sauvegardé de façon sécurisée. La disponibilité des registres, le démarrage Docker Windows et le traitement OCR n'ont pas été vérifiés ici.

## Données et sécurité

Le fichier original est stocké dans le volume Docker `documents`, sous un identifiant aléatoire. Les champs extraits, utilisateurs et événements sont dans PostgreSQL, volume `database`. L'extraction PDF et Tesseract s'exécutent dans le conteneur local. Aucun modèle ni API cloud ne traite les documents. Les liens réglementaires s'ouvrent dans le navigateur et contactent les sites officiels uniquement sur clic. Docker et les registres peuvent transmettre des données techniques au moment du téléchargement des images ; le navigateur et le système hôte restent sous la responsabilité de leur configuration respective.

Les contrôles présents sont préliminaires : mot de passe Argon2, session signée, liaison loopback, taille/type de fichier, noms aléatoires, détection SHA-256 et quelques limites OCR. Ils n'ont pas reçu de revue indépendante. Les cookies sont non chiffrés sur HTTP local. Absence notamment de limitation des tentatives, de sauvegarde/restauration testée, d'isolation forte du traitement de documents, de protection complète contre CSRF/DNS rebinding, de migrations, d'audit détaillé et d'autorisations complètes. Une session signée n'est pas un stockage serveur révocable. Ne pas exposer l'application au réseau. Consultez [le modèle de sécurité](docs/SECURITY.md).

## Vérification locale

`python -m unittest discover -s tests` teste l'extraction déterministe sans dépendances externes. Les tests complets nécessitent l'environnement Docker, des fichiers synthétiques PDF/images et des tests d'intégration supplémentaires. Aucun document réel ne doit être utilisé pendant le développement.
