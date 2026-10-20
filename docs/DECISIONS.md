# Alliage — décisions (19 octobre 2026)

## Adoptées

**A001 — Référentiel technique public unique.** `djibian/alliage`, séparé de tout dépôt pédagogique ou infrastructure privé. Sources éditables, tests et documentation versionnés ; pas de ZIP seul.

**A002 — Expérimenter avant de généraliser.** Le prototype réel Quarto v0.4 est repris sans réécriture : sélection HTML → ancre `.qmd` → variantes Quarto de test → comparaison → choix local. Les quatre critères sont richesse, fluidité, maîtrise et fidélité.

**A003 — Source canonique et gestes séparés.** Une ancre DOM n'est pas une cible source tant que le rapprochement Git n'est pas vérifié. Aperçu DOM ≠ expérimentation réelle ≠ version approuvée ≠ publication. Échec fermé en cas d'ambiguïté, source modifiée ou rendu incorrect.

**A004 — Sécurité et isolation.** Pas de données élèves, secrets, corrections réservées ou sources pédagogiques privées dans Alliage. Source pédagogique en clone autorisé externe, expérience hors Git, serveur uniquement en loopback, jeton éphémère, aucun déploiement automatique.

**A005 — Identité du produit Alliage.** L'ancien nom n'est plus utilisé dans l'interface visible. Pour préserver la compatibilité de v0.4, les anciens identifiants de protocole et variables techniques sont conservés provisoirement : migration ultérieure testée.

**A006 — GitHub traçable.** Branche/PR pour changement substantiel ; tests Python et examen de confidentialité avant publication ; documenter les réussites réelles sans extrapoler.

**A007 — Licence AGPL-3.0-or-later (adoptée le 19 octobre 2026).** Le propriétaire a confirmé explicitement « AGPL 3 or later » pour Alliage. Les fichiers sources d'Alliage utilisent l'identifiant SPDX `AGPL-3.0-or-later`, et la déclaration complémentaire `LICENSE-NOTICE.md` accompagne le texte intégral inchangé de l'AGPL v3 dans `LICENSE`. Ce choix n'étend pas la licence aux dépôts pédagogiques privés ou aux ressources externes.

## Hypothèses à éprouver

**H001 — Extension de navigateur + adaptateurs légers + connecteurs.** Viser une expérience unifiée, mais adapter les mécanismes de modification réelle à Quarto/Grist/etc. Aucun framework multiapplication imposé.

**H002 — IA interchangeable.** Aucun moteur (OpenCode, OpenHands, autre) ni mode d'accès aux modèles choisi ; privilégier les connecteurs existants, tester avec cas concrets.

**H003 — Licence : levée, voir A007.** L'hypothèse a été résolue par la confirmation explicite du propriétaire le 19 octobre 2026.

## Abandonnés ou différés

- **Nom de travail PédagoLab** : remplacé par **Alliage** ; chaînes `pedagolab.*` encore présentes seulement comme compatibilité technique.
- **Copie volatile sous `/tmp`** : remplacée dans les consignes par un clone Git persistant sous `~/projets/pedagogie` ; possibilité de chemin explicite `--repo` conservée.
- **Rendus DOM comme preuves suffisantes** : exclus ; rendu réel Quarto requis.
- **Serveur IA générique / fork des applications / publication automatique** : différés faute de nécessité démontrée.

## Nouvelle orientation adoptée — 20 octobre 2026

**A008 — La ressource versionnée devient l'objet central.** Le cycle A/B v0.4 est conservé comme expérience qualifiée, mais **ne constitue plus l'interaction cible**. L'enseignant travaille sur une unique ressource de conception dont une révision est publiée explicitement, sans double édition des contenus.

**A009 — Git est l'autorité Quarto.** Une identité logique explicite désigne le dépôt et le `.qmd` ; un SHA complet désigne l'état du projet. Une branche de travail désigne un pointeur mutable, pas une révision. Les labels pédagogiques et messages de commit ne remplacent ni le SHA ni les vérifications de rendu. Les renommages de chemins demanderont ultérieurement une migration contrôlée d'identité.

**A010 — Publication séparée et prouvée.** Une révision déclarée comme publiée sans attestation vérifiable reste `DECLARED_NOT_VERIFIED` ; ne jamais conclure du seul commit qu'un élève reçoit effectivement cette version. La conception, la validation, le rendu élève, le déploiement et les instances déjà commencées doivent rester distincts. Aucune publication automatique.

**A011 — Agents externes et IA interchangeable.** Les agents modifient les branches autorisées par les moyens dont ils disposent (par exemple GitHub), sans extraction des conversations web ni création d'un chatbot/API IA. Les accès ChatGPT sont à qualifier **dans le mode exact utilisé** ; la présence d'un connecteur dans une conversation ne garantit pas son fonctionnement dans la barre latérale Firefox.

**A012 — Prototype incrémental Quarto d'abord.** Premier incrément strictement en lecture seule, sans nouvelle base, serveur, moteur de rendu ou modification du prototype v0.4 ; tests sur Git temporaire et ressources fictives. L'aperçu historique, la détection de commits distants, la navigation Firefox et la publication seront des étapes ultérieures et distinctes.

**Arbitrage ouvert :** la future topologie des branches par ressource et le registre d'attestations de publication ne sont pas imposés par P3.0. Expérimenter une branche dédiée sur un dépôt de test, puis décider à partir du parcours réel.
