# Alliage — vision produit

Alliage est un **environnement ouvert d'ingénierie pédagogique augmentée par l'IA**. Il ne remplace pas les logiciels dans lesquels les enseignants travaillent : il augmente leur capacité à montrer, discuter, transformer et expérimenter les ressources **dans leur véritable contexte d'utilisation**.

L'enseignant doit pouvoir sélectionner précisément un passage, désigner un composant, capturer ou annoter une zone, désigner plusieurs éléments et dialoguer par texte ou oralement. L'IA tient compte de la ressource, de sa source, de sa version, du référentiel et de la progression ; elle peut proposer des corrections, transformations ou créations d'activités. L'enseignant compare les propositions en situation, expérimente le fonctionnement réel, accepte, ajuste, refuse ou annule. **Validation, sauvegarde et publication sont des actes distincts et explicites.**

## Critères de réussite

1. **Richesse** : l'intention s'exprime naturellement par texte, parole, sélection et annotation.
2. **Fluidité** : dialogue, comparaison, essais et reprise de dialogue ne nécessitent pas de manœuvres techniques.
3. **Maîtrise** : traçabilité, versions, réversibilité, comparaison et contrôle de publication.
4. **Fidélité** : la ressource source et le comportement réellement obtenus correspondent à la proposition expérimentée puis choisie.

## Applications cibles

Quarto/HTML ; Grist Community (connecteur Gia existant) ; Moodle ; Snap! ; Collabora Online ; WebeeBlocks une fois sa version web intégrant Webots disponible. Firefox/Ubuntu et Chrome/ChromeOS sont des navigateurs cibles, dans les limites des politiques de gestion des appareils.

L'extension navigateur avec panneau de dialogue est une **hypothèse prioritaire**, pas un dogme. Évaluer ce qui existe déjà avant de développer un composant. L'expérience utilisateur doit rester commune ; les mécanismes de modification réelle pourront varier selon l'application. Le moteur d'agent IA n'est pas choisi.

## Ressource unique et révisions de conception (décision du 20 octobre 2026)

Alliage n'est **pas** principalement un comparateur A/B ni un chatbot supplémentaire. L'enseignant travaille sur une ressource canonique dans l'application réelle ; le dialogue IA, indépendant du fournisseur, peut entraîner des modifications autorisées dans les fichiers versionnés. Alliage observe et vérifie ces modifications plutôt que d'extraire les réponses du chatbot.

Chaque ressource a une identité stable, une histoire de révisions vérifiables, un pointeur de travail et une publication explicite. La « version élève » est un rendu ou une instance produite à partir d'une révision validée, non une seconde source éditable à synchroniser. L'enseignant peut continuer à concevoir une révision ultérieure pendant que les élèves consultent la précédente.

**Enregistrer, créer une révision, valider, publier et restaurer sont des opérations distinctes.** Toute restauration conserve l'historique ; aucune révision de travail ne déclenche une publication. Les contenus réservés aux enseignants ne doivent pas être révélés dans la projection élève.

La navigation pédagogique présente des libellés compréhensibles, mais lie chaque vue au SHA Git et aux empreintes de contenu. Un résumé, une demande IA ou un message de commit ne prouve pas la modification ; une déclaration de SHA « publié » ne prouve pas le déploiement.

La navigation historique constitue une ambition d'interface commune pour Quarto, Grist, Snap!, Moodle, Collabora et WebeeBlocks, **sans imposer de stockage ni d'opérations universelles**. Les instances et données des élèves demeurent distinctes de l'historique de conception. Les premières expériences concernent uniquement Quarto.
