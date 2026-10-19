# AGENTS — contrat des agents intervenant sur Alliage

## Mission

Alliage augmente des applications pédagogiques web par une interaction contextualisée enseignant–IA–ressource. Ne remplace pas Quarto, Grist, Moodle, Snap!, Collabora ou WebeeBlocks. Priorité : **richesse, fluidité, maîtrise, fidélité**. Construire par expérimentation réelle, sans agent/framework générique prématuré.

## Avant chaque intervention

1. Lire ce fichier, `docs/PRODUCT_VISION.md`, `docs/ROADMAP.md`, `docs/IMPLEMENTATION_STATE.md`, `docs/DECISIONS.md`.
2. Lire le SHA exact de `main`, les branches/PR et checks existants ; revalider la gouvernance si `main` a changé.
3. Vérifier le véritable code et les tests ; ne jamais supposer que l'état d'une conversation reflète l'état GitHub.
4. Avant interaction avec un dépôt pédagogique/serveur externe : lire son `AGENTS.md` et ses décisions applicables, demander l'autorisation de toute écriture. Les dépôts `pedagogie`, `webeeblocks` et `infrastructure` restent distincts et privés le cas échéant.

## Règles de développement

- Faire évoluer la **v0.4 existante** (`extension/`, `serveur.py`, `resolve_source.py`, `experiment.py`), ne pas la remplacer par un pseudocode.
- L'interface commune, les adaptateurs par application et les connecteurs de modification sont une **hypothèse**, pas des couches imposées.
- Distinguer : sélection HTML, compréhension, proposition temporaire, variante de test réelle, choix local, modification de conception et publication. Un changement DOM n'est jamais un rendu réel.
- Conserver des ancres liées à la version Git, au fichier, aux offsets et au contexte ; refuser une cible ambiguë ou une source dérivée.
- Tests en copies isolées ; opérations traçables, réversibles, **aucune écriture sur des ressources d'élèves**, aucun déploiement automatique.
- Les identifiants `pedagolab.*`, `X-Pedagolab-Token`, les dossiers internes et sélecteurs hérités sont des **interfaces techniques de compatibilité v0**, pas le nom du produit. Ne les renommer qu'avec tests de migration.
- Tout code, exemple et test du dépôt public doit être publiable et reproductible, sans contenu provenant des dépôts privés.

## Commandes de base

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile serveur.py experiment.py resolve_source.py
git diff --check
```

Le rendu réel exige `quarto` dans `PATH`. Le test interactif pilote exige une **copie locale autorisée** du dépôt pédagogique, un `--repo` vers cette copie, le serveur en `127.0.0.1:8765` et l'extension temporaire Firefox (`extension/manifest.json`). Détails dans `README.md`. Les 18 tests automatisés **simulent Quarto** ; ne pas leur attribuer une qualification de navigation réelle.

## Sécurité et publication

- Dépôt **public**. Contrôler fichiers **et historique Git** avant tout push/merge : secrets, données personnelles, captures réelles, corrections, projets `.qmd` privés, configurations VPS, artéfacts locaux, répertoires de clones.
- Ne pas committer de jeton de serveur ; jeton éphémère en mémoire uniquement. Ne pas ouvrir le pont local sur le réseau.
- Les sources pédagogiques privées doivent rester hors du dépôt et hors des fixtures publiques. Les tests de sélection sont fictifs.
- Une décision locale A/B n'est **pas** une acceptation de modification dans Git, ni une publication aux élèves.
- Le fichier `LICENSE` AGPL v3 préexiste ; qualification `-only`/`-or-later` **à décider avec le propriétaire** avant validation de licence. Ne pas inventer d'accord.

## Branches, PR, preuves et reprise

- Travail significatif sur branche dédiée puis PR révisable, jamais de force-push sur `main`. Regrouper changements cohérents.
- Tester avant push, vérifier `git diff --check`, relire le diff et les fichiers suivis, vérifier CI puis tester le résultat après fusion. Une CI verte ne remplace pas les tests humains.
- Conserver dans `docs/IMPLEMENTATION_STATE.md` : SHA, tests réellement exécutés, blocages, limitations et prochaine action. Noter toute décision stable dans `docs/DECISIONS.md` et ajuster `docs/ROADMAP.md` seulement si utile.
- Reprise après interruption : repartir des **faits GitHub** (main, branches, PR, checks), relire les fichiers, refaire les tests, puis poursuivre la plus petite action éligible. Ne pas déduire une réussite d'une archive ou d'une précédente conversation.
