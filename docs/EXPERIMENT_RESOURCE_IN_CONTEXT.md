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
- **Détail critique Firefox :** les motifs `content_scripts.matches` comparent
  aussi la query à la partie chemin. La règle destinée au pilote comporte
  donc deux motifs : `.../activite.html` (ouverture neutre sans métadonnées)
  et `.../activite.html?*` (ouverture avec `alliage-history-v0`).
  Sans le second, le navigateur ne charge pas le script sur `resource_url`,
  même si l'extension est correctement installée et l'accès aux fichiers
  locaux autorisé. Le script valide ensuite le paramètre unique et les SHA.
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

**Blocage supplémentaire observé sur Firefox Ubuntu :** le chargement de
modules JavaScript Quarto (`quarto.js`, `tabsets.js`) depuis `file://`
est refusé par CORS. Il est **distinct** de la garde d'injection Alliage
corrigée ci-dessus, et empêche à lui seul d'affirmer la fidélité fonctionnelle
de la ressource. Ne pas modifier les paramètres de sécurité Firefox pour
contourner CORS ; l'étudier séparément avant de qualifier la ressource Quarto
comme pleinement opérationnelle.

Une CI Node simule le DOM et les URL ; une CI Quarto réelle contrôle
les SHA et l'absence de modification des HTML, mais seule l'observation
humaine valide le navigateur Firefox et son comportement `file://`.

## Variante HTTP locale pour qualifier les modules Quarto (pilote optionnel)

Le premier essai humain a **confirmé** la présence du panneau et le parcours
historique en `file://`. Il a aussi mis en évidence que Firefox bloque les
modules ES natifs `quarto.js` et `tabsets.js` chargés depuis ce schéma :
la navigation de l'extension ne constitue donc pas, à elle seule, une
qualification complète de Quarto.

Pour ce **blocage démontré seulement**, un transport HTTP expérimental distinct
du pont v0.4 sert **uniquement les fichiers générés et inventoriés** de V1/V2.
Il n'introduit ni point d'écriture, ni pilotage Quarto/Git par le navigateur,
ni publication, ni serveur permanent, ni répertoire partagé librement.

Dans un terminal Ubuntu, depuis le clone Alliage sur le HEAD de la PR :

```bash
python3 "$CODE/quarto_local_http.py" \
  --session "$HOME/alliage-experiences/historique/p31-final-observed-4kdo1004" \
  --resource-id "quarto:djibian/alliage-test:activite.qmd"
```

**Garder ce terminal ouvert** jusqu'à la fin de l'essai. Il imprime une seule
adresse `http://127.0.0.1:<port>/alliage-local-<jeton>/V2/project/_site/activite.html?alliage-history-v0=...`
à copier **intégralement** dans Firefox avec l'extension rechargée depuis la
version actuelle de `extension/manifest.json`. Le port est choisi par le
système et le jeton local est régénéré à chaque lancement. Ne pas partager
ce lien. Arrêter le serveur par **Ctrl+C**, sans état persistant.

**Garde-fous :** écoute uniquement sur `127.0.0.1` ; Host exact ; rejet
des origines externes et des requêtes `Sec-Fetch-Site: cross-site` ; préfixe
aléatoire imprévisible ; routes explicitement limitées aux fichiers
`project/_site` des deux manifestes revérifiés ; SHA-256 et tailles revérifiés
**à chaque réponse** ; refus des liens symboliques, chemins non inventoriés,
fichiers modifiés et méthodes d'écriture ; en-têtes `no-store`,
`nosniff`, `no-referrer`, `same-origin` et refus d'iframe.
Aucune origine CORS générale n'est autorisée. La navigation conserve le jeton
de session et le paramètre historique, mais celui-ci reste **déclaratif et
non signé**. Tout autre processus présent sur le même poste peut en principe
contacter le loopback : le jeton réduit l'exposition, il ne crée pas une
isolation de sécurité contre un poste compromis.

Vérifications humaines demandées : les modules Quarto ne produisent plus
d'erreur CORS ; sommaire et interactions natifs fonctionnent ; V2 violet →
V1 rouge → V2 violet, `#consigne`, retour navigateur, et absence du panneau
si la query est supprimée ; aucun changement des octets HTML/CSS des deux
instantanés et aucun effet Git/publication. Le navigateur doit signaler
une erreur plutôt que servir un actif modifié. **Ce résultat HTTP devra être
observé dans Firefox réel** ; les tests locaux HTTP ou les CI seuls ne le
démontrent pas.

Le transport ne constitue **pas** le modèle de navigation produit (A013).
Le `file://` antérieur et la `navigation_url` existante sont préservés.

## Si le pilote est concluant

Ne pas généraliser le paramètre de requête d'URL à une architecture produit ; le
traiter comme un mécanisme de laboratoire à éliminer ou remplacer. La
prochaine question est l'attachement sûr de l'historique au document
enseignant réellement consulté, avec source canonique, SHA de provenance
et identité d'application. La publication reste un chantier distinct.
