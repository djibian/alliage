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
