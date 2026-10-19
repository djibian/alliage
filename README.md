# Alliage

**Alliage** est un atelier libre d'ingénierie pédagogique augmentée par l'IA : l'enseignant montre un élément dans une application web, dialogue, compare, expérimente et valide des modifications **réelles** sans les publier automatiquement.

> **État : prototype Quarto v0.4, expérimental, parcours Firefox validé sur la Mission 02 le 19 octobre 2026.** La sélection, le rendu local de deux variantes, la comparaison et le choix expérimental ont fonctionné avec Firefox, Quarto 1.10.19 et le pont local. Les 18 tests automatisés ont aussi réussi en CI. **Aucune IA n'est intégrée, aucune source pédagogique n'est modifiée et aucune publication n'est effectuée.** Ne pas utiliser avec des données sensibles.

La vision, les contraintes et les priorités figurent dans [PRODUCT_VISION](docs/PRODUCT_VISION.md), [ROADMAP](docs/ROADMAP.md), [IMPLEMENTATION_STATE](docs/IMPLEMENTATION_STATE.md) et [DECISIONS](docs/DECISIONS.md). **Agents : lire [AGENTS.md](AGENTS.md) avant toute intervention.**

## Organisation

- `extension/` : extension WebExtension expérimentale **sans étape de compilation** (`manifest.json`, `atelier.js`, `background.js`).
- `serveur.py` : passerelle HTTP locale sur `127.0.0.1:8765`, avec jeton temporaire.
- `resolve_source.py` : ancrage du texte sélectionné dans un `.qmd` Git.
- `experiment.py` : copies source isolées, rendu Quarto, comparaison et vérification.
- `tests/`, `exemples/` : tests unitaires et ancrages **fictifs**, libres de contenu pédagogique privé.
- `docs/ORIGIN_HASHES.json` : empreintes de l'archive v0.4 effectivement reprise, pour la traçabilité.

## Prérequis et tests sans accès privé

Ubuntu/Linux, Python **3.12**, Git ; **aucun package Python externe** pour les tests. Quarto n'est nécessaire que pour le rendu réel.

```bash
git clone git@github.com:djibian/alliage.git
cd alliage
python3 -m unittest discover -s tests -v
python3 -m py_compile serveur.py experiment.py resolve_source.py
```

Le résultat local lors de la capitalisation : **18 tests OK**, tests simulant Quarto et serveurs HTTP de test. Le workflow GitHub `Tests du prototype Alliage` exécute la même suite. Le test de navigateur et le rendu réel restent distincts.

## Démonstration Quarto actuelle (requiert un accès autorisé au dépôt pédagogique séparé)

Les tests automatisés sont indépendants de `djibian/pedagogie`. En revanche, **la v0.4 interactive est encore liée à une seule page pilote publiée** : ne pas prétendre qu'elle fonctionne déjà sur toute page HTML. Le dépôt public **ne contient pas la ressource source privée**. Pour la tester, disposer légitimement d'une copie locale du dépôt pédagogique dans un chemin persistant, **extérieur à Alliage** :

```bash
mkdir -p "$HOME/projets"
git clone git@github.com:djibian/pedagogie.git "$HOME/projets/pedagogie-alliage-test"
git -C "$HOME/projets/pedagogie-alliage-test" switch --detach 4530afacc4b45d5707f4f3c5029386bb5e141ec4
git -C "$HOME/projets/pedagogie-alliage-test" status --porcelain
export PATH="$HOME/.local/bin:$PATH"
quarto --version
python3 serveur.py --repo "$HOME/projets/pedagogie-alliage-test"
```

Cette procédure reproduit le **commit source exact** du pilote qualifié (`4530afacc4b45d5707f4f3c5029386bb5e141ec4`) sans modifier la branche principale. Si tu disposes déjà d’une copie locale, ne la réinitialise pas : choisis un autre chemin pour cette copie de test. La version HTML actuellement publiée **n’est pas** cryptographiquement reliée à ce commit : le résultat reste expérimental. Le programme refuse une source locale modifiée.

Dans Firefox : ouvrir `about:debugging#/runtime/this-firefox`, choisir « Charger un module complémentaire temporaire », sélectionner `extension/manifest.json`, puis ouvrir la [page pilote Quarto](https://djibian.github.io/pedagogie/enseignements/tim/4e-3e/activites/3e/02-nommer-classer/activite.html). Sélectionner une occurrence de texte, coller dans le panneau le **jeton temporaire** affiché par le serveur, saisir A/B, lancer la vérification, comparer, puis choisir ou rejeter. **Ce parcours a été validé manuellement sur cette page pilote le 19/10/2026**, et reste à généraliser. Arrêt du serveur : `Ctrl+C`.

Le serveur écrit uniquement dans `~/alliage-experiences/interactif/`, jamais dans la copie Git. Pour vérifier :

```bash
git -C "$HOME/projets/pedagogie-alliage-test" status --porcelain
ls -la "$HOME/alliage-experiences/interactif/"
```

**Option témoins supplémentaires :** les vrais fichiers `selection-1.json` et `selection-2.json`, si l'enseignant souhaite les garder, peuvent être placés dans `local-anchors/` (ignoré par Git). Sans eux, le contrôle global du texte rendu fonctionne, mais `guard_count` peut être `0`. Les exemples publics dans `exemples/` sont **fictifs** et ne servent pas de gardes de la page réelle.

## Qualification Firefox réelle le 19 octobre 2026

L'enseignant a testé avec succès le serveur local et son endpoint `/api/health` (`READY_LOCAL`, commit source `4530afacc4b45d5707f4f3c5029386bb5e141ec4`), puis la sélection, les variantes A/B, la comparaison Firefox et le choix « Garder A ». Les deux fichiers `rapport.json` et `decision.json` sont présents dans son espace expérimental local ; `git status --porcelain` du clone pédagogique est vide. **Ces résultats sont rapportés par le testeur ; les contenus des deux fichiers de preuve privés n'ont pas été copiés ni audités dans le dépôt public.** Le HTML public n'est toujours pas lié cryptographiquement au commit source.

## Problème constaté le 19 octobre 2026

La commande `python3 serveur.py --repo /tmp/pedagolab-pedagogie` a échoué avec `FileNotFoundError` : `/tmp` a été vidé et la source privée locale avait disparu. Solution : utiliser une copie Git persistante dans `~/projets/pedagogie-alliage-test`. Le CLI explicite maintenant la cause lorsque le chemin fourni n'existe pas. **Ne pas recopier le dépôt privé dans Alliage.**

## Sécurité, confidentialité et licence

Ne jamais committer : sources pédagogiques privées, captures réelles non autorisées, jetons, clés, `.env`, données d'élèves ou résultats d'expérience. Toute version approuvée reste *expérimentale* tant qu'une publication séparée n'est pas autorisée. Le service reste local, sans exposition réseau.

**Licence confirmée le 19 octobre 2026 : GNU Affero General Public License v3 ou toute version ultérieure, `AGPL-3.0-or-later`.** Voir [LICENSE](LICENSE) pour le texte intégral de l'AGPL v3 et [LICENSE-NOTICE.md](LICENSE-NOTICE.md) pour la déclaration « or later » applicable au code original d'Alliage. Les sources privées externes ne font pas partie de cette licence ni de ce dépôt.
