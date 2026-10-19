# Alliage — décisions (19 octobre 2026)

## Adoptées

**A001 — Référentiel technique public unique.** `djibian/alliage`, séparé de tout dépôt pédagogique ou infrastructure privé. Sources éditables, tests et documentation versionnés ; pas de ZIP seul.

**A002 — Expérimenter avant de généraliser.** Le prototype réel Quarto v0.4 est repris sans réécriture : sélection HTML → ancre `.qmd` → variantes Quarto de test → comparaison → choix local. Les quatre critères sont richesse, fluidité, maîtrise et fidélité.

**A003 — Source canonique et gestes séparés.** Une ancre DOM n'est pas une cible source tant que le rapprochement Git n'est pas vérifié. Aperçu DOM ≠ expérimentation réelle ≠ version approuvée ≠ publication. Échec fermé en cas d'ambiguïté, source modifiée ou rendu incorrect.

**A004 — Sécurité et isolation.** Pas de données élèves, secrets, corrections réservées ou sources pédagogiques privées dans Alliage. Source pédagogique en clone autorisé externe, expérience hors Git, serveur uniquement en loopback, jeton éphémère, aucun déploiement automatique.

**A005 — Identité du produit Alliage.** L'ancien nom n'est plus utilisé dans l'interface visible. Pour préserver la compatibilité de v0.4, les anciens identifiants de protocole et variables techniques sont conservés provisoirement : migration ultérieure testée.

**A006 — GitHub traçable.** Branche/PR pour changement substantiel ; tests Python et examen de confidentialité avant publication ; documenter les réussites réelles sans extrapoler.

## Hypothèses à éprouver

**H001 — Extension de navigateur + adaptateurs légers + connecteurs.** Viser une expérience unifiée, mais adapter les mécanismes de modification réelle à Quarto/Grist/etc. Aucun framework multiapplication imposé.

**H002 — IA interchangeable.** Aucun moteur (OpenCode, OpenHands, autre) ni mode d'accès aux modèles choisi ; privilégier les connecteurs existants, tester avec cas concrets.

**H003 — Licence.** Le dépôt **préexistant** contient la GNU AGPL **v3** intégrale. `AGPL-3.0-only` et `AGPL-3.0-or-later` ne sont **pas interchangeables** : mention « ou toute version ultérieure » exige une intention explicite du titulaire des droits dans les notices de licence. Le propriétaire doit arrêter le choix et les notices avant annonce d'une licence définitive du projet. Fichier initial préservé.

## Abandonnés ou différés

- **Nom de travail PédagoLab** : remplacé par **Alliage** ; chaînes `pedagolab.*` encore présentes seulement comme compatibilité technique.
- **Copie volatile sous `/tmp`** : remplacée dans les consignes par un clone Git persistant sous `~/projets/pedagogie` ; possibilité de chemin explicite `--repo` conservée.
- **Rendus DOM comme preuves suffisantes** : exclus ; rendu réel Quarto requis.
- **Serveur IA générique / fork des applications / publication automatique** : différés faute de nécessité démontrée.
