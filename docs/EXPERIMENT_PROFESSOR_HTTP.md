# P3.6B — Lecteur HTTP de sortie professeur : preuve fictive avant toute exposition privée

**Statut : expérimentation Draft.** PR #14 empilée sur la PR #13 ; cette
dernière a réussi le rendu réel professeur local sur Ubuntu, mais ne possède
toujours aucun droit de diffusion en HTTP ou Firefox.

## Hypothèse et décision expérimentale

Le prototype historique `quarto_local_http.py` sert deux révisions Quarto
*monopages fictives* ; il ne saurait attester, par simple changement de chemin,
un rendu multi-QMD `dist/professeur/`. Cet incrément crée un transport de
lecture minimal pour **des sessions P3.6A fictives uniquement**. Un contrôle
bloquant exige une identité de ressource `quarto:fiction/...` dans le manifeste.
Ce marqueur est **un verrou de laboratoire, pas une autorisation fiable** pour
des documents réellement privés puisque le manifeste n'est pas signé.

Le lecteur `quarto_teacher_http.py` n'accède ni à Git, ni au moteur Quarto,
ni à une API IA ; il n'écrit ni ne publie de ressource.

## Frontières observables

1. **Admission :** `verify_session()` rehash l'inventaire de sortie P3.6A et
   contrôle l'HTML attendu ; le lecteur vérifie ensuite l'identité fictive.
   Le manifeste de session est une déclaration locale et n'est pas signé.
2. **Routes :** le serveur écoute seulement `127.0.0.1` sur un port éphémère.
   Un préfixe secret aléatoire de 128 bits limite l'accès aux seules routes
   préénumérées dans `rendered_files`, sous `dist/professeur/`.
   Tous les octets retournés sont revérifiés avec le SHA-256 d'inventaire.
3. **Exclusions :** aucun accès aux blobs Git, `.qmd`, manifeste,
   `dist/eleve/`, sortie hors inventaire, traversal, symlinks de chemin ou
   méthode d'écriture. Pas de routes API et pas de logs du préfixe privé.
   Un fichier source/configuration copié par Quarto **à l'intérieur** de
   `dist/professeur/` n'acquiert pas pour autant un droit d'accès :
   fichiers `.qmd`, `.md`, `.ipynb`, YAML, scripts Python/Lua/shell,
   noms cachés et `manifest.json` provoquent le refus de la session entière,
   même si leur SHA-256 figure dans l'inventaire. Cette liste n'est pas
   une analyse sémantique de tous les actifs : le HTML et les ressources
   publiables peuvent eux-mêmes contenir du texte réservé à l'enseignant.
4. **HTTP navigateur :** contrôles stricts Host/Origin/Sec-Fetch-Site,
   `Cache-Control: no-store`, `nosniff`, CORP, COOP, X-Frame-Options,
   Referrer-Policy, désactivation DNS prefetch et CSP restrictive.
   La CSP applique `sandbox allow-same-origin`, `script-src 'none'`,
   `connect-src 'none'` et des sources locales pour images, styles, polices.
5. **Aucune fidélité interactive revendiquée :** les scripts Quarto sont
   explicitement bloqués. Cette première étape teste l'affichage statique,
   la confidentialité du transport et les cas de refus. L'expérience Firefox
   devra inventorier précisément ce que cette politique casse.
6. **Limitations de sécurité :** ce serveur n'authentifie pas son manifeste ;
   le préfixe n'est pas une authentification utilisateur ; un processus
   local privilégié ou de même UID peut tenter des courses TOCTOU ; les liens,
   médias et navigateurs externes réclament une analyse de politique avant
   tout usage réel. Cette expérience ne prouve ni sandbox du HTML ni
   impossibilité universelle d'exfiltration.

## Qualification et critères de sortie

- Tests adversariaux publics et fictifs : interdiction source/manifeste/élève,
  refus Host/Origin, path exact, mutation post-admission, symlinks, headers.
- Quarto **réel** 1.10.19 et 1.10.20, uniquement sur fixture Git fictive :
  session P3.6A générée, rehashée, page servie à l'identique ; aucun artefact
  contenant des données pédagogiques privées.
- Revue indépendante de la frontière HTTP/CSP, refus d'ouverture privée tant
  que des vulnérabilités ou des effets navigateur restent non maîtrisés.
- Démonstration Firefox sur une fixture fictive, avec inventaire des scripts
  et fonctionnalités Quarto désactivés : observer la fidélité plutôt que
  l'inférer.
- Le raccordement au vrai rendu professeur, la navigation historique et le
  branchement vers une IA restent des **incréments distincts**. Leur
  autorisation doit être demandée explicitement au propriétaire.

## Gouvernance

Pas de fusion des PR #13 ou #14 sans décision du propriétaire. Aucun fichier
pédagogique privé, sortie HTML enseignant, manifeste réel, chemin de session
ou secret ne doit être mis dans les commits, les logs GitHub ou les fixtures.

## Démonstration Firefox uniquement fictive (après audit indépendant)

La [contre-revue de la PR #14](https://github.com/djibian/alliage/pull/14#pullrequestreview-5723954886)
accorde **GO pour une seule première démonstration Firefox sur fixture inspectée**,
mais **NO-GO pour une véritable session professeur**. Elle documente :
L1 l'identité fictive non authentifiée dans le manifeste ;
L2 la possibilité de renommer un fichier source en actif autorisé ;
L3 les ambiguïtés HTTP de `BaseHTTPRequestHandler` ;
L4 la différence entre CSP et blocage universel des navigations ;
L5 les limites de vérification ponctuelle/TOCTOU.
Ces limites subsistent et devront être résolues avant une autorisation réelle.

Pour éviter de faire passer une vraie session pour une fixture fictive,
`p36b_fictional_firefox_demo.py` n'accepte **ni `--repo` ni
`--session`**. Il construit dans un répertoire temporaire la fixture Git
publique de `tests/test_quarto_teacher_render.py`, rend cette fixture
avec Quarto local 1.10.19 ou 1.10.20 après l'option explicite
`--trusted-fixture-quarto`, vérifie les marqueurs professeur/élève et
`verify_session()`, puis sert la page par le lecteur P3.6B en loopback.
Ctrl+C ferme le serveur et déclenche le nettoyage de la fixture.

Sur une **copie de qualification Alliage propre et isolée**, épingler le
SHA exact de la PR #14 après contrôle de ses CI et de la revue, puis lancer :

```bash
python3 p36b_fictional_firefox_demo.py --trusted-fixture-quarto
```

Aucun autre dépôt, chemin de session ou identifiant de projet n'est requis.
Ouvrir uniquement l'URL aléatoire affichée dans **un nouveau profil Firefox
de test sans extension**, sans la publier ni la transmettre. Idéalement,
couper la connectivité externe de la machine au moment de l'observation,
en conservant la boucle locale `127.0.0.1`.

**Protocole humain :** dans Firefox, examiner Réseau et Console (F12),
noter les requêtes 200/403/404, les refus CSP et les chargements externes ;
vérifier l'affichage du contenu fictif et l'absence de sentinelle élève.
Observer les écarts de fidélité : le JavaScript Quarto est *intentionnellement
bloqué* (onglets interactifs, recherche, copy-code, etc.). Ne pas cliquer
de lien externe vers Internet actif ; ne pas interpréter une absence
d'affichage comme une preuve de confidentialité. Pas d'ouverture de
la vraie session professeur avant un incrément distinct, revu et
autorisé explicitement.

**Statut du lancement :** l'existence de cette commande et les tests CI
ne constituent pas une preuve d'exécution Firefox humaine ; attendre
son rapport d'observation avant toute conclusion sur Firefox.
