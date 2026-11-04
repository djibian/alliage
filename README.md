# Alliage — démonstration Quarto fictive

Branche expérimentale `experiment/pareto-quarto-demo` du dépôt public `djibian/alliage`. Elle est volontairement un **arbre Git minimal**, distinct du code logiciel de `main`. **Ne jamais créer ni fusionner une PR de cette branche vers `main`** : cela effacerait les fichiers absents de cette branche dans le diff.

Utilisation : noter le SHA de cette révision de départ (V1), demander au chatbot Firefox une modification explicite de `activite.qmd` ou `styles.css` sur cette même branche, puis récupérer volontairement la nouvelle révision (V2). Le programme `quarto_pareto_demo.py` sur `main` rend les deux SHA en copies séparées et ouvre un aperçu HTTP loopback. Aucune validation n'entraîne une publication élève.
