# P3.6F — Architecture expérimentale de confinement des navigations Firefox

**Statut : PROPOSITION À AUDITER.** Date : 2 novembre 2026.
**Base Git immuable :** PR #16, `9f7a02d1b089a38b554af94aedaf8ca377da407a`.
**Dépendance concurrente :** PR #17 (P3.6E) en contre-revue, **non fusionnée**.
**Périmètre :** ressources et serveurs **100 % fictifs**, aucun HTML professeur réel.

## 1. Décision de conception proposée

P3.6E a montré à plusieurs reprises qu'un prédicat statique sur le HTML
n'est pas une preuve d'absence de navigation dans Firefox. Même une
analyse DOM HTML5 peut ignorer un mécanisme de chargement, un
changement de contexte ou une différence d'implémentation.

**Séparer désormais trois responsabilités :**
1. **Intégrité / autorisation de la ressource** : chaîne P3.6A/C/D,
   Git + Quarto + inventaire vérifié + unique HTML scellé, mais **L1
   (provenance authentifiée et consentement réel) non résolue**.
2. **Veto de requêtes/navigation du navigateur** : une **WebExtension
   expérimentale dédiée** à un profil Firefox *jetable*, enregistrant
   un listener bloquant de `webRequest.onBeforeRequest` **avant**
   l'ouverture de la page ; politique d'admission bornée à une
   **unique URL HTTP loopback exacte**, un onglet identifié, et une
   phase de session explicite. `webNavigation` vérifie l'état et
   signale les navigations : **ne constitue pas un bloqueur**.
3. **Barrière réseau indépendante (expérience Ubuntu)** : lorsque
   techniquement disponible et vérifié, Firefox, le serveur fictif et
   les sondes locales s'exécutent **dans un même espace de noms réseau**
   sans interface externe, uniquement `lo`. Toute tentative de
   sortie Internet échoue au niveau réseau, même si le listener
   d'extension n'est pas appelé. **Pas de repli implicite** vers un
   Firefox connecté. Si l'isolation de l'OS ne peut pas être attestée,
   la qualification « isolement réseau » est **NO_GO**.

Cette topologie est **un banc de recherche**, pas un choix définitif
de déploiement pour l'enseignant : Alliage doit continuer à augmenter
les applications existantes dans le Firefox habituel, avec IA externe
et historique Git, une fois les frontières de sécurité réellement prouvées.

## 2. État effectivement examiné

- `extension/manifest.json` : Manifest V3, `background.scripts` et
  `background.service_worker`, droits hôtes limités à la page publiée
  et à `http://127.0.0.1/*` ; pas de `webRequestBlocking`.
- `extension/background.js` : pont POST v0.4 vers
  `http://127.0.0.1:8765` pour les actions `experiment`/`decision`,
  exclusivement depuis la page publique précise. **Ne pas modifier
  ce pont pour mener l'expérience de confinement.**
- P3.6D : HTTP `127.0.0.1` avec capacité non prédictible dans le
  chemin, sortie **HTML unique scellée**, ressources auxiliaires
  interdites, CSP sans scripts/connect-src.
- P3.6E : filtre d'admission HTML expérimental sur la PR #17.
  Son résultat et ses nouvelles dépendances **ne sont pas présumés
  acquis** sur la présente branche sœur.

Le simple mode « fenêtre de navigation privée » ne crée ni un
profil Firefox dédié, ni une isolation des extensions installées,
ni un blocage réseau garanti.

## 3. Modèle de menace et objectifs vérifiables

**Protégé :** contenu de l'HTML professeur (ultérieurement),
identifiant opaque de session, attributs de navigation et absence
de publication. Pour P3.6F, seulement des chaînes fictives.

**Origines de risques :**
- liens cliquables, menus contextuels, onglets créés par l'utilisateur ;
- images/CSS/SVG/MathML, `meta refresh`, préchargements et
  redirections ; le JS de la page demeure désactivé ;
- `http:`/`https:`, `ws:`/`wss:`, `data:`, `blob:`,
  `file:`, `about:`, et gestionnaires de protocoles externes ;
- activité spéculative du navigateur, DNS, caches et service workers ;
- extension arrêtée, permissions révoquées, démarrage avant listener,
  extension concurrente ou contournement via nouvel onglet ;
- serveur sur mauvais port, réutilisation d'une capacité, accès à
  d'autres services loopback, requête sortante indirecte ;
- détenteur local déjà privilégié ou code arbitraire dans le
  navigateur/l'extension (hors protection assurée par une simple
  WebExtension).

**Invariants à démontrer séparément :**
- F1 : seul le **document principal** exactement autorisé peut être
  chargé ; le listener doit refuser tout autre HTTP(S) provenant de
  l'onglet de test, y compris un autre chemin/port loopback.
- F2 : aucun changement de navigation vers une destination non admise
  n'est **commis** durant les scénarios testés ; nouveaux onglets/
  fenêtres non autorisés détectés et refusés ou invalidant le test.
- F3 : aucun serveur *leurre* local d'une autre origine ne reçoit
  la requête de l'onglet surveillé pendant les tests de veto.
- F4 : la barrière réseau extérieure est démontrée **par le système
  d'exploitation**, pas déduite du seul panneau Réseau de Firefox.
- F5 : toute modification de permissions, arrêt/crash d'extension,
  échec du handshake ou impossibilité de prouver F1–F4 entraîne un
  **NO_GO**, pas une ouverture du HTML privé.
- F6 : les octets du HTML P3.6D et l'identité Git/Quarto ne sont
  jamais altérés par le banc ni par l'extension.
- F7 : l'extension expérimentale ne transmet aucune page, sélection,
  URL de capacité ou contenu à une IA ou à un serveur externe.

**Non-objectifs :** neutraliser une compromission de Firefox, du
noyau ou du processus de l'extension ; fournir un accès à une
vraie session professeur ; attester le profil Quarto ; piloter Git,
modifier un `.qmd`, publier aux élèves ; reproduire le confinement
sur Moodle/Snap!/Grist avant une qualification Quarto satisfaisante.

## 4. Composants proposés et frontière de confiance

```text
Dépôt Git fictif -> Quarto réel -> P3.6A verify_session
                                      |
                                      v
                 P3.6D admission HTML seul / SHA / snapshot
                                      |
                         serveur HTTP fictif 127.0.0.1:PORT
                                      |
            +-------------------------+--------------------+
            |  espace de noms réseau dédié (lo seulement)  |
            |                                                |
            |   Firefox profil jetable (aucune autre ext.)    |
            |      `webRequest` veto local                  |
            |      `webNavigation` observation              |
            |       onglet / URL / capacité admis            |
            |   serveur piège 127.0.0.1:AUTRE_PORT          |
            |                                                |
            +-------------------X----------------------------+
                                X sorties Internet impossibles
                                  dans le banc attesté
```

Le **serveur de fixture**, l'extension et l'isolateur sont des
composants différents : une réussite de l'un n'est pas une preuve
implicite des autres. Le serveur n'est pas déplacé dans le réseau
domestique ; toute écoute doit rester sur `127.0.0.1`.
Les chemins de sessions et les fichiers privés ne sont jamais
montés dans un contexte navigateur fictif.

### 4.1 WebExtension de banc, séparée de v0.4

Créer ultérieurement `experiments/p36f-extension/` avec un manifeste
distinct. Ne **pas** augmenter les permissions de
`extension/manifest.json` en production pendant l'expérience.

- Firefox MV3 : `background.scripts` (Firefox utilise le contexte de
  document de fond / event page, non `background.service_worker`).
  Enregistrement `webRequest.onBeforeRequest` au niveau supérieur,
  de façon synchrone et avant création de l'onglet.
- Demander `webRequest`, `webRequestBlocking`, `webNavigation`,
  `tabs` et l'ensemble **effectivement nécessaire** des permissions
  hôtes pour observer requêtes source et destination. L'interception
  des ressources croisées nécessite la permission de la page
  **et** celle de la destination ; une permission uniquement loopback
  ne suffit pas à démontrer le refus de tout domaine.
- `<all_urls>` est **envisagé uniquement dans ce profil jetable**,
  jamais implicitement dans la v0.4. Il est sensible : faire valider
  explicitement son usage et confirmer la couverture par les tests.
- Filtre des requêtes HTTP(S) global et contrôle `tabId`,
  `frameId`, `type`, `documentUrl`/initiator lorsque fournis.
  La **seule** URL de document autorisée est égale à l'URL canonique
  éphémère approuvée. Toute autre demande HTTP(S) venant du
  contexte admis est refusée. Les métadonnées de provenance
  absentes/ambiguës ne valent jamais autorisation.
- `webNavigation` observe `onBeforeNavigate`,
  `onCommitted`, nouveaux onglets/fenêtres, navigation interne
  sans requête. **Ne jamais utiliser ses événements comme s'ils
  pouvaient annuler la navigation.** Les changements de fragment
  `#...` sont permis sans sortir du même document, à tester.
- Les navigations `file:`, `data:`, `blob:`, `about:`,
  les gestionnaires de protocoles et les navigations internes sans
  HTTP(S) **ne sont pas couverts par la preuve `webRequest`**.
  Bloquer/désactiver à un autre niveau ou classer NO_GO.
- Les extensions de tiers et permissions de l'environnement de
  l'enseignant restent **hors du banc jetable**.
- L'extension n'agit pas comme proxy de données ni comme canal
  entre le HTML et l'IA. Les événements et les compteurs de test
  doivent être **expurgés** des jetons, contenus et URL de capacité.

### 4.2 Machine à états d'un essai

`CREATED → PERMISSIONS_VERIFIED → LISTENER_REGISTERED →
ISOLATION_ATTESTED → ARMED → VIEW_OPEN → CLOSED`.

- `ARMED` est un **ack explicite du processus d'extension**,
  après constatation des permissions et de la présence du listener.
  Aucun appel de page avant ce point.
- `VIEW_OPEN` admet un **tabId** précis et une URL HTML exacte.
  Éviter la fenêtre où le premier chargement précède l'association
  au tabId ; le protocole devra créer d'abord un onglet neutre,
  assigner son identité, puis seulement autoriser sa navigation.
- Retour à `CLOSED` en cas de navigation inattendue, crash,
  révocation de permission, expiration de session, fermeture de
  l'onglet ou du serveur. L'état doit être *fail closed* et ne
  pas réutiliser un ancien autorisation après redémarrage de l'event
  page. Conserver seulement l'état minimal requis par l'extension.
- `CLOSED` n'autorise pas de rejouer automatiquement un ancien jeton,
  ni de restaurer silencieusement un onglet sensible.

Le handshake est un **contrôle de disponibilité**, et non une
attestation cryptographique d'intégrité du processus Firefox.

### 4.3 Barrière réseau système — expérimentation Ubuntu

**Hypothèse à vérifier avant mise en œuvre :** lancer le navigateur,
son serveur local et le serveur piège **dans le même namespace réseau**
avec uniquement l'interface loopback active. Un namespace réseau
différent pour le seul Firefox **empêcherait aussi d'atteindre** le
serveur HTTP loopback de l'hôte ; cette erreur de topologie est
explicitement interdite.

Les namespaces utilisateur/réseau non privilégiés peuvent être
refusés par Ubuntu/AppArmor, et l'installation Firefox, les
profiles et les services de démarrage ont leurs propres contraintes.
Le lanceur doit :
1. vérifier ses capacités locales et refuser de démarrer si
   les isolations demandées ne sont pas disponibles ;
2. démontrer l'absence d'interface/route externe avant de charger
   la fixture ;
3. prouver que **le même** namespace contient le serveur et Firefox ;
4. démontrer qu'une URL d'Internet ne peut pas être jointe
   indépendamment de l'extension, et qu'un second serveur loopback
   est joignable **si et seulement si** le veto Firefox est désactivé
   dans l'essai négatif contrôlé.

Aucune commande d'isolation n'est exécutée par ce document.
Ne pas suggérer `firefox --private-window`, le simple mode hors ligne,
la CSP ou `--no-remote` comme équivalents d'une barrière réseau
OS prouvée.

## 5. Conditions d'entrée et de sortie

**Avant tout développement de P3.6F actif :**
- approbation indépendante de l'architecture et des permissions
  WebExtension envisagées ;
- PR #17 revue indépendamment ; sa fusion n'est pas un prérequis
  pour créer une fixture F *sœur* sur le HEAD approuvé de #16 ;
- aucune ressource Quarto réelle, aucun dépôt privé, aucun compte
  GitHub pédagogique chargé dans le profil de test.

**Incréments proposés :**
- **F0 — présent :** contrat d'architecture, menaces et matrice
  de tests ; **aucun code d'interception** ni droit navigateur accru.
- **F1 :** WebExtension distincte + politiques pures/testables +
  fixture locale volontairement hostile + faux serveur piège ;
  CI unitaires sans navigateur et contre-revue.
- **F2 :** mesures Firefox *réel* en profil dédié, navigation,
  redirection, frames, changement d'onglet, blocage de requêtes,
  permissions révoquées, état d'event page et contamination des logs.
- **F3 :** preuve du namespace/réseau indépendant, y compris épreuve
  négative ; considérer `NETWORK_CONFINEMENT_UNPROVEN`
  si le noyau/Ubuntu ne permet pas cette isolation.
- **F4 :** expertise de composition P3.6A + D + E + F sur fixtures.
  L1/L2/attestation du vrai profil restent des portes distinctes
  **même si F4 réussit**.

## 6. Arbitrages ouverts et risques de conception

| Option | Intérêt | Limite / décision |
| --- | --- | --- |
| Filtrage statique P3.6E seul | Rejet précoce | **Insuffisant** pour la navigation Firefox |
| CSP + `sandbox` | Réduction surface active | Ne garantit pas les navigations top-level |
| `webNavigation` | Observation d'URL et d'onglets | **Ne bloque pas** |
| `webRequest` bloquant | Veto HTTP(S) testable | Permissions larges, protocoles non couverts, démarrage / autres extensions |
| Namespace réseau sans extérieur | Barrière réseau indépendante | Peut être indisponible ; serveur et Firefox doivent partager le namespace |
| Revenir au Firefox habituel immédiatement | UX fluide | **Prématuré** pour de vraies données privées |

La plus petite expérience utile n'est **pas** un nouveau filtre
HTML. C'est un **test Firefox sur page fictive navigable**, avec un
serveur piège local qui détecte une connexion interdite, puis une
barrière réseau OS indépendamment vérifiée.

## 7. Références techniques primaires (consultées le 2 novembre 2026)

- Mozilla MDN — `webRequest` (permissions de la page et de la
  destination, limites d'interception) :
  https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/webRequest
- MDN — `webRequest.onBeforeRequest` (annulation, séquence et limites) :
  https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/webRequest/onBeforeRequest
- MDN — `webRequest.RequestFilter` : uniquement HTTP(S), filtre
  `tabId`, `windowId`, `types` :
  https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/webRequest/RequestFilter
- MDN — `webNavigation` : surveillance des changements de contexte :
  https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/webNavigation
- MDN — `background` : Firefox MV3 emploie `background.scripts`,
  pas `background.service_worker` :
  https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/manifest.json/background
- MDN — `host_permissions` et autorisations utilisateur :
  https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/manifest.json/host_permissions

**Ce document est une spécification proposée, pas une attestation
de sécurité.** Ne pas fusionner, publier ou ouvrir une vraie session
professeur sur la seule foi de cette architecture.
