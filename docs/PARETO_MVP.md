# Alliage — première démonstration pédagogique Pareto (Firefox + IA + Git + Quarto)

**Statut : `DEMO_REAL_FIREFOX_PASS` confirmé par l'enseignant le 5 novembre 2026 sur l'issue #23 ; PR #22 prête pour revue indépendante, non fusionnée.**
**Strictement ressources publiques/fictives** ; jamais de document professeur privé.
**Version de référence :** `main` `7231ac4fb54ec54aebd498e72d4bd588878e631e`.

> **FIXTURE DE DÉMONSTRATION ADOPTÉE (4 novembre 2026).** La
> [PR #24](https://github.com/djibian/alliage/pull/24) a été intégrée
> **uniquement** à `experiment/pareto-quarto-demo` après exception de
> maintenance autorisée et contre-expertise indépendante `APPROUVABLE`.
> Son HEAD réel est
> `affdb099bafd94099bf219c174e1ec6bbf82968f`.
> **Première paire à utiliser** : V1 =
> `5b477ca0436cff5a4e5a3ec9b3b0bfbb8a514347` (CSS bleu), V2 =
> `affdb099bafd94099bf219c174e1ec6bbf82968f` (CSS vert).
> L'arbre de V2 est exactement celui du commit V6
> `8e2f8b84515e9555c853c42f14cde0bca2c5de53`,
> préservé comme parent du merge ; les SHA anciens V1/V2 ne sont
> **pas** rendables sous Quarto 1.11.9. La [CI #41890947229](https://github.com/djibian/alliage/actions/runs/41890947229)
> **SUCCESS** qualifie les deux rendus Quarto et HTTP directement sur
> la **branche distante adoptée** ; elle ne prouve ni Firefox ni
> les capacités du chatbot. Aucune
> publication ni modification de `main`.

## Expérience visée

Dans Firefox Ubuntu, ouvrir une activité Quarto **réellement rendue**.
Sur la page, sélectionner une consigne ou choisir la ressource entière,
cliquer sur **« Préparer demande IA »**, confirmer que le contexte est
partageable, puis copier le texte préparé **dans le chatbot déjà ouvert
dans le panneau latéral natif**. Aucun chatbot n'est intégré à Alliage.
L'IA propose une modification Git explicitement autorisée (sinon un patch).
Après récupération volontaire du nouveau commit, une commande unique
relance les rendus Git/Quarto et sert les deux versions par HTTP loopback.
L'enseignant compare V1/V2 et clique **Retenir/Écarter V2 (local)**.
**Aucun bouton ne fusionne, ne publie ni ne modifie les sources.**

## Dépôts et refs — tous publics/fictifs

- **Code logiciel** : `djibian/alliage`, branche
  `feat/pareto-firefox-sidebar-context` (PR Draft). Conserver
  `AGENTS.md` et la gouvernance de `main`.
- **Projet de démonstration autonome dans le MÊME dépôt** :
  `djibian/alliage`, branche `experiment/pareto-quarto-demo`.
  Son arbre Git ne contient que `activite.qmd`, `styles.css`,
  `_quarto.yml`, un README, un AGENTS et un gitignore.
  **NE JAMAIS fusionner cette branche dans main** :
  elle ferait apparaître la suppression des sources du logiciel.
  Toute modification IA doit être exclusivement sur cette branche,
  après autorisation explicite.
- **V1 initiale, rendable avec Quarto 1.11.9** :
  `5b477ca0436cff5a4e5a3ec9b3b0bfbb8a514347` (bleu).
- **V2 initiale, HEAD distant adopté** :
  `affdb099bafd94099bf219c174e1ec6bbf82968f` (vert).
  Le merge conserve V6 `8e2f8b84515e9555c853c42f14cde0bca2c5de53`
  comme parent et a **le même arbre Git**. Ces commits sont des
  versions de test préexistantes, **pas une modification IA**.
- **Toute nouvelle modification IA** nécessite une autorisation
  explicite supplémentaire sur `activite.qmd` ou `styles.css`
  (ou `_quarto.yml`), et un nouveau SHA doit être constaté.

La branche de démonstration est un **pointeur Git mutable** : revalider
son SHA courant avant chaque nouvelle modification. Aucun SHA ne prouve
une publication ou une authentification de la page ouverte.

## Configuration initiale (à faire une seule fois, après revue de la PR)

Sur Ubuntu, disposer de Git, Python 3, Quarto réel et Firefox. Garder
des répertoires distincts pour le code Alliage et le projet Quarto :

```sh
git clone --branch feat/pareto-firefox-sidebar-context --single-branch \
  https://github.com/djibian/alliage.git "$HOME/projets/alliage-code"

git clone --branch experiment/pareto-quarto-demo --single-branch \
  https://github.com/djibian/alliage.git "$HOME/projets/alliage-demo"

git -C "$HOME/projets/alliage-demo" rev-parse HEAD
# Au 5 novembre après un premier commit IA : ecf35454aa3e0e93802041944a17241ef4866e09
# La branche est mutable : vérifier le HEAD réel, ne jamais exiger une valeur figée.
```

Charger temporairement **uniquement** `extension/manifest.json`
du clone de CODE dans `about:debugging` → « Ce Firefox » →
« Charger un module complémentaire temporaire ». Accorder la lecture
des fichiers locaux si Firefox la requiert. **Pas**
`experiments/p36f-extension/`, réservé au laboratoire P3.6.
La vraie compatibilité du rendu et de l'injection reste à observer.

## Premier aperçu V5 → branche adoptée pour préparer la demande IA

```sh
python3 "$HOME/projets/alliage-code/quarto_pareto_demo.py" \
  --repo "$HOME/projets/alliage-demo" \
  --demo \
  --baseline-sha 5b477ca0436cff5a4e5a3ec9b3b0bfbb8a514347 \
  --public-fictional-trusted
```

Le raccourci `--demo` sélectionne **uniquement** l'identité
`djibian/alliage` et la référence de la branche de démonstration ;
il n'autorise aucune écriture et n'enlève pas l'attestation
`--public-fictional-trusted`. La forme explicite
`--repository-id … --tracking-ref …` reste disponible.

Cette première commande **ne fait aucun fetch**. Elle compare
V1 = V5 (CSS bleu) au SHA de suivi **déjà présent dans le clone**
(initialement le merge approuvé, puis éventuellement un commit IA) ;
elle ne présente jamais une ancienne version de test comme une
révision produite par l'IA. Elle utilise les objets Git
déjà présents, confirme le FAST_FORWARD et rend avec **le véritable
Quarto** deux instantanés à SHA complets, sans checkout. Le mode
`--fetch-demo` ci-dessous permet ensuite une **récupération Git volontaire**
depuis la seule branche publique de la démonstration, sans toucher au checkout. Elle démarre
le serveur HTTP existant, lié uniquement à `127.0.0.1`, inventaire et
SHA-256 recontrôlés à chaque réponse. Elle imprime une **URL locale
contenant une capacité** ; la coller **uniquement dans Firefox local**,
ne jamais la transmettre au chatbot ni à GitHub. Arrêt : Ctrl+C.
Ce prévisualiseur **n'est pas une protection pour contenu confidentiel**.

Tester V2 → V1 → V2 et le CSS. Cocher
« Je confirme que ce contexte est public ou fictif… » puis utiliser
« Préparer demande IA ». Le texte est généré localement dans une
zone de texte en lecture seule, avec l'identité Git
**déclarée**, les SHA et la sélection de taille ≤ 2 400 caractères.
Pour **cette démonstration uniquement**, il propose aussi la branche
`experiment/pareto-quarto-demo` en la signalant comme non vérifiée :
l'IA doit confirmer cette branche et demander l'autorisation
avant toute écriture.
**Rien n'est transmis automatiquement**. Copier (Ctrl+C) et coller
(Ctrl+V) dans **ChatGPT déjà affiché dans le panneau latéral natif**,
puis dialoguer.

## Vérification obligatoire du chatbot dans CETTE surface

Demander d'abord **sans écrire** :

> « Peux-tu lire `AGENTS.md` et `styles.css` de la branche
> `experiment/pareto-quarto-demo` du dépôt `djibian/alliage` ?
> Indique le SHA de branche réellement consulté, et précise si
> tu disposes ici d'un outil d'écriture GitHub. N'écris rien. »

La simple présence d'un connecteur GitHub dans **une autre
conversation** n'atteste pas son accès dans le panneau natif.
Le connecteur GitHub standard documenté par OpenAI est notamment
orienté lecture ; certaines expériences d'agent/Codex peuvent
avoir d'autres outils. Ne jamais inventer une écriture réussie.

Après vérification et **autorisation explicite** pour cette
branche uniquement, demander une modification pédagogique
minimale, par exemple :

> « Sur `djibian/alliage`, branche
> `experiment/pareto-quarto-demo` seulement, propose de
> rendre la consigne 1 plus claire et commite la modification
> si et seulement si ton interface possède réellement l'outil
> de modification GitHub. Ne touche ni `main`, ni à un autre
> dépôt, ni aux autres fichiers. Rapporte le SHA exact. »

**Repli si écriture GitHub absente :** le chatbot fournit un
patch ou une proposition textuelle ; l'enseignant l'applique
explicitement par l'interface GitHub, Codex ou une conversation
outillée et autorisée. **Pas d'automatisation du panneau**.
Le chatbot reste l'interface du dialogue, la modification Git
est un acte contrôlé par ailleurs. Mesurer cette friction.

## Récupération, comparaison et décision (après commit IA vérifié)

Fermer le serveur (Ctrl+C), puis relancer avec l'option
**`--fetch-demo`** : elle constitue l'ordre **explicite de récupération**
depuis la seule branche publique fictive de `djibian/alliage`,
avec contrôle de l'origine Git. Le lanceur capture l'ancien SHA de suivi
**avant le fetch**, vérifie ensuite que la branche a avancé sans divergence,
et génère une nouvelle session Quarto réelle depuis les deux commits.
Il ne modifie pas le checkout et ne publie rien.

```sh
python3 "$HOME/projets/alliage-code/quarto_pareto_demo.py" \
  --repo "$HOME/projets/alliage-demo" \
  --demo --fetch-demo --public-fictional-trusted
```

Si GitHub n'a pas encore de nouveau commit ou si la branche est réécrite,
la comparaison est **refusée**, jamais simulée. Il reste une intervention
dans le terminal après l'essai IA, mais **plus besoin de saisir soi-même
un refspec Git ou un nouveau SHA**. La chaîne a été qualifiée en vrai Firefox le 5 novembre 2026 ;
une éventuelle actualisation en un clic depuis la page nécessitera
une évolution **distincte, explicite et testée** du pont local,
sans mise à jour ni publication automatique.

Dans Firefox, comparer V1 (départ avant IA) et V2
(proposition IA), utiliser « Retenir V2 (local) »
ou « Écarter V2 (local) ». Ces boutons
conservent **au plus un état navigateur de session** :
ce n'est **pas** une validation durable dans Git.
**Aucune fusion ni publication élèves** n'est autorisée.

## Première qualification réelle Firefox — 5 novembre 2026

**Preuves humaines transmises pour l'issue #23 :** Quarto a rendu
deux instantanés avec les SHA
`affdb099bafd94099bf219c174e1ec6bbf82968f` (avant modification)
et `ecf35454aa3e0e93802041944a17241ef4866e09` (après
modification), grâce à `--fetch-demo --public-fictional-trusted`.
La capture réelle Firefox montre la nouvelle consigne, l'extension
Alliage et le chatbot natif dans la même fenêtre. La conversation
du panneau a vérifié le SHA de branche, lu `AGENTS.md` et
`styles.css` puis créé le commit directement grâce à ses
outils GitHub, sur demande explicite de l'enseignant. Le diff GitHub
confirme **un seul fichier modifié, `activite.qmd`**, et `main`
inchangé. Le bouton « Préparer demande IA » a également été
essayé et fonctionne selon l'enseignant.

**Réussite finale confirmée par l'enseignant le 5 novembre 2026 :**
la navigation V1 ↔ V2 **fonctionne** et le clic sur
« Retenir V2 (local) » affiche exactement :
« V2 retenue dans ce navigateur, sans écriture Git ni publication. »
Cette confirmation humaine clôt les deux observations qui manquaient
à la première capture. **`DEMO_REAL_FIREFOX_PASS`** est enregistré
sur [l'issue #23](https://github.com/djibian/alliage/issues/23).
La validation Git durable et la publication élèves restent hors du MVP.

**Après un clonage effectué après le commit IA :** la branche
locale de suivi pointe déjà sur `ecf35454...` ; **ne pas**
lancer `--fetch-demo` sans nouveau commit : ce mode refuse
correctement l'absence de nouvelle révision. Pour revoir la
comparaison correspondant à l'intervention IA, employer
`--baseline-sha affdb099bafd94099bf219c174e1ec6bbf82968f`
dans la première commande **sans fetch**. Après un prochain
commit explicitement autorisé, `--fetch-demo` redevient
pertinent.

**Raccourci natif Firefox après sélection :** l'icône
étincelante fournit déjà des actions de texte vers le
chatbot du panneau latéral. Mozilla précise que le
raccourci transmet le passage sélectionné et le titre
de page ; il **ne remplace pas** le contexte Git vérifié
(SHA, dépôt, branche, règles `AGENTS.md`) ni un
consentement à l'écriture. Tester l'intérêt UX sur
**la seule fixture publique/fictive**, sans automatiser
ou extraire la conversation, et comparer la friction
avec « Préparer demande IA ».


## Protocole d'acceptation à renseigner

| Critère | Preuve requise | État actuel |
| --- | --- | --- |
| Page initiale Quarto affichée dans Firefox | Capture fictive (version Firefox exacte non consignée) | PASS réel |
| Texte transféré au panneau IA | Dialogues natifs + préparation testée par l'enseignant | PASS rapporté (geste précis non instrumenté) |
| Lecture GitHub dans le panneau exact | SHA, fichiers et blobs vérifiés sur GitHub | PASS réel |
| Écriture GitHub dans le panneau exact | Commit ecf35454… sur seule fixture | PASS réel |
| Repli en patch si besoin | Patch appliqué avec autorisation | NON TESTÉ |
| Rendu initial Quarto V5 → HEAD adopté | Deux SHA, actifs, HTTP, intégrité des fichiers suivis | CI réelle sur branche adoptée : PASS (run 41890947229) |
| Navigation V1/V2 dans Firefox | Aller-retour confirmé explicitement par l'enseignant (05/11/2026) | PASS réel |
| Décision humaine locale | Clic « Retenir V2 » et message local exact rapporté (05/11/2026) | PASS réel, non durable |
| Absence de modification du site élèves | Diff limité à la fixture, aucune publication initiée par Alliage | PASS dans le périmètre MVP |

**Conclusion : `DEMO_REAL_FIREFOX_PASS`** dans le périmètre
public/fictif : contexte et dialogue dans la sidebar native,
écriture Git autorisée, fetch volontaire, vrais rendus Quarto,
navigation V1/V2 et décision locale, sans publication.
Le geste exact de copie du texte préparé par Alliage n'est
pas instrumenté séparément ; la préparation est rapportée
comme fonctionnelle, et le dialogue réellement contextualisé.
La décision locale ne vaut toujours ni approbation Git
durable ni publication. La PR #22 reste à relire indépendamment
avant intégration éventuelle dans `main`.

### Documentation externe
- Firefox, chatbot natif et sélection :
  https://support.mozilla.org/en-US/kb/ai-chatbot
- OpenAI, limites de l'application GitHub :
  https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt
