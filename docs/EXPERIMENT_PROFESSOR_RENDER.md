# P3.6A — Rendu Quarto professeur isolé (expérience, sans diffusion)

## Objectif et portée

Après la PR #11 (provenance Git et profils déclarés, `SOURCE_PINNED_PROFILES_DECLARED_RENDER_NOT_VERIFIED`),
ce pilote utilise une **copie complète des blobs Git d'un commit épinglé**, extérieure
au dépôt de conception, pour demander à **Quarto réel** de rendre **une seule
activité** sous le profil explicite `professeur`.

P3.6A n'intègre **aucune interface navigateur**, aucune sélection d'une
ancienne version depuis Firefox, aucune publication, ni aucun moteur IA.
L'outil `quarto_teacher_render.py` ne remplace pas P3.1 ; celui-ci reste
limité à son petit projet `_site` monopage.

**Quarto n'est pas sandboxé.** Même un rendu de document unique avec
`--no-execute` peut exécuter des hooks/extensions/filtres de projet,
lire le réseau, accéder au système de fichiers ou écrire ailleurs.
L'option `--trusted-quarto` indique que l'utilisateur a examiné et
accepte cette exécution. Le prototype refuse les couches de configuration
Quarto hors du sous-ensemble qualifié ; ce refus n'est **pas une
protection complète contre le code arbitraire**. Un projet non fiable
ou des corrections/données sensibles ne doivent pas être rendus dans un
environnement insuffisamment isolé.

## Portes techniques

1. `--check` est une observation Git seule : référence explicite,
   SHA40 attendu, validations P3.5 des profils, arbre complet et inventaire
   Git borné (2000 fichiers, 100 Mio). Aucune copie ni exécution Quarto.
2. Préflight syntaxique conservateur : aucun profil supplémentaire, environnement
   Quarto, métadonnées de répertoire, fichier dist préexistant ni filtre
   exécutable dans les métadonnées QMD du document cible.
3. `--render --trusted-quarto` : recrée les fichiers Git dans un dossier
   privé (permissions 0700), exécute `quarto render <source> --to html
   --profile professeur --no-execute` avec environnement de subprocess
   réduit, dans une copie sans `.git`, puis contrôle les SHA256 des
   fichiers Git d'entrée et le caractère unique du HTML professeur.
   Les sorties `dist/eleve` ou hors des emplacements autorisés sont refusées.
4. Liste exhaustive des fichiers professeur générés, taille et SHA-256 ;
   `verify_session()` vérifie à nouveau les octets au moment de la lecture.
   Le dossier de session **contient la copie intégrale des sources privées**
   et les rendus enseignant, et ne doit donc **jamais** être publié, uploadé
   en artefact CI, partagé ou exposé à une route HTTP.
5. Le résultat rend explicitement `render_profile_effective_verified=false`.
   La sélection du profil est demandée à Quarto et le HTML observé, mais
   aucune attestation indépendante universelle de l'interprétation de
   tous les profils ou filtres Quarto n'est revendiquée. La fixture
   **fictive** en CI vérifie par sentinelles que la sortie professeur
   contient uniquement son contenu et que la sortie élève n'en contient pas.

## Essai local : d'abord exclusivement en lecture seule

Après vérification des tests sur la branche P3.6A :

```bash
CODE="$HOME/projets/alliage-qualification"
REPO="$HOME/projets/pedagogie-alliage-test"
REF="refs/remotes/origin/main"
SHA="$(git -C "$REPO" rev-parse --verify "$REF^{commit}")"

python3 "$CODE/quarto_teacher_render.py" --check \
  --repo "$REPO" --repository-id djibian/pedagogie \
  --source enseignants/tim/EXEMPLE.qmd \
  --working-ref "$REF" --expected-sha "$SHA"
```

**Remplacer le chemin illustratif** par le chemin réellement autorisé ; ne
pas appeler `--render` dans une première qualification simplement parce
que `--check` réussit. Le rendu réel attend une revue indépendante,
un environnement Quarto maîtrisé et un choix d'emplacement de session privée.

Le futur rendu professeur réel (avec consentement à l'exécution) prendra
également `--out <dossier-privé-neuf>` et `--trusted-quarto`.
Les fichiers générés restent sur la machine, hors du dépôt, et ne sont
**pas** rendus accessibles à Firefox par ce premier incrément.

## Premier audit indépendant — trois blocages corrigés (31 octobre 2026)

L'audit de la PR #13 sur le HEAD `a6e973e896ad93b47c1ecf69f75ee008a11099cb`
a conclu **CORRECTIONS REQUISES**, avec trois défauts distincts.
Le correctif préserve la séparation entre préflight, rendu opt-in et
publication, ainsi que l'absence de sandbox.

- **B1 — Métadonnées YAML QMD :** les recherches de clés interdites
  par regex ont été remplacées par la lecture **exhaustive** d'un
  sous-ensemble strict des métadonnées en tête de fichier. Il faut
  un en-tête LF délimité, sans CRLF, sans alias, tag, bloc YAML,
  mapping compact, clé entre guillemets, commentaire, doublon ou
  clé inconnue. Les champs admis actuellement sont
  `title`, `subtitle`, `activity-id`, `activity-order`,
  `curriculum-unit`, `publication-status`, `duration`,
  `official-refs`, `concepts` et `support-level`, avec valeurs
  textuelles, numériques ou listes **selon leur clé**. Ce contrat
  correspond à l'activité pilote inspectée, mais **n'est pas un
  parseur général** : d'autres QMD valides peuvent être refusés.
  Les essais réels Quarto sur **fixtures fictives** démontrent que
  les filtres Lua associés à `"filters":` et aux fins de ligne CRLF
  sont exécutables même avec `--no-execute` ; ces mêmes entrées sont
  systématiquement refusées par le nouveau préflight.
- **B2 — Liens symboliques intermédiaires :** `verify_session()`
  refuse maintenant les liens sur `project`, `dist`,
  `professeur`, vérifie les résolutions physiques sous la
  racine du projet et refuse toute redirection même si les SHA-256
  de fichiers externes correspondent au manifeste.
- **B3 — Substitution d'identité HTML :** `render()` et
  `verify_session()` réutilisent **la même règle** : chemin
  `dist/professeur/<source>.html` issu d'une source QMD canonique,
  **un seul** fichier HTML, taille bornée et entrée
  `rendered_html` strictement égale à l'inventaire recalculé.
  Un manifeste substituant `asset.txt` au HTML est refusé.

**Durcissement additionnel borné :** les globs des entrées Quarto
`project.render` et `project.resources` ne peuvent plus contenir
les segments `..`, `.`, vides ou `.git`. Il n'est pas prétendu
que le comportement Quarto aurait permis une fuite effective.

**Limites inchangées :** aucune protection complète contre les
courses avec un processus hostile ayant les mêmes droits ;
les sorties et le manifeste local ne sont **pas authentifiés
cryptographiquement** ; `verify_session()` ne revalide pas tout
l'instantané Git, mais seulement l'inventaire de la sortie professeur.
Aucune de ces preuves ne qualifie l'exécution d'un Quarto non fiable
sur le véritable corpus privé. La contre-revue indépendante du
nouveau HEAD reste obligatoire.

## Hypothèses ouvertes

- Le modèle de sortie Quarto multipage appliqué à un document unique
  doit être validé par **Quarto réel** ; des fixtures unitaires ne
  suffisent pas.
- Les sorties professeur et élève sont distinctes **dans la fixture
  contrôlée**, pas une preuve de non-divulgation de tout le corpus réel.
- La sauvegarde de session est privée par permissions de fichiers,
  pas par une sandbox système ni une frontière entre processus locaux.
- Le rattachement à la page Firefox, l'historique V1/V2 et une
  éventuelle qualification de déploiement élève nécessitent des étapes
  séparées, après l'expertise de P3.6A.

## Premier essai Ubuntu 1.10.19 — anomalie d'intégrité détectée (31 octobre 2026)

Le propriétaire a obtenu `--check=PASS` avec les 542 objets Git suivis,
puis a autorisé un premier `--render --trusted-quarto` sur **une copie privée**
du commit pédagogique explicite.

**Résultat observé : REFUSED — `Fichier Git suivi modifié par Quarto.`**
Le moteur Quarto avait retourné `returncode=0`, mais au moins un fichier
de la copie ne correspondait plus à son SHA-256 Git d'origine. Ce refus
est une garantie de sûreté : **la sortie n'est pas qualifiée** et ne doit
être ni acceptée ni publiée. Le programme efface son instantané de
travail temporaire lors de cet échec ; le parent privé vide créé sur Ubuntu
peut subsister. Aucun nom de fichier ni mécanisme causal particulier
n'est actuellement établi par ce premier journal.

L'essai local utilisait **Quarto 1.10.19**, tandis que les premiers tests
Quarto en CI utilisaient **1.10.20**. Ce seul écart ne permet
**pas** d'attribuer l'anomalie à une régression de Quarto. Un nouveau
workflow sur **fixtures fictives uniquement** couvre désormais ces deux
versions afin d'éviter de généraliser le résultat d'une seule version.

### Diagnostic local optionnel et refus fermé inchangé

Le paramètre `--diagnose-integrity` exige toujours `--render`,
`--trusted-quarto`, un chemin de sortie privé et un commit Git attendu.
En cas d'altération d'un fichier suivi, il ajoute exclusivement au message
d'erreur local un compte, le **chemin relatif du premier fichier** et les
SHA-256 attendu et observé, sans contenu de fichier. Sans cette option,
le message de refus générique est **strictement inchangé**. Le répertoire
de staging est nettoyé comme avant et aucun manifeste qualifié n'est créé.

**Ce paramètre déclenche une nouvelle exécution Quarto**, non une inspection
de l'ancienne session (déjà détruite). Ne le lancer qu'après l'examen
indépendant du correctif diagnostic et une décision explicite du propriétaire.
Les chemins privés ne doivent pas être publiés tels quels dans GitHub
ou les journaux CI ; ne communiquer que le type d'anomalie et, si utile,
une catégorie de fichier expurgée.

Il est interdit d'assouplir le contrôle SHA-256 ou de supposer qu'un
fichier Git modifié par Quarto est automatiquement acceptable.
Après identification du fichier, rechercher la cause exacte puis
corriger le mécanisme minimalement, avec une fixture reproductible.

## Incident Ubuntu — transformation exacte de `.gitignore` par Quarto 1.10.19

Le diagnostic privé du propriétaire a établi **une seule divergence sur 542
fichiers** : `.gitignore`, classe `CONTENT_CHANGED`. Empreinte attendue
`cf0f54c8350431d5e34fb232399852ee4e619c048a8fe47a2b45bff7164e3672`,
empreinte de la copie après rendu
`89280212b11b9ee18e893cb742f94db7374bbbbabe7226036c93718e3dc4d6c2`.
**Aucun autre fichier suivi n'était divergent à cette porte.**
Le rendu et les contrôles ultérieurs demeuraient non qualifiés, car
le moteur s'était arrêté au premier refus.

La recherche causale a identifié, dans le **code source exact de Quarto
1.10.19 et 1.10.20**, l'appel à `ensureGitignore(context.dir)` pendant
`renderProject()` ; la fonction
`src/project/project-gitignore.ts` lit toutes les lignes de
`.gitignore`, applique `trim()` et ajoute, si elles manquent,
`/.quarto/` et `**/*.quarto_ipynb`, avant de réécrire le fichier
avec les sauts de ligne attendus. Références :
`quarto-dev/quarto-cli@v1.10.19:src/command/render/project.ts`,
`src/project/project-gitignore.ts` et `src/core/lib/text.ts`.

La reconstruction **hors du dépôt pédagogique** de cette transformation
sur les octets Git initiaux reproduit **exactement** le SHA-256
`89280212b11b9ee18e893cb742f94db7374bbbbabe7226036c93718e3dc4d6c2`
observé sur Ubuntu. La cause est donc établie pour le fichier refusé :
une écriture automatique déterministe de Quarto dans **la copie privée**,
pas une mutation nécessaire du checkout canonique.

### Correction causale bornée

`_expected_quarto_gitignore(original)` calcule les **octets exacts**
qu'un Quarto 1.10.19/1.10.20 doit produire en l'absence d'un fichier
`_*.local` racine déclenchant une règle supplémentaire.
`_verify_tracked_copy()` n'accepte cette unique mutation que si
le nom est **exactement `.gitignore`**, que le fichier reste régulier
et que son SHA-256 est **exactement** celui du contenu projeté.
Une modification même d'un octet de plus, un fichier manquant,
symbolique ou une modification d'un autre fichier suivi déclenchent
toujours `REFUSED`.

L'exception est **tracée** dans le manifeste par
`tracked_source_mutations_accepted`, avec nom du fichier, raison,
SHA-256 initial et observé, et
`tracked_source_bytes_all_preserved=false`. Le rendu n'affirme donc
**pas** que l'ensemble des fichiers suivis est demeuré byte-identique
au commit pendant Quarto. La source Git canonique garde son identité
et son SHA initiaux ; aucune écriture dans le checkout pédagogique.
Aucune sortie publiée ni autorisation Firefox n'est introduite.

**Tests obligatoires :** fixture fictive avec `.gitignore` suivi,
rendu Quarto réel 1.10.19 et 1.10.20, confirmation que les octets
post-rendu correspondent exactement au prédicat, contrôle des
manifests, refus des mutations adversariales et non-régression P3.5.
Le correctif ne doit être considéré comme qualifié qu'après ces CI
et une contre-revue indépendante de cette exception ciblée.


### Raffinement de la prédiction exacte : Unicode `trim()` (31 octobre 2026)

Une contre-épreuve supplémentaire sur le correctif `.gitignore` a démontré que
`str.strip()` (Python) et `String.trim()` (ECMAScript, réellement utilisé par
Quarto 1.10.19/1.10.20) ne reconnaissent pas exactement les mêmes caractères :
Python retire notamment U+0085 et U+001C, tandis que JavaScript les conserve ;
JavaScript retire U+FEFF, contrairement au `strip()` Python sans paramètre.
Ce désaccord pouvait accepter une prédiction qui ne correspondrait pas aux octets
produits par Quarto sur une entrée synthétique atypique.

`_expected_quarto_gitignore()` emploie maintenant explicitement l'ensemble de
blancs ECMAScript pour le retrait des espaces aux extrémités des lignes.
Tests fictifs ciblés sur U+0085, U+001C et U+FEFF, plus une exécution Quarto
réelle sous deux versions sur un `.gitignore` synthétique contenant U+0085.
Le traitement de toutes les autres entrées Git, les restrictions de profil,
l'inventaire et les refus d'intégrité restent inchangés.

**Statut :** nouvelle CI et contre-revue indépendante requises sur le HEAD
intégrant cette correction ; aucune autorisation implicite de rendu privé,
d'exposition navigateur ou de fusion. Cette précision n'est pas une preuve que
l'ensemble du code Quarto installé est sandboxé ou immuable.

### Contre-revue indépendante G2 — liaison explicite du SHA Git (31 octobre 2026)

La contre-revue du HEAD `e9c6f31b7968ca4829a14bf4b1dfd7d6e12d8d62`
a conclu **CORRECTIONS REQUISES (G2 uniquement)** : un appel direct de
`_verify_tracked_copy()` pouvait fournir des octets `original_gitignore`
différents du SHA Git déclaré dans `expected[".gitignore"]`, puis faire
accepter leur transformation prédite. Le parcours normal de `render()`
fournissait déjà ces deux valeurs à partir des mêmes octets Git, mais
l'invariant n'était pas imposé à la frontière du vérificateur.

**Correction minimale :** lorsque `original_gitignore` est fourni, le
vérificateur exige la présence de `.gitignore` dans `expected` et l'égalité
de son SHA-256 avec celui des octets d'origine. Sinon, il refuse avant même
de calculer une prédiction Quarto. Un test fictif de substitution des octets
initiaux reproduit le contre-exemple et impose son refus ; un test d'entrée
sans nom `.gitignore` vérifie le refus, tandis que la transformation légitime
reste acceptée et tracée. Aucun autre fichier suivi ni mécanisme de rendu,
de sortie, de publication ou de confidentialité n'est modifié.

**Qualification requise :** CI Python, P3.5 et Quarto réel 1.10.19/1.10.20
sur le HEAD corrigé, puis relecture indépendante ciblée G2.
Les rendus pédagogiques privés restent soumis à une autorisation distincte ;
le code Quarto demeure non sandboxé.
