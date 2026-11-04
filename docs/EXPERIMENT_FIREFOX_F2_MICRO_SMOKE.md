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

### Témoin négatif (G1 : B est joignable SANS veto)

1. Dans un Firefox invité **sans l'extension F1**, ouvrir
   la page A. Vérifier un rendu réel, pas seulement HTTP 200
   obtenu par un autre client.
2. Cliquer sur le lien `target=_blank` vers B `/probe`.
3. Lire B `/stats` depuis un **client HTTP local externe
   à Firefox**, toujours dans l'invité : le compteur doit
   être **strictement > 0**. Noter si le nouvel onglet a
   effectivement affiché la réponse de B.
4. Arrêter complètement Firefox et A/B. Redémarrer A/B
   pour **réinitialiser réellement** B à zéro. Vérifier
   `/stats=0` avant l'essai positif.

**Si le témoin négatif ne parvient pas à B, arrêter :
`UNPROVEN_WITNESS_NOT_REACHABLE`.** L'absence de réception
par B lors de l'essai positif serait alors non interprétable.

### Essai positif (G2 : veto observé)

1. Toujours dans la **même VM déconnectée**, utiliser
   un **nouveau profil Firefox jetable**, sans extension
   de tiers. Installer temporairement **seule**
   `experiments/p36f-extension/` via `about:debugging`.
   Ne jamais installer `extension/` v0.4 ici.
2. Dans la popup F1, relever `STATUS` initial
   (`CLOSED`, `allowed=0`). Vérifier dans le
   processus d'extension l'inscription du listener et
   `permissions.contains` : si un droit manque,
   **NO_GO** ; aucune relaxation de permissions ni
   chargement direct de A en contournant le contrôle.
3. Utiliser `OPEN_FICTION` avec les ports A=18765
   et B=18766. Vérifier visuellement que la page
   fictive A est effectivement chargée, puis contrôler
   l'autorisation unique : `allowed=1` (après
   sa consommation), sans deuxième exception.
4. Relever B `/stats=0` avec le client local hors
   Firefox. Cliquer **une seule fois** sur le lien
   `target=_blank` de A vers B, sans autre clic.
   Relever immédiatement `STATUS` et B `/stats`.
5. Observer si B a reçu la requête, si une navigation
   vers B a été **commise** (pas seulement tentée),
   et si `deniedHTTPB` puis éventuellement
   `deniedHTTPBLinkedTarget` ont augmenté.
   Noter explicitement l'ordre
   `onCreatedNavigationTarget` /
   `onBeforeRequest` si observable **sans journaliser
   d'URL ni contenu sensible**. La documentation MDN
   garantit un ordre avec `onBeforeNavigate`, pas
   avec `onBeforeRequest`.
6. Réessayer le chargement initial A : une **seconde**
   autorisation `GET/main_frame` ne doit pas être
   obtenue par un simple rechargement. Ne pas confondre
   cache/erreur UI et refus `webRequest`.
   Fermer l'extension et le profil.

## 5. Verdicts falsifiables (non interchangeables)

| Conditions observées | Verdict maximal |
| --- | --- |
| Isolation non attestée avant Firefox | `NO_GO_ISOLATION_UNPROVEN` ; ne pas démarrer |
| B inaccessible SANS veto | `UNPROVEN_WITNESS_NOT_REACHABLE` |
| A pas réellement chargé avec l'extension | `NO_GO_F1_MAIN_DOCUMENT` |
| B reçoit un GET avec veto | `NO_GO_HTTP_VETO` |
| B=0 mais aucun refus B observable, ou permissions incertaines | `UNPROVEN` |
| B=0, `deniedHTTPB>0`, aucune navigation B commise, témoin négatif OK | `INTERCEPTION_OBSERVED_HTTP_LOCAL_DESTINATION` (preuve bornée, attribution de cible potentiellement incertaine) |
| Cas précédent ET `deniedHTTPBLinkedTarget>0`, avec événement A→B de l'essai courant observé avant veto | `INTERCEPTION_OBSERVED_HTTP_LOCAL_LINKED_TARGET` (preuve plus forte, toujours locale) |
| Événement de création après veto, lien attribué absent | `UNPROVEN_LINKED_TARGET` même si le veto B peut être observé par ailleurs |

Le compteur `deniedHTTPB` est **un indicateur de la
décision du listener**, pas une preuve OS. Le compteur lié
est une **corrélation d'événements**, pas une garantie
que les événements arrivent dans cet ordre pour toutes
les versions Firefox. Le serveur B indépendant et
l'absence de commit complètent l'oracle ; aucune mesure
isolée ne suffit à généraliser.

**La seule conclusion positive possible en F2 est
`INTERCEPTION_OBSERVED_HTTP_LOCAL*`.** Elle ne certifie
ni HTTPS ni les schémas non HTTP, ni l'absence globale de
sortie de Firefox/du système. F3 (réseau et relais OS)
et F4 (composition) restent des portes distinctes ;
L1/L2/attestation Quarto restent non résolues.

## 6. Fiche de résultats à renseigner (aucune donnée personnelle)

```text
F2_RUN_ID: <identifiant local non sensible>
GIT_F1_SHA: 32af1710dc56c30b55aa961ed9ecfca318774c96
GIT_F2_SHA: <sha complet du protocole audité>
FIREFOX_VERSION: <version constatée dans l'invité>
GUEST_OS: <version exacte>
ISOLATION_HOST_VERIFIED: PASS / FAIL / UNPROVEN
GUEST_ONLY_LO_ACTIVE: PASS / FAIL
GUEST_IPV4_IPV6_ROUTES_ABSENT: PASS / FAIL
GUEST_HOST_RELAY_EXCLUDED: PASS / FAIL / UNPROVEN
G1_NO_EXTENSION_A_RENDERED: PASS / FAIL
G1_NO_EXTENSION_B_COUNT_AFTER_CLICK: <entier>
G2_EXTENSION_PERMISSION_CONTAINS: PASS / FAIL
G2_EXTENSION_INITIAL_CLOSED: PASS / FAIL
G2_A_RENDERED: PASS / FAIL
G2_ALLOWED_ONCE: PASS / FAIL
G2_B_COUNT_BEFORE: <entier>
G2_DENIED_HTTP_B: <entier>
G2_DENIED_HTTP_B_LINKED_TARGET: <entier>
G2_B_COUNT_AFTER: <entier>
G2_NAVIGATION_COMMITTED_TO_B: YES / NO / UNPROVEN
G2_RELOAD_A_BLOCKED: PASS / FAIL / UNPROVEN
RESULT: <verdict précisément borné ci-dessus>
LIMITATIONS: <constats vérifiés, sans inventer une preuve>
```

**Publication :** conserver cette fiche et les traces
expurgées dans une issue/PR après validation des preuves.
Ne jamais joindre un profil Firefox, un historique de
navigation privé, un jeton, une URL de capacité privée,
une capture de contenu enseignant ou une configuration
du réseau domestique.

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

Ce protocole **ne rend aucune session professeur réelle accessible**.
