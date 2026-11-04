# P3.6F1 — Lab Firefox MV3, HTTP fictif uniquement

**Statut : `F1_UNIT_ONLY / INTERCEPTION_UNPROVEN`.**
**Ne pas installer l'extension dans le Firefox personnel ou scolaire.**
Ce laboratoire expérimental **n'est pas un mécanisme de confinement
validé**, même si toutes ses simulations et tests loopback sont verts.
Base : P3.6F/F0 approuvée (PR #18), sœur de P3.6E (PR #17).
Aucun contenu professeur réel ne doit être utilisé.

## Périmètre livré

- `experiments/p36f-extension/` : extension **Firefox MV3 séparée**,
  avec `background.scripts`, un veto `webRequest.onBeforeRequest`
  global (`{urls:["<all_urls>"]}`, `["blocking"]`) enregistré
  **au top-level, même CLOSED** ; `webNavigation` seulement
  pour observation, aucune transformation de contenu HTML.
- `policy.js` : état mémoire fermé au lancement et au redémarrage,
  génération éphémère, refus par défaut de tout événement intercepté
  sauf **un seul** `GET/main_frame` à
  `http://127.0.0.1:PORT/p36f-fiction/lesson.html`
  depuis le `tabId` initialement armé (`frameId=0`).
  Permission consommée AVANT de retourner `{cancel:false}`.
  Aucun stockage persistant, aucune exception pour les nouveaux
  onglets, frames, images, requêtes spéculatives ou URLs secondaires.
- `background.js` : contrôle des permissions et du listener
  avant l'armement, fenêtre neutre `about:blank` créée avant
  d'autoriser son tabId ; dialogue limité à `control.html`
  propre à l'extension. Les traces n'incluent aucune URL/capacité.
  Une erreur, permission manquante ou révocation connue ferme le
  droit ; si l'extension est **désactivée ou arrêtée**, elle ne peut
  plus annuler aucune requête. Seule une barrière **OS indépendante**
  pourrait traiter ce cas.
- `experiments/p36f_fixture.py` : deux serveurs HTTP fictifs
  **liés exclusivement à `127.0.0.1`**. A fournit le document
  avec un lien vers B ; B reçoit les demandes `GET /probe`
  et fournit un compteur `GET /stats`. Ce sont des témoins,
  non une isolation.
- `experiments/p36f-tests/` : tests Node natifs de la politique
  et simulations d'API d'extension, **pas un Firefox réel**.
  `tests/test_p36f_fixture.py` : témoin A/B réellement
  joignable par HTTP local et décompte sans veto, **pas de
  démonstration de blocage navigateur**.

La WebExtension demande `<all_urls>` et des permissions puissantes
(`webRequestBlocking`, `webRequest`, `tabs`,
`webNavigation`) **uniquement dans ce dossier expérimental**.
Elles pourraient permettre de voir/bloquer les requêtes de
nombreux sites : permissions de banc, **jamais** celles de la
v0.4 quotidienne. Aucun content script ni échange avec une IA.

## Épreuves couvertes / non couvertes

**CI unitaires :** commandes de vérification reproductibles
sans dépendance npm externe :

```bash
node --test experiments/p36f-tests/*.test.cjs
python3 -m unittest discover -s tests -p 'test_p36f_fixture.py' -v
```

Cela vérifie la logique **simulée** : démarrage CLOSED,
consommation unique, URL exacte, mauvais onglet,
`tabId=-1`, frame, méthode, permissions absentes,
nouveau chargement et fermeture. Le serveur local A/B
prouve que B est joignable sans veto. **Le chiffre
`FIREFOX_INTERCEPTION=UNPROVEN` doit rester affiché.**

**NON démontrés par F1 unité :** autorisations effectivement
accordées sur Firefox réel, fonctionnement du listener
MV3 au réveil, `target=_blank` réel, blocage du serveur B
dans le navigateur, redirections, HTTPS, DNS, WebSocket,
schémas non HTTP, désactivation après chargement, confinement
de tout le trafic, isolement OS Ubuntu et absence de fuite
par sockets ou services de l'hôte. Les tests du navigateur
sont **F1 micro-smoke/F2**, ceux du système **F3**.

## Porte opérationnelle avant micro-smoke Firefox réel

**NE PAS exécuter l'extension Firefox hors d'une isolation déjà
attestée**, même avec une fixture fictive. En particulier :
- Firefox et les deux serveurs témoins doivent partager un
  environnement isolé **sans sortie Internet depuis le début**,
  profil Firefox neuf, aucune autre extension ;
- la permission `<all_urls>` demande un accord conscient pour
  ce profil jetable ; vérifier `permissions.contains` en runtime ;
- prouver séparément les compteurs B sans veto
  (`requests_received>0`) et avec veto
  (`DENY` corrélé, `requests_received=0`) ;
- consigner si la requête B est réellement bloquée et si une
  navigation a été commise ; la seule invalidation ultérieure
  n'est jamais `BLOCKED_HTTP_REQUEST` ;
- pour une sécurité OS forte, vérifier aussi relais/FD/IPC/Unix
  conformément à F0. En l'absence de cet environnement,
  **ne pas démarrer le smoke et conserver `UNPROVEN`**.

Les ports par défaut A=18765 et B=18766 ne sont pas secrets.
Les pages sont entièrement fictives. La commande
`python3 experiments/p36f_fixture.py` **ne crée PAS**
l'isolation OS ; elle ne doit être lancée que par le futur
protocole de smoke isolé, après revue indépendante.
Ne jamais utiliser `p36b_fictional_firefox_demo.py` ou le
serveur des ressources pédagogiques réelles pour une
fixture hostile.

## Gouvernance

P3.6F1 ne modifie ni `extension/` v0.4, ni le serveur
professeur P3.6D, ni Quarto, ni les PR #17/#18.
Pas de merge, pas de publication élève, pas d'usage du
véritable contenu enseignant. Même une interception
Firefox observée ne clôturerait pas L1/L2/L4 global
ou l'attestation du profil Quarto.

## Correctif C2 et oracle B — contre-expertise du 3 novembre 2026

[Rapport indépendant P3.6F1](https://github.com/djibian/alliage/pull/19#issuecomment-6588821737)
sur le HEAD initial `133216f99844b7843e2ec9d7dda2d1fe1e40ce5a` :
**CORRECTIONS REQUISES**, avec un contournement reproductible du
contrat de fermeture dans un modèle asynchrone : `OPEN_FICTION`
suspendu pendant `permissions.contains` pouvait réarmer après
un `CLOSE` déjà confirmé. Deuxième réserve : un simple compteur
global `denied` ne relie pas une requête rejetée à B.

**Corrections sur la même branche, aucun Firefox réel :**
- Une génération éphémère `generation` reste liée au processus
  d'event page ; une nouvelle **époque d'opération `epoch`**
  invalide synchroniquement toute continuation en cours lors
  de `CLOSE`, d'un second `OPEN_FICTION`, d'une fermeture de
  l'onglet surveillé, d'un commit HTTP inattendu et d'une notification
  `permissions.onRemoved`.
- Le jeton d'opération est vérifié **après chacun des `await`**
  (`permissions.contains`, `tabs.create`, second contrôle des
  permissions et `tabs.update`). Un ancien `OPEN` ne
  peut plus appeler `arm` ni retourner un succès après révocation
  (résultat `NO_GO_REVOKED`). Les tests utilisent des Promises
  à résolution contrôlée, pas des temporisations fragiles.
- La popup accepte un port distinct pour le témoin B
  (par défaut 18766). Le listener ne compte `deniedHTTPB`
  que lorsque **`details.url` est exactement**
  `http://127.0.0.1:B/probe`, méthode `GET`, et que
  le veto renvoie effectivement `cancel:true`.
  `deniedHTTPBNewTab` isole les tentatives `main_frame`
  provenant d'un autre `tabId`. Les URL/capacités exactes
  ne figurent jamais dans `STATUS`, qui ne publie que des
  compteurs fictifs.
- Les compteurs du témoin B sont **réinitialisés par nouvel
  `OPEN_FICTION`** mais conservés après `CLOSE` pour
  permettre de consulter les résultats de l'essai arrêté.
  Une hausse du compteur ne prouve **pas seule** le
  confinement. Il faut conjointement démontrer que le
  serveur B est joignable **sans veto**, puis que
  `deniedHTTPBNewTab` augmente avec le veto ET que
  B ne reçoit rien et qu'aucune navigation n'est commise.
- `permissions.onRemoved` réduit la fenêtre logique de
  révocation pendant le fonctionnement de l'extension. Une
  extension totalement arrêtée/désinstallée ne peut toujours
  pas garantir son propre blocage : isolement réseau OS
  indépendant et tests dans Firefox réel demeurent requis.

**Tests ciblés :** fermeture pendant chacune des opérations
asynchrones, second `OPEN` concurrent, fermeture d'onglet
pendant `tabs.update`, commit de navigation inattendu,
notification de révocation de permission, refus B ciblé
et non-confusion avec les autres requêtes. Les deux tests
du serveur A/B sont inchangés : B demeure joignable sans veto.

La qualification du **HEAD documentaire final** est à recontrôler
en CI après cette mise à jour. Jusqu'à observation Firefox
dans un environnement sans sortie Internet :
**`F1_UNIT_ONLY / INTERCEPTION_UNPROVEN`**.
L1/L2/L4 réel et attestation du profil Quarto demeurent
non qualifiés ; aucun contenu professeur privé ne peut être
ouvert ou servi.

### Limite de linéarisation et précision des observations

`CLOSE` invalide toutes les **autorisations futures** et
continuations asynchrones déjà suspendues. Il ne peut
**annuler rétroactivement** un `GET` qui a déjà obtenu
`cancel:false`, une connexion déjà transmise, ou les
octets d'une page déjà chargée. La qualification Firefox
doit provoquer et observer séparément ce scénario ;
l'autorité de révocation serveur et l'isolation OS
restent des protections indépendantes.

Le champ `deniedHTTPBNewTab` ne compte comme « autre onglet »
qu'un `main_frame` avec `tabId` entier positif
**connu et distinct** de l'onglet observé. Les requêtes
`tabId=-1` ou `tabId` absent restent dans
`deniedHTTPB`, mais ne sont pas attribuées à un
nouvel onglet : cette distinction est testée explicitement.
Aucune métrique de veto simulé ne remplace le compteur
réel du serveur B.

## Deuxième contre-expertise — fermeture de tab avant ID et attribution à l'essai

La [contre-expertise finale](https://github.com/djibian/alliage/pull/19#issuecomment-6614286095)
sur `2cdbe51f5e5558a6abf077770887fd75ac986d61`
conclut **CORRECTIONS REQUISES**. Les corrections
`OPEN → CLOSE` et l'identification de la destination B
étaient conformes, mais deux garanties plus précises
restaient réfutables dans un navigateur simulé :

1. Une notification `tabs.onRemoved(id)` pendant la
   suspension de `tabs.create()`, **avant** que
   l'ID soit connu, pouvait être ignorée. À la reprise,
   l'ancien `OPEN` réarmait cet onglet fermé.
2. Un simple `tabId` différent du tab A ne lie pas une
   requête B à la navigation `target=_blank` de
   **l'essai courant** : un ancien onglet ou un onglet
   préexistant pouvait alimenter le compteur « NewTab ».

**Correctifs ciblés, sans nouveau privilège :**

- `pendingCreateTicket` identifie **l'opération** en cours
  de `tabs.create`, même avant de connaître l'ID.
  **Toute fermeture d'onglet** pendant ce délai
  révoque conservativement l'essai : s'il s'agissait
  d'un onglet sans rapport, le test peut échouer par
  sur-refus, mais il ne réarme jamais un onglet fermé.
  Le ticket est contrôlé après la résolution de la
  Promise ; `CLOSE`, une nouvelle ouverture et les
  révocations précédentes invalident aussi l'attente.
- Un listener d'**observation uniquement**
  `webNavigation.onCreatedNavigationTarget` est
  enregistré. Seul un événement avec `sourceTabId`
  égal au tab A **courant**, `sourceFrameId=0`,
  `url` égale au GET B fictif exact et un
  `tabId` cible valide/distinct ajoute une cible
  à un ensemble **éphémère**. Un GET B `main_frame`
  effectivement refusé consomme cette cible au
  plus **une fois**, incrémentant le compteur
  `deniedHTTPBLinkedTarget`.
- Le compteur `deniedHTTPB` reste un indicateur
  brut du refus de **cette destination**, sans
  promesse d'appartenance à l'essai courant.
  Le **nouveau** champ `deniedHTTPBLinkedTarget`
  **remplace** l'ancien `deniedHTTPBNewTab`, qui
  déduisait abusivement « nouvel onglet » de
  `tabId != tabForObservation`. Les preuves
  historiques basées sur cet ancien compteur
  ne sont **pas valables** pour une attribution.
- `revoke()`, fermeture de cible et nouvel
  `OPEN` effacent les cibles observées. La
  présence du listener `webNavigation` ne
  crée **aucune capacité d'annulation** :
  seul `webRequest` peut refuser une requête
  dans la catégorie effectivement interceptée.

**Tests nouveaux :** notification `onRemoved`
avant résolution de `tabs.create` puis
`NO_GO_REVOKED`, fermeture non attribuable
pendant la création, ancien GET B après deux
`OPEN`, anciens onglets non liés, origine/frame
et URL de destination incohérentes, cible
fermée et `CLOSE`, consommation unique du lien
de navigation. Tous sur fixtures fictives.

**Condition stricte de preuve :** si
`onCreatedNavigationTarget` ne précède pas
le veto `onBeforeRequest` réel, si les
notifications arrivent trop tard, ou si la
provenance reste ambiguë, le compteur attribué
peut **rester à zéro** : l'expérience est alors
`UNPROVEN`, et non un PASS obtenu en réintroduisant
l'inférence par un tabId différent.

L'expérience HTTP réelle nécessite toujours
le témoin B joignable **sans veto**, puis
`DENY` ciblé et associé à la cible,
zéro réception serveur B et aucune
navigation B commise avec veto.
Le navigateur doit être isolé **avant lancement**,
avec des ressources entièrement fictives.
Les appels d'API Node simulés ne prouvent
pas ce comportement Firefox. L1/L2/L4 globale
et le profil professeur restent hors périmètre.

## Troisième contre-expertise — notifications tardives après fermeture (4 novembre 2026)

La [contre-expertise indépendante de la PR #19](https://github.com/djibian/alliage/pull/19#issuecomment-6626556643)
sur le HEAD `4424a75a3b2e0a758a0fed2e9564721bac217e7a`
conclut **CORRECTIONS REQUISES** sur une seule objection résiduelle.
La fermeture d'onglet AVANT résolution de `tabs.create` et la
correction principale de la liaison A → B sont **PASS en simulation**.

**Nouveau contre-exemple :** dans une seule époque,
`tabs.onRemoved(70)` peut précéder la notification tardive
`webNavigation.onCreatedNavigationTarget(A → B, tabId=70)`.
Auparavant, la suppression d'un ID absent de `linkedTargets`
était sans effet : la création tardive pouvait réinsérer 70
et l'oracle attribuait abusivement le refus d'un `GET B`
à une cible encore vivante.

**Correction minimale :** ajouter `removedTargets`,
ensemble éphémère des identifiants positifs signalés par
`tabs.onRemoved` pendant un essai actif, **y compris avant
leur éventuel lien A → B**. L'événement
`onCreatedNavigationTarget` refuse de réinsérer une cible
présente dans cet ensemble. `revoke()`, `CLOSE` et un
nouvel `OPEN` le purgent avec les autres observations de
l'époque. Les fermetures pendant `tabs.create` continuent
de révoquer totalement l'opération, sans assouplissement.

**Régressions déterministes sur la vraie fonction simulée** :
`onRemoved → onCreatedNavigationTarget tardif → veto B`
implique `deniedHTTPBLinkedTarget === 0`, tout en
conservant le compteur brut `deniedHTTPB === 1`.
Cas également couverts : liaison d'abord, fermeture, puis
notification de création répétée ; époques successives et
absence de réattribution depuis l'ancien onglet source.

**Limites inchangées :** un `tabId` peut être inconnu,
des notifications Firefox peuvent être livrées dans un
ordre différent, et le listener `onCreatedNavigationTarget`
n'est pas garanti être appelé avant le veto
`webRequest.onBeforeRequest`. L'oracle lié à l'essai
doit alors rester **UNPROVEN**, sans inférer de succès du
seul compteur brut. Les tests Node et la CI ne sont pas
une preuve d'interception Firefox, ni de confinement
réseau OS. Aucune installation sur Firefox habituel,
aucune ressource professeur réelle, aucune fusion ni
publication élève.

**Porte suivante :** CI sur le HEAD documentaire final,
puis contre-revue indépendante strictement limitée aux
tombstones, à leur purge par époque et aux anciens invariants ;
ensuite **seulement préparation** d'un essai Firefox fictif
dans un environnement sans sortie Internet attesté avant
démarrage.
