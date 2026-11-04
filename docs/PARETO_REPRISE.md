# Alliage — reprise opérationnelle Pareto (4 novembre 2026)

**Source de vérité : GitHub, pas cette fiche.** À chaque reprise résoudre
le SHA de `main`, vérifier les PR/CI/commits/avis puis lire
`AGENTS.md`, `docs/PRODUCT_VISION.md`, `docs/ROADMAP.md`,
`docs/DECISIONS.md`, `docs/IMPLEMENTATION_STATE.md`.
Ne jamais supposer que les valeurs ci-dessous n'ont pas changé.

## But du MVP et critère de sortie

Sur une ressource Quarto **entièrement fictive/publique** dans le vrai
Firefox Ubuntu : ouvrir une page réellement rendue, sélectionner un
passage, préparer/copier **volontairement** le contexte dans le chatbot
déjà présent dans le panneau latéral natif ; vérifier les capacités
GitHub READ/WRITE dans **cette interface précise** ; obtenir après
autorisation un commit de la seule branche de test (ou un patch
appliqué explicitement via GitHub/Codex) ; déclencher `--fetch-demo` ;
comparer deux vrais rendus et choisir V2 ou l'écarter **localement**,
sans publication. `DEMO_REAL_FIREFOX_PASS` exige ces observations
réelles ; sinon consigner `DEMO_PARTIAL` sans extrapoler la CI.

## Faits revérifiés après PR #24

- `main` = `7231ac4fb54ec54aebd498e72d4bd588878e631e`
  lors de cette reprise, **intact**.
- [PR #24](https://github.com/djibian/alliage/pull/24)
  **fusionnée par merge normal** après autorisation exceptionnelle
  du propriétaire et contre-expertise indépendante `APPROUVABLE`
  sur HEAD exact `8e2f8b84515e9555c853c42f14cde0bca2c5de53`.
  Base **exclusivement**
  `experiment/pareto-quarto-demo`, JAMAIS `main`.
- Branche fictive réellement adoptée :
  `affdb099bafd94099bf219c174e1ec6bbf82968f`.
  Merge parents =
  `4a3028334a63fdd722ffd4d3da7886558127d033` (ancienne cible)
  et `8e2f8b84515e9555c853c42f14cde0bca2c5de53` (V6).
  **L'arbre du merge est identique à V6**.
- Premier aperçu reproductible : V1 =
  `5b477ca0436cff5a4e5a3ec9b3b0bfbb8a514347` (V5, CSS bleu) ;
  V2 = `affdb099bafd94099bf219c174e1ec6bbf82968f`
  (branche adoptée, CSS vert). L'ancien couple V1/V2,
  et les essais intermédiaires V3/V4 **ne sont pas rendables**
  sous Quarto 1.11.9 (mutation de `.gitignore`).
- Le nouveau workflow dans la [PR #22](https://github.com/djibian/alliage/pull/22)
  clone la **vraie branche distante adoptée**, exige son SHA,
  et rend V5 → HEAD avec vrais Git/Quarto et HTTP.
  [CI #41890947229](https://github.com/djibian/alliage/actions/runs/41890947229)
  **SUCCESS** sur `15df12fd59f1d832aa424d40f9879ad8a64e2c8f` :
  deux rendus réels Quarto V5 → HEAD adopté, HTTP et CSS vérifiés.
  **`ADOPTED_FIXTURE_QUARTO_CI_PASS`** sur ce HEAD.
  Le verdict Firefox reste `UNPROVEN`.
- #22 reste une PR du **logiciel** vers `main`, désormais
  **Ready for review**, en attente de revue indépendante ciblée.
  Pas de fusion automatique.
  Elle conserve l'extension v0.4 et ses composants historiques.
- [Issue #23](https://github.com/djibian/alliage/issues/23)
  = porte principale de démonstration réelle. Les essais CI/DOM
  n'attestent ni le panneau latéral natif ni ses droits GitHub.
- P3.6 (#13–#21) est suspendu sans suppression.

## Actions opérationnelles (Pareto)

1. **Revalider la CI sur tout nouveau HEAD #22**. Sur
   `15df12fd...`, Quarto réel / HTTP / navigation / Python étaient
   PASS. Corriger seulement une régression prouvée. Ne pas refaire
   l'étude de la fixture ; revérifier les SHA mutables.
2. Faire relire #22 **indépendamment** : consentement et contexte
   limité, absence d'envoi IA automatique, identité Git déclarée,
   fetch borné et volontaire, décision locale non publiée.
3. Pour [#23](https://github.com/djibian/alliage/issues/23),
   utiliser [le guide exact](PARETO_MVP.md) : clone du code #22
   et clone de la fixture **séparés**, extension temporaire
   `extension/manifest.json`, lancement de
   `quarto_pareto_demo.py` sur V5 → merge, URL locale seulement
   dans Firefox, sélection/consentement/copier/coller latéral.
4. Tester READ et capacité WRITE du **véritable chatbot latéral**.
   Si WRITE absent : patch demandé à l'IA puis appliqué explicitement
   via GitHub/Codex avec autorisation du professeur pour la seule
   branche fictive (nouvelle autorisation d'écriture, indépendante
   de la maintenance de #24).
5. Après commit **réel** sur la branche fictive, arrêt du serveur
   précédent, `--fetch-demo --public-fictional-trusted`, relecture
   des deux SHA, vrai rendu, comparaison V1/V2, décision locale ;
   noter Firefox/version, SHA, capacités et friction.
6. Déposer sur #23 `DEMO_REAL_FIREFOX_PASS` uniquement si
   observé dans le Firefox réel ; sinon `DEMO_PARTIAL` avec
   le blocage déterminant et le plus petit correctif.

## Limites strictes

Aucune modification des ressources élèves, dépôt externe privé,
publication, API IA ou scraping du chatbot. Les objets Git et la page
ouverte ont des garanties différentes ; les paramètres de l'URL
n'authentifient pas la publication. Même `--no-execute` dans Quarto
n'en fait pas une sandbox : ne rendre que ce projet fictif de confiance.
L'enseignant conserve la maîtrise de toute écriture et publication.
