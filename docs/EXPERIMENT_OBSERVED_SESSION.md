# Alliage — raccordement expérimental local P3.3 → P3.1 → P3.2

> **Expérience Quarto fictive uniquement.** Ce protocole n'est ni une interface
> produit, ni une procédure de publication, ni une synchronisation élève.

## Objet et frontières

Une seule commande Python relie les trois composants existants. Elle lit une
**ref de suivi Git locale explicite**, vérifie que celle-ci avance depuis un SHA
antérieur sans divergence, recrée des instantanés complets Git dans une nouvelle
session extérieure au dépôt, les rend avec Quarto réel sur demande, puis prépare
la page historique existante pour Firefox. Aucune IA n'est intégrée.

Cette version est volontairement limitée à `activite.qmd` dont le rendu est
`activite.html` : c'est la cible actuellement autorisée par l'extension Firefox
P3.2. Pour une autre ressource, elle **refuse** plutôt que d'annoncer une navigation
non qualifiée. Les labels locaux `V1` et `V2` sont propres à chaque session :
ils ne sont **pas** des versions pédagogiques mondiales.

## Préconditions

- Ubuntu avec Python 3, Git, Quarto installé et l'extension historique Firefox
  P3.2 déjà autorisée à lire les pages `file://`.
- Clone **local et autorisé**, dont le contrat `AGENTS.md` a été lu ; projet
  entièrement fictif, examiné et jugé digne de confiance.
- Branche dédiée `experiment/*` et SHA complet de référence déjà connu.
- Le suivi de la branche distante (`refs/remotes/origin/experiment/*`) est
  déjà présent. L'actualiser **séparément et explicitement**, seulement si
  l'enseignant le décide : Alliage n'exécute **aucun fetch**.
- Aucun contenu privé ne doit être copié dans le dépôt public Alliage.

## Étape 1 — précontrôle sans rendu ni dossier créé

```bash
python3 quarto_observed_session.py \
  --repo "$HOME/projets/alliage-p31/alliage-test" \
  --repository-id djibian/alliage-test \
  --source activite.qmd \
  --tracking-ref refs/remotes/origin/experiment/historique-quarto \
  --baseline-sha cb15dc87417992d7debdd7e0dc4ade4fb5688877 \
  --check
```

Attendu pour le scénario fictif V3 → V4 : `relation=FAST_FORWARD`,
`project_tree_changed=true`, `source_blob_changed=false`, le SHA V4 exact
dans `observed_commit` et `remote_freshness_verified=false`.
Une ref inchangée, en recul ou divergente, un arbre identique ou une
ressource hors du pilote sont refusés. Aucun rendu ni réseau implicite.

## Étape 2 — rendu volontaire du projet Quarto de confiance

Ne lancer ceci que si le projet historique (y compris ses filtres, hooks et
extensions éventuels) est jugé fiable : **`--no-execute` n'est pas un
environnement isolé** et les effets externes restent non vérifiés.

```bash
python3 quarto_observed_session.py \
  --repo "$HOME/projets/alliage-p31/alliage-test" \
  --repository-id djibian/alliage-test \
  --source activite.qmd \
  --tracking-ref refs/remotes/origin/experiment/historique-quarto \
  --baseline-sha cb15dc87417992d7debdd7e0dc4ade4fb5688877 \
  --render --trusted-quarto
```

Le JSON de sortie fournit `navigation_url` et les SHA de référence/observation
immuables. Ouvrir l'URL dans **Firefox avec extension P3.2 autorisée** ; observer
V1 (Git V3), choisir V2 (Git V4), puis revenir à la référence V1. Contrôler
manuellement le CSS et le retour. **Aucun résultat Firefox n'est déclaré PASS par
cette commande** ; `firefox_manually_verified=false`.

## Garanties limitées

- Pas de fetch, checkout, commit, validation, restauration ni publication par
  le raccordement. Les commits rendus sont fixés par SHA, même si la ref de
  suivi change entre observation et rendu.
- Nouvelle session `~/alliage-experiences/historique/p31-final-observed-*/` à
  chaque essai ; les sessions antérieures ne sont jamais remplacées. Une session
  incomplète est supprimée après échec ordinaire ou interruption Python
  (`KeyboardInterrupt`/Ctrl+C, `SystemExit`), si le système de fichiers
  le permet. **Ni SIGKILL, ni arrêt machine, ni coupure électrique ne sont couverts.**
- `checkout_head_and_status_unchanged=true` signifie seulement que le SHA
  du HEAD et le résultat de `git status --porcelain` sont identiques avant et
  après la commande. `checkout_file_contents_unchanged_verified=false` :
  les octets, attributs et modifications intermédiaires du checkout ne sont
  **pas** attestés ; un fichier déjà marqué `M` peut être modifié à nouveau
  sans changement de statut. Aucun contrôle universel des effets externes
  de Quarto.
- Le HTML et les dépendances sont vérifiés **à la création seulement** ;
  Firefox ne réalise pas de vérification cryptographique permanente.
- `repository_id` est une identité **déclarée**, pas une identité distante
  cryptographiquement authentifiée. Une ref `origin/*` locale ne prouve pas
  la fraîcheur du serveur. Aucun statut de publication/déploiement n'est attesté.

## Qualification et prochaine décision

Les tests unitaires utilisent des dépôts Git entièrement fictifs ; le
workflow Quarto réel doit exécuter **les deux suites** `test_quarto_historical_preview.py`
et `test_quarto_observed_session.py` sous `ALLIAGE_TEST_REAL_QUARTO=1`.
Sa réussite est à établir sur le HEAD exact dans les journaux, sans test réel ignoré.
Le workflow P3.2 continue de tester le DOM de l'extension, mais n'est pas une
qualification visuelle automatisée de Firefox. Une validation humaine reste
nécessaire pour confirmer l'utilité et l'ergonomie de la commande.

Mesurer : **richesse** neutre (aucune nouvelle sélection), **fluidité** améliorée
pour les seules opérations manuelles déjà démontrées, **maîtrise** renforcée par
l'immuabilité et l'absence de publication, **fidélité** vérifiée sur Git, les
dépendances et le rendu Quarto. Les sessions et `navigation.html` demeurent un
support expérimental, non le modèle produit définitif.
