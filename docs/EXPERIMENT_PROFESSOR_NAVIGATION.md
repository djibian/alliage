# P3.6E — L4a : refus d'admission des navigations HTML connues

**Statut : expérience Draft sur corpus Quarto fictif uniquement.**
Base P3.6D au HEAD `9f7a02d1b089a38b554af94aedaf8ca377da407a`,
approuvée pour la **route unique HTML**, avec observation Firefox
statique réussie le 2 novembre 2026. Aucun HTML professeur réel
admissible sur HTTP.

## Pourquoi un simple en-tête CSP ne suffit pas

Les contrôles `script-src 'none'`, `connect-src 'none'`, le
`sandbox allow-same-origin` et `frame-src 'none'` sont utiles mais
ne sont pas un *verrou universel de navigation* : les contrôles
`allow-top-navigation` du CSP sandbox s'appliquent aux documents
imbriqués dans un iframe, et n'empêchent pas à eux seuls le document
de premier niveau de naviguer *lui-même*. Firefox n'implémente pas
une politique CSP universelle `navigate-to` utilisable comme garantie.
Les navigations initiées par un lien cliquable peuvent quitter la page
et provoquer une requête à un site extérieur même si les sous-ressources
sont interdites.

Références : documentation Mozilla / MDN,
`Content-Security-Policy: sandbox` et `Content-Security-Policy`,
et API Firefox `webRequest.onBeforeRequest`.
Une extension bloquant les navigations serait une autre stratégie,
à qualifier séparément avec ses permissions, son comportement et ses
risques de remplacement d'URL.

## Plus petit invariant L4a

**Avant l'ouverture du socket HTTP**, analyser les **octets scellés
de l'unique HTML déjà vérifié**. Conserver strictement ces octets :
aucune réécriture ou assainissement silencieux n'est autorisé, car
cela casserait l'identité SHA du rendu admis.

Pour le **laboratoire fictif**, refuser explicitement :
- `<a>` et `<area>` dont `href` ou `xlink:href` n'est pas un
  fragment ASCII `#...` du même document, ainsi que les attributs
  de navigation `target`, `ping`, `download` ;
- `<meta http-equiv="refresh">`, `<base>`, formulaires et cibles
  `formaction`, frames et objets incorporés ;
- `<link rel="preconnect|prefetch|dns-prefetch|preload|...">` et
  stylesheets qui ne sont pas des URLs CSS `data:text/css,`
  déjà intégrées par Quarto ;
- en cas d'attributs dupliqués ou d'encodage UTF-8 invalide :
  refus de la page entière plutôt qu'un choix de priorité ambigu.

Autoriser le HTML textuel, ses CSS intégrés et les ancres de fragment
`#titre`. Garder les scripts Quarto **bloqués par CSP** : leur
présence en source HTML n'autorise jamais leur exécution.

**Les contrôles du parseur sont un filtrage de constructions connues
et non une preuve de conformité du parseur au navigateur.**
`html.parser.HTMLParser` n'implémente pas toutes les règles de
reconstruction HTML5 de Firefox. Les URL intégrées dans les images,
CSS, SVG/MathML, attributs exotiques, navigation initiée par une
extension de navigateur et liens générés par des techniques non
couvertes ne sont pas exhaustivement démontrés sûrs. Les navigateurs
peuvent encore effectuer des requêtes non pédagogiques
(ex. favicon), y compris lorsqu'elles sont refusées par le serveur.

## Tests requis avant tout GO limité

- Contre-épreuves unitaires sur les types de navigation connus
  (HTTP[S], URL relatives, `//`, `javascript:`, `data:`,
  `meta refresh`, formulaires, liens d'anticipation).
- Preuve d'admission et de refus dans `FictionalTeacherPreview`
  sur du HTML fictif **correctement rehashé par P3.6A**.
- Préservation exacte des octets pour un HTML sûr et ancré.
- Rendu Quarto réel 1.10.19/1.10.20 sur la fixture publique,
  sans changer son format `embed-resources: true`.
- Revue indépendante du code et de la portée ; seulement ensuite,
  campagne Firefox fictive **adversariale** avec liens externes,
  vérification Réseau et distinction entre requêtes externes
  et navigations.
- **Aucune conclusion « L4 levée »** sans analyser séparément
  la sémantique navigateur effective, les différences de parseurs,
  les sources de chargement actives et les restrictions locales.

Les PR #13 à #16 restent Draft et non fusionnées.
La porte L1 de provenance et consentement explicite de l'enseignant
reste fermée ; un marqueur `quarto:fiction/` dans un manifeste
local ne constitue pas un contrôle d'accès.

## Contre-expertise du 2 novembre 2026 — MathML et SMIL

La [contre-expertise indépendante P3.6E](https://github.com/djibian/alliage/pull/17#issuecomment-6581380069)
du HEAD initial `a80982b97c7392c1ccf18950f36d3aac813df349`
conclut **CORRECTIONS REQUISES** avec deux réfutations concrètes :

1. **MathML** : `href` peut être un attribut global, notamment sur
   `<math>` et `<mi>`. Un document portant `<math href="https://...">`
   passait le filtre initial alors qu'il propose une navigation.
2. **SVG/SMIL** : `<set attributeName="href" to="...">` et
   `<animate attributeName="href" values="...">` peuvent modifier
   la destination effective d'un `<a href="#fragment">`
   sans JavaScript. L'audit a observé cet écart entre valeur statique et
   valeur animée sous Chromium ; ce n'est **pas une preuve Firefox**.

**Correction minimale à l'admission, jamais une transformation HTML :**
- Tout `href` ou `xlink:href` sur un élément **autre que les
  exceptions explicitement analysées** `a`, `area`, `link`
  provoque le refus. `a` et `area` conservent exclusivement les
  fragments `#...` ; `link` conserve seulement la CSS Quarto
  intégrée `data:text/css,` et refuse `xlink:href`.
- Les tags SMIL `set`, `animate`, `animateMotion`,
  `animateTransform`, `animateColor` et `discard` sont refusés
  sans chercher à interpréter leur chronologie et leurs mutations.
- Les contre-exemples MathML et SMIL précédents, leurs variantes
  d'attributs et l'invariant d'admission HTTP sont désormais dans les
  tests fictifs. Le document réel Quarto synthétique et son CSS
  intégré continuent d'être testés sur les deux versions cibles.

**Limites maintenues :** le refus des tags SMIL connus ne prouve pas
l'équivalence du parseur Python au parseur HTML5 de Firefox ;
les chargements indirects CSS, SVG ou autres, les fonctionnalités
externes du navigateur et l'interaction JS restent à qualifier.
Les règles ne sont **pas un assainisseur de contenu** ni un contrôle
de provenance. L1, L2, L4 général et l'attestation de profil réel
restent des portes fermées à l'exposition professeur.
La PR #17 reste Draft et doit recevoir une nouvelle contre-revue
indépendante sur son HEAD corrigé avant tout essai Firefox adversarial.

## Deuxième contre-expertise — écarts de reconstruction HTML5 (2 novembre 2026)

La [nouvelle contre-expertise indépendante](https://github.com/djibian/alliage/pull/17#issuecomment-6582722330)
du HEAD `84a9b567bd3844bde79f652580b9e03984bbe489`
conclut **CORRECTIONS REQUISES**. Le refus MathML/SMIL fonctionne
lorsque les balises sont vues par `HTMLParser`, mais **certaines
déclarations ou commentaires HTML malformés empêchent ces callbacks**
alors que le parseur HTML5 du navigateur restitue les éléments actifs.
Les fixtures adversariales `<!----!>` et `<![CDATA[>` sont
entièrement fictives. Une observation Chromium sur un DOM restauré
ne remplace pas une qualification Firefox.

**Tentative infructueuse documentée :** le rejet de *tous* les
commentaires/déclarations HTML a correctement fermé ces vecteurs,
mais a aussi refusé la fixture Quarto **réel** (CI
[Python](https://github.com/djibian/alliage/actions/runs/41484653791)
et [Quarto 1.10.19/1.10.20](https://github.com/djibian/alliage/actions/runs/41484653706)).
Ce résultat démontre qu'un refus excessif n'est pas un produit
fonctionnel et ne doit pas être présenté comme un GO.

**Grammaire expérimentale resserrée, sans réécriture :**
- au plus un doctype HTML simple au début ;
- accepter seulement les commentaires simples `<!-- ... -->`
  terminés par `-->` sans `<`, `>` ou `--` intérieur ;
- refuser toutes les autres introductions de déclaration,
  CDATA, commentaires ambigus et instructions `<?...`;
- appliquer ensuite les contrôles existants sur les balises
  réellement signalées par le `HTMLParser`.

Ce préfiltre lexical ne dépend pas des callbacks perdus du
parseur Python, mais ne constitue **ni un parseur HTML5 complet,
ni une preuve de concordance exhaustive entre les moteurs**.
La compatibilité avec le rendu Quarto fictif réel est testée
explicitement en CI 1.10.19 et 1.10.20 ; le HTML admis reste
**identique bit à bit** au fichier déjà rehashé par P3.6A.

**Décision de conception :** arrêter les ajouts opportunistes
de balises interdites en tant que prétendue barrière générale.
La voie vers l'aperçu réel devra comparer, sur fixtures fictives,
un contrôle de navigation **dans Firefox**, par exemple une extension
avec `webRequest.onBeforeRequest` et permissions bornées, ou un contexte
d'affichage isolé. Le contrôle au navigateur nécessitera à son tour des
tests de requêtes principales, sous-ressources, changements de contexte,
extensions concurrentes et permissions. Aucun de ces moyens n'est
encore implémenté ni approuvé.

Les limites L1 provenance/consentement, L2 contenu intégré dans
l'unique HTML, L4 générale et la vérification du profil Quarto
continuent de **bloquer toute exposition de la session réelle**.
La PR #17 reste Draft jusqu'à une nouvelle revue indépendante
du changement de grammaire et de ses limites.

## Troisième contre-expertise — divergence raw-text SVG/MathML (2 novembre 2026)

La [contre-expertise indépendante finale](https://github.com/djibian/alliage/pull/17#issuecomment-6583146348)
du HEAD `707677dff3a9f79994ab6012e6bd77eab3d97156`
a conclu **CORRECTIONS REQUISES**. Les contournements par commentaires
malformés étaient fermés, mais `HTMLParser` Python interprétait le
contenu de `style`/`script` comme texte brut même lorsque des règles
de sortie des espaces de noms SVG/MathML conduisaient le navigateur HTML5
à construire de véritables liens HTML et des `meta refresh`.

**Changement de méthode**, et non une nouvelle expression régulière
sur `<svg><style>` : abandon de `HTMLParser` comme autorité du DOM.
L'admission inspecte l'arbre reconstruit par **html5lib 1.1**, une
implémentation HTML5 tenant compte des espaces de noms HTML, SVG et MathML,
avec builder `etree`. Les exceptions pour `a`/`area` et `link`
s'appliquent aux seuls espaces de noms attendus. Les attributs de
navigation et les animations SMIL sont examinés **sur les éléments
effectivement reconstruits**. Les attributs dupliqués sont refusés
à partir des diagnostics du parseur HTML5.

Le refus lexical des déclarations/commentaires ambigus est conservé
comme **restriction supplémentaire** de la fixture ; il ne prétend pas
implémenter la reconstruction HTML5. Aucune sérialisation ou réécriture
du DOM n'est utilisée : le navigateur reçoit toujours les octets
vérifiés par l'oracle P3.6A.

**Nouvelle dépendance isolée et épinglée** :
`requirements-p36e.txt` (html5lib 1.1, six, webencodings). Les deux
workflows de tests installent ces versions avant qualification. Un
environnement sans html5lib doit refuser le démarrage, sans revenir
silencieusement au parseur Python incomplet. Pour une éventuelle
expérience locale future, installer la dépendance dans un venv dédié ;
ne pas modifier l'environnement Python système.

**Contre-tests :** liens HTML actifs récupérés par le parseur depuis
`svg/style`, `svg/script`, `math/style` et `meta refresh`
reconstitué ; intégration `verify_session()=PASS` puis **refus
avant HTTP**, avec snapshot préexistant inchangé. Les cas MathML
href, SMIL, commentaires malformés, fragments locaux et CSS Quarto
embarqué demeurent dans la suite. Une CI verte n'exclut pas de
nouvelles divergences HTML5/Firefox : le parseur externe, les
autres caractéristiques du navigateur et les chargements CSS/SVG
ne constituent pas une garantie de confinement général.

**Statut et barrières :** P3.6E reste **strictement fictive**.
L1 autorisation/provenance/consentement, L2 contenu intégré du HTML,
L4 confinement des navigations et requêtes **dans Firefox** et
l'attestation du profil professeur restent NON RÉSOLUS. Aucune session
professeur réelle ne doit être servie par HTTP, aucune fusion,
aucun JS activé ni publication élève. Soumettre le HEAD
final aux CI Quarto et à une contre-revue indépendante.

## Quatrième contre-expertise — diagnostics des balises écartées (2 novembre 2026)

La [contre-expertise indépendante de la PR #17](https://github.com/djibian/alliage/pull/17#issuecomment-6584277621)
du HEAD `06491151a80a89228fcb42e6ffaf1a2c741cb626`
conclut **CORRECTIONS REQUISES** pour le contrat de *refus syntaxique*.
Les contre-exemples SVG/style, SVG/script et MathML/style qui
avaient motivé `html5lib` sont **effectivement refusés**.
En revanche, une balise interdite telle que
`<select><iframe src="https://example.invalid/fiction"></iframe></select>`
peut être éliminée par la récupération HTML5, avec le diagnostic
`unexpected-start-tag-in-select`. Le garde ne considérait auparavant
que `unexpected-start-tag-ignored`, et acceptait donc ce HTML.

**Précision essentielle de sécurité :** l'élément supprimé du DOM
était **inerte** dans la construction HTML5 observée ; aucun chargement
ni navigation Firefox n'a été démontré. La réfutation vise la
**politique expérimentale de refus conservateur de syntaxe interdite**,
pas une nouvelle fuite avérée.

**Correction ciblée dans P3.6E :** examiner les diagnostics de
la famille `start-tag` qui portent un nom d'élément, et refuser
les noms de la liste d'éléments interdits, ainsi que les éléments de
navigation conditionnelle `a`, `area`, `meta`, `link`
lorsqu'ils sont écartés. Les interdictions des éléments présents
dans le DOM continuent d'être évaluées sur l'arbre HTML5.
Cette politique peut refuser du contenu qui aurait été inerte dans
ce contexte : choix conservateur **propre au laboratoire fictif**.

**Contre-tests sans contenu privé :** variantes interdites
sous `select` dans le test de parseur et test HTTP
`P3.6A rehash PASS → admission REFUSÉE`, avec contrôle
des octets scellés déjà servis. La compatibilité de l'activité
Quarto fictive sur 1.10.19 et 1.10.20 doit être contrôlée sur
le HEAD final avant nouvelle contre-revue indépendante.

Le module `html5lib` n'est **pas** un confinement du navigateur :
L1, L2 dans le HTML, L4 générale et l'attestation de profil restent
non résolus. Aucune session professeur réelle ne doit être servie
en HTTP, aucun JS, aucun merge ni publication élève.
