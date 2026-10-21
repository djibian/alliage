# Alliage — état technique de reprise

**Date de capitalisation : 19 octobre 2026. Qualification Firefox du pilote : 19 octobre 2026.** Sources reprises **effectivement** de l'archive `pedagolab-atelier-quarto-v0.4.zip` (`docs/ORIGIN_HASHES.json`) ; sans réimplémentation de substitution. Distinguer les 18 tests unitaires simulés, la CI et le test manuel Firefox réel sur une unique activité.

## Inventaire des quatre livrables antérieurs

Archives originelles de la conversation (l’enseignant dispose des ZIP téléchargés, le dépôt public ne les contient pas) : `pedagolab-selection-v0.zip` (v0.1 : `manifest.json`, `selection.js`) ; `pedagolab-source-v0.2.zip` (v0.2 : `resolve_source.py`, ancrages, tests) ; `pedagolab-quarto-experiment-v0.3.zip` (v0.3 : `experiment.py`, tests de rendu simulé et comparaison) ; `pedagolab-atelier-quarto-v0.4.zip` (v0.4 : les **12 fichiers sources** énumérés dans le référentiel de provenance). Les fichiers du code actuel sont conservés à la racine et dans `extension/`, `tests/`, `exemples/`, sans recopier les archives ni les documents du dépôt pédagogique privé. Le dernier ZIP v0.4 avait été extrait par l’enseignant dans `~/Téléchargements/pedagolab-atelier-quarto-v0.4/`, et sa source externe de test dans `/tmp/pedagolab-pedagogie/` a ensuite disparu. La copie de conservation est désormais le dépôt `djibian/alliage` **après push**, pas une archive temporaire.

## Dernières versions validées

- **v0.3 (fonctionnement Quarto réel validé par l'enseignant le 18/10/2026)** : 13 tests automatisés OK ; deux variantes `cinq ressources`/`cinq fichiers proposés`, `RENDER_VERIFIED_LOCAL` avec `render_verified=true` pour A et B ; visualisation OK ; `production_write=false`, `publication=NOT_PUBLISHED`. Source pilote au commit `4530afacc4b45d5707f4f3c5029386bb5e141ec4`, blob `df1f38bb6e6178fc07f2d078cb86256a8791d05c`.
- **v0.4 (code actuel)** : 18 tests automatisés OK (suite initiale), 18 OK après anonymisation des exemples publics le **19/10/2026**, Python 3.12 ; CI du commit de fusion de la PR #1 sur `main` réussie (`fade04a37cef99f5b1bde9c7c51ad183a61c45fe`). Tests automatisés avec Quarto **simulé** et pont local de test. **Le cycle complet sur le pilote Firefox réel a depuis été validé manuellement** (détails ci-dessous).
- **Premier lancement v0.4 sur ordinateur enseignant** : échec **avant démarrage** : `FileNotFoundError` du clone `/tmp/pedagolab-pedagogie`, disparu. Aucune requête extension/vrai Quarto lancée lors de cet essai. Le CLI amélioré signale le chemin absent et exige `--repo` ; correction non encore testée sur l'ordinateur enseignant.

## Qualification manuelle du parcours Firefox (19 octobre 2026)

**Source : retour explicite de l'enseignant, non audit indépendant des fichiers d'expérience.** Sur Ubuntu, Quarto `1.10.19`, dépôt externe de test persistant sous `~/projets/pedagogie-alliage-test` à la révision `4530afacc4b45d5707f4f3c5029386bb5e141ec4` :

- `python3 serveur.py --repo "$HOME/projets/pedagogie-alliage-test"` démarre sans erreur ; `curl http://127.0.0.1:8765/api/health` rend `READY_LOCAL` et le commit attendu.
- Dans Firefox, l'enseignant confirme **toutes les étapes OK** : panneau Alliage, sélection de « cinq fichiers », génération/rendu des propositions A/B, ouverture de la comparaison, choix « Garder A » et enregistrement local de la décision.
- `git -C "$HOME/projets/pedagogie-alliage-test" status --porcelain` ne produit aucune sortie : **copie source inchangée**.
- Le dossier privé des expériences contient bien **un `rapport.json` et un `decision.json`**. Ni jeton, ni identifiant de session, ni contenu privé de ces fichiers ne sont committés.

**Conclusion :** parcours v0.4 opérationnel sur le pilote Quarto/Firefox testé. Ne pas extrapoler à d'autres pages ou à Chrome. Le `decision.json` n'a pas été relu directement par l'assistant ; l'intégrité détaillée de ses champs n'est donc pas attestée indépendamment.

## Implémentation conservée

| Composant | Fonction réelle / limite |
|---|---|
| `extension/atelier.js` | Ancre DOM/UTF-16, panneau dans la page, saisie A/B, comparaison, décisions. Limité à un URL exact du pilote. |
| `extension/background.js` | Requêtes du content script vers pont local avec jeton. Pas de modèle IA. |
| `serveur.py` | HTTP loopback 127.0.0.1:8765, contrôle Host/Origin/jeton, session en mémoire, test du rapport/empreinte puis décision locale, aperçu rendu. |
| `resolve_source.py` | Localise passage simple sur une seule ligne `.qmd`, avec contrôle Git et refus d'ambiguïtés. |
| `experiment.py` | Copie un sous-ensemble Quarto, remplace des octets exacts, rend A/B, compare texte cible et reste de la page, écrit rapports et HTML expérimentaux, aucune publication. |
| `tests/` | 18 tests unitaires, dont refus de mutations, chemin traversal et garde des autres occurrences. |

La reprise préserve les identifiants de **protocole** `pedagolab.*`, le header `X-Pedagolab-Token`, des sélecteurs DOM et certaines variables historiques ; renommer à part avec tests de migration. Les intitulés visibles du produit sont **Alliage**. Les exemples publics sont désormais **fictifs** et non des captures pédagogiques réelles. Des captures réelles éventuelles vont uniquement dans le dossier local ignoré `local-anchors/`.

## Limites et risques connus

- Page publiée non reliée cryptographiquement à son commit : `published_html_revision_verified=false` même quand le rendu local est vérifié.
- Modification `.qmd` limitée au texte simple sans traversée de balisage complexe ; les comparaisons HTML réduisent les espaces et vérifient le **texte visible**, pas chaque propriété interactive.
- Pas de dialogue IA intégré, de microphone, d'annotations ni d'adaptateur Grist ; pas de publication.
- Firefox Manifest V3 et la comparaison via pont local ont été qualifiés **uniquement sur le pilote** ; Chrome, les autres pages et les scénarios d'erreur/récupération restent non qualifiés.
- Le pont ne persiste pas ses sessions en cas de redémarrage ; décisions antérieures conservées localement mais non rouvrables via l'interface. Port et page pilote codés en dur.
- Sélections de test anonymisées : par défaut, pas de garde additionnelle (`guard_count=0`) en situation réelle tant que les captures `local-anchors/` de l'enseignant n'ont pas été fournies ; contrôle global du rendu néanmoins maintenu.
- Reproductibilité **unitaire** sans ressource privée ; parcours utilisateur complet actuel **nécessite un accès autorisé séparé au dépôt pédagogique**. Une démonstration autonome publique reste à développer.

## Décision de licence (19 octobre 2026)

Le propriétaire a confirmé **AGPL-3.0-or-later**. `LICENSE` conserve le texte FSF original (AGPL v3) ; `LICENSE-NOTICE.md`, les notices SPDX dans le code et `README.md` précisent l'option « ou toute version ultérieure ». Les vérifications GitHub Actions après changement de licence et fusion de la PR #1 sont passées. L'intégration Firefox v0.4 a ensuite réussi sur le pilote (témoignage de l'enseignant du 19/10/2026).

## Orientation du 19 octobre (historique, remplacée par la transition ci-dessous)

1. **Préserver la v0.4 qualifiée**, ne pas remanier l'extension ni le pont local sans nécessité et tests de non-régression.
2. Examiner comment exploiter l'IA déjà accessible à l'enseignant pour **un dialogue contextualisé sur le passage sélectionné**, sans choisir prématurément un fournisseur, un framework ou une infrastructure. Priorité au parcours : sélection → demande libre → propositions IA explicites → essai A/B Quarto → décision locale.
3. Qualifier ce nouveau parcours d'abord sur le pilote Firefox ; maintenir la source pédagogique intacte, sans publication automatique et sans introduire de données privées dans le dépôt public.
4. Puis préparer une page Quarto **fictive et publiable** pour la reproduction autonome du parcours ; poursuivre la vérification du lien HTML publié ↔ commit source (`revision_verified=false`).

## Transition architecturale — 20 octobre 2026, branche `feat/quarto-readonly-revisions`

L'état initial contrôlé de `main` est `860bccf0df568c200d59ab2eaca0ec6b8e097095` : PR #1/#2 fusionnées, aucune PR ouverte, CI du push main réussie. Cette section décrit un **candidat de branche non fusionné**, pas une fonctionnalité de main.

La v0.4 est conservée sans modification de `extension/`, `serveur.py`, `resolve_source.py` ni `experiment.py`. Une couche Quarto *en lecture seule* est ajoutée avec `quarto_versions.py` et des tests purement fictifs :

- Identité logique explicite (`quarto:organisation/projet:chemin.qmd`), branche de travail nommée, commit Git SHA complet, blob Git + SHA-256.
- Déclaration éventuelle d'un commit « publié » avec `deployment_verified=false` ; l'absence de preuve laisse l'état `UNDECLARED` ou `DECLARED_NOT_VERIFIED`. Aucune publication réalisée ou supposée.
- Historique des commits touchant le seul fichier `.qmd` ; les dépendances Quarto restent **hors du périmètre de cet historique** et nécessiteront la vérification d'un instantané complet lors du rendu.
- Révisions lues dans les objets Git locaux : aucune récupération réseau, aucun changement de branche, aucun dossier de ressources privées, aucune écriture.
- Refus de chemins traversants, refs non explicites, SHA absents et liens symboliques.

**Vérifications au moment de la préparation de la branche :** 5 nouveaux tests unitaires réussis sur des dépôts Git temporaires fictifs ; compilation Python réussie. Les 18 tests historiques et les 5 nouveaux tests font partie de la suite exécutée par GitHub Actions : succès du job `unittest` sur `5a78f63b70e588be134445f69744b5b65307ed2f` ([exécution 39383644923](https://github.com/djibian/alliage/actions/runs/39383644923)). La CI simule Quarto et ne vaut pas validation Firefox. Pas de qualification Firefox ni de Quarto réel pour cette extension.

**Prochaine étape après revue et fusion humaine :** démonstration sur un projet Quarto fictif et construction d'aperçus historiques isolés, puis navigation Firefox. La modification Git externe et son rapatriement ne sont pas encore implémentés.

## Corrections demandées par la revue indépendante de P3.0 (20 octobre 2026)

L'[audit indépendant de la PR #3](https://github.com/djibian/alliage/pull/3#issuecomment-6285689245) a démontré trois défauts. La branche candidate a reçu une correction ciblée sans modifier la v0.4 :

- Désactivation de la substitution locale d'objets `git replace` pour les opérations de lecture et de comparaison d'ascendance : le SHA annoncé ne doit pas être associé au contenu d'un objet de remplacement.
- Utilisation de `git ls-tree -z` et analyse en octets pour accepter les noms de fichiers `.qmd` UTF-8, notamment les accents et guillemets, sans interpolation ni interprétation de chemin échappé.
- Utilisation de `git log -z` et découpage sur NUL pour préserver des sujets de commit contenant un retour chariot.

Trois tests fictifs de non-régression complètent les cinq tests P3.0 : la suite passe à 26 tests (18 historiques + 8 P3.0). L'intégration Firefox, le rendu historique Quarto et une publication réelle restent hors périmètre. Les tests et la CI sur le HEAD définitif doivent être revalidés avant fusion humaine, ainsi qu'une relecture indépendante des corrections.


## P3.1 — candidat d'aperçu historique isolé (20 octobre 2026)

**Base contrôlée** : PR #3 fusionnée sur `main` au SHA `6213db0ca3aa9927eab0b5a5ce9d9162b08c9185` ; les 26 tests (18 historiques + 8 P3.0) sont verts. Développement P3.1 sur `feat/quarto-historical-preview`, sans modifier les composants Firefox et le pont local.

Un laboratoire **privé** séparé a été initialisé avec une activité Quarto fictive (aucune ressource `pedagogie` transférée) : V1 conserve l'état initial, V2 modifie consigne et `_quarto.yml`, V3 modifie uniquement le CSS et l'illustration SVG, sans changer le blob du `.qmd`. Aucune page n'a été publiée.

Le candidat `quarto_historical_preview.py` extrait tous les fichiers **suivis par Git** d'un commit SHA-1 complet vers un dossier neuf à l'extérieur du dépôt source, avec `git --no-replace-objects`, analyse des chemins NUL, contrôles de taille, mode et SHA-256, refus des liens, gitlinks/sous-modules et pointeurs Git LFS. Il conserve un `manifest.json` et peut lancer un rendu Quarto local **uniquement sur demande explicite** avec `--render` et `--no-execute`. Les dépendances distantes restent non vérifiées, ainsi que l'équivalence avec un déploiement externe ; le rendu Quarto ne constitue pas une sandbox contre les scripts de projet ou filtres. Le format Git SHA-256 n'est pas pris en charge.

**Preuves** : tests unitaires sur dépôts Git temporaires fictifs, y compris commits à dépendances différentes et blob `.qmd` inchangé V2→V3 ; tests adversariaux `git replace`, sorties interdites, symlinks et LFS. Le workflow `quarto-historical-real.yml` installe Quarto 1.10.19 et rend réellement V1/V2/V3 du fixture fictif généré dans les tests. Le premier essai CI a détecté que `quarto render document.qmd --output-dir` est invalide ; le candidat a retiré cette option. Le second a montré qu'un document rendu peut écrire le HTML à côté du `.qmd`, même si un `output-dir` figure dans la configuration. Le candidat identifie maintenant explicitement le fichier HTML réellement obtenu et inscrit son chemin dans le manifeste. Les résultats CI du HEAD final restent à contrôler et n'autorisent pas une fusion sans revue.

**Étape suivante** : vérifier les tests GitHub exacts, obtenir une revue indépendante, fusion humaine, puis essai manuel de deux HTML de révisions différentes dans Firefox. Le navigateur de versions intégré est réservé à P3.2.


## P3.1 — corrections de provenance après audit indépendant (21 octobre 2026)

La [revue indépendante PR #4](https://github.com/djibian/alliage/pull/4#issuecomment-6309985044) conclut **CORRECTIONS REQUISES** sur deux points sans remettre en question l'architecture : un HTML de nom standard déjà présent dans l'instantané pouvait être confondu avec le fichier effectivement rendu lorsque Quarto produit une sortie personnalisée ; le manifeste affirmait à tort qu'aucune modification du dépôt et aucune publication n'avaient eu lieu, alors que Quarto peut exécuter des hooks même avec `--no-execute`.

Correctifs minimaux appliqués sur `feat/quarto-historical-preview` : refus **avant l'invocation de rendu** si l'un des chemins candidats HTML de nom standard existe déjà ; admission uniquement d'un candidat absent avant et présent après le rendu. Les sorties personnalisées hors de ce périmètre ne sont pas attestées. Test réel Quarto avec `output-file: personnalise.html` et ancien `activite.html` suivi par Git. Aucun support générique d'`output-file` n'est revendiqué à ce stade.

Le manifeste indique désormais `publication_status=NOT_INITIATED_BY_ALLIAGE`, `deployment_verified=false`, `source_repository_modified=null`, `source_repository_modification_verified=false` et `external_render_effects=NOT_VERIFIED` pour un rendu. Ces champs distinguent les **opérations demandées par Alliage** des effets potentiels du moteur Quarto, non confinés par une sandbox. Un test avec moteur simulé modifiant le dépôt original vérifie cette absence de fausse attestation. Le test avec `--render` continue d'exiger un projet **explicitement fiable**.

Conserver la distinction : la restitution des blobs Git est démontrable ; le lien exact entre rendu local et dépendances externes, les effets des hooks, les déploiements réels et la navigation Firefox restent hors des garanties P3.1. CI sur HEAD final puis revue indépendante du diff correctif requises avant fusion humaine.


## P3.1 — découverte au contrôle Firefox humain du 21 octobre 2026

L'enseignant a exécuté P3.1 avec Quarto 1.10.19 sur Ubuntu : V1, V2 et V3 sont reconstruits avec SHA et empreintes cohérents ; les trois HTML existent et sont visibles dans Firefox ; V2/V3 conservent le même blob `.qmd` mais illustrent des SVG différents ; le dépôt source reste intact selon la procédure de contrôle locale.

**Une anomalie visuelle a été observée dans les captures :** la configuration `_quarto.yml` de V2/V3 demande CSS et sommaire, mais les pages affichées ne présentent pas ces effets. Un diagnostic GitHub Actions sur le **laboratoire privé fictif** a confirmé l'absence de `styles.css` et d'indicateurs de sommaire dans les trois HTML produits par `quarto render activite.qmd --to html --no-execute` ([exécution de diagnostic](https://github.com/djibian/alliage-test/actions/runs/39567170016)). Un second essai en mode **projet Quarto** (`quarto render --to html --no-execute`) restitue les références CSS et le sommaire attendu en V2/V3 ([exécution comparative](https://github.com/djibian/alliage-test/actions/runs/39567325769)). Cette exécution de diagnostic termine sur un échec à l'étape suivante car le second rendu dans le même dossier modifie l'environnement déjà contrôlé ; **les observations CSS/sommaire ont été enregistrées avant cet échec**, mais ce job ne constitue pas une preuve de CI verte.

**Conséquence :** la qualification manuelle de P3.1 est seulement **partielle** : historique Git, contenu textuel et SVG validés ; prise en compte des paramètres de projet non qualifiée et désormais identifiée comme un défaut à corriger avant P3.2.

**Candidat correctif** sur `fix/quarto-project-context` : rendre en mode projet pour appliquer `_quarto.yml`, mais refuser par prudence les instantanés multi-documents et sans `_quarto.yml` ; la restitution sans `--render` reste disponible. Ajouter un test Quarto 1.10.19 vérifiant explicitement `styles.css`, la présence du sommaire en V2/V3 et son absence en V1. La validation complète, l'audit indépendant et une éventuelle fusion humaine sont encore à obtenir ; la PR #4 fusionnée n'est pas modifiée.


## P3.1 — résultat de la correction du contexte Quarto (21 octobre 2026)

La CI réelle de la PR #5 démontre qu'un instantané reconstruit dans un dossier temporaire **non caché** et rendu en **mode projet** applique la configuration `_quarto.yml`. L'essai intermédiaire dans un dossier caché `.alliage-preview-*` réussissait la commande Quarto mais ne produisait aucun HTML (l'énumération des sources à rendre n'aboutissait pas). Le correctif utilise désormais `alliage-preview-*` (sans point initial) et conserve l'extraction hors du dépôt source.

**Preuve P3.1 renforcée** : le test Quarto réel exige maintenant non seulement un HTML au SHA voulu, mais également une référence à `styles.css` sur V1/V2/V3 et la présence du sommaire attendu sur V2/V3. Il vérifie un répertoire de sortie `_site`, et le pilote refuse explicitement les rendus multi-documents ou sans `_quarto.yml`. Le scénario de sortie personnalisée avec ancien HTML et les attestations de non-publication précédemment corrigés restent testés.

**CI initiale du correctif** : [Quarto réel sur PR #5 : 8 tests réussis](https://github.com/djibian/alliage/actions/runs/39568121963) ; [CI Python du même HEAD](https://github.com/djibian/alliage/actions/runs/39568121759) réussie. Confirmation ultérieure sur le HEAD final et sur le laboratoire privé à effectuer avant revue indépendante et fusion éventuelle.
