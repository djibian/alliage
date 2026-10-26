# Alliage — navigation historique dans le HTML Quarto rendu (essai Firefox)

**Statut : candidat expérimental**, à qualifier dans Firefox avant toute fusion.
Ce n'est **pas** encore l'ouverture de l'historique depuis la ressource
canonique enseignante publiée : la version publiée n'a pas de lien de provenance
vérifiable avec le laboratoire fictif. L'expérience porte sur les **vrais
aperçus Quarto locaux** déjà produits à partir de commits Git explicites.

## Ce qui change

Le parcours P3.3 → P3.1 → P3.2 continue de produire et vérifier deux
instantanés historiques, sans écriture sur les sources ni déploiement.

La commande `quarto_observed_session.py --render --trusted-quarto` renvoie
désormais **deux adresses distinctes** :

- `navigation_url` : ancienne page de navigation dans une iframe, conservée
  pour comparaison et non-régression ;
- `resource_url` : ouverture **directe du fichier
  `V2/project/_site/activite.html`** tel que rendu par Quarto, sans wrapper
  et sans modifier les octets de son HTML. Un paramètre de requête d'URL transporte
  uniquement l'identité déclarée de la ressource, deux SHA Git et la version
  visible au moment de la préparation. L'extension ajoute un panneau
  surimposé au DOM du navigateur ; elle n'écrit aucun fichier.

La nouvelle interface « Alliage · Historique sur la ressource » affiche
`V1` (référence antérieure) et `V2` (révision observée), permettant
`V2 → V1 → V2` **sans revenir à `navigation.html`**.

À la création des aperçus, P3.1 établit maintenant un **inventaire borné
de tous les fichiers réguliers produits dans `project/_site`**, avec SHA-256,
taille et chemin. P3.2 compare lors de chaque construction d'URL directe
l'inventaire à l'ensemble réellement présent (y compris le CSS généré
`_site/styles.css`, distinct du CSS suivi dans Git) et refuse tout fichier
absent, surnuméraire, modifié, symbolique ou non régulier. Les sessions
antérieures sans cet inventaire restent lisibles dans la navigation P3.2
historique, mais **ne peuvent pas obtenir cette nouvelle URL directe**.
Les deux manifestes doivent aussi attester exactement la source
`activite.qmd` et son HTML `project/_site/activite.html`.

Les SHA montrés dans l'interface proviennent de métadonnées transmises par
l'URL ; ils **ne sont pas authentifiés de nouveau par Firefox**. Une personne
peut modifier ce paramètre de requête : il ne constitue ni preuve de provenance en
temps réel, ni certificat d'intégrité, ni signature. La vérification des
manifestes et des empreintes appartient à P3.1/P3.2 **au moment où l'URL
est générée**. Aucun navigateur n'a été attesté par les seuls tests DOM.

## Frontières et garanties

- **Aucun appel réseau, accès Git, lecture d'un fichier compagnon, serveur
  supplémentaire, mémoire du navigateur ou permission large**. La nouvelle
  règle de l'extension est limitée au chemin local du laboratoire
  `p31-final-observed-*/V*/project/_site/activite.html`. La garde JS
  exige en plus un chemin strict, un paramètre de requête explicite et le document
  principal (pas l'iframe). Pas d'activation sur les autres HTML, ni sur la
  page publique de la v0.4.
- Un paramètre de requête malformé ou absent produit **aucun panneau historique** ;
  les destinations de navigation sont reconstruites à partir de la session
  visible et des noms fixes `V1`/`V2`, jamais depuis une URL transmise
  par le paramètre de requête.
- **Attestation ponctuelle uniquement** : les empreintes des dépendances
  générées sont vérifiées avant la fourniture de l'URL directe. Firefox ne
  recalcule pas ces empreintes pendant l'affichage. L'inventaire porte sur
  `_site` ; les éventuels effets externes du moteur restent non vérifiés.
- Quarto n'est **pas sandboxé** ; l'exécution demande toujours
  `--trusted-quarto`. La ref de suivi locale peut être obsolète ; le
  checkout n'est attesté qu'au niveau HEAD/statut, pas de ses octets.
- La navigation ne valide, ne restaure, ne sauvegarde et ne publie rien.
  Elle n'affecte pas les ressources élèves. Les intitulés `V1` et `V2`
  restent **locaux à la session expérimentale**, non des statuts métier.
- **Limite produit importante :** l'aperçu Git est une copie isolée du
  rendu, pas la véritable ressource canonique ouverte sur son URL
  enseignante. Lier cette dernière à l'historique nécessite un contrat de
  provenance qu'on ne supposera pas sans preuve.

## Essai manuel attendu (Ubuntu / Firefox)

1. Charger la version de l'extension depuis la **branche de la PR sur son
   SHA exact**, en sélectionnant `extension/manifest.json` dans
   `about:debugging#/runtime/this-firefox` ; autoriser la lecture des
   fichiers locaux si Firefox le demande. Ne pas modifier les ressources
   pédagogiques.
2. Dans le **laboratoire fictif autorisé et vérifié**, exécuter
   `quarto_observed_session.py --check`, puis explicitement
   `--render --trusted-quarto` comme documenté dans
   [EXPERIMENT_OBSERVED_SESSION](EXPERIMENT_OBSERVED_SESSION.md).
3. Copier le champ **`resource_url` complet** (y compris son paramètre de requête
   `?alliage-history-v0=...`) dans Firefox.
4. Vérifier directement sur la ressource rendue : titres violets V2,
   bouton V1 → titres rouges, bouton V2 → titres violets. Le panneau doit
   rester visible, sans ouvrir `navigation.html` et sans iframe principale.
5. Contrôler ensuite `navigation_url` (ancien pilote), l'état HEAD/statut du
   clone, la consultation d'une ancienne session et l'absence de publication.
6. Vérifier que l'ouverture **sans paramètre de requête** du même
   `activite.html` ne crée pas de panneau. Vérifier également qu'un lien
   Quarto vers `#consigne` conserve le panneau et que le changement de
   révision conserve cette ancre. L'extension v0.4 publique ne doit
   pas être affectée par cette nouvelle injection locale.

Critères : **fluidité** de navigation dans la ressource elle-même ;
**fidélité** aux rendus CSS natifs ; **maîtrise** de la révision affichée
et absence de publication ; **richesse** inchangée.

Une CI Node simule le DOM et les URL ; une CI Quarto réelle contrôle
les SHA et l'absence de modification des HTML, mais seule l'observation
humaine valide le navigateur Firefox et son comportement `file://`.

## Si le pilote est concluant

Ne pas généraliser le paramètre de requête d'URL à une architecture produit ; le
traiter comme un mécanisme de laboratoire à éliminer ou remplacer. La
prochaine question est l'attachement sûr de l'historique au document
enseignant réellement consulté, avec source canonique, SHA de provenance
et identité d'application. La publication reste un chantier distinct.
