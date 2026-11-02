# P3.6F — Architecture expérimentale de confinement des navigations Firefox

**Statut : F0 corrigé après contre-expertise ; nouvelle revue requise.** Date : 2 novembre 2026.
**Base Git immuable :** PR #16, `9f7a02d1b089a38b554af94aedaf8ca377da407a`.
**Dépendance concurrente :** PR #17 (P3.6E) **APPROUVABLE dans son périmètre fictif** au HEAD `b7bd1f7820dd72f45cb22dbf592ad0eb0d250192`, **non fusionnée**. La présente branche reste sœur de #17 et ne reprend aucun de ses correctifs.
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
2. **Veto des requêtes HTTP(S) interceptées, pour le profil de test
   ENTIER** : une WebExtension de banc distincte enregistre
   synchroniquement un listener bloquant `webRequest.onBeforeRequest`
   **global sans restriction `tabId` dans le filtre** ; toute requête
   interceptée est refusée par défaut. Une seule requête initiale
   `main_frame` à l'URL loopback exacte, depuis l'onglet armé et
   dans la génération courante, peut être autorisée. Nouveaux onglets,
   sous-frames, requêtes spéculatives et métadonnées ambiguës :
   refus. `webNavigation` OBSERVE mais ne bloque jamais.
3. **Barrière réseau indépendante (expérience Ubuntu)** : Firefox,
   le serveur fictif et les sondes utilisent le même namespace
   réseau avec uniquement `lo`, si la configuration est possible et
   attestée. Cette topologie démontre au mieux
   `NO_IP_EGRESS_FROM_TEST_NAMESPACE` ; elle ne prouve PAS à elle
   seule l'absence de fuite via socket Unix lié à un chemin, proxy
   de l'hôte, IPC, descripteurs hérités ou processus hors namespace.
   Revendiquer `NO_EXTERNAL_EGRESS_VIA_HOST_SERVICES` exige des
   contrôles OS/IPC complémentaires. Sinon **NO_GO**, sans repli
   silencieux sur un Firefox connecté.

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
- F1 : pour toute requête HTTP(S) effectivement interceptée **dans
  l'ensemble du profil jetable**, `DENY` par défaut. Un unique
  `main_frame` HTTP `GET` à l'URL exacte, depuis le `tabId`
  préalablement armé dans la génération courante, peut être admis.
  Cette permission est consommée au plus une fois ; pas de redirect
  autorisé implicitement, aucune autre sous-ressource admise.
- F2 : distinguer `BLOCKED_HTTP_REQUEST` (veto pré-réseau),
  `NAVIGATION_COMMITTED` (observation d'une transition),
  `SESSION_INVALIDATED` (réaction potentiellement TARDIVE),
  `OS_EGRESS_DENIED` et `UNOBSERVABLE`. Une simple invalidation
  APRES navigation ne constitue jamais un PASS de confinement.
- F3 : pour chaque destination locale HTTP/HTTPS, un témoin négatif
  sans veto démontre que le serveur peut recevoir la demande,
  puis le témoin positif lie `DENY`, zéro réception et absence
  de navigation commise. La même exigence s'applique aux nouveaux
  onglets, aux sous-frames et aux requêtes spéculatives interceptées.
- F4 : preuve OS distincte `NO_IP_EGRESS_FROM_TEST_NAMESPACE` ;
  le niveau supérieur `NO_EXTERNAL_EGRESS_VIA_HOST_SERVICES`
  exige audit des relais, sockets, IPC et descripteurs hérités.
- F5 : permissions absentes ou révoquées, listener absent, extension
  arrêtée, génération périmée, ou preuve incomplète : **NO_GO**.
  Un arrêt d'extension n'est pas bloqué par l'extension elle-même
  et peut laisser visible un DOM déjà chargé : la barrière OS et
  la révocation/expiration serveur restent indispensables.
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
            |      `webRequest` veto GLOBAL du profil                  |
            |      `webNavigation` observation uniquement              |
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
- Listener bloquant `onBeforeRequest` au niveau supérieur, avec
  un filtre HTTP(S) **global à tout le profil** (`<all_urls>`
  sous réserve d'autorisations explicites) et **sans `tabId`
  dans le filtre**. Pour toutes les requêtes INTERCEPTÉES :
  `{cancel:true}` sauf un unique événement `main_frame`
  de méthode `GET`, URL exacte et `tabId` de l'onglet armé,
  `frameId` principal, permission et génération valides.
  Refuser également `tabId=-1`, nouvel onglet, provenance
  manquante/ambiguë, catégories spéculatives, redirections,
  sous-frames et sous-ressources. La présence d'un événement
  n'implique pas couverture des requêtes non interceptées.
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

- Le listener de veto est **toujours enregistré** au niveau
  supérieur à l'initialisation de l'event page ; l'état local
  commence en `CLOSED`. Ne jamais le retirer pour « désarmer ».
- `ARMED` est un ACK explicite et **éphémère**, lié à la
  génération courante du processus/session, aux permissions
  vérifiées et à l'URL exacte ; son absence interdit le
  chargement de la page dans le banc.
- Créer d'abord un onglet neutre, établir son `tabId`, puis
  accorder **une seule ouverture initiale GET/main_frame**.
  Déconsommer cette permission AVANT de rendre la décision
  d'autorisation. Le chargement de l'URL ne doit pas précéder
  le handshake et l'armement.
- Au redémarrage de l'event page, toute autorisation et ancien
  `tabId` sont invalidés. Nouvelle génération et nouvel
  ACK obligatoires. Un état conservé dans un stockage persistant
  ne peut jamais être interprété comme une autorisation.
- Révocation, fermeture, arrêt/crash de l'extension et retour
  arrière déclenchent un `NO_GO`. **Si l'extension n'exécute
  plus aucun code, elle ne peut pas se protéger elle-même** :
  la protection résiduelle repose sur l'isolation OS et sur
  l'expiration/révocation serveur, sans effacer rétroactivement
  le contenu d'un document déjà chargé.
- `webNavigation` signale les transitions, y compris celles
  sur schéma non HTTP ; une invalidation ultérieure n'est pas
  l'annulation de la transition.

Le handshake n'est ni une attestation cryptographique Firefox
ni une garantie si l'extension est absente ou désactivée.

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
1. vérifier les capacités système sans supposer les namespaces
   rootless disponibles ou désactiver les protections Ubuntu ;
2. prouver que le processus Firefox **réel**, ses processus
   réseau/enfants, le serveur fictif et le leurre ont une
   identité cohérente `/proc/<pid>/ns/net` ;
3. inventorier interfaces IPv4/IPv6, routes, `veth`, proxies,
   processus dans le namespace de l'hôte, sockets hérités,
   IPC et sockets Unix liés à un chemin accessibles ;
4. vérifier l'absence de relais par services de l'hôte et, si
   nécessaire, imposer en plus une isolation mount/IPC/FD
   sous revue spécifique ;
5. produire séparément les attestations
   `NO_IP_EGRESS_FROM_TEST_NAMESPACE` et
   `NO_EXTERNAL_EGRESS_VIA_HOST_SERVICES` (cette dernière
   reste `UNPROVEN` si tous les relais ne sont pas exclus) ;
6. montrer qu'une destination leurre HTTP **et HTTPS** est
   joignable dans le témoin négatif, puis non contactée grâce
   au veto, avec événement `DENY` corrélé.

Aucune commande d'isolation n'est exécutée par ce document.
Ne pas suggérer `firefox --private-window`, le simple mode hors ligne,
la CSP ou `--no-remote` comme équivalents d'une barrière réseau
OS prouvée.

## 5. Conditions d'entrée et de sortie

**Avant tout développement de P3.6F actif :**
- contre-revue indépendante de **ce F0 corrigé** et des permissions
  WebExtension envisagées ;
- PR #17 approuvée dans son périmètre fictif au HEAD exact
  `b7bd1f7820dd72f45cb22dbf592ad0eb0d250192` ;
  sa fusion n'est pas un prérequis pour développer F1 comme
  expérience *sœur* sur le HEAD approuvé de #16 ;
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

## 8. Corrections de la contre-expertise F0 (2 novembre 2026)

[Rapport indépendant C1–C4](https://github.com/djibian/alliage/pull/18#issuecomment-6585166865) :
**CORRECTIONS REQUISES** sur le HEAD initial
`e8b834ddee229173ac5e48cc88d17edb15408dbf`.

**C1 — Veto profil entier :** les autorisations sont bornées
par un seul onglet et une seule URL, mais le **refus** s'applique
à l'ensemble des requêtes interceptables du profil, y compris
les onglets nouvellement créés et les requêtes à `tabId`
inconnu. Ne pas limiter le `RequestFilter` au tab autorisé.
Une politique « onglet courant seulement » permettrait
à `target=_blank` et aux requêtes spéculatives de sortir
du périmètre.

**C2 — Défaillance :** le veto est inscrit de façon synchrone
au chargement de l'extension et démarre en `CLOSED`. Une
permission d'ouverture est unique, générationnelle et
non persistée. Cependant une extension désactivée, désinstallée,
révoquée ou arrêtée ne peut garantir elle-même l'annulation
de nouvelles requêtes. Exiger séparément la barrière OS et
le refus/expiration serveur. Ne pas confondre disponibilité
`ARMED`, refus effectif et effacement d'un DOM déjà affiché.

**C3 — Système :** un namespace réseau ne bloque pas forcément
les relais par fichiers-sockets Unix, FD hérités, proxies
ni les processus de l'hôte. Les preuves sont distinguées :
`NO_IP_EGRESS_FROM_TEST_NAMESPACE` n'implique pas
`NO_EXTERNAL_EGRESS_VIA_HOST_SERVICES`. La seconde
conclusion reste refusée sans inspection et contrôle des
possibles relais, potentiellement via isolation IPC/mount
et environnement déjà confiné. Ne jamais désactiver AppArmor.

**C4 — Témoins causaux :** employer des serveurs de test
**HTTP et HTTPS réellement joignables**, tous locaux et hors
Internet, pour distinguer « requête annulée par extension »
de « pas de route/DNS ». Le témoin **sans veto** doit recevoir
la requête ; le témoin **avec veto** ne reçoit rien ET
`onBeforeRequest` produit un `DENY` corrélé. Mesurer
également redirections, `target=_blank`, sous-frames,
requêtes spéculatives, WebSocket, protocoles locaux/non
HTTP et cas où JS est volontairement activé **uniquement
dans la fixture hostile isolée**. Jamais dans l'aperçu
professeur.

**Statuts de preuve non interchangeables :**
`BLOCKED_HTTP_REQUEST`, `NAVIGATION_COMMITTED`,
`SESSION_INVALIDATED`, `OS_EGRESS_DENIED`,
`UNOBSERVABLE`. Le dernier est un **NO_GO pour toute
revendication de confinement**. Une navigation commise,
même suivie d'invalidation, n'est pas une navigation bloquée.

**L1/L2, l'attestation de profil et L4 générale restent
ouverts même si cette conception est approuvée.**
