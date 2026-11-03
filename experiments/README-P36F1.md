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
