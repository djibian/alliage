# Alliage — feuille de route

## Acquis observés (expérimentations pilotes)

- **P1** : sélections de deux occurrences identiques distinguées dans la page HTML Quarto publiée.
- **P2a** : deux ancrages exacts retrouvés dans le `.qmd` au même commit.
- **P2b** : deux variantes `.qmd` expérimentales rendues par le vrai Quarto (`RENDER_VERIFIED_LOCAL`), comparaison vérifiée par l'enseignant, source intacte.
- **v0.4 qualifiée pour le pilote Firefox (19/10/2026)** : extension + pont local et vrai Quarto 1.10.19 ; sélection, deux variantes A/B, comparaison et choix local fonctionnent d'après l'essai utilisateur. L'endpoint de santé confirme le commit source, les fichiers de rapport et décision existent, le dépôt pédagogique reste propre. Les 18 tests automatisés et la CI restent verts. La qualification se limite à la Mission 02.

## Prochaine expérimentation — priorité absolue

**Expérimenter un premier dialogue contextualisé avec l'IA directement depuis la sélection dans Firefox**, sans remplacer la v0.4 qualifiée : une demande de l'enseignant sur un passage identifié doit pouvoir produire des formulations proposées par l'IA, clairement distinguées de modifications réelles ; celles retenues doivent suivre le cycle Quarto A/B déjà vérifié. Comparer les possibilités existantes de connexion à un modèle, documenter la confidentialité et ne choisir ni plateforme ni framework générique avant ce test. La provenance exacte de la page HTML publique reste `revision_verified=false`.

## Puis, progressivement

1. Prouver la correspondance de version entre le HTML publié et le commit source avant toute écriture future ; compléter les gardes de sécurité et les tests de reprise de session.
2. Rendre le pilote reproductible sur **une ressource Quarto fictive publiable**, indépendante de tout dépôt pédagogique privé ; renforcer tests de sécurité et de provenance.
3. **Grist T01** : expérimenter sur un document de test isolé, avec Gia, sans toucher au tutoriel original ; vérifier droits, duplication, projection source JSON et comportement réel. La PR pédagogique #44 a été fusionnée le 18/10/2026 ; l'accès Gia VPS à T01 est actuellement à confirmer.
4. Enrichir la désignation : captures, annotation, plusieurs éléments, oral ; qualifier les permissions Chrome/Firefox.
5. Concevoir/restructurer des activités entières en s'appuyant sur les progressions et référentiels ; espaces de conception, historique et publication séparée.
6. Intégrer progressivement Moodle, Snap!, Collabora, puis WebeeBlocks web ; consolider distribution, sécurité, documentation et tests.

## Différé

Infrastructure serveur dédiée, orchestration d'agents générique, publication automatisée, synchronisation transversale des applications, distribution sur les magasins d'extensions : **aucun besoin prouvé à ce stade**.
