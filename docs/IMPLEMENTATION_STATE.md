# Alliage — état technique de reprise

**Date de capitalisation : 19 octobre 2026.** Sources reprises **effectivement** de l'archive `pedagolab-atelier-quarto-v0.4.zip` (`docs/ORIGIN_HASHES.json`) ; sans réimplémentation de substitution. Ne pas confondre les tests unitaires locaux avec une qualification Firefox réelle.

## Inventaire des quatre livrables antérieurs

Archives originelles de la conversation (l’enseignant dispose des ZIP téléchargés, le dépôt public ne les contient pas) : `pedagolab-selection-v0.zip` (v0.1 : `manifest.json`, `selection.js`) ; `pedagolab-source-v0.2.zip` (v0.2 : `resolve_source.py`, ancrages, tests) ; `pedagolab-quarto-experiment-v0.3.zip` (v0.3 : `experiment.py`, tests de rendu simulé et comparaison) ; `pedagolab-atelier-quarto-v0.4.zip` (v0.4 : les **12 fichiers sources** énumérés dans le référentiel de provenance). Les fichiers du code actuel sont conservés à la racine et dans `extension/`, `tests/`, `exemples/`, sans recopier les archives ni les documents du dépôt pédagogique privé. Le dernier ZIP v0.4 avait été extrait par l’enseignant dans `~/Téléchargements/pedagolab-atelier-quarto-v0.4/`, et sa source externe de test dans `/tmp/pedagolab-pedagogie/` a ensuite disparu. La copie de conservation est désormais le dépôt `djibian/alliage` **après push**, pas une archive temporaire.

## Dernières versions validées

- **v0.3 (fonctionnement Quarto réel validé par l'enseignant le 18/10/2026)** : 13 tests automatisés OK ; deux variantes `cinq ressources`/`cinq fichiers proposés`, `RENDER_VERIFIED_LOCAL` avec `render_verified=true` pour A et B ; visualisation OK ; `production_write=false`, `publication=NOT_PUBLISHED`. Source pilote au commit `4530afacc4b45d5707f4f3c5029386bb5e141ec4`, blob `df1f38bb6e6178fc07f2d078cb86256a8791d05c`.
- **v0.4 (code actuel)** : 18 tests automatisés OK (suite initiale) puis 18 OK après anonymisation des exemples publics et reprise du code, le **19/10/2026**, Python 3.12. Tests avec moteur Quarto **simulé** et serveur HTTP en boucle locale ; **cycle entier Firefox + pont local non encore qualifié**.
- **Premier lancement v0.4 sur ordinateur enseignant** : échec **avant démarrage** : `FileNotFoundError` du clone `/tmp/pedagolab-pedagogie`, disparu. Aucune requête extension/vrai Quarto lancée lors de cet essai. Le CLI amélioré signale le chemin absent et exige `--repo` ; correction non encore testée sur l'ordinateur enseignant.

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
- Extension Firefox Manifest V3 et Chrome non qualifiées sur les navigateurs réels ; ouverture local comparaisons et sécurité du pont à revoir en tests d'intégration.
- Le pont ne persiste pas ses sessions en cas de redémarrage ; décisions antérieures conservées localement mais non rouvrables via l'interface. Port et page pilote codés en dur.
- Sélections de test anonymisées : par défaut, pas de garde additionnelle (`guard_count=0`) en situation réelle tant que les captures `local-anchors/` de l'enseignant n'ont pas été fournies ; contrôle global du rendu néanmoins maintenu.
- Reproductibilité **unitaire** sans ressource privée ; parcours utilisateur complet actuel **nécessite un accès autorisé séparé au dépôt pédagogique**. Une démonstration autonome publique reste à développer.

## Première action après capitalisation

1. Vérifier le commit/PR contenant cette reprise ; tests CI, statut licence et absence d'informations privées.
2. Sur l'ordinateur Ubuntu de l'enseignant : cloner la source dans `~/projets/pedagogie` (ou réutiliser une copie persistante propre), lancer `python3 serveur.py --repo "$HOME/projets/pedagogie"`, charger temporairement l'extension Firefox.
3. Refaire le parcours réel A/B/rejet sur la page pilote, contrôler `rapport.json`, `decision.json`, garder source Git inchangée ; rapporter résultats et captures **hors dépôt public**.
4. Ensuite seulement : IA contextuelle et page fictive publique autonome.
