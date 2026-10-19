# Démonstration fictive

Les ancrages JSON dans `../exemples/` et les projets Quarto fictifs intégrés aux tests
sont utilisables sans accès à une ressource pédagogique privée.

Le pilote Firefox v0.4 demeure **volontairement limité** à une adresse de page
de référence et ne fonctionne pas encore sur un site de démonstration public arbitraire.
`python3 -m unittest discover -s tests -v` reproduit les tests hors ligne ;
le test bout en bout Firefox nécessite l’accès autorisé au dépôt pédagogique concerné.

Un pilote public autonome constitue une **prochaine étape**, pas une fonction disponible.
