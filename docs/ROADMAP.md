# Alliage — feuille de route

## Acquis observés (expérimentations pilotes)

- **P1** : sélections de deux occurrences identiques distinguées dans la page HTML Quarto publiée.
- **P2a** : deux ancrages exacts retrouvés dans le `.qmd` au même commit.
- **P2b** : deux variantes `.qmd` expérimentales rendues par le vrai Quarto (`RENDER_VERIFIED_LOCAL`), comparaison vérifiée par l'enseignant, source intacte.
- **v0.4 capitalisée** : extension + pont local, 18 tests automatisés **simulés**, essai Firefox de bout en bout **non vérifié**.

## Prochaine expérimentation — priorité absolue

**Qualifier la v0.4 réelle dans Firefox**, après correction de l'emplacement local volatile `/tmp`. Depuis la page publiée : sélectionner, saisir A/B, produire des rendus Quarto, comparer, enregistrer A/B/rejet, vérifier absence d'écriture dans le dépôt source. Contrôler la provenance de la page HTML publiée ultérieurement ; elle reste `revision_verified=false`.

## Puis, progressivement

1. Intégrer un dialogue avec IA de manière indépendante du modèle, sans sacrifier l'ancrage précis, la comparaison et le refus en cas de doute. Ne pas choisir prématurément OpenCode, OpenHands, etc.
2. Rendre le pilote reproductible sur **une ressource Quarto fictive publiable**, indépendante de tout dépôt pédagogique privé ; renforcer tests de sécurité et de provenance.
3. **Grist T01** : expérimenter sur un document de test isolé, avec Gia, sans toucher au tutoriel original ; vérifier droits, duplication, projection source JSON et comportement réel. La PR pédagogique #44 a été fusionnée le 18/10/2026 ; l'accès Gia VPS à T01 est actuellement à confirmer.
4. Enrichir la désignation : captures, annotation, plusieurs éléments, oral ; qualifier les permissions Chrome/Firefox.
5. Concevoir/restructurer des activités entières en s'appuyant sur les progressions et référentiels ; espaces de conception, historique et publication séparée.
6. Intégrer progressivement Moodle, Snap!, Collabora, puis WebeeBlocks web ; consolider distribution, sécurité, documentation et tests.

## Différé

Infrastructure serveur dédiée, orchestration d'agents générique, publication automatisée, synchronisation transversale des applications, distribution sur les magasins d'extensions : **aucun besoin prouvé à ce stade**.
