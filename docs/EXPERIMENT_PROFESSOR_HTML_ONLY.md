# P3.6D — Projection d'un seul document HTML fictif

**Statut : PR #16 Draft, empilée sur la PR #15.**
Aucun corpus professeur réel n'est admis ni ouvert sur HTTP.

## Constat utilisé

La démonstration Firefox fictive P3.6B avec `embed-resources: true`
a effectivement affiché la page avec une seule requête utile : le HTML
complet (CSS `data:text/css` inclus dans le fichier). Une requête
automatique distincte à `favicon.ico` a été refusée (404).

La surface historique P3.6C prévoyait une route par actif présent sous
`dist/professeur/`, même pour CSS, JS, médias et fichiers renommés
conformes aux extensions autorisées. Le vérificateur de SHA démontre
l'intégrité d'un fichier, **pas** l'autorisation de le diffuser.

## Contrat expérimental plus strict

1. Vérifier la **session entière** et le manifeste par l'oracle P3.6A
   (`verify_session(..., include_manifest=True)`), sans seconde
   désérialisation d'un manifeste mutable.
2. Vérifier la structure de l'inventaire de sortie, les limites de taille,
   l'identité du seul HTML, et refuser les noms de source/configuration
   précédemment interdits.
3. Sceller par `dir_fd`, `O_NOFOLLOW`, `fstat`, SHA-256
   uniquement les octets du fichier `rendered_html` vérifié.
4. Construire une **table d'une unique route HTTP**, correspondant
   exactement au HTML. Toutes les autres demandes sont refusées, y
   compris vers des ressources qui existent sur disque, sont inscrites
   dans le manifeste et ont un SHA-256 valide.
5. Conserver la table figée, les octets scellés, la politique CSP sans
   scripts ni connexions, le serveur loopback à capacité aléatoire, le
   refus des en-têtes ambigus et la CLI directe désactivée.

## Épreuves à exécuter

- HTML canonique : 200, octets exacts, méthode HEAD sans corps.
- CSS et JS de sortie inventoriés, empreintes correctes : 404.
- Source fictive intentionnellement déguisée en `.css` et inventoriée :
  vérification P3.6A PASS, refus HTTP 404.
- Après mutation du HTML sur disque : serveur déjà admis → octets
  scellés inchangés ; nouvelle admission → refus.
- Inventaire erroné, symlink, manifeste remplacé, Host/Origin non
  conforme, réaffectation des attributs : tests historiques conservés.
- Fixture Quarto réelle 1.10.19 et 1.10.20 via CI. La fidélité
  d'affichage doit être recontrôlée en Firefox après contre-revue.

## Portée et limitations

Ce mode ferme **la classe de routes HTTP auxiliaires** : les fichiers
sources renommés en CSS, JS ou image ne sont plus servis *en tant que
fichiers séparés*, même si leur nom trompe une liste de suffixes.
Cela **ne prouve PAS que le contenu du HTML est sûr** : il peut contenir
du texte confidentiel, des liens, du CSS ou du contenu intégré. Une
source délibérément recopiée dans l'unique HTML reste exposée à
l'utilisateur qui ouvre la page.

Le coût fonctionnel est intentionnel : une ressource Quarto qui
référence un CSS, une image ou une vidéo non embarqués peut perdre cet
élément. **Ne pas réactiver automatiquement les actifs pour restaurer
l'apparence.** La fidélité sera validée uniquement sur la fixture
`embed-resources: true`, puis mesurée à nouveau si le produit évolue.

L1 (provenance + consentement), L4 (navigation externe, ancre/URL,
meta refresh, chargements) et la portée réelle de l'application du
profil Quarto restent hors de cette PR. Le marqueur `fiction` n'est
pas une preuve cryptographique d'autorisation. Aucune activation sur
la session enseignante réelle, aucune fusion, aucun JS et aucune
publication élève.

**Porte suivante :** CI sur le HEAD final, revue indépendante ciblée
sur le principe « HTML seul », puis régression Firefox fictive avant
toute décision d'architecture sur le véritable lecteur professeur.
