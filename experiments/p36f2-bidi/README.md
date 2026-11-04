# P3.6F2 — Observateur passif WebDriver BiDi (candidat, NON QUALIFIÉ)

**État : CODE DE LABORATOIRE, TESTS SYNTHÉTIQUES UNIQUEMENT.**
**Ne pas lancer sur l'ordinateur ou le Firefox habituel.**
**Aucun navigateur ni VM n'a été utilisé pour le développer.**

## Pourquoi cet observateur ?

[La contre-expertise F2](https://github.com/djibian/alliage/pull/20#issuecomment-6631168270)
approuve le protocole, mais le verdict complet exige une preuve
**indépendante** que B n'a pas été commis pendant toute la fenêtre.
L'extension F1 ne possède pas cette preuve. Une seconde extension
avec permissions supplémentaires ajouterait un risque de perturbation.

Firefox propose **WebDriver BiDi** avec l'événement
`browsingContext.navigationCommitted`. Cette instrumentation
**externe à F1**, activée par le navigateur de laboratoire lui-même,
est une **hypothèse à vérifier** sur la version exacte de Firefox.
Source : https://developer.mozilla.org/en-US/docs/Web/WebDriver/How_to/Create_BiDi_connection

## Périmètre effectif du code

- `observer.mjs` : Node.js **22**, WebSocket **natif**, sans paquet
  externe ni serveur auxiliaire. Se connecte **uniquement** à
  `ws://127.0.0.1:PORT/session`, à l'intérieur d'une VM déjà isolée.
- Commandes envoyées : `session.new`, `session.subscribe`,
  `browsingContext.getTree`. Aucune commande de navigation,
  de modification de pages, de scripts ou de configuration de Firefox.
- Événements observés : création/destruction de contextes,
  `navigationStarted`, `navigationCommitted`,
  `navigationFailed`, `navigationAborted`.
- Ne publie **jamais** les URL reçues hors des fixtures, ni les
  identifiants bruts de contexte, ni les identifiants de navigation.
  Les contextes sont pseudonymisés (`CTX_1`, `CTX_2`, ...),
  les destinations classées `A_FIXTURE`, `B_PROBE`,
  `OTHER_REDACTED`.
- L'observation ne peut être armée qu'après réponse positive
  de `session.subscribe` et `getTree` confirmant que A est
  présent. Le clic est effectué **manuellement**, après
  affichage `READY_SUBSCRIBED_BIDI` puis démarrage explicite
  d'une fenêtre **15 s**.
- Le programme émet **des observations**, jamais un verdict de
  confinement. Le succès du témoin G1 doit être corroboré par
  le compteur indépendant B et le rendu exact dans Firefox.

## Préparation possible, UNIQUEMENT après G0 approuvé

La commande ci-dessous est **documentée pour une utilisation
ultérieure dans la VM Ubuntu jetable effectivement isolée**.
Ne l'exécuter ni sur l'hôte connecté ni avant l'approbation
indépendante du présent code et de l'inventaire G0.

D'abord, dans le *guest* déjà isolé, Firefox doit avoir été lancé
dans son profil vierge de la phase (même option pour G1 et G2) :

```sh
firefox --remote-debugging-port 9222 --profile /chemin/absolu/du/profil-jetable
```

Ne pas réutiliser un Firefox déjà ouvert, ne pas démarrer de
Firefox avec un port de débogage accessible à d'autres machines.
La commande ne constitue **ni une isolation ni un certificat
d'absence de sortie réseau** ; l'argument `--profile` et la
compatibilité Ubuntu/snap doivent être validés sur l'invité.

Après ouverture de A, dans **l'invité exclusivement** :

```sh
node experiments/p36f2-bidi/observer.mjs --phase G1 --port 9222
# Pour l'autre profil de G2, après arrêt complet de Firefox G1 :
node experiments/p36f2-bidi/observer.mjs --phase G2 --port 9222
```

L'observateur attend un appui sur Entrée pour commencer
la fenêtre de 15 s ; **ne cliquer qu'après**
`OBSERVATION_WINDOW_STARTED`. Dans G1 sans extension,
le clic sur `target="_blank"` vers B doit faire apparaître
`browsingContext.navigationCommitted` classé B.
Dans G2 avec F1, l'absence de B ne sera interprétable que
si la connexion BiDi reste active et que G1 a démontré
la sensibilité de cet observateur sur la **même version
Firefox, avec les mêmes paramètres de débogage**.

Le programme n'automatise pas le clic et ne modifie pas F1.
G1 et G2 doivent conserver la comparabilité de profils et
l'observation du témoin B prévue par la PR #20.

## Règles de verdict / risques résiduels

- `G1_B_COMMIT_OBSERVED` : l'observateur a effectivement
  vu un commit B sur l'intervalle G1, **mais** G1 ne vaut PASS
  que si `ΔB>0` et si Firefox affiche
  `FICTIONAL_DECOY_RECEIVED`.
- `G2_B_COMMIT_NOT_OBSERVED_UNPROVEN_WITHOUT_G1` :
  événement absent, **pas** preuve autonome.
  Même après G1, seul le protocole F2 complet G0/G1/G2
  autorise un verdict limité HTTP local.
- `G2_B_COMMIT_OBSERVED` : le navigateur annonce un commit B,
  objection forte au verdict « non-commit ».
- `UNPROVEN_OBSERVER` : connexion interrompue, abonnement
  non confirmé, A non présent ou commit B avant la fenêtre ;
  aucune conclusion négative.
- L'ordre entre `webNavigation.onCreatedNavigationTarget`
  et `webRequest.onBeforeRequest` reste **non garanti**.
  Le verdict `LINKED_TARGET` reste **désactivé**.
- Une connexion de débogage peut modifier le comportement du
  navigateur. Comparer G1 et G2 dans le même mode, vérifier
  l'absence d'effet perturbateur et archiver cet écart
  potentiel ; ne pas prétendre généraliser au Firefox ordinaire.
- **Bug ou lacune éventuels** des événements Firefox : un flux
  silencieux est `UNPROVEN`, jamais une absence de navigation
  certifiée sans le témoin G1 et une couverture continue.
- Le port BiDi doit rester **local à l'invité**, jamais exposé
  à l'hôte ou au réseau. Il donne de larges pouvoirs
  d'automatisation au client local et doit être arrêté
  en même temps que le profil jetable.

## Preuve automatisée existante

```sh
node --test experiments/p36f2-bidi/observer.test.mjs
```

Cette commande teste seulement le classement des événements
**fictifs injectés en mémoire** : G1 positif, G2 silencieux
non probant, erreurs et fermeture du transport, événements
antérieurs, anonymisation et refus d'URL WebSocket
arbitraires. Elle ne lance ni Firefox ni réseau.

**Prochaine porte :** contre-expertise indépendante du
code observateur et de sa non-perturbation, puis attestation
réelle G0 avec consentement du propriétaire de l'hôte
avant toute VM/Firefox. Le maintien de la PR #20 comme
protocole approuvé n'implique aucune exécution.
