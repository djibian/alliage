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

## Première observation Firefox fictive — défaut d'intégration CSS (31 octobre 2026)

Le propriétaire a lancé le lecteur fictif sur Firefox et constaté que le
HTML de l'activité et la sentinelle professeur fictive s'affichent. La page
est cependant visuellement **sans mise en forme Quarto**, avec deux refus
CSP `style-src-elem` visant des stylesheets `data:text/css`. Aucune
preuve d'absence totale de requêtes externes ni de fonctionnalité
interactive n'a été fournie à ce stade. L'image de navigateur, l'URL
contenant une capacité et les informations de profil de l'utilisateur
**ne doivent pas être reproduites dans le dépôt public**.

**Cause ciblée :** la fixture Quarto utilise `embed-resources: true`,
qui produit des feuilles CSS via des URLs `data:text/css`. La directive
`style-src 'self' 'unsafe-inline'` n'autorise pas ces URLs ; `unsafe-inline`
ne signifie pas `data:`.

**Correction expérimentale minimale :** autoriser uniquement le schéma
`data:` supplémentaire dans `style-src` ; préserver
`script-src 'none'`, `connect-src 'none'`, l'absence d'origines externes
dans la CSP et la barrière fictive. Un test adversarial vérifie ces invariants
et le test Quarto réel exige la présence de `data:text/css` dans le HTML
généré. Il faudra **une nouvelle observation Firefox après CI** pour
confirmer le retour de la mise en forme et inventorier les refus restants.

**Isolement du navigateur :** l'essai initial s'est déroulé en fenêtre de
navigation privée d'un Firefox déjà ouvert. Cette configuration ne vaut pas
nouveau profil dédié sans extensions et ne vérifie pas l'absence de réseau
externe. Elle est acceptée comme **observation initiale fictive seulement**.

Les observations navigateur et cette exception CSS ne lèvent **aucune**
limite L1–L5 de l'audit, ni le NO-GO pour HTML professeur réel.

## P3.6C — instantané mémoire et requêtes HTTP canoniques (2 novembre 2026)

**PR #15 Draft empilée sur #14**, sans modification du contenu de la
PR #14 et sans autorisation d'afficher le vrai HTML professeur.

**Correction L5 partielle :** le lecteur fictif `FictionalTeacherPreview`
utilise désormais `verify_session()`, puis lit une seule fois chaque actif
inscrit dans l'inventaire, par un parcours POSIX de descripteurs de répertoires
(`dir_fd`, `O_NOFOLLOW`, `O_DIRECTORY`). L'actif final est ouvert avec
`O_NOFOLLOW` et `O_NONBLOCK`, vérifié par `fstat` sur le *même* descripteur,
puis borné en taille et comparé au SHA-256 annoncé. Un OS ne disposant pas
de ce mécanisme est refusé, sans repli sur un `read_bytes()` non atomique.

Les octets ainsi contrôlés sont conservés en mémoire, avec le type MIME :
GET et HEAD ne touchent **plus au système de fichiers**. La précédente
sémantique « mutation du disque après démarrage -> HTTP 404 » est remplacée
par « mutation du disque après démarrage -> **mêmes octets de l'instantané
initial** ». Une nouvelle admission sur les fichiers modifiés doit toujours
être refusée. Le budget total des sorties est borné par `MAX_RENDERED_BYTES`
de P3.6A (100 Mio). Cette méthode évite la course de chemin dans la lecture
HTTP après admission, mais ne rend **pas authentique** un manifeste local
modifié par le propriétaire ou un processus déjà autorisé.

**Correction L3 ciblée :** le request-target est observé avant la
normalisation de `BaseHTTPRequestHandler` et les alias `//...`, les URI
absolues et les chemins non canoniques sont refusés ; un seul `Host`
exact est admis, zéro ou un `Origin` et `Sec-Fetch-Site`, sans doublon.
Des requêtes HTTP brutes adversariales vérifient ces refus, en préservant
les chemins normaux.

**Réduction de L1, non résolution :** l'entrée CLI
`python3 quarto_teacher_http.py --session ...` est désormais systématiquement
refusée. Le seul lanceur prévu pour l'essai humain est
`p36b_fictional_firefox_demo.py --trusted-fixture-quarto`, qui construit
localement sa propre fixture connue. Un appel Python direct à
`FictionalTeacherPreview(session)` reste toutefois possible et le marqueur
`quarto:fiction/...` du manifeste demeure forgeable : **ne jamais le
considérer comme une authentification ou une autorisation du vrai contenu**.

**Limites bloquantes :** L1 identité et mandat non signés, L2 fichiers
sources déguisés en actifs, L4 liens/navigations externes et exfiltration,
absence d'attestation universelle de l'application du profil Quarto ;
aucune habilitation à la session réelle, aucun JS activé et aucune
publication. Le passage vers un vrai aperçu professeur nécessite un
dispositif de consentement/provenance indépendant de ce laboratoire et
un nouveau verdict de sécurité.

**Validation attendue :** CI Python complète et Quarto 1.10.19/1.10.20
sur le HEAD exact, puis revue indépendante centrée sur L3/L5 et les
limites restantes. Une réussite synthétique n'est pas un test Firefox
supplémentaire, ni une autorisation de fusion des PR #13/#14/#15.

## P3.6C — contre-expertise C1/C2, frontière de preuve corrigée (2 novembre 2026)

La [contre-expertise indépendante de P3.6C](https://github.com/djibian/alliage/pull/15#issuecomment-6578152166)
a conclu **CORRECTIONS REQUISES** sur le HEAD
`276035b2d0316606f35a29a51277ae3fb4e8ed87` :
L3 est confirmé, mais C1 démontre une substitution de `manifest.json`
entre le rehash `verify_session(session)` et la deuxième lecture JSON
réalisée par `FictionalTeacherPreview`. Le vérificateur avait validé
une première identité HTML alors que le lecteur pouvait admettre une
entrée modifiée `rendered_html` et un actif ajouté. C2 note que le
dictionnaire des routes demeurait mutable en mémoire par code Python,
même si les valeurs `bytes` étaient immuables.

**C1 corrigé sans modifier le protocole par défaut de P3.6A :**
`verify_session(session, include_manifest=True)` retourne, **uniquement
sur opt-in interne**, l'objet `verified_manifest` qui a été effectivement
lu et vérifié, ainsi que son SHA-256 calculé sur les mêmes octets
`manifest_raw`. L'appel ordinaire conserve son résultat limité
`status/file_count/html_sha256/publication_performed/student_deployment_verified`.
Le lecteur n'effectue **aucune seconde désérialisation JSON** : ses
routes et l'identité HTML proviennent exclusivement de l'objet validé.
Il détecte par un contrôle SHA-256 séparé, après la copie des actifs,
une substitution ultérieure du manifeste et refuse d'ouvrir le
serveur. Ce second contrôle est une **détection d'écart**, et non une
revalidation ou une revendication d'atomicité temporelle totale :
après admission, seule la première table validée est conservée.

**C2 corrigé :** le lecteur construit les routes dans un dictionnaire
local, puis publie seulement un `MappingProxyType` en lecture seule ;
les valeurs restent des tuples `(bytes, type_mime)` et sont scellées
avant toute écoute HTTP. Une tentative d'écriture ou de suppression
de route par code interne lève `TypeError`.

**Contre-épreuves :** une fixture publique modifie délibérément
`manifest.json` **après** le vrai `verify_session` et avant
l'admission HTTP ; l'admission doit refuser. L'état final est
également refusé par le vérificateur initial. D'autres tests
vérifient le résultat du mode facultatif et l'impossibilité
de muter la table de routes. Les tests POSIX/HTTP L3/L5
précédents restent actifs.

**Limites inchangées :** ces preuves concernent exclusivement une
fixture fictive, dans un modèle où un code malveillant de même privilège
pourrait aussi modifier le processus. L1 (provenance/consentement réel),
L2 (actif sensible déguisé), L4 (navigation externe/exfiltration),
et la vérification exhaustive du profil Quarto restent bloquants
pour l'usage réel. Aucune session privée, aucune ouverture Firefox
réelle, aucun JS activé et aucune publication n'est autorisé.

## P3.6C — réaffectation d'attribut C2 (2 novembre 2026)

La [contre-expertise finale](https://github.com/djibian/alliage/pull/15#issuecomment-6578674893)
du HEAD `f25b05c6d90ab685fde26de53a0552ef03ef93e7`
confirme **C1 LEVÉE**, mais conclut **CORRECTIONS REQUISES sur C2** :
`MappingProxyType` empêchait une modification par élément, sans empêcher
la réaffectation ordinaire `preview.routes = {...}`. Un consommateur
Python dans le même processus pouvait alors faire servir une nouvelle
table non vérifiée par `get_asset` et le handler déjà ouvert. Aucun
chemin d'écriture via HTTP n'a été identifié par l'audit.

**Correctif C2 de périmètre minimal :** le lecteur est une
`@dataclass(frozen=True, slots=True, init=False, eq=False, repr=False)`.
Ses quatre attributs (`session`, `prefix`, `html_route`, `routes`)
sont établis pendant l'admission uniquement par `object.__setattr__`,
puis non réaffectables par les opérations Python ordinaires. L'inventaire
est toujours construit localement, converti en `MappingProxyType`
contenant des tuples `(bytes, MIME)`, avant tout démarrage HTTP.

**Régression discriminante :** le test C2 tente désormais explicitement
`preview.routes = {route: (b"FICTIONAL_UNVERIFIED", "text/html")}`,
la suppression de `routes` et la réaffectation de l'identité HTML,
du préfixe et du chemin de session. Il exige le refus et confirme
la réponse du serveur HTTP déjà démarré depuis les octets scellés.

**Portée exacte :** cette immutabilité est un contrat contre les
*opérations ordinaires sur les instances Python*, non une barrière
contre du code arbitraire déjà exécuté dans le processus :
`object.__setattr__`, monkeypatch de classe/méthode ou mémoire
modifiée sont hors de portée. Aucun changement de protocole,
d'autorisation, de confidentialité, de politique CSP ou de
publication. L1, L2 et L4 ainsi que l'attestation du profil
Quarto restent ouvertes : **NO-GO pour toute ressource professeur
réelle sur HTTP**. Qualification CI sur le HEAD final et
nouvelle contre-revue ciblée nécessaires.
