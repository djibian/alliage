# Alliage — feuille de route

## Acquis observés (expérimentations pilotes)

- **P1** : sélections de deux occurrences identiques distinguées dans la page HTML Quarto publiée.
- **P2a** : deux ancrages exacts retrouvés dans le `.qmd` au même commit.
- **P2b** : deux variantes `.qmd` expérimentales rendues par le vrai Quarto (`RENDER_VERIFIED_LOCAL`), comparaison vérifiée par l'enseignant, source intacte.
- **v0.4 qualifiée pour le pilote Firefox (19/10/2026)** : extension + pont local et vrai Quarto 1.10.19 ; sélection, deux variantes A/B, comparaison et choix local fonctionnent d'après l'essai utilisateur. L'endpoint de santé confirme le commit source, les fichiers de rapport et décision existent, le dépôt pédagogique reste propre. Les 18 tests automatisés et la CI restent verts. La qualification se limite à la Mission 02.

## Priorité actuelle — Quarto avec révisions Git (décision du 20 octobre 2026)

La priorité historique « dialogue direct → variantes A/B » est remplacée : l'IA pourra modifier **une révision de travail autorisée**, Alliage détectera les nouveaux commits et montrera les versions sans publier. Le parcours A/B qualifié reste disponible ; il n'est plus l'interface cible.

Expériences courtes, séquentielles et non destructives :

1. **P3.0 — lecture du modèle Git** : identifier une ressource fictive publiable, le SHA de sa branche de travail, son historique et un SHA publié *déclaré non vérifié* ; aucune écriture et aucun changement de checkout. Implémentation initiale : `quarto_versions.py` et tests autonomes.
2. **P3.1 — aperçus isolés** : créer deux vraies révisions Quarto fictives, restituer l'ensemble des dépendances de chacune et vérifier le rendu HTML obtenu avec Quarto réel, sans toucher aux sources ni aux données élèves.
3. **P3.2 — navigation Firefox** : afficher le navigateur d'historique sur les seuls aperçus locaux identifiés, retour à la révision de travail ; vérification manuelle et régression v0.4.
4. **P3.3 — modification externe** : tester un commit sur une branche de test autorisée via connecteur GitHub de la conversation ordinaire, puis récupération Git explicite et détection de l'écart de SHA. Vérifier séparément les capacités du panneau Firefox ; aucun accès Work/API présumé.
5. **Raccordement expérimental P3.3 → P3.1 → P3.2 (avant P3.4)** : V3/V4 fictives qualifiées sur Ubuntu/Quarto réel et Firefox (26/10/2026), avec intervention manuelle. Prochaine preuve : commande locale minimale, explicite et réversible réutilisant les composants ; tests d'identité de ressource, d'intégrité, de non-récupération Git implicite, de sessions neuves et de non-régression v0.4. Les chemins et `navigation.html` restent des outils de laboratoire, non une architecture produit définitive.
6. **P3.4 — préparation de publication** : distinguer validation, SHA source, rendu élève et attestation de déploiement, sans déployer. Tester la non-divulgation des sections enseignantes avant toute étape de publication effective.

**Hors phase :** restauration réelle, publication effective, Grist et toutes les autres applications.

## Puis, progressivement

1. Prouver la correspondance de version entre le HTML publié et le commit source avant toute écriture future ; compléter les gardes de sécurité et les tests de reprise de session.
2. Rendre le pilote reproductible sur **une ressource Quarto fictive publiable**, indépendante de tout dépôt pédagogique privé ; renforcer tests de sécurité et de provenance.
3. **Grist T01** : expérimenter sur un document de test isolé, avec Gia, sans toucher au tutoriel original ; vérifier droits, duplication, projection source JSON et comportement réel. La PR pédagogique #44 a été fusionnée le 18/10/2026 ; l'accès Gia VPS à T01 est actuellement à confirmer.
4. Enrichir la désignation : captures, annotation, plusieurs éléments, oral ; qualifier les permissions Chrome/Firefox.
5. Concevoir/restructurer des activités entières en s'appuyant sur les progressions et référentiels ; espaces de conception, historique et publication séparée.
6. Intégrer progressivement Moodle, Snap!, Collabora, puis WebeeBlocks web ; consolider distribution, sécurité, documentation et tests.

## Différé

Infrastructure serveur dédiée, orchestration d'agents générique, publication automatisée, synchronisation transversale des applications, distribution sur les magasins d'extensions : **aucun besoin prouvé à ce stade**.
