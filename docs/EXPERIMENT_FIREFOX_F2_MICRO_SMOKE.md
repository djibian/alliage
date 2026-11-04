# P3.6F2 — Premier essai Firefox réel, entièrement fictif

**État : PROTOCOLE PRÉPARÉ, NON EXÉCUTÉ, NON APPROUVÉ.** 4 novembre 2026.
**Base :** PR #19, HEAD approuvé **pour la simulation seulement**
`32af1710dc56c30b55aa961ed9ecfca318774c96`.
**Verdict de référence :** [contre-expertise indépendante F1 APPROUVABLE](https://github.com/djibian/alliage/pull/19#issuecomment-6629201343).
**Restriction absolue :** aucun HTML professeur réel, aucun dépôt pédagogique
privé, aucune extension installée sur le Firefox habituel, aucun merge/publication.

## 1. Question expérimentale UNIQUE

Dans **Firefox réel**, dans un environnement jetable sans accès réseau
externe préalablement attesté, le listener bloquant de la WebExtension
`experiments/p36f-extension/` empêche-t-il un GET vers le serveur
témoin B **pourtant joignable localement**, avant la réception HTTP ?

**On ne cherche pas encore** à démontrer la couverture globale de
Firefox, les schémas non HTTP(S), les pannes d'extension, la confidentialité
du HTML professeur, l'authenticité Quarto, ni le fonctionnement du
navigateur ordinaire.

La réussite est **nécessaire mais non suffisante** pour les étapes F3/F4.

## 2. Précondition bloquante : l'isolement AVANT le navigateur

**Voie privilégiée pour une première qualification : VM jetable
réellement déconnectée** (aucune carte réseau virtuelle, ni NAT/bridge/
host-only ; aucun partage de répertoire, presse-papiers ou
guest-agent/port-forwarding vers l'hôte). Cette configuration est
à vérifier sur la VM effective ; écrire « réseau désactivé »
sur une fiche ne suffit pas. Aucun navigateur connecté ne doit
être lancé par erreur pendant l'essai.

- Préinstaller Firefox et préparer une copie du **seul laboratoire
  fictif** dans la VM **avant** de déconnecter définitivement son
  accès réseau. Éventuellement employer un média ISO local préchargé,
  monté en lecture seule. Ne jamais importer un document privé ni
  fournir un partage de fichiers de l'hôte à la VM pendant l'essai.
- Avant Firefox, dans le système invité, relever : version de la VM,
  Ubuntu, Firefox, liste des interfaces et routes IPv4/IPv6, présence
  de proxies et de services de transport vers l'hôte.
  Les commandes de lecture `ip -br link`, `ip -4 route show`,
  `ip -6 route show`, `env | grep -i proxy` et
  `readlink /proc/self/ns/net` sont des indices, **pas** à elles
  seules une attestation de confinement des sockets Unix/IPC/FD.
- **Une seule interface activée : `lo`.** Aucune interface
  extérieure, route IPv4/IPv6, service proxy, socket hôte
  exploitable ou réseau de contournement ne doit subsister.
  Vérifier la configuration de la VM côté hôte et côté invité,
  sans utiliser le Firefox habituel pour le faire.
- Aucun réseau n'est nécessaire pour les deux serveurs HTTP
  `127.0.0.1` du banc, qui doivent **partager le réseau
  loopback de l'invité** avec Firefox. Le loopback doit être actif.
- En cas de doute sur les relais hôte, la VM, les permissions,
  les interfaces ou le profil : **`NO_GO_ISOLATION_UNPROVEN`** ;
  ne pas démarrer Firefox, ni activer `<all_urls>` sur l'hôte.
  Aucune commande ne désactive AppArmor ou le sandbox Firefox.

**Option alternative :** namespace réseau/mount/IPC Linux isolé
seulement si une preuve indépendante couvre les mêmes relais.
`unshare -n` seul ne démontre pas cette propriété et peut en
outre casser l'accès au serveur A/B sur le loopback de l'hôte.
Aucun script d'isolation privilégié n'est fourni dans F2.

## 3. Matériel déjà présent (aucun nouveau serveur requis)

Sur le HEAD épinglé :
- `experiments/p36f_fixture.py` : A, page fictive
  `http://127.0.0.1:18765/p36f-fiction/lesson.html`,
  et B, témoin `http://127.0.0.1:18766/probe`
  avec compteur `/stats`. Ces deux serveurs sont uniquement
  liés à `127.0.0.1`.
- `experiments/p36f-extension/manifest.json`, `policy.js`,
  `background.js`, `control.html`, `control.js` :
  extension Firefox MV3 **distincte** de `extension/` v0.4.
  Demande `<all_urls>`, `webRequestBlocking`,
  `webRequest`, `webNavigation` et `tabs`.
- `experiments/p36f-tests/` : tests Node **simulés seulement**.
  La suite F1 a été approuvée pour la simulation, **pas**
  pour un usage sur du HTML professeur.

Préférer l'installation **temporaire** depuis
`about:debugging` → « Ce Firefox » → « Charger un module
complémentaire temporaire » → `manifest.json`,
dans le **seul Firefox invité au profil vierge**.
Une extension temporaire disparaît au redémarrage et ne
reproduit pas exactement le parcours d'installation signée.
Il faut contrôler les permissions réellement accordées,
non se fier à la liste du manifeste.

La page A contient un lien classique vers B et un lien
`target="_blank"` vers ce même B. Les octets ne
contiennent aucune information enseignant.

## 4. Séquence de preuve minimale — essais distincts


### Audit obligatoire de la VM (G0-A, avant tout Firefox)

Cette porte exige **deux vérifications indépendantes** :
- **Côté hôte/hyperviseur :** inventaire de la configuration *effective* QEMU/KVM
  (liste des périphériques/channels en fonctionnement et non seulement du
  fichier de configuration) : NIC, NAT/bridge/host-only, vsock,
  virtio-serial, virtiofs/9p, SPICE/WebDAV, presse-papiers, partage
  de fichiers, guest-agent, USB réseau, redirections de ports, tunnels.
  **Aucun lien de données** de l'invité vers l'hôte/Internet n'est
  admissible pour cette expérience ; une présence ambiguë = NO_GO.
- **Côté invité :** inventorier interfaces et routes IPv4/IPv6, proxy
  configuré dans Firefox et dans l'environnement, montages, sockets
  Unix accessibles, agents, services et processus de relais, FDs hérités,
  et vérifier que seuls A/B et Firefox utiliseront le loopback de l'invité.
  Le nom `lo` ne suffit pas à attester l'absence de service hôte.
- **Traçabilité :** une fiche expurgée précise ce qui a été effectivement
  vérifié, les versions d'hyperviseur/OS/Firefox, le profil de périphériques
  et la décision `G0=PASS`. Ne pas publier la configuration du réseau privé.
  Si une preuve manque : `NO_GO_ISOLATION_UNPROVEN` **avant de lancer Firefox**.
- **Profils comparables :** G1 et G2 utilisent deux clones vierges
  d'un même gabarit local hors réseau (même Firefox, mêmes préférences,
  proxy/DNS, cache initial vide, politiques et paramètres de navigation).
  La seule différence permise pour G2 est l'extension temporaire F1,
  ses permissions et le contrôle d'armement. Conserver un inventaire
  comparatif expurgé des paramètres, sans réutiliser un profil habituel.

### Prévol (G0, bloque toute exécution en cas d'échec)

1. Identifier et consigner le SHA exact de la branche F2
   et la base F1 ; figer les sources servant à l'essai.
2. Attester les barrières de la §2 et l'absence de partage/
   proxy/route extérieure **avant lancement de Firefox**.
3. Vérifier qu'aucune autre extension utilisateur et aucun
   profil habituel ne seront utilisés ; aucun compte connecté.
4. Démarrer **dans l'invité uniquement** les deux serveurs
   fictifs (port A 18765, B 18766) ; ne pas exécuter leur
   commande sur l'hôte connecté. Vérifier B `/stats=0`
   avec un client HTTP local hors Firefox.

### Témoin négatif (G1 : B joignable PAR LE CLIC SANS veto)

1. Lancer Firefox dans l'invité **sans extension F1**, sous le
   premier profil vierge de G0. Charger la page fictive A :
   attester son rendu réel (titre `ALLIAGE_FICTION_ONLY`).
   Contrôler que les paramètres proxy/DNS sont ceux du gabarit.
2. Vérifier le lien exact `target="_blank"` pointant vers
   `http://127.0.0.1:18766/probe`. Ne déclencher aucune autre
   interaction ni requête volontaire vers B.
3. Lire **immédiatement avant le clic** `B /stats` depuis un client
   local extérieur à Firefox ; consigner `G1_B_BEFORE`.
   Cette lecture n'incrémente pas `/probe`.
4. Effectuer **un seul clic observable** sur le lien B depuis
   la page A ; identifier le nouvel onglet et vérifier que
   Firefox y affiche le corps exact `FICTIONAL_DECOY_RECEIVED`
   provenant de B (pas seulement une page d'erreur ou son URL).
5. Lire **après le clic** `B /stats` depuis le même client
   local ; consigner `G1_B_AFTER` et
   `G1_DELTA_B = G1_B_AFTER - G1_B_BEFORE`.
   Exiger `G1_DELTA_B > 0` **ET** le contenu exact affiché
   dans le nouvel onglet. Un compteur déjà positif avant le
   clic n'est pas une preuve : seul le delta observé compte.
6. Arrêter complètement Firefox et les deux serveurs ;
   redémarrer A/B afin de remettre le compteur B réellement
   à zéro. Vérifier `/stats=0` avant G2. Le profil G1
   ne doit plus être utilisé.

**Un seul des deux oracles manquant (delta ou contenu du nouvel
onglet) ⇒ `UNPROVEN_WITNESS_NOT_REACHABLE_BY_CLICK` ; arrêter.
En particulier, ne jamais accepter un simple `B /stats>0`
provenant d'une requête antérieure.**

### Essai positif (G2 : veto observé)

**Périmètre :** une seule action de clic, pas de seconde session,
pas de requête B volontaire concurrente, sources F1 intactes. Un
résultat sur le clic A→B ne peut être établi par un compteur
non attribuable à l'action.

1. Toujours dans la **même VM déconnectée**, ouvrir le **second
   clone vierge du même gabarit G0**. Confirmer la comparaison
   Firefox/proxy/DNS/politiques/profil avec G1 ; aucune autre
   extension. Installer temporairement **uniquement**
   `experiments/p36f-extension/` via `about:debugging`.
2. Confirmer la présence du listener et les permissions
   effectives, en particulier `permissions.contains`.
   `STATUS` doit démarrer fermé, `allowed=0`.
   Un défaut = `NO_GO_PERMISSIONS_OR_LISTENER`, pas de contournement.
3. Exécuter `OPEN_FICTION` (A=18765, B=18766).
   Vérifier le rendu réel de A dans Firefox,
   `allowed=1` après consommation de l'unique ouverture,
   et `permissionFailure=false`. Si la page A est absente :
   `NO_GO_F1_MAIN_DOCUMENT`.
4. **Avant le clic**, depuis le client local de l'invité relever
   `G2_B_BEFORE = B /stats` (doit être zéro après remise à
   zéro G1). Depuis la popup relever le `STATUS` **complet** :
   `allowed`, `denied`, `deniedHTTPB`,
   `deniedHTTPBLinkedTarget`, `unexpectedCommits`,
   `permissionFailure` et `armed`. Les valeurs absolues
   ne suffisent jamais : elles seront comparées à l'après.
   Vérifier une seconde fois les paramètres proxy/DNS.
5. Démarrer **avant le clic** une observation bornée de la
   navigation de l'onglet cible et de l'activité HTTP de B :
   - Idéalement une **trace indépendante des commits de
     navigation**, horodatée et restreinte à la seule fixture
     fictive, indiquant l'ID de l'onglet et sa destination ;
     préciser son outil exact et sa couverture réelle. Aucun
     outil ne sera ajouté à F1 sans revue distincte.
   - Observer séparément l'URL et le contenu réellement
     affichés dans l'onglet cible et conserver une trace
     expurgée de l'état des onglets. **La seule UI
     « page bloquée » et le compteur global
     `unexpectedCommits` ne prouvent pas l'absence
     de commit intermédiaire.**
   - Si aucun observateur indépendant de `onCommitted`
     pour B n'est disponible, la propriété « B jamais
     commise » est `UNPROVEN_COMMIT`. Ne pas saisir
     artificiellement `NO`.
6. Réaliser **un clic unique effectivement observé** dans A
   sur son lien `target="_blank"` vers B. Aucun rechargement
   ni nouveau `OPEN` pendant l'observation. Relever
   immédiatement `STATUS` complet et B `/stats` puis
   poursuivre jusqu'à quiescence.
7. **Fenêtre définie :** observer au maximum 15 secondes
   après le clic, avec un premier contrôle immédiat,
   puis lectures à environ 1, 2, 3 secondes et à la fin
   (ou jusqu'à 3 contrôles successifs à 1 seconde
   d'intervalle sans nouvelle activité Firefox liée à
   l'essai ni évolution de B). La quiescence exige
   la fin de la tentative réseau/navigation observable,
   une trace d'onglet stabilisée et **au moins trois lectures
   B indépendantes stables** ; si cette condition ne peut
   pas être démontrée dans la fenêtre, noter `UNPROVEN_QUIESCENCE`.
   Les mesures et leur instant réel sont consignés ; ne
   pas remplacer la stabilité par une lecture « immédiate »
   isolée. Un timeout ne prouve pas une absence définitive
   de requête future.
8. Relever **après stabilisation** le `STATUS` complet :
   `G2_DENIED_B_AFTER`, `G2_DENIED_LINKED_AFTER`,
   `G2_ALLOWED_AFTER`, `G2_UNEXPECTED_AFTER`,
   `G2_PERMISSION_FAILURE_AFTER`.
   Calculer `DELTA_DENIED_B = AFTER - BEFORE` ;
   exiger `DELTA_DENIED_B>0` après ce **seul clic**.
   Exiger `B /stats` inchangé entre avant et
   après (zéro), `allowed` inchangé (=1),
   `permissionFailure=false` en continu, absence
   de réinitialisation/réveil non contrôlé de l'event
   page, et absence de source concurrente de requêtes
   vers B. Sinon `UNPROVEN` ou `NO_GO` selon le défaut.
9. Relever indépendamment l'existence de commits de
   navigation vers B **pendant toute la fenêtre**.
   Si la preuve d'absence manque, `G2_COMMIT_B=UNPROVEN`
   et le verdict positif complet est indisponible.
   `unexpectedCommits` est seulement un indicateur
   global (pas un oracle B).
10. Vérifier séparément qu'un rechargement de A
    n'obtient pas une **deuxième** autorisation
    `GET/main_frame` ; distinguer cache, erreur UI
    et veto. Fermer le profil jetable.

**Chronologie A→B :** les champs actuels
`deniedHTTPBLinkedTarget` et `deniedHTTPB` ne contiennent
ni `requestId` ni horodatage d'événement ni preuve d'ordre
entre `onCreatedNavigationTarget` et
`onBeforeRequest`. **Ne pas revendiquer
`INTERCEPTION_OBSERVED_HTTP_LOCAL_LINKED_TARGET`
avec ces seules données.** Une instrumentation séparée,
revue indépendamment, sera nécessaire si ce niveau de
preuve devient utile.

**La condition « aucun commit B » n'est PASS que si
un observateur indépendant effectivement opérationnel
couvre toute la fenêtre.** En son absence, conserver
un résultat partiel `B_VETO_COUNTER_DELTA_OBSERVED`
et `UNPROVEN_COMMIT` ; ne pas assimiler ce résultat
à la qualification d'absence de navigation.

## 5. Verdicts falsifiables (non interchangeables)

| Conditions observées | Verdict maximal |
| --- | --- |
| Isolation hôte **ou** invité incomplète avant Firefox | `NO_GO_ISOLATION_UNPROVEN` ; aucun lancement |
| G1 : absence de delta B attribuable au clic **ou** mauvais contenu du nouvel onglet | `UNPROVEN_WITNESS_NOT_REACHABLE_BY_CLICK` |
| G2 : permissions/listener incertains | `NO_GO_PERMISSIONS_OR_LISTENER` |
| G2 : page A non rendue ou unique GET initial non admis | `NO_GO_F1_MAIN_DOCUMENT` |
| B reçoit un GET durant G2 | `NO_GO_HTTP_VETO` |
| B reste à zéro mais `ΔdeniedHTTPB≤0`, ou le clic n'est pas observable | `UNPROVEN_CLICK_CAUSALITY` |
| `ΔdeniedHTTPB>0`, B stable à zéro, G1 valide, mais non-commit sans oracle indépendant | `B_VETO_COUNTER_DELTA_OBSERVED ; UNPROVEN_COMMIT`, preuve partielle uniquement |
| Même cas et pas de quiescence vérifiée | `UNPROVEN_QUIESCENCE`, pas de preuve de non-réception définitive |
| G0/G1/G2 contrôlés, `ΔdeniedHTTPB>0` après clic unique, B sans réception à quiescence, `allowed`/permissions/génération stables, absence de commit B démontrée indépendamment | `INTERCEPTION_OBSERVED_HTTP_LOCAL_DESTINATION` (preuve locale bornée) |
| Compteur `deniedHTTPBLinkedTarget>0` sans trace `requestId` + chronologie fiable | **Aucun verdict renforcé** : `UNPROVEN_LINKED_TARGET` |

Le résultat plus fort
`INTERCEPTION_OBSERVED_HTTP_LOCAL_LINKED_TARGET` est
**désactivé dans F2** : les compteurs F1 n'en apportent
pas la causalité temporelle. Une preuve future exige une
instrumentation indépendante de l'événement de création et
du veto de la **même** requête, soumise à contre-revue.

**Aucun verdict F2, même positif, ne prouve le
confinement général Firefox ou de l'OS.** Les schémas
non HTTP, HTTPS, extension désactivée, relais hôte et
l'ensemble L1/L2/profil Quarto restent hors preuve.
La conclusion intermédiaire `B_VETO_COUNTER_DELTA_OBSERVED`
ne devient jamais un PASS général par simple interprétation.

## 6. Fiche de résultats (données entièrement fictives)

```text
F2_RUN_ID: <identifiant local non sensible>
GIT_F1_SHA: 32af1710dc56c30b55aa961ed9ecfca318774c96
GIT_F2_SHA: <SHA du protocole après revue>
FIREFOX_VERSION: <constatée dans la VM>
GUEST_OS: <version exacte>
VM_HYPERVISOR_DEVICE_INVENTORY: PASS / FAIL / UNPROVEN
VM_NO_HOST_CHANNELS: PASS / FAIL / UNPROVEN
GUEST_ONLY_LO_ACTIVE: PASS / FAIL
GUEST_IPV4_IPV6_ROUTES_ABSENT: PASS / FAIL
GUEST_MOUNTS_PROXY_FD_IPC_AUDITED: PASS / FAIL / UNPROVEN
G0_ISOLATION_RESULT: PASS / NO_GO_ISOLATION_UNPROVEN
G1_G2_PROFILE_PREFS_COMPARABLE: PASS / FAIL / UNPROVEN
G1_NO_EXTENSION_A_RENDERED: PASS / FAIL
G1_B_BEFORE: <entier>
G1_B_AFTER: <entier>
G1_DELTA_B: <entier strictement positif attendu>
G1_TARGET_TAB_SHOWS_EXACT_FICTIONAL_DECOY_RECEIVED: YES / NO / UNPROVEN
G2_PERMISSIONS_AND_LISTENER_CONFIRMED: PASS / FAIL
G2_EXTENSION_INITIAL_CLOSED: PASS / FAIL
G2_A_RENDERED: PASS / FAIL
G2_STATUS_BEFORE: <allowed, denied, deniedHTTPB, deniedHTTPBLinkedTarget, unexpectedCommits, permissionFailure, armed>
G2_B_BEFORE: <entier doit être zéro>
G2_ONE_CLICK_FROM_A_OBSERVED: YES / NO / UNPROVEN
G2_OBSERVER_IDENTITY_AND_COVERAGE: <outil précis ou UNPROVEN>
G2_OBSERVATION_WINDOW_SECONDS: <durée constatée, maximum 15>
G2_QUIESCENCE_3_STABLE_B_READS: PASS / FAIL / UNPROVEN
G2_B_AFTER: <entier>
G2_B_COUNT_SERIES: <séquence temporelle expurgée>
G2_STATUS_AFTER: <champs STATUS complets>
G2_DELTA_DENIED_HTTP_B: <entier>
G2_DELTA_DENIED_LINKED_TARGET: <entier, NON probant seul>
G2_ALLOWED_STABLE: PASS / FAIL
G2_PERMISSION_FAILURE_REMAINS_FALSE: PASS / FAIL
G2_NO_EVENT_PAGE_RESET: PASS / FAIL / UNPROVEN
G2_NAVIGATION_COMMITTED_TO_B: YES / NO / UNPROVEN
G2_NO_COMMIT_INDEPENDENT_EVIDENCE: PASS / UNPROVEN
G2_RELOAD_A_BLOCKED: PASS / FAIL / UNPROVEN
LINKED_TARGET_CHRONOLOGY: UNPROVEN (instrumentation absente)
RESULT: <verdict borné de §5>
LIMITATIONS: <faits observés uniquement>
```

**Publication :** archiver la fiche et des traces **expurgées**
dans GitHub uniquement après validation des preuves et de leur
caractère public. Ne jamais joindre un profil Firefox,
un jeton, un historique de navigation réel, une URL
enseignant privée ou une configuration du réseau domestique.
Une fiche `UNPROVEN` est un résultat honnête, non un
prétexte pour assouplir G0.

## 7. Portes et gouvernance

- **Présente PR :** protocole F2 et préparation uniquement.
  Aucune exécution Firefox, aucune installation de module,
  aucune modification OS et aucun échange réseau.
- **Avant exécution :** contre-revue indépendante du
  protocole, puis attestation pratique de la VM sans egress
  et accord explicite de l'utilisateur si une configuration
  locale/VM doit être modifiée.
- **Après un éventuel succès F2 :** soumettre les résultats
  empiriques à une revue indépendante avant toute
  généralisation ou réutilisation de cette protection.

### Sources d'API primaires

- MDN `webRequest.onBeforeRequest` :
  https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/webRequest/onBeforeRequest
- MDN `webNavigation.onCreatedNavigationTarget` :
  https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/webNavigation/onCreatedNavigationTarget
- Mozilla Extension Workshop, installation temporaire :
  https://extensionworkshop.com/documentation/develop/temporary-installation-in-firefox/

## 8. Amendements après contre-expertise du protocole (4 novembre 2026)

[Audit indépendant](https://github.com/djibian/alliage/pull/20#issuecomment-6630262624)
sur `581a31b4b50f0d119a30993c51f918511a51f614` :
**CORRECTIONS REQUISES**, sur des risques de faux PASS et non sur
un comportement Firefox exécuté.

- **C1** : G1 exige `B_after-B_before>0` **et**
  affichage du corps exact de B après un clic observable.
- **C2** : G2 relève le `STATUS` complet avant/après,
  calcule `ΔdeniedHTTPB`, contrôle `allowed`,
  `permissionFailure`, la stabilité d'event page et les
  paramètres proxy/DNS ; aucun compteur absolu ne prouve
  seul le clic.
- **C3** : observation bornée, quiescence à lectures B
  répétées, distinction entre compteur global de commits
  et preuve indépendante d'absence de commit B ; le
  défaut de cette preuve produit `UNPROVEN_COMMIT`.
- **C4** : retrait du verdict renforcé
  `...LINKED_TARGET` sans journal causal horodaté de
  la même requête ; instrumentation séparée seulement
  si elle apporte un gain expérimental démontré.
- **G0** : profil VM sans périphériques réseau ni canaux
  hôte et inventaire hôte/invité explicitement auditable,
  comparaison des profils G1/G2 depuis un gabarit identique.

**Statut inchangé** : revue indépendante du présent HEAD
corrigé nécessaire, aucune VM/Firefox lancée, aucun contenu
professeur réel, aucun privilège supplémentaire.

Ce protocole **ne rend aucune session professeur réelle accessible**.
