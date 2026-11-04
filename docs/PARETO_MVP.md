# Alliage — première démonstration pédagogique Pareto (Firefox + IA + Git + Quarto)

**Statut : candidat en PR Draft, NON QUALIFIÉ dans le Firefox réel.**
**Strictement ressources publiques/fictives** ; jamais de document professeur privé.
**Version de référence :** `main` `7231ac4fb54ec54aebd498e72d4bd588878e631e`.

> **BLOCAGE EXPÉRIMENTAL IDENTIFIÉ (4 novembre 2026).** Le test du
> **véritable** couple de commits initial V1=`1b1c0f22…`,
> V2=`4a302833…` a montré que Quarto réécrit leur `.gitignore`
> suivi, ce que le moteur P3.1 refuse correctement. **Ne pas lancer la
> première démonstration décrite plus bas tant que ce blocage n'est pas
> levé.** Une correction révisable et non fusionnée existe en
> [PR #24](https://github.com/djibian/alliage/pull/24) : V5
> `5b477ca0436cff5a4e5a3ec9b3b0bfbb8a514347` (motifs Quarto
> canoniques) et V6 `8e2f8b84515e9555c853c42f14cde0bca2c5de53`
> (CSS fictif). La validation CI de cette nouvelle paire, puis son
> approbation avant mise à jour du protocole de démarrage, sont
> obligatoires. **Aucune modification du moteur Git/Quarto pour tolérer
> les fichiers suivis modifiés.**


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
- **Premier SHA fictif V1** :
  `1b1c0f22e4f210bb24396274f56401ade0723353`.
- **Deuxième SHA initial V2, avant intervention IA** :
  `4a3028334a63fdd722ffd4d3da7886558127d033`.
  Ce deuxième commit ne représente **pas** une révision IA.

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
# Doit donner au départ : 4a3028334a63fdd722ffd4d3da7886558127d033
```

Charger temporairement **uniquement** `extension/manifest.json`
du clone de CODE dans `about:debugging` → « Ce Firefox » →
« Charger un module complémentaire temporaire ». Accorder la lecture
des fichiers locaux si Firefox la requiert. **Pas**
`experiments/p36f-extension/`, réservé au laboratoire P3.6.
La vraie compatibilité du rendu et de l'injection reste à observer.

## Premier aperçu V1/V2 pour préparer la demande IA

```sh
python3 "$HOME/projets/alliage-code/quarto_pareto_demo.py" \
  --repo "$HOME/projets/alliage-demo" \
  --repository-id djibian/alliage \
  --tracking-ref refs/remotes/origin/experiment/pareto-quarto-demo \
  --baseline-sha 1b1c0f22e4f210bb24396274f56401ade0723353 \
  --public-fictional-trusted
```

Cette première commande **ne fait aucun fetch**. Elle utilise les objets Git
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
  --repository-id djibian/alliage \
  --tracking-ref refs/remotes/origin/experiment/pareto-quarto-demo \
  --fetch-demo --public-fictional-trusted
```

Si GitHub n'a pas encore de nouveau commit ou si la branche est réécrite,
la comparaison est **refusée**, jamais simulée. Il reste une intervention
dans le terminal après l'essai IA, mais **plus besoin de saisir soi-même
un refspec Git ou un nouveau SHA**. La commande de lancement et la
reprise pourront devenir un bouton local seulement après qualification
du parcours réel dans Firefox.

Dans Firefox, comparer V1 (départ avant IA) et V2
(proposition IA), utiliser « Retenir V2 (local) »
ou « Écarter V2 (local) ». Ces boutons
conservent **au plus un état navigateur de session** :
ce n'est **pas** une validation durable dans Git.
**Aucune fusion ni publication élèves** n'est autorisée.

## Protocole d'acceptation à renseigner

| Critère | Preuve requise | État actuel |
| --- | --- | --- |
| Page initiale Quarto affichée dans Firefox | Capture fictive / version Firefox | NON OBSERVÉ |
| Texte transféré au panneau IA | Copie manuelle explicitement consentie | NON OBSERVÉ |
| Lecture GitHub dans le panneau exact | Réponse avec branche et SHA vérifiables | UNPROVEN |
| Écriture GitHub dans le panneau exact | Commit SHA réellement créé | UNPROVEN |
| Repli en patch si besoin | Patch appliqué avec autorisation | NON TESTÉ |
| Rendu nouveau commit par vrai Quarto | Deux SHA et assets vérifiés | CI À QUALIFIER |
| Navigation V1/V2 dans Firefox | Différence visible, aucune erreur CORS | NON OBSERVÉ |
| Décision humaine locale | Choix puis état affiché, aucune publication | DOM SIMULÉ |
| Absence de modification du site élèves | Git/HTTP et revue du diff | À CONTRÔLER |

**Conclusion autorisée au stade de cette PR :** expérimentation
préparée ; ni le panneau IA réel ni son éventuelle écriture GitHub
n'ont été observés. La décision locale n'est pas une
approbation Git ; un mécanisme durable devra être conçu
**après la première démonstration**, si utile.

### Documentation externe
- Firefox, chatbot natif et sélection :
  https://support.mozilla.org/en-US/kb/ai-chatbot
- OpenAI, limites de l'application GitHub :
  https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt
