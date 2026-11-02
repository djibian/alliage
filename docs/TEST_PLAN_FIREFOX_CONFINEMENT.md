# P3.6F — Protocole de qualification Firefox et réseau (fixtures fictives)

**Statut : plan proposé, non exécuté.** Voir
[`ARCHITECTURE_FIREFOX_CONFINEMENT.md`](ARCHITECTURE_FIREFOX_CONFINEMENT.md).
Base PR #16, SHA `9f7a02d1b089a38b554af94aedaf8ca377da407a`.
PR #17 **APPROUVABLE uniquement pour la fixture fictive** au HEAD `b7bd1f7820dd72f45cb22dbf592ad0eb0d250192` ; la branche F0 reste indépendante de ses modifications, sans dépendance de fusion implicite.

## Règles de preuve

- Aucun essai ne charge un HTML, dépôt ou capture pédagogique privé.
- Une CI JavaScript/Python **ne prouve pas** un comportement Firefox.
- Un HTTP 404 sur le serveur local ne prouve pas que le navigateur
  n'a pas tenté de joindre une autre origine. Observer le serveur
  cible **et** le navigateur ; distinguer « bloqué par extension »
  de « inaccessible par la barrière OS ».
- Un `webNavigation.onBeforeNavigate` observé ne bloque **rien**.
  Une invalidation de session déclenchée APRÈS une transition n'est
  pas un blocage de navigation. Un veto n'est attesté que par
  **`DENY` corrélé avant réception** et témoin local joignable.
- Les requêtes `data:`/`blob:`/`file:` ne relèvent pas des mêmes
  événements que HTTP(S). Toute revendication hors du périmètre mesuré
  doit être explicitement classée `UNPROVEN`.
- Aucun journal public ne contient URL de capacité, fragment privé,
  HTML réel, corps de requête, token ou identifiant de session.
- Une réussite sur profil de qualification ne généralise pas à une
  installation Firefox habituelle avec extensions concurrentes.
- La qualification doit porter sur des versions Firefox et Ubuntu
  **exactes**, pas sur des noms génériques.

## 1. Fixtures et sources de preuve

**Fixture de référence :** HTML Quarto fictif `embed-resources:
true` rendu par Quarto réel (1.10.19/1.10.20 déjà qualifiés sur #16),
admis par P3.6D en une seule route. Port serveur éphémère.

**Fixture d'attaque dédiée :** un serveur HTTP test-only contenant
des liens sortants et des constructions malveillantes fictives
(pas d'accès au `quarto_teacher_http.py` réel pour ce contenu).
Ce serveur n'est accessible que dans l'espace de noms jetable et
n'est jamais relié à une session P3.6A réelle. La fixture d'attaque
peut être volontairement refusée par P3.6E : **ne jamais affaiblir le
filtre P3.6E pour tester le navigateur**.

**Serveurs leurres HTTP et HTTPS :** autres ports/origines
loopback, compteurs de réception sans collecte de secrets.
Chaque destination doit être **effectivement joignable** en
témoin négatif sans veto (profil isolé, toujours hors Internet)
puis non contactée lorsque le veto est armé.
Le HTTPS emploie un certificat de test que **seul le profil
jetable** sait vérifier (aucune autorité installée dans
le Firefox quotidien). Un échec de certificat sans veto
n'est PAS une preuve de blocage `webRequest`.

**Trace navigateur :** événements `webRequest` et `webNavigation`
convertis en événements structurés expurgés, avec codes
`ALLOW_MAIN`, `DENY_HTTP`, `NAVIGATION_COMMITTED`,
`SESSION_INVALIDATED`, `BLOCKER_NOT_READY`,
`PERMISSION_MISSING`, `OS_EGRESS_DENIED`,
`UNOBSERVABLE`, `SESSION_CLOSED`.
Ne jamais compter `SESSION_INVALIDATED` comme un refus
pré-réseau. Inclure la génération du banc et un identifiant
de tentative non sensible pour corréler veto et serveur témoin.
Éviter de publier les URL complètes ; un hash d'URL n'est pas une
mesure universelle d'anonymisation et n'est pas requis.

**Trace OS :** identité `/proc/<pid>/ns/net` du véritable
processus Firefox, de ses enfants réseau, des serveurs et leurres ;
interfaces et routes IPv4+IPv6, `veth`, proxies,
sockets hérités, sockets Unix liés à des chemins, canaux
IPC/mount vers l'hôte et éventuels relais de services.
Publier séparément `NO_IP_EGRESS_FROM_TEST_NAMESPACE`
et `NO_EXTERNAL_EGRESS_VIA_HOST_SERVICES` ;
en cas d'hypothèse non vérifiée, afficher `UNPROVEN`.
Exclure les chemins ou données privés des journaux.

## 2. Scénarios bloquants (F1/F2/F3)

| Test | Stimulus synthétique | Oracle Firefox | Oracle leurre | Verdict attendu |
| --- | --- | --- | --- | --- |
| N00 | Onglet neutre créé, extension `CLOSED` puis `ARMED` ; requête initiale autorisée exactement une fois | `main_frame` GET exact + tabId/génération ; HTTP 200 | 0 | PASS limité |
| N01 | Lien `#section` dans le même document | pas de nouvelle requête HTTP | 0 | PASS |
| N02 | Clic sur `http://127.0.0.1:AUTRE_PORT/escape` | veto bloquant, aucune navigation engagée | 0 | PASS |
| N03 | Clic sur autre chemin du **même port** | veto ; la navigation ne quitte pas l'HTML | 0 | PASS |
| N04 | Deux leurres **HTTP et HTTPS loopback joignables** avec origine/port distincts | témoin sans veto reçu ; avec veto `DENY` corrélé, aucune navigation commise | 0 avec veto | PASS borné HTTP(S) |
| N05 | `target=_blank` HTML sans JS ; `window.open` uniquement fixture hostile JS séparée | refus GLOBAL du profil depuis nouveau `tabId`, `DENY` ; une invalidation tardive = NO_GO | 0 | PASS si veto anticipé |
| N06 | Redirect HTTP 302 vers leurre joignable, URL autorisée ne conférant pas l'accès à la destination | `DENY` sur requête de destination, aucun accord implicite sur redirect | 0 | PASS conditionnel |
| N07 | Sous-ressource `img`/`link`/`iframe` HTTP(S), nouveaux frames, `tabId` ambigu | veto global, quelle que soit la provenance, permissions origine ET destination confirmées | 0 | PASS borné |
| N08 | WebSocket `ws:`/`wss:` fictif vers serveur local ; aucune activation JS dans la page professeur | séparer veto du handshake HTTP, trames et couverture réelle ; si non couvert `UNPROVEN` | 0 | PASS seulement si vérifié |
| N09 | `data:`, `blob:`, `file:`, `about:`, protocol handlers | `webRequest` non présumé couvrant ; observer commits et contamination | 0 | `UNOBSERVABLE` ⇒ NO_GO global |
| N10 | Navigation par menu, barre d'adresse ou historique ; nouvel onglet | distinguer transition `NAVIGATION_COMMITTED`, veto réel ou invalidation APRÈS ; cette dernière ne vaut pas PASS | 0 | PASS seulement avec prévention attestée |
| N11 | `meta refresh` externe, scripts de page coupés | pas de transition ; le banc hostile peut tester séparément le mécanisme sans JS | 0 | PASS |
| N12 | CSS/SVG contenant URLs de chargement fictives | veto des HTTP(S) générées ; risques de parsers/CSP explicités | 0 | PASS |
| N13 | Fermeture / retour arrière / restauration | aucun jeton réarmé ; pas de page sensible restaurée | 0 | PASS |

Une requête vers l'Internet public est **interdite pour le banc**.
Employer `example.invalid` comme destination syntaxique et des
terminaux loopback pour les preuves de réception ; ne jamais créer
un serveur tiers réel pour tester des fuites.

## 3. Scénarios de panne (F4/F5/F7)

| Test | Défaillance provoquée | Résultat accepté |
| --- | --- | --- |
| P00 | Permissions hôtes non accordées | aucun onglet d'essai lancé, `NO_GO` |
| P01 | `webRequestBlocking` absent | listener impossible → `NO_GO` |
| P02 | Listener non enregistré / tardif | `ARMED` impossible → `NO_GO` |
| P03 | Extension redémarrée / contexte MV3 évincé **après chargement** | écouteur top-level ré-enregistré, `CLOSED`, aucune ancienne génération réarmée ; barrière OS indépendante |
| P04 | Permission révoquée **après chargement**, puis clic externe | invalidation potentiellement tardive ; prouver indépendamment absence de livraison OS ; pas de PASS du veto si listener absent |
| P05 | Onglet fermé/remplacé, `tabId` réutilisé | ancienne autorisation non récupérable |
| P06 | Extension concurrente simulant redirection | le serveur leurre reste à zéro ; sinon NO_GO |
| P07 | URL de capacité réutilisée après fermeture | refus par le serveur et/ou invalidation de session |
| P08 | `webRequest` manque une catégorie de requête | `UNOBSERVABLE` pour le veto, test OS indépendant obligatoire |
| P09 | Journaux / événements d'extension | aucun token, sélection, HTML ou URL sensible exporté |
| P10 | Fenêtre habituelle Firefox déjà ouverte | le lanceur doit prouver le **profil distinct** |
| P11 | Tentative de restauration de session au redémarrage | refuser toute ancienne capacité non réarmée |

Pour P03–P08, un simple message dans les logs ne suffit
pas : vérifier également la destination et le niveau OS.
Une défaillance de veto n'est pas masquée par la seule réussite
de la barrière réseau ; consigner les deux résultats séparément.

## 4. Isolement réseau indépendant

L'isolation Ubuntu est une **obligation de qualification F3**,
à ne pas présumer disponible. La préparation de F3 nécessite :
- un processus Firefox et le serveur de fixture **dans le même
  namespace réseau** ; des namespaces différents casseraient la
  communication vers `127.0.0.1` ;
- uniquement `lo` dans ce namespace, aucune route externe
  IPv4/IPv6, aucun `veth` ou proxy donnant accès à l'hôte ;
  démontrer l'absence de sortie IP sans aucune requête publique ;
- un témoin négatif **sans veto**, toujours isolé :
  la page atteint réellement les leurres HTTP **et HTTPS**
  locaux (en veillant au certificat de test) ;
- un témoin positif avec veto : `DENY` corrélé, aucune
  réception par le leurre, absence de navigation commise ;
- vérifier les sockets de fichiers accessibles, les
  descripteurs hérités, les proxies, IPC et relais éventuels
  de services de l'hôte ; un simple namespace réseau peut
  être insuffisant. Si nécessaire, isoler aussi mount/IPC
  et l'environnement des processus sous revue spécifique ;
- arrêt de tous les processus et suppression du profil jetable.

Si les namespaces réseau sans privilège sont bloqués par
Ubuntu/AppArmor ou la distribution Firefox ne fonctionne pas
dans l'environnement testé : **NO_GO F3**, pas de « sudo »
implicite ni de désactivation de protections de l'ordinateur
de l'enseignant. Étudier ensuite un environnement VM/containeur
déjà disponible, avec revue de sécurité propre.

## 5. Critères d'acceptation et preuves à archiver

**F0 — présent (conception)** : architecture, matrice et menaces
publiées sur PR Draft ; revue indépendante de la pertinence
et du privilège `<all_urls>` ; rien de fonctionnel revendiqué.

**F1 — extension fictive** : les tests unitaires vérifient
strictement le prédicat d'autorisation HTTP sur des événements
synthétiques (bon port, mauvais port, chemin, tabId, frame,
type, origine absente, redirect, permission manquante).
Source JS et manifeste du banc vérifiés ; aucune modification
de la v0.4 ; **CI seule = comportement simulé**.

**F2 — Firefox réel** : journal de tests avec la version exacte
de Firefox, états handshake, décisions `allow`/`deny`,
destinations de navigation et compteurs serveur leurre.
La réussite des tests doit inclure un contrôle positif
(demande principale autorisée) **et un contrôle négatif**
(requête vers le leurre visible sans veto).
Aucune requête privée dans les logs.

**F3 — isolement OS** : deux verdicts distincts :
`NO_IP_EGRESS_FROM_TEST_NAMESPACE` si la preuve des interfaces,
routes, namespaces et processus est complète ; et
`NO_EXTERNAL_EGRESS_VIA_HOST_SERVICES` uniquement si
les canaux IPC/Unix/FD/proxy ont eux aussi été neutralisés
et leurs preuves contrôlées. Sinon `UNPROVEN`
pour cette propriété plus forte.

**F4 — composition et décision** : rapport
`GO_FICTIONAL_NETWORK_LAB` ou `NO_GO` avec exceptions précises ;
contre-expertise indépendante obligatoire. Cela n'ouvre
**jamais** les droits de vraie session professeur : L1
(provenance/consentement), L2 (confidentialité des octets HTML)
et attestation réelle du profil Quarto restent non satisfaits.

## 6. Conditions d'arrêt immédiat

- Une fixture de test se révèle être un document pédagogique réel.
- Un navigateur de test ouvre une origine externe ou une ressource
  privée sans que les permissions/isolations requises soient attestées.
- Le profil jetable n'est pas distinct du Firefox habituel.
- Les permissions ou la version de l'extension ont dérivé.
- Un processus du banc existe hors du namespace prévu.
- Les traces contiennent un secret, une capacité d'URL ou un
  contenu pédagogique privé.

**Aucune exécution Firefox ou commande réseau n'est demandée
au propriétaire pendant F0.**

## 7. Amendements opposables issus de l'audit F0

Source : [contre-expertise indépendante #18](https://github.com/djibian/alliage/pull/18#issuecomment-6585166865).

### Test initial, génération et permissions (C1/C2)

- Contrôler les permissions réellement accordées par Firefox
  (`permissions.contains`) pour les deux origines (initiateur,
  destination), pas seulement le texte du manifeste ;
  consigner la version Firefox MV3 exacte.
- Enregistrer le listener **global au profil** et le maintenir
  présent dans l'état `CLOSED` : il ne laisse passer
  aucune requête HTTP(S) interceptée. Pas de `tabId` dans
  le filtre du listener.
- Un onglet neutre est créé puis lié à un `tabId`, à une URL
  de capacité exacte et à une génération. Une seule requête
  `GET/main_frame` est autorisée ; permission consommée
  avant réponse. Un deuxième chargement, une destination
  après redirection ou une requête depuis un autre onglet
  est refusée.
- Tester l'arrêt/désactivation/révocation *après chargement*,
  pas uniquement avant l'ouverture. Sans extension,
  aucun veto extension n'est encore possible :
  `OS_EGRESS_DENIED` et expiration serveur sont des preuves
  distinctes, et le DOM déjà chargé n'est pas effacé.
- Vérifier qu'une reprise de l'event page MV3 ne restaure
  ni l'ancien tabId ni une ancienne génération d'armement.

### Oracles non confondus (C3/C4)

Chaque cas annonce séparément les états :
`BLOCKED_HTTP_REQUEST`, `NAVIGATION_COMMITTED`,
`SESSION_INVALIDATED`, `OS_EGRESS_DENIED`,
`UNOBSERVABLE`. Une invalidation après une navigation
commise est une **détection tardive**, jamais un
`BLOCKED_HTTP_REQUEST`.

Le témoin de blocage HTTP(S) exige une destination locale
JOIGNABLE (compteur > 0 sans veto), puis `DENY`
de la demande correspondant au même stimulus et compteur = 0
avec veto. La simple erreur DNS de `example.invalid`
ne démontre rien. Chaque cas HTTPS requiert une configuration
TLS de test complète sans modifier la configuration du
Firefox quotidien. La paire IP-only / relais services-hôte
produit deux conclusions indépendantes.

### Couverture additionnelle obligatoire

- `tabId=-1`, requêtes `speculative` et autres origines ;
- `target=_blank` sans JS, puis `window.open` uniquement
  dans une fixture hostile distincte activant JS ;
- HTTP 302, HTTPS, sous-frame, IPv6 loopback, WebSocket
  (handshake vs données), et schémas non HTTP ;
- proxies actifs/configurations navigateur, permissions révoquées,
  listeners absents, session expirée/restaurée, profils concurrents ;
- réseau et processus réels en namespace, sockets Unix liés à
  des fichiers accessibles depuis l'environnement Firefox,
  descripteurs hérités et relais IPC vers l'hôte.

**Toute preuve incomplète ⇒ `UNPROVEN` et pas de GO général.**
L1/L2, attestation du profil Quarto, accès réel professeur et
publication élèves restent toujours interdits.
