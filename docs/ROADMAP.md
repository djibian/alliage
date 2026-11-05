# Alliage — roadmap opérationnelle Pareto (5 novembre 2026)

**But produit :** dans Firefox, l'enseignant visualise une activité Quarto
publique/fictive, dialogue avec le **chatbot natif du panneau latéral**,
autorise une modification Git dans une branche isolée, compare deux
rendus **Quarto réels**, puis retient ou écarte la proposition,
sans publication automatique.

L'ancienne roadmap, ses expérimentations et décisions restent conservées
dans [ROADMAP_ARCHIVE_202610.md](ROADMAP_ARCHIVE_202610.md).
Contrats inchangés : `AGENTS.md`, `PRODUCT_VISION.md`, `DECISIONS.md`.

## V0 pédagogique — `DEMO_REAL_FIREFOX_PASS`, logiciel intégré dans `main`

**Preuve métier acquise le 5 novembre 2026** :
[issue #23 clôturée](https://github.com/djibian/alliage/issues/23).
Dans le véritable Firefox Ubuntu, l'enseignant a sélectionné
un passage Quarto fictif, utilisé ChatGPT dans le panneau
latéral natif, obtenu la lecture puis l'écriture GitHub
sur la branche autorisée, déclenché la récupération Git
volontaire et deux rendus Quarto réels, navigué V1/V2
et choisi « Retenir V2 (local) », sans publication.
L'IA de la sidebar disposait effectivement d'outils
GitHub en lecture **et en écriture dans cette configuration**.
Cela ne garantit pas l'accès sur toutes les installations.

**Logiciel livré :** [PR #22](https://github.com/djibian/alliage/pull/22)
fusionnée dans `main` après contre-expertise indépendante favorable
et autorisation explicite du propriétaire ; commit
`3494ec2b9112dfd98e13936de7d5a8eb9b204c5d`,
trois workflows post-fusion verts. La branche
`experiment/pareto-quarto-demo` est restée séparée : **ne jamais
la fusionner dans `main`.**

**Itération suivante, Pareto :** éliminer les manipulations
récurrentes sans inventer d'infrastructure IA.
1. Premier gain livré dans la PR #22 : raccourci
   `quarto_pareto_demo.py --demo` pour éviter de répéter
   dépôt et ref, **sans** retirer la confirmation de confiance
   ou autoriser un fetch implicite.
2. **Après intégration de #22** : mesurer l'intérêt du
   raccourci IA natif de sélection Firefox pour le
   dialogue simple. La sélection et le titre ne prouvent
   ni SHA Git ni branche autorisée : le bouton Alliage
   demeure utile pour une demande de modification de source.
3. [Issue #25](https://github.com/djibian/alliage/issues/25) :
   **actualisation Quarto volontaire depuis Firefox**,
   après un commit autorisé. Candidat
   [PR #26](https://github.com/djibian/alliage/pull/26) en Draft :
   réemploi du serveur loopback existant, ouverture explicite
   `--browser-refresh` sur la seule fixture publique, confirmation
   distincte et token HTTP à usage unique. Le rendu antérieur
   reste actif jusqu'à vérification complète du nouveau.
   **CI Quarto réelle et contrôles HTTP nécessaires ; une
   preuve Firefox réelle est obligatoire avant livraison.**
   Aucun fetch caché, checkout, écriture source ou publication.

Les étapes ci-dessous constituent le **contrat historique
qui a été validé**, et non des travaux à relancer :



1. **Fournir une activité Quarto publiable sans secrets** : branche
   `experiment/pareto-quarto-demo` du seul dépôt `djibian/alliage`,
   arbre minimal autonome ; ne jamais proposer sa fusion dans `main`.
2. **Transfert volontaire vers l'IA existante :** bouton sur l'aperçu
   `historique_ressource.js` qui prépare un texte limité
   (passage sélectionné ou identité de la ressource). Confirmation
   explicite « public/fictif » avant copie manuelle ; aucun accès
   au contenu privé ni aux conversations. **À qualifier dans Firefox réel.**
3. **Écriture Git externe et autorisée :** tester le chatbot **dans le
   panneau natif Firefox**, non dans une autre conversation, en
   lecture puis en écriture sur la branche expérimentale.
   Si écriture indisponible : demander un patch explicite et
   l'appliquer via interface GitHub/Codex/outil connecté autorisé,
   sans chercher à automatiser la page du chatbot.
4. **Rendu et comparaison :** récupération Git explicitement choisie,
   puis `quarto_pareto_demo.py` réutilise la chaîne P3.3→P3.1→P3.2
   et le HTTP inventorié pour afficher V1/V2 dans Firefox ;
   aucun moteur ni serveur de publication nouveau.
5. **Décision humaine** : `Retenir V2` ou `Écarter V2`,
   signalée localement par l'extension ; **pas encore une
   validation Git durable** ni un déploiement. Vérifier
   concrètement les boutons et l'absence de publication.
6. **Preuve verticale** : rapport du test réel Firefox
   (version, SHA, succès/échecs, permissions, captures expurgées,
   qualité pédagogique), à réaliser par l'enseignant.
   **NE PAS déclarer la livraison fonctionnelle sur CI seule.**

**Critère de sortie :** un enseignant accomplit le trajet
« sélectionner → dialoguer dans le panneau latéral → modification
Git explicite → visualiser deux rendus → choix humain » sur
une ressource fictive, sans manipulation complexe une fois la
configuration initiale faite. Si le connecteur latéral ne peut
pas écrire, le repli explicite est acceptable pour ce premier
parcours seulement ; mesurer la friction.

## Acquis à réutiliser, sans réécriture

- `extension/` v0.4 (sélection et historique Quarto) ;
- `quarto_branch_delta.py` (détection Git après fetch explicite) ;
- `quarto_historical_preview.py` (copies Git et Quarto réel) ;
- `quarto_observed_session.py`, `quarto_resource_entry.py`,
  `quarto_local_http.py` (comparaison et HTTP local vérifié) ;
- chaîne de tests Python/Node, workflow Quarto réel, gouvernance
  Draft→revue→fusion uniquement sur autorisation.

## Suspendus — pas supprimés

**P3.6A–F2/O1, PR #13 à #21 :** recherches sur isolation
du HTML professeur / confinement Firefox, avec preuves
unitaires, revues et contrats utiles conservés **en Draft**.
Elles ne sont **ni prérequis ni garanties de sécurité**
pour la démonstration exclusivement fictive. Ne pas
fusionner leur chaîne par simple urgence produit.
Réexaminer seulement quand un contenu professeur privé
doit effectivement être affiché en HTTP.

**Reportés :** profils Quarto professeur/élève réels,
ressources confidentielles, publication/deploiement élève,
historique durable des validations, multiapplication
(Grist, Moodle, Snap!, Collabora, WebeeBlocks), annotation,
captures, oral, agent IA, base de données, synchronisation
et infrastructure dédiée.

## Sécurité non négociable

Aucune donnée élève, correction privée, dépôt pédagogique
externe ni secret dans le dépôt public ou dans un prompt IA
sans consentement. Aucun HTML professeur réel sur le serveur
expérimental. Révisions Git = SHA exacts ; branche mutable ≠
preuve d'authenticité distante ; comparaison locale ≠
publication. Quarto peut exécuter des hooks même avec
`--no-execute` : rendu uniquement depuis projet de
confiance explicitement accepté. Les droits GitHub du
chatbot latéral doivent être **observés, pas supposés**.

**Pilotage :** une seule PR MVP active à la fois ;
corriger les défauts démontrés, éviter les audits spéculatifs,
conserver les SHA et preuves dans `IMPLEMENTATION_STATE.md`.
