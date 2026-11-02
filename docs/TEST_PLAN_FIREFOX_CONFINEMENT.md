# P3.6F — Protocole de qualification Firefox et réseau (fixtures fictives)

**Statut : plan proposé, non exécuté.** Voir
[`ARCHITECTURE_FIREFOX_CONFINEMENT.md`](ARCHITECTURE_FIREFOX_CONFINEMENT.md).
Base PR #16, SHA `9f7a02d1b089a38b554af94aedaf8ca377da407a`.
PR #17 en contre-revue **parallèle**, aucune dépendance implicite.

## Règles de preuve

- Aucun essai ne charge un HTML, dépôt ou capture pédagogique privé.
- Une CI JavaScript/Python **ne prouve pas** un comportement Firefox.
- Un HTTP 404 sur le serveur local ne prouve pas que le navigateur
  n'a pas tenté de joindre une autre origine. Observer le serveur
  cible **et** le navigateur ; distinguer « bloqué par extension »
  de « inaccessible par la barrière OS ».
- Un `webNavigation.onBeforeNavigate` observé ne bloque **rien**.
  Un veto n'est acquis que si le point de contrôle annule la requête
  **avant** que le serveur piège ne la reçoive.
- Les requêtes `data:`/`blob:`/`file:` ne relèvent pas des mêmes
  événements que HTTP(S). Toute revendication hors du périmètre mesuré
  doit être explicitement classée `UNPROVEN`.
- Aucun journal public ne contient URL de capacité, fragment privé,
  HTML réel, corps de requête, token ou identifiant de session.
- Une réussite sur profil de qualification ne généralise pas à une
  installation Firefox habituelle avec extensions concurrentes.
- La qualification doit porter sur des versions Firefox et Ubuntu
  **exactes**, pas sur des noms génériques.

## 1. Fixtures et sources de preuve

**Fixture de référence :** HTML Quarto fictif `embed-resources:
true` rendu par Quarto réel (1.10.19/1.10.20 déjà qualifiés sur #16),
admis par P3.6D en une seule route. Port serveur éphémère.

**Fixture d'attaque dédiée :** un serveur HTTP test-only contenant
des liens sortants et des constructions malveillantes fictives
(pas d'accès au `quarto_teacher_http.py` réel pour ce contenu).
Ce serveur n'est accessible que dans l'espace de noms jetable et
n'est jamais relié à une session P3.6A réelle. La fixture d'attaque
peut être volontairement refusée par P3.6E : **ne jamais affaiblir le
filtre P3.6E pour tester le navigateur**.

**Serveur leurre :** deuxième adresse `127.0.0.1:AUTRE_PORT`,
compteur `requests_received`, zéro collecte de secrets. Une
requête interdite doit être visible dans le témoin négatif
(sans veto, mais toujours hors Internet) et absente avec le veto.

**Trace navigateur :** événements `webRequest` et `webNavigation`
convertis en événements structurés expurgés, avec codes
`ALLOW_MAIN`, `DENY_HTTP`, `NAVIGATION_OBSERVED`,
`BLOCKER_NOT_READY`, `PERMISSION_MISSING`, `SESSION_CLOSED`.
Éviter de publier les URL complètes ; un hash d'URL n'est pas une
mesure universelle d'anonymisation et n'est pas requis.

**Trace OS :** liste d'interfaces et routes, namespace de chaque
processus, preuve que le serveur et Firefox partagent la même
identité de namespace et qu'aucune route externe n'existe,
résultats de test local et test externe. Les logs doivent exclure
le répertoire privé de P3.6A.

## 2. Scénarios bloquants (F1/F2/F3)

| Test | Stimulus synthétique | Oracle Firefox | Oracle leurre | Verdict attendu |
| --- | --- | --- | --- | --- |
| N00 | Ouvrir l'URL unique sous listener armé | une requête principale autorisée, HTTP 200 | 0 | PASS |
| N01 | Lien `#section` dans le même document | pas de nouvelle requête HTTP | 0 | PASS |
| N02 | Clic sur `http://127.0.0.1:AUTRE_PORT/escape` | veto bloquant, aucune navigation engagée | 0 | PASS |
| N03 | Clic sur autre chemin du **même port** | veto ; la navigation ne quitte pas l'HTML | 0 | PASS |
| N04 | Lien HTTP(S) vers une origine externe fictive | veto observable, aucune navigation commise | 0 | PASS |
| N05 | `window.open` / clic avec `target=_blank` | nouvel onglet refusé ou session invalidée ; ne pas prétendre neutralisation anticipée sans preuve | 0 | PASS borné |
| N06 | Redirection HTTP 302 vers autre origine | destination bloquée au nouvel `onBeforeRequest` (à confirmer) | 0 | PASS |
| N07 | Sous-ressource `img`/`link`/`iframe` HTTP(S) | veto avec type correct et origine du document | 0 | PASS |
| N08 | Une requête `ws:`/`wss:` fictive | vérifier couverture réelle, sinon UNPROVEN | 0 | PASS ou NO_GO |
| N09 | `data:`, `blob:`, `file:`, `about:` | vérification comportement/navigations sans inférer veto webRequest | 0 | NO_GO si scénario sensible non confiné |
| N10 | Navigation par menu, adresse ou historique | refus ou invalidation observée de la session sensible | 0 | PASS borné |
| N11 | `meta refresh` externe, scripts de page coupés | pas de transition ; le banc hostile peut tester séparément le mécanisme sans JS | 0 | PASS |
| N12 | CSS/SVG contenant URLs de chargement fictives | veto des HTTP(S) générées ; risques de parsers/CSP explicités | 0 | PASS |
| N13 | Fermeture / retour arrière / restauration | aucun jeton réarmé ; pas de page sensible restaurée | 0 | PASS |

Une requête vers l'Internet public est **interdite pour le banc**.
Employer `example.invalid` comme destination syntaxique et des
terminaux loopback pour les preuves de réception ; ne jamais créer
un serveur tiers réel pour tester des fuites.

## 3. Scénarios de panne (F4/F5/F7)

| Test | Défaillance provoquée | Résultat accepté |
| --- | --- | --- |
| P00 | Permissions hôtes non accordées | aucun onglet d'essai lancé, `NO_GO` |
| P01 | `webRequestBlocking` absent | listener impossible → `NO_GO` |
| P02 | Listener non enregistré / tardif | `ARMED` impossible → `NO_GO` |
| P03 | Extension redémarrée / contexte MV3 évincé | pas de réarmement implicite ; re-handshake obligatoire |
| P04 | Permission révoquée pendant l'essai | session invalide ; vérifier l'absence de sortie réelle |
| P05 | Onglet fermé/remplacé, `tabId` réutilisé | ancienne autorisation non récupérable |
| P06 | Extension concurrente simulant redirection | le serveur leurre reste à zéro ; sinon NO_GO |
| P07 | URL de capacité réutilisée après fermeture | refus par le serveur et/ou invalidation de session |
| P08 | `webRequest` manque une catégorie de requête | pas d'affirmation « absence de fuite » sans preuve OS |
| P09 | Journaux / événements d'extension | aucun token, sélection, HTML ou URL sensible exporté |
| P10 | Fenêtre habituelle Firefox déjà ouverte | le lanceur doit prouver le **profil distinct** |
| P11 | Tentative de restauration de session au redémarrage | refuser toute ancienne capacité non réarmée |

Pour P03–P08, un simple message dans les logs ne suffit
pas : vérifier également la destination et le niveau OS.
Une défaillance de veto n'est pas masquée par la seule réussite
de la barrière réseau ; consigner les deux résultats séparément.

## 4. Isolement réseau indépendant

L'isolation Ubuntu est une **obligation de qualification F3**,
à ne pas présumer disponible. La préparation de F3 nécessite :
- un processus Firefox et le serveur de fixture **dans le même
  namespace réseau** ; des namespaces différents casseraient la
  communication vers `127.0.0.1` ;
- uniquement l'interface `lo` active, aucune route réseau externe,
  pas de connectivité ni résolution DNS externe opérationnelle ;
- une preuve négative par un navigateur **sans** listener, toujours
  dans le namespace : la page peut joindre le serveur piège
  loopback mais ne peut pas joindre Internet ;
- une preuve positive avec listener : ni navigation interdite,
  ni connexion au serveur piège ;
- arrêt de tous les processus et suppression du profil jetable.

Si les namespaces réseau sans privilège sont bloqués par
Ubuntu/AppArmor ou la distribution Firefox ne fonctionne pas
dans l'environnement testé : **NO_GO F3**, pas de « sudo »
implicite ni de désactivation de protections de l'ordinateur
de l'enseignant. Étudier ensuite un environnement VM/containeur
déjà disponible, avec revue de sécurité propre.

## 5. Critères d'acceptation et preuves à archiver

**F0 — présent (conception)** : architecture, matrice et menaces
publiées sur PR Draft ; revue indépendante de la pertinence
et du privilège `<all_urls>` ; rien de fonctionnel revendiqué.

**F1 — extension fictive** : les tests unitaires vérifient
strictement le prédicat d'autorisation HTTP sur des événements
synthétiques (bon port, mauvais port, chemin, tabId, frame,
type, origine absente, redirect, permission manquante).
Source JS et manifeste du banc vérifiés ; aucune modification
de la v0.4 ; **CI seule = comportement simulé**.

**F2 — Firefox réel** : journal de tests avec la version exacte
de Firefox, états handshake, décisions `allow`/`deny`,
destinations de navigation et compteurs serveur leurre.
La réussite des tests doit inclure un contrôle positif
(demande principale autorisée) **et un contrôle négatif**
(requête vers le leurre visible sans veto).
Aucune requête privée dans les logs.

**F3 — isolement OS** : preuve de namespace, routes et interfaces,
contact autorisé entre serveur et Firefox, impossibilité
d'accès Internet, vérification que le veto navigateur ne remplace
pas la barrière système.

**F4 — composition et décision** : rapport
`GO_FICTIONAL_NETWORK_LAB` ou `NO_GO` avec exceptions précises ;
contre-expertise indépendante obligatoire. Cela n'ouvre
**jamais** les droits de vraie session professeur : L1
(provenance/consentement), L2 (confidentialité des octets HTML)
et attestation réelle du profil Quarto restent non satisfaits.

## 6. Conditions d'arrêt immédiat

- Une fixture de test se révèle être un document pédagogique réel.
- Un navigateur de test ouvre une origine externe ou une ressource
  privée sans que les permissions/isolations requises soient attestées.
- Le profil jetable n'est pas distinct du Firefox habituel.
- Les permissions ou la version de l'extension ont dérivé.
- Un processus du banc existe hors du namespace prévu.
- Les traces contiennent un secret, une capacité d'URL ou un
  contenu pédagogique privé.

**Aucune exécution Firefox ou commande réseau n'est demandée
au propriétaire pendant F0.**
