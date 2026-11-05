# Alliage — reprise opérationnelle Pareto (5 novembre 2026)

**Source de vérité : GitHub, pas cette fiche.** Relire les SHA
actuels de `main`, de #22 et de la branche fictive, les avis,
`AGENTS.md` et les CI avant tout changement. Garder les preuves
détaillées dans `IMPLEMENTATION_STATE.md` et `PARETO_MVP.md`.

## Objectif de sortie — issue #23

Dans le vrai Firefox Ubuntu : passage d'une activité Quarto
**publique/fictive** au chatbot **déjà présent** dans la sidebar
native, modification GitHub explicitement autorisée, récupération
Git volontaire, deux rendus Quarto réels, aller-retour V1/V2,
décision locale et **zéro publication automatique**.
Ne jamais développer de nouveau chatbot, pont de scraping,
orchestrateur générique ou infrastructure de publication.
Reporter données professeur privées, multiapplication et P3.6 (#13–#21).

## Acquis Git et Quarto

- `main` vérifié à
  `7231ac4fb54ec54aebd498e72d4bd588878e631e` ;
  **inchangé** lors des opérations ci-dessous.
- [PR #24](https://github.com/djibian/alliage/pull/24)
  intégrée **uniquement** à `experiment/pareto-quarto-demo`
  avec accord exceptionnel du propriétaire et contre-revue
  indépendante `APPROUVABLE` au SHA
  `8e2f8b84515e9555c853c42f14cde0bca2c5de53`.
  Merge `affdb099bafd94099bf219c174e1ec6bbf82968f`
  (même arbre que V6), V5
  `5b477ca0436cff5a4e5a3ec9b3b0bfbb8a514347`
  reste ancêtre. **Jamais de fusion de la branche fictive
  dans `main`.**
- **Premier commit effectué depuis ChatGPT en sidebar Firefox**
  le 5 novembre 2026 :
  `ecf35454aa3e0e93802041944a17241ef4866e09`,
  enfant direct du merge `affdb099...`. GitHub vérifie
  une seule consigne modifiée dans `activite.qmd`,
  `AGENTS.md` et CSS inchangés ; branche distante
  actuellement au nouveau SHA selon le contrôle.
- L'enseignant a déclenché localement
  `quarto_pareto_demo.py --fetch-demo --public-fictional-trusted` ;
  Quarto réel a rendu `affdb099...` puis `ecf35454...`.
  La capture de Firefox montre **V2 réellement servie**
  avec la nouvelle consigne, l'overlay Alliage, une sélection
  et **ChatGPT dans le panneau natif** ; la préparation IA
  fonctionne selon l'enseignant.
- La lecture GitHub et les outils d'écriture
  **dans cette surface exacte** ont effectivement fonctionné.
  `GITHUB_READ=PASS`, `GITHUB_WRITE=AVAILABLE_AND_USED`.
  La disponibilité n'est pas généralisable à toutes les
  configurations Firefox ou ChatGPT.
- [PR #22](https://github.com/djibian/alliage/pull/22) :
  MVP logiciel **Ready for review**, non fusionné dans `main`.
  La CI de la fixture a été corrigée pour accepter les
  nouveaux commits de démonstration tout en exigeant
  l'ascendance du merge de maintenance, sans ref fictive
  ni perte des contrôles Git/Quarto. Preuve du workflow
  corrigé : [CI #42060660921](https://github.com/djibian/alliage/actions/runs/42060660921)
  `SUCCESS` sur le commit technique `3ec749794f1eb22a1c7551f767e9bb47ab4673cd`.
  Vérifier les CI du **HEAD mutable** courant de #22.

## Verdict humain et dernière action

**`DEMO_PARTIAL` : la véritable sidebar Firefox n'est plus
`UNPROVEN`.** Il reste exactement deux preuves humaines :
1. Cliquer `← V1`, constater l'ancienne consigne, puis
   `V2 →` et constater la nouvelle.
2. Cliquer `Retenir V2 (local)` ou `Écarter V2 (local)`
   et constater le statut local (la capture initiale affichait
   **« Décision non prise »**).

Confirmer ces deux gestes dans
[l'issue #23](https://github.com/djibian/alliage/issues/23)
pour déclarer `DEMO_REAL_FIREFOX_PASS`, sans inventer
une validation Git durable ou une publication élèves.
Ne pas réclamer un nouveau commit : la modification GitHub
et les rendus sont déjà réussis.

## Simplification UX à éprouver ensuite

Le raccourci natif à icône étincelante après sélection peut
adresser le texte sélectionné et le titre de page au chatbot
Firefox, d'après Mozilla. Tester d'abord sur la fixture
publique, comparer la friction avec le bouton
« Préparer demande IA » ; le raccourci ne contient pas
automatiquement le dépôt, le SHA, la branche ni les règles
`AGENTS.md`. Il ne justifie ni API IA supplémentaire,
ni extension accédant au DOM du chatbot.

## Gardes

Aucune ressource privée, secret ou URL locale contenant
une capacité dans le dépôt ou le prompt IA ; aucune
publication, merge automatique, force-push ou adaptation
P3.6. Le droit d'écrire sur la branche fictive est
strictement explicite et distinct de l'accord de
maintenance `.gitignore`. La décision Retenir/Écarter
n'est qu'une préférence locale, **pas une validation
Git ni un déploiement**.
