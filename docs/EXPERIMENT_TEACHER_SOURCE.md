# P3.5 — Première liaison à la source canonique enseignante (lecture seule)

**Statut : expérimentation préparatoire ; pas encore de page professeur ouverte dans Firefox.**

## Constat architectural vérifié sans modification pédagogique

Le véritable référentiel Git de conception peut contenir **plusieurs activités Quarto**,
avec deux profils explicites issus des mêmes sources :
`eleve` et `professeur`. La destination professeur peut être
`dist/professeur`, la destination élève `dist/eleve`.
Ces chemins sont déclarés dans la configuration Quarto, distincts de l'URL
publique et de toute preuve de déploiement. Le profil professeur peut contenir
des informations réservées. **Ne jamais publier, copier dans Alliage ou servir
sur un réseau le rendu enseignant sans un nouveau contrat de confidentialité.**

Le moteur P3.1 utilisé par la PR #10 accepte, intentionnellement, un projet
minimal avec `_site`, une seule source et aucune configuration de profil.
Il **refuse** donc légitimement un projet réel multipage/profilé. Il serait
incorrect de desserrer ces restrictions sans expérience séparée du vrai rendu,
de ses dépendances, de la sélection de profil et des contrôles de sortie.

## Première preuve limitée

`quarto_teacher_provenance.py` compare une **ref Git explicitement nommée**
à un **SHA40 attendu** et lit à ce commit uniquement les objets Git de la source
`.qmd`, le SHA de l'arbre complet et les fichiers de configuration Quarto.
Il reconnaît une structure de configuration **très étroite** pour les
déclarations `professeur` et `eleve`. Cette reconnaissance n'est ni un
parseur YAML général ni une preuve du comportement effectif de Quarto.

Les statuts sont explicites :

- `SOURCE_PINNED_PROFILES_DECLARED_RENDER_NOT_VERIFIED` : source et déclarations
  profilées reconnues à un commit local Git, **rendu non exécuté**.
- `teacher_html_url_verified = false` : aucune page navigateur liée à ce
  commit n'a encore été attestée.
- `profile_effective_render_verified = false` : sortie réelle professeur non
  démontrée ; la séparation élève/professeur reste à vérifier sur le rendu.
- `checkout_bytes_verified = false`, `repository_id_scope =
  DECLARED_NOT_REMOTE_AUTHENTICATED` et `student_deployment_verified = false` :
  aucune inférence depuis le checkout, un nom de dépôt ou une publication.
- `publication_performed = false`, `network_access_performed_by_alliage =
  false`, `quarto_executed = false` : lecture seule.

### Essai volontaire sur une copie locale autorisée, en lecture seule

La copie du dépôt pédagogique reste **hors du dépôt Alliage**.
Le propriétaire choisit explicitement un clone déjà disponible et la
référence à examiner. Ne pas effectuer de `git fetch` ou `git checkout`
automatique ; ne pas prendre une ancienne ref pour une preuve de fraîcheur.

```bash
CODE="$HOME/projets/alliage-qualification"
REPO="$HOME/projets/pedagogie-alliage-test"
REF="refs/remotes/origin/main"
SHA="$(git -C "$REPO" rev-parse --verify "$REF^{commit}")"
python3 "$CODE/quarto_teacher_provenance.py" \
  --repo "$REPO" \
  --repository-id "djibian/pedagogie" \
  --source "enseignements/tim/4e-3e/activites/3e/02-nommer-classer/activite.qmd" \
  --working-ref "$REF" \
  --expected-sha "$SHA"
```

Ne **pas** transférer le JSON intégral de provenance si ses noms de chemin ou
SHA sont privés. Il suffit de signaler `status` et les booléens
`profile_effective_render_verified`, `teacher_html_url_verified`.
La commande ne produit pas de rendu professeur et ne touche pas aux
documents élèves. Son succès ne qualifie pas encore une page utilisable.

## Prochaine expérience, seulement après cette preuve

1. Rendre **une ressource précise au profil `professeur`** dans un
   instantané Git isolé, avec Quarto réel et consentement explicite à
   l'exécution de hooks/filters ; ne jamais rendre/publiciser les autres
   ressources par inadvertance.
2. Vérifier le graphe complet des dépendances, le HTML produit, le
   cloisonnement des sorties et les éventuelles informations réservées.
3. Ouvrir la ressource enseignante via un canal local sûr, en ancrant l'URL
   courante au commit et aux empreintes plutôt qu'à une query libre.
4. Prouver la conservation du panneau historique, le comportement natif
   Quarto et l'absence de toute synchronisation ou publication élève.

L'interface finale ne doit pas être une nouvelle commande de laboratoire :
cette preuve de provenance sert seulement à fixer les invariants qui
permettront ensuite une expérience fluide dans le navigateur (A013).
