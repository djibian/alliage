# Alliage — roadmap opérationnelle Pareto (4 novembre 2026)

**But produit :** dans Firefox, l'enseignant visualise une activité Quarto
publique/fictive, dialogue avec le **chatbot natif du panneau latéral**,
autorise une modification Git dans une branche isolée, compare deux
rendus **Quarto réels**, puis retient ou écarte la proposition,
sans publication automatique.

L'ancienne roadmap, ses expérimentations et décisions restent conservées
dans [ROADMAP_ARCHIVE_202610.md](ROADMAP_ARCHIVE_202610.md).
Contrats inchangés : `AGENTS.md`, `PRODUCT_VISION.md`, `DECISIONS.md`.

## V0 pédagogique — chemin critique à terminer AVANT toute autre phase

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
