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
