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
