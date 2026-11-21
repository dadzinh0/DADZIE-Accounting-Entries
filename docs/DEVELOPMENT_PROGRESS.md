# État du développement — 16 novembre 2026

## En-tête du logo

Le logo occupe désormais toute la zone supérieure blanche de la barre latérale, sans carte blanche flottante. Un fin séparateur doré marque la transition vers le menu marine, qui conserve sa couleur et ses états actifs. Vérification HTTP du CSS servi localement effectuée.

## Palette moins lumineuse

La navigation reprend un fond marine sombre ; seul le panneau du logo a un fond blanc pour préserver sa lisibilité. Le fond principal, la barre supérieure, les cartes, tableaux et contrôles utilisent des tons ardoise plus sombres et moins éblouissants. Le CSS versionné est servi par l'application locale ; contrôle HTTP effectué. Pas de capture navigateur automatisée disponible dans cette session.

## Présentation affinée

La page d'accueil n'affiche plus de bannière « Version de développement » ni de consignes de test ; les notices comparables ont été retirées du traitement par lots, de la vue document et du référentiel. Le tableau de bord présente des compteurs de documents et de lots. Les anciens liens bleus sont présentés comme des contrôles sobres et cohérents ; boutons, tableaux, formulaires et surfaces ont été harmonisés. Contrôle syntaxique JavaScript et réponses HTTP de la page, du script et du CSS effectués. Aucun navigateur automatisé n'était disponible pour une capture visuelle.

## Logo transparent haute résolution

Le logo fourni a été nettoyé en image transparente RGBA 2170×725 (`frontend/proheat-logo-clean.png`). La navigation utilise une surface claire afin de garder les lettres marine et bleues lisibles, sans fond blanc intégré à l'image ni superposition de tons sombres. Les boutons restent bleu PROHEAT avec accent doré. Contrôle JavaScript et réponses HTTP du logo, du CSS, du JS et de la page effectués ; pas de test de rendu automatisé du navigateur.

## Identité visuelle PROHEAT INDUSTRY

Le visuel fourni par l'utilisateur remplace le pictogramme provisoire dans la connexion et la barre latérale. La palette de l'interface suit le logo : marine, bleu/bleu-vert et accent doré ; boutons, navigation, liens, focus et typographie ont été harmonisés. Le logo est stocké localement dans `frontend/proheat-logo.png`. Vérification JavaScript et réponses HTTP des quatre ressources principales effectuées ; aucune capture navigateur automatisée n'a été réalisée.

## Navigation limitée à cinq onglets

La barre latérale affiche uniquement Tableau de bord, Traitement par lots, Référentiel réglementaire, Journal d'audit et Paramètres. L'import et l'export restent accessibles dans le flux de traitement par lots. Vérification syntaxique JavaScript et réponse HTTP du script déployé effectuées.

## Export sans statut d'approbation

À la demande de l'utilisateur, la colonne « État comptable / Non validée » a été retirée du classeur de données de factures et la page de traitement par lots n'affiche plus de consigne d'approbation. L'export reste un relevé des données extraites avec anomalies sur cellules rouges ; il ne génère pas d'écritures comptables. Suite Docker : 19 tests réussis.

## Noms des lots

Les lots récents sont affichés au format `PHI-INV-B<numéro>-JJ-MM-AAAA`, avec numéro chronologique et date en fuseau Africa/Casablanca. Les identifiants internes restent inchangés. Test de format exécuté avec la suite Docker : 19 tests réussis.

## Bouton de suppression des lots

Un bouton « Supprimer ce lot » est affiché pour les lots terminés. Il masque le lot de la liste via une nouvelle table additive `hidden_batches`, avec confirmation et événement d'audit. Aucun fichier ni historique n'est effacé ; les lots en attente de traitement ne peuvent pas être masqués.

## Restauration de l'interface complète

À la demande de l'utilisateur, restauration des fichiers frontend de la version précédant la simplification (8fde5f1). Navigation, tableau de bord, documents, traitement par lots et téléchargement Excel sont rétablis. Le point de téléchargement direct du dernier lot est conservé. Aucune donnée ou volume supprimé.

## Interface simplifiée : fichiers vers Excel

L'interface authentifiée se limite maintenant au choix des fichiers, au bouton « Créer mon Excel », à la progression et au téléchargement direct. Les menus, tableau de bord, listes, revue et paramètres ont été retirés de l'interface. La dernière opération reste accessible après rafraîchissement ; les données, historiques et API existants sont conservés. Les problèmes restent indiqués en rouge avec commentaires dans l'Excel.

## Téléchargement Excel direct

Correction du bouton « Télécharger Excel » de la vue document : il télécharge désormais le classeur du lot associé (ou celui du document pour un import isolé), au lieu de rediriger vers la page d'envoi. La page des lots sélectionne automatiquement le lot le plus récent. Version déployée ; syntaxe JavaScript vérifiée et retour de fichier Excel contrôlé sur une facture fictive existante.

## Suppression de la saisie manuelle des factures

Le formulaire de correction, les champs et les boutons Enregistrer/Rejeter ont été retirés de la vue document. Celle-ci affiche uniquement le document et un accès au téléchargement Excel par lot. Toutes les cellules signalées (valeurs manquantes, doutes, incohérences) utilisent désormais un fond rouge et un commentaire explicatif. Les 18 tests ont réussi dans Docker ; syntaxe JavaScript validée et version déployée localement.

## 21 novembre 2026 — annotations des anomalies dans Excel

Le fichier de données inclut désormais des commentaires Excel et une couleur sur les cellules concernées : champ obligatoire absent en jaune, montants incohérents en rouge, doublon signalé en orange. Les remarques sur la règle comptable non activée ne sont pas traitées comme une anomalie d'extraction. L'onglet `ANOMALIES` reste une liste compacte des vrais problèmes de données. Le tableau du lot distingue les factures extraites des factures avec anomalies ; la correction par formulaire est facultative. Les données de chaque facture continuent à figurer dans l'Excel, avec les vides conservés et les incohérences non corrigées automatiquement.

Le classeur fictif à cinq factures a été régénéré puis rouvert : commentaires et couleurs vérifiés en `FACTURES!E5` (référence absente) et `FACTURES!I6:K6` (total incohérent), avec 5 factures, 7 lignes et 2 anomalies. Les volumes PostgreSQL et documents sont inchangés.

## 21 novembre 2026 — export des données de factures

Le besoin utilisateur est un Excel détaillé après import, y compris lorsque des écritures comptables ne sont pas validées. Ajout de `backend/invoice_workbook.py` et de `/api/batches/{id}/invoice-data.xlsx`. Le classeur contient `FACTURES` (une ligne par fichier, champs extraits, contrôle des montants, état d'extraction et indicateur de doublon), `LIGNES` (articles détectés) et `ANOMALIES` (champs absents et incohérences). Les montants sont des cellules numériques et les dates sont typées/formattées. Le fichier est rouvert pour contrôler ses valeurs, le nombre de lignes, ses onglets et l'absence de formules. L'export est disponible même si des exceptions subsistent. Il ne constitue pas un journal comptable validé.

L'extraction a été adaptée à la mise en page réelle des cinq PDF **fictifs** déjà présents dans le stockage local : fournisseur/ICE sous en-tête, référence et dates en tableau, montant HT/TVA sur la ligne suivante, lignes d'articles, ainsi que la disposition OCR du scan. L'endpoint d'export réextrait à partir de chaque fichier conservé, y compris pour les anciens lots dont les champs liés aux doublons étaient vides. Le tableau d'un ancien lot reste basé sur les champs enregistrés ; le bouton « Retraiter ce lot » le met à jour via un nouveau lot sans effacer l'historique.

Vérifications exécutées : 17 tests dans l'image Docker, tous réussis. Un classeur réel a été généré et rouvert à partir des cinq PDF fictifs : 5 factures, 7 lignes, 2 anomalies (`04_reference_manquante.pdf`, `05_scan_total_incorrect.pdf`). L'extraction ne remplit pas la référence volontairement absente et ne corrige pas le total incohérent. Aucun taux de TVA ni compte comptable n'a été inféré. Le classeur généré est dans `outputs/proheat-fictional-invoice-details.xlsx` et n'est pas suivi par Git.

## 21 novembre 2026 — formulaire d'import unifié

Le formulaire « Importer des documents » utilisait encore `/api/documents`, qui renvoie HTTP 409 sur un hash déjà connu. Ses cinq messages « Fichier identique déjà importé » provenaient de ce chemin, et non du traitement par lots. L'entrée de navigation et le bouton du tableau de bord ouvrent désormais « Traitement par lots » ; l'ancien formulaire a été retiré de l'interface. Les fichiers déjà présents peuvent être soumis dans un nouveau lot : ils sont extraits et signalés avec leur référence d'origine dans les exceptions. Le point d'API historique `/api/documents` garde son comportement 409 pour les clients directs.

Contrôle exécuté dans l'image Docker avec base SQLite temporaire, sans toucher aux volumes PostgreSQL/documents : 13 tests réussis, aucun ignoré. Le test de cinq factures distinctes et les tests de doublons intra/inter-lots ont réussi. Le scan OCR réel et les cinq fichiers précis de l'utilisateur restent à vérifier depuis le navigateur.

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
