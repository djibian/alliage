# Alliage — reprise opérationnelle Pareto (4 novembre 2026)

**Source de vérité : GitHub, pas cette fiche figée.** À chaque reprise,
résoudre le HEAD exact de `main`, puis relire `AGENTS.md`,
`docs/PRODUCT_VISION.md`, `docs/ROADMAP.md`,
`docs/DECISIONS.md` et `docs/IMPLEMENTATION_STATE.md`.
Vérifier PR/CI/issue et les SHA avant toute écriture.

## Cible de livraison

**Première démonstration complète uniquement sur Quarto fictif public** :
Firefox affiche la vraie page ; l'enseignant sélectionne un passage,
prépare/colle explicitement une demande dans **le chatbot déjà présent
dans le panneau latéral Firefox**, l'IA consulte ou reçoit le contexte,
une modification Git sur une branche autorisée est effectuée par la
capacité réellement disponible (repli manuel/patch explicite sinon),
Alliage récupère un SHA nouveau, rend deux vrais instantanés Quarto,
l'enseignant navigue V1/V2 et décide, **sans publication**.

Conserver ChatGPT/Firefox/GitHub/Quarto/Git existants.
**Ne jamais** construire un autre chatbot, une API IA, un framework
multiapplication, un système générique de publication ou prolonger
P3.6 pour ce premier résultat fictif.

## État GitHub à revérifier

- `main` examiné initialement :
  `7231ac4fb54ec54aebd498e72d4bd588878e631e`.
- [PR #22](https://github.com/djibian/alliage/pull/22) Draft sur
  `main` : bouton « Préparer demande IA » avec consentement et copie
  manuelle, décisions locales, commande Git/Quarto/HTTP
  `quarto_pareto_demo.py`, tests et roadmap Pareto.
  **Ne pas fusionner sans revue**.
- [Issue #23](https://github.com/djibian/alliage/issues/23) :
  protocole d'essai sur le **chatbot natif réellement utilisé** dans
  Firefox Ubuntu ; écrire explicitement READ/WRITE/UNPROVEN.
- Projet public fictif dans **le même dépôt**, branche
  `experiment/pareto-quarto-demo`, ne jamais fusionner vers main.
  V1 ancienne `1b1c0f22e4f210bb24396274f56401ade0723353`,
  V2 ancienne `4a3028334a63fdd722ffd4d3da7886558127d033`.
- **Blocage trouvé sur les vrais fichiers :** Quarto modifie le
  `.gitignore` suivi de cette branche (`.quarto/` au lieu du motif
  `/.quarto/`) ; le moteur P3.1 refuse correctement le rendu.
  Ce constat est issu de CI véritable Quarto, **pas de Firefox**.
  Ne jamais affaiblir l'invariant des fichiers Git suivis inchangés.
- [PR #24](https://github.com/djibian/alliage/pull/24)
  **Draft ciblant exclusivement cette branche fictive** :
  une correction technique de `.gitignore` (exception de maintenance
  soumise à autorisation, non mutation IA) et une variation CSS.
  Paire candidate : V5
  `5b477ca0436cff5a4e5a3ec9b3b0bfbb8a514347`,
  V4 `8e2f8b84515e9555c853c42f14cde0bca2c5de53`.
  **La tête réelle de la branche de démonstration n'a pas été changée.**
- PR expérimentales P3.6 #13–#21 : **suspendre sans détruire** ;
  pas de vraie donnée professeur/élève dans les aperçus HTTP.

## Chemin critique — ne faire que cela

1. Vérifier la **CI exacte** de #22 : Python et tests DOM,
   **Quarto réel sur paire candidate V3/V4**. Si rouge, corriger
   seulement la cause démontrée ; ne pas contourner P3.1.
2. Faire auditer #24 ; **ne pas la fusionner sans autorisation**
   en tenant compte du `AGENTS.md` spécifique à la fixture.
   Après approbation, actualiser `docs/PARETO_MVP.md`,
   les SHA de référence et tester la **branche finale**, pas
   seulement la proposition. Ne pas mélanger des SHAs de versions
   rendables et non rendables.
3. Faire relire rapidement #22 sur consentement/contextualisation,
   portée exacte du clone et interdiction d'écriture implicite ;
   ne pas déclencher une revue de sécurité P3.6 complète pour
   des contenus exclusivement fictifs.
4. **Exécuter l'issue #23 dans le vrai Firefox** avec l'utilisateur.
   Ses observations réelles sont nécessaires :
   affichage de la page/overlay, transfert du contexte dans
   l'interface latérale, accès GitHub en **lecture**, possibilité
   réelle d'écriture dans CETTE surface, et friction des manipulations.
   La présence d'outils GitHub dans un autre chat NE PROUVE RIEN.
5. Avec consentement explicite pour **la seule branche fictive** :
   modification IA via capacité réellement disponible ou patch appliqué
   manuellement par GitHub/Codex ; noter le nouveau SHA, relancer
   `--fetch-demo`, inspecter Quarto réel et décider localement.
   Aucune PR ou commit de déploiement/merge n'est automatique.
6. Publier un verdict `DEMO_REAL_FIREFOX_PASS` ou `DEMO_PARTIAL`
   sur l'issue #23, avec les étapes factuellement observées,
   captures uniquement fictives et SHA publics. Ne pas assimiler
   un DOM simulé ou une CI GitHub à cette preuve humaine.

## Limites assumées

- Firefox ne fournit pas de pont garanti de l'extension Alliage
  vers la conversation du panneau latéral : **copie/collage volontaire**.
- Le connecteur GitHub standard OpenAI est documenté **lecture seule**
  ; les capacités d'autres modes/outils (Codex, etc.) diffèrent.
  Les capacités du **véritable chatbot latéral** restent `UNPROVEN`
  tant qu'elles n'ont pas été testées dans cette surface.
- `Retenir/Écarter V2 (local)` est seulement une préférence de
  session navigateur ; ce n'est pas une validation durable Git.
  Concevoir un mécanisme durable **après** le test métier seulement.
- Les vrais projets professeur multipages/profilés et le
  confinement avancé ne sont **pas** qualifiés par ce MVP.
