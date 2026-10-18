# Specs / Site famille sur pragma

Clé : `site-famille` (pas de ticket Jira). Version 1.2 du 18 octobre 2026.
Sources : `docs/spec-site-famille.md` v0.2, `docs/plan-site-famille.md` v0.3, `docs/collecte-site-famille.md`, `docs/challenge-site-famille.md`, `docs/challenge-site-famille-v1.1.md`.
Ce fichier est la spec canonique du pipeline. Les tables détaillées du portage restent dans `docs/spec-site-famille.md`, section 6. Ce fichier y renvoie sans les recopier.

Changements depuis la v1.0 : section 9. Changements depuis la v1.1 : section 10.

## 1. Contexte

Aujourd'hui, trois interfaces locales servent la famille :

| Interface | Dépôt | Port | Fonction |
|---|---|---|---|
| `manager.py` | kids_control | 8800 | listes de blocage, `install.sh`, temps d'écran Timekpr, par `ssh` |
| `tuteur/ui/serveur.py`, `enfant.html`, `bilan.html` | tuteur | 8801 | séance de l'enfant, bilan et profil parent, onglet « Mon assistant » |
| `tuteur/ui/api_rapport.py`, `parent-web/` | tuteur | 8803, 4300 | rapport parent (Angular, ECharts) |

Le client demande un site Angular unique, protégé par RBAC, servi par un serveur pragma. Le rôle de l'utilisateur connecté choisit les pages enfant ou parent. Le code vit sous `/home/ptskn/Desktop/code/WebSites/`.

Contraintes actées par le client (plan v0.3, section 4) :

- aucun processus Python sur le serveur du site : le Tuteur et le chat passent en C++ (plugins) et en Angular (pages) ;
- une instance pragma dédiée `famille`, ports proposés 9050 (serveur) et 9051 (web) ;
- login RBAC standard de pragma, réseau local seulement, accès externe par VPN ;
- un compte RBAC par enfant, plusieurs enfants de niveaux différents ;
- le chat `kid` reste une application distincte du Tuteur ;
- le prénom de l'enfant n'apparaît ni dans le code, ni dans les chemins, ni dans les noms de plugins.

Constats sur la plateforme, relus le 18 octobre 2026 :

- Un plugin pragma est une bibliothèque C++ compilée contre le SDK. Il n'existe pas de plugin Python.
- Une permission RBAC porte sur un plugin entier. La séparation enfant / parent passe donc par des plugins distincts.
- `IRbacService.h` (lignes 21-62) n'expose aucune lecture des rôles d'un compte. Un plugin ne connaît donc pas le rôle de l'appelant.
- `McpServer.cpp` (lignes 586-596) injecte `_username` et `_is_admin` dans les arguments de tout outil appelé par une session connectée.
- `RbacService.h` (lignes 61-75) exempte les outils `rbac_*` du contrôle par plugin, dont `rbac_login`, `rbac_my_permissions` et `rbac_my_roles`.
- `resolveEffectivePlugins` (`RbacService.h`, lignes 485-500) ne retient que les permissions `true`. Un plugin absent de la carte d'un rôle est donc refusé.
- `mcp-clients/projects/mcp-web-core` fournit login, `authGuard`, `adminGuard`, `pluginGuard(plugin)` et `AppShellComponent`. Il ne stocke rien dans `localStorage` ni `sessionStorage`.
- `theme_set` enregistre la préférence de l'appelant, mais diffuse le thème à tous les clients connectés (`ThemeManager.cpp`, lignes 256-281).

## 2. Périmètre et hors-périmètre

### 2.1 Périmètre

- Cinq plugins C++ sous `WebSites/pragma-workspace/Famille/` : `KidsControlPlugin`, `TuteurPlugin`, `TuteurParentPlugin`, `KidChatPlugin`, `KidChatParentPlugin`.
- La bibliothèque statique `famille_commun` (`Famille/commun/`) : `pyrandom`, `texte`, `protection`, `profil`, `claude`, `registre`, `erreurs`.
- Le portage C++ du domaine du Tuteur au commit `72bfb48` et du chat (`assistant.py`).
- Le corpus de référence, produit une fois par le Python au commit `72bfb48`.
- L'application Angular `famille` sous `WebSites/mcp-clients/projects/famille/`.
- Les rôles `enfant` et `parent` dans `Famille/team/rbac/roles.json`.
- L'entrée `famille` de `/home/ptskn/Desktop/code/deployed/deployments.json`.
- Sur le PC de l'enfant : deux politiques Firefox (`PasswordManagerEnabled`, `OfferToSaveLogins`) et le lanceur « Mon tuteur » vers le site.
- La migration des journaux, profils et historiques de chat existants, puis le retrait des anciennes interfaces.

### 2.2 Hors-périmètre

- Les autres mécanismes de blocage du PC de l'enfant : uBlock, `/etc/hosts`, DNS familial, Timekpr, `WebsiteFilter`. Seule leur commande à distance change.
- La page d'accueil Firefox du PC de l'enfant : elle reste `https://www.qwantjunior.com/`.
- Toute évolution du contenu pédagogique : le portage reprend catalogue, générateurs et correcteur sans modification.
- L'accès public depuis Internet et un reverse proxy public.
- `TuteurAnthropic` (`ia = "anthropic-api"`) : non porté.
- Les commandes `tuteur lancer` et `tuteur console` : non portées.
- `deploy/CLAUDE-enfant.md` du dépôt tuteur : il encadre l'usage direct de `claude` sur le PC de l'enfant et reste en place.
- Les mentions du prénom hors des dépôts du site (`/mnt/hdd2to/Auregane/`, `AureganePlugin`, `tuteur/CLAUDE.local.md`).

## 3. Exigences

Chaque exigence porte sa méthode de vérification (colonne V) :

- `ctest` : test unitaire C++ ;
- `e2e` : Playwright contre l'instance `famille` ;
- `inst` : appel MCP sur l'instance `famille` ;
- `cmd` : commande shell sur le serveur `famille` ;
- `pc` : commande shell sur le PC de l'enfant, dans la session de l'enfant ;
- `rev` : relecture d'un fichier.

### 3.1 Outils, plugins et codes d'erreur

Table 3.1.1 : répartition des outils. La colonne « `enfant` » donne le statut de l'argument `enfant`.

| Plugin | Rôle | Outil | `enfant` | Autres arguments |
|---|---|---|---|---|
| `TuteurPlugin` | enfant | `tuteur_themes` | interdit | aucun |
| | | `tuteur_config` | interdit | aucun |
| | | `tuteur_seance` | interdit | `theme`, `competence` |
| | | `tuteur_reponse` | interdit | `seance_id`, `index`, `reponse`, `duree_s` |
| | | `tuteur_aide` | interdit | `seance_id`, `index`, `question` |
| | | `tuteur_expliquer` | interdit | `seance_id`, `index` |
| | | `tuteur_fin` | interdit | `seance_id` |
| | | `tuteur_apparence_get` | interdit | aucun |
| | | `tuteur_apparence_set` | interdit | `apparence` |
| `KidChatPlugin` | enfant | `chat_envoyer` | interdit | `message` |
| | | `chat_historique` | interdit | `limite` |
| | | `chat_reset` | interdit | aucun |
| `TuteurParentPlugin` | parent | `tuteur_rapport` | obligatoire | `du`, `au`, `pas`, `discipline` |
| | | `tuteur_bilan` | obligatoire | `jours` |
| | | `tuteur_profil_get` | obligatoire | aucun |
| | | `tuteur_profil_set` | obligatoire | `profil` |
| | | `tuteur_importer` | obligatoire | aucun |
| | | `tuteur_verifier` | absent | aucun |
| `KidChatParentPlugin` | parent | `chat_journal` | obligatoire | `du`, `au`, `limite` |
| | | `chat_importer` | obligatoire | aucun |
| `KidsControlPlugin` | parent | `kc_enfants` | absent | aucun |
| | | `kc_host_get` | obligatoire | aucun |
| | | `kc_host_set` | obligatoire | `hote`, `utilisateur` |
| | | `kc_status` | obligatoire | aucun |
| | | `kc_list_get` | obligatoire | `liste` |
| | | `kc_list_save` | obligatoire | `liste`, `contenu` |
| | | `kc_apply` | obligatoire | aucun |
| | | `kc_screen_users` | obligatoire | aucun |
| | | `kc_screen_info` | obligatoire | aucun |
| | | `kc_screen_schedule` | obligatoire | `jours`, `limites`, `heure_debut`, `heure_fin` |
| | | `kc_screen_bonus` | obligatoire | `operation`, `secondes` |

- Un parent n'a pas accès à `TuteurPlugin` ni à `KidChatPlugin`. RBAC refuse donc un appel parent à `tuteur_seance`.
- `TuteurParentPlugin` résout `TuteurPlugin` par `IPluginResolver` et partage ses instances `tuteur::Application`. `KidChatParentPlugin` résout `KidChatPlugin` de la même façon.
- `KidChatPlugin` résout `TuteurPlugin` pour lire le profil et la compétence en cours, entrées de `prompt_assistant`.

Table 3.1.2 : codes d'erreur. Un outil en erreur rend un résultat d'outil en erreur, avec un code et un message.

| Code | Cas |
|---|---|
| `requete` | `enfant` présent alors qu'il est interdit ; `enfant` absent alors qu'il est obligatoire ; élève hors du registre ; identifiant hors motif |
| `argument` | autre argument manquant, hors motif ou hors bornes ; `seance_id` ou `index` inconnu |
| `interdit` | opération refusée par le domaine, dont un import vers une cible non vide |
| `distant` | échec `ssh` : code retour non nul ou délai dépassé |
| `interne` | toute autre exception |

### 3.2 Identité et RBAC

| Id | Exigence | V |
|---|---|---|
| SP-1 | `roles.json` donne `true` au rôle `enfant` pour `TuteurPlugin` et `KidChatPlugin`, et à lui seul. Le rôle `parent` reçoit `true` pour `KidsControlPlugin`, `TuteurParentPlugin` et `KidChatParentPlugin`, et à eux seuls. | rev, inst |
| SP-2 | Une session `enfant` qui appelle un outil d'un plugin absent de la carte de son rôle, par exemple `bash_execute`, est refusée par RBAC. | inst |
| SP-3 | Un compte `enfant` se connecte et lit ses permissions sans droit supplémentaire. `rbac_login`, `rbac_my_permissions` et `rbac_my_roles` sont exemptés par `isRbacTool`. | e2e |
| SP-4 | Le registre des enfants est le fichier `<racineFamille>/enfants.json`, objet `{ "<compte>": { "hote": "...", "utilisateur": "..." } }`. Un compte est un enfant si et seulement s'il est clé de ce fichier. Chaque plugin relit le fichier quand sa date de modification change : un ajout ne demande aucun redémarrage. | ctest |
| SP-5 | Un outil de `TuteurPlugin` ou `KidChatPlugin` prend l'élève dans `_username`. Un argument `enfant` fourni rend `requete`. Un `_username` hors du registre rend `requete`, sans accès disque. | ctest, inst |
| SP-6 | Un outil des trois plugins parent marqué « obligatoire » exige `enfant`, clé du registre. Sinon il rend `requete`. `kc_host_set` crée la clé quand elle manque. | ctest, inst |
| SP-7 | Un identifiant d'élève respecte `^[a-z][a-z0-9_-]{0,31}$`. Toute autre valeur rend `requete`, sans accès disque. | ctest |
| SP-8 | `tools/list` sur l'instance rattache chaque outil au plugin de la table 3.1.1. | inst |
| SP-9 | Chaque refus d'un outil porte l'un des cinq codes de la table 3.1.2, et aucun autre. | ctest |
| SP-10 | Les rôles sont versionnés dans `Famille/team/rbac/roles.json`. Le dépôt ne contient aucun compte nominatif. | rev |
| SP-11 | Ajouter un enfant ne demande aucune modification de code. Il suffit de créer le compte, de lui donner le rôle `enfant` et d'appeler `kc_host_set`. | inst |

### 3.3 Pages enfant

| Id | Exigence | V |
|---|---|---|
| SP-12 | Après connexion, un compte `enfant` arrive sur `/enfant/seance`. | e2e |
| SP-13 | Un compte `enfant` qui ouvre une route `/parent/*` ou `/admin-rbac` est redirigé vers `/enfant/seance`. | e2e |
| SP-14 | `/enfant/themes` affiche les thèmes et compétences du niveau de l'élève (`tuteur_themes`). | e2e |
| SP-15 | `/enfant/seance` enchaîne démarrage, réponses, aide, explication et fin de séance (`tuteur_seance`, `tuteur_reponse`, `tuteur_aide`, `tuteur_expliquer`, `tuteur_fin`). | e2e |
| SP-16 | `/enfant/chat` envoie un message, affiche la conversation en cours et en commence une nouvelle (`chat_envoyer`, `chat_historique`, `chat_reset`). | e2e |
| SP-17 | L'enfant choisit une apparence parmi `clair`, `sombre`, `ocean`, `foret`. `tuteur_apparence_set` l'écrit dans `<racineDonnees tuteur>/<eleve>/preferences.json`. `tuteur_apparence_get` la relit à la connexion ; défaut `clair`. | ctest, e2e |
| SP-18 | Une `apparence` hors de la liste de SP-17 rend `argument`. Le site n'appelle jamais `theme_set`. | ctest, rev |
| SP-19 | Les libellés des écrans `accueil`, `theme`, `exercice`, `fin` et de l'onglet « Mon assistant » sont ceux de `enfant.html` au commit `72bfb48`. Les écrans nouveaux (connexion, apparence) sont hors de cette exigence. | rev |

### 3.4 Pages parent

| Id | Exigence | V |
|---|---|---|
| SP-20 | Après connexion, un compte `parent` arrive sur `/parent`. Chaque page parent affiche un sélecteur d'enfant rempli par `kc_enfants` ; le choix part en argument `enfant`. | e2e |
| SP-21 | `/parent/protections` affiche l'état du PC (`kc_status`), lit et enregistre les listes `channels`, `domains`, `patterns`, puis lance `kc_apply` et affiche sa sortie. | e2e |
| SP-22 | `/parent/temps-ecran` lit et modifie jours, limites, plage horaire et bonus (`kc_screen_*`). | e2e |
| SP-23 | `/parent/rapport` affiche le rapport ECharts par période, pas et discipline (`tuteur_rapport`). | e2e |
| SP-24 | `/parent/bilan` affiche le bilan des 14 derniers jours (`tuteur_bilan`). | e2e |
| SP-25 | `/parent/profil` lit et modifie prénom affiché, âge, classe, niveaux et consignes (`tuteur_profil_get`, `tuteur_profil_set`). `tuteur_profil_set` n'a pas d'argument `code` : le rôle `parent` remplace `code_parent` de `config.py` (ligne 42), qui n'est pas porté. | e2e, rev |
| SP-26 | `/parent/chat` affiche l'historique complet du chat de l'enfant choisi, en lecture seule (`chat_journal`). | e2e |
| SP-27 | Le parent associe chaque enfant à un hôte SSH et à un utilisateur Linux (`kc_host_get`, `kc_host_set`). | inst |
| SP-28 | `tuteur_verifier` rend les messages de `Catalogue.verifier` sur le catalogue chargé. | ctest |

### 3.5 Protection de l'enfant

| Id | Exigence | V |
|---|---|---|
| SP-29 | Toute commande `claude` construite par un plugin se termine par `--disallowed-tools` suivi de chaque entrée de `OUTILS_INTERDITS`. | ctest |
| SP-30 | Les prompts système produits par le C++ sont identiques, à l'octet près, à ceux de `prompts.json`. Ce fichier du corpus contient `prompt_tuteur` et `prompt_assistant` pour chaque profil du corpus. | ctest |
| SP-31 | Un sous-processus `claude` s'exécute sans shell (`execvp` sur un tableau d'arguments). Le texte de l'enfant n'apparaît que dans l'argument du message. | ctest |
| SP-32 | Aucun résultat de `tuteur_seance` ne contient la réponse attendue d'un item. `tuteur_reponse` la rend une fois l'item terminé. | ctest |
| SP-33 | Deux élèves ont des séances, des journaux, des profils, des préférences et des historiques de chat séparés. | ctest, inst |
| SP-34 | `chat_envoyer` refuse un message vide ou de plus de 2000 caractères avec `argument`. Ce comportement est nouveau : `assistant.py` n'a pas de limite, et SP-49 ne s'applique pas ici. | ctest |

### 3.6 Commande à distance du PC (`KidsControlPlugin`)

| Id | Exigence | V |
|---|---|---|
| SP-35 | L'hôte respecte `^[A-Za-z0-9@._:-]+$` et l'utilisateur `^[a-z_][a-z0-9_-]*$` (lignes 36-37 de `manager.py`). Une valeur hors motif rend `argument`, sans appel `ssh`. | ctest |
| SP-36 | `liste` n'accepte que `channels`, `domains`, `patterns`, associées à `blocked-channels.txt`, `blocked-domains.txt`, `blocked-url-patterns.txt` sous `/opt/kids-control/config/`. Toute autre valeur rend `argument`, sans appel `ssh`. | ctest |
| SP-37 | `kc_list_save` ajoute un saut de ligne final à un contenu non vide qui n'en a pas. | ctest |
| SP-38 | `ssh` s'exécute avec `-o BatchMode=yes -o ConnectTimeout=6`. Le plugin ne stocke aucun mot de passe. | ctest |
| SP-39 | Délais repris de `manager.py` : 20 s pour `kc_status`, 300 s pour `kc_apply`, 30 s pour `kc_screen_*`, 60 s pour les autres appels `ssh`. Un dépassement rend `distant`. | ctest |
| SP-40 | `STATUS_SCRIPT` est repris à l'octet près. `kc_status` rend les clés `reachable`, `filters`, `applied`, `hosts`, `firefox`, `canapply`, `canscreen`, `writable`, `host`, `error`. | ctest |
| SP-41 | Bornes de `kc_screen_schedule` : `jours` triés, uniques, entre 1 et 7 ; une limite par jour, entre 0 et 86400 s ; `0 <= heure_debut < heure_fin <= 24`. Une valeur hors bornes rend `argument`. | ctest |
| SP-42 | Bornes de `kc_screen_bonus` : `operation` vaut `+` ou `-`, `secondes` entre 1 et 14400. Une valeur hors bornes rend `argument`. | ctest |
| SP-43 | L'utilisateur Linux visé par `kc_screen_*` est celui du registre pour cet enfant, jamais un argument de l'outil. | ctest |
| SP-44 | `kc_status` sur le PC réel d'un enfant rend `reachable=true`. | inst |

### 3.7 Équivalence du portage

| Id | Exigence | V |
|---|---|---|
| SP-45 | `pyrandom` reproduit les 50 × 1000 sorties de `pyrandom.json` pour `random`, `randint`, `randrange`, `choice`, `shuffle`, `sample`. | ctest |
| SP-46 | `generateurs` et `correcteur` concordent à 100 % avec `generateurs.json` et `correcteur.json`. | ctest |
| SP-47 | `planificateur`, `rapport` et `application` concordent avec `planificateur.json`, `rapport.json` et `application.json`. Les flottants sont comparés à 1e-9 près. | ctest |
| SP-48 | Le C++ lit les journaux Python du corpus sans migration. Un journal écrit par le C++ passe `PRAGMA integrity_check` et garde le schéma de `journal.py`. | ctest |
| SP-49 | Chaque commande `claude` construite concorde avec `claude_argv.json`. | ctest |
| SP-50 | Deux exécutions du script du corpus produisent des fichiers identiques octet par octet. | cmd |
| SP-51 | Chaque assertion d'un test Python de `tests/` a son équivalent dans le test ctest correspondant (table 6.6 de `docs/spec-site-famille.md`). | rev |

### 3.8 Exigences non fonctionnelles

| Id | Exigence | V |
|---|---|---|
| SP-52 | Sur le serveur `famille` en service, `pgrep -a python` ne liste aucun processus lancé par pragma. | cmd |
| SP-53 | `ldd` et `nm -C` sur les bibliothèques des plugins ne montrent aucune dépendance à `libpython`. | cmd |
| SP-54 | `grep -rnE 'execv|execl|posix_spawn|popen|system\(' Famille/` ne trouve d'appel que dans `commun/claude/` et `KidsControlPlugin/adapters/SshRemoteHost`. | rev |
| SP-55 | Les plugins n'ouvrent aucun port. `ss -ltnp` ne montre, pour l'instance `famille`, que les ports 9050 et 9051. | cmd |
| SP-56 | `domain/` ne dépend ni de SQLite, ni de la bibliothèque TOML, ni de `claude`. Aucune logique pédagogique dans `tools/` ni dans Angular. | rev |
| SP-57 | Hors appel `claude`, `tuteur_seance`, `tuteur_reponse` et `tuteur_rapport` répondent en moins de 200 ms au 95e centile sur 100 appels. La mesure porte sur `journal-1an.sqlite`, en build Release, sur le serveur `famille`. | ctest |
| SP-58 | `journal-1an.sqlite` est produit par le script du corpus : 365 séances (une par jour), 12 réponses par séance, soit 4380 réponses. | cmd |
| SP-59 | Délais des sous-processus `claude` : 40 s côté Tuteur, 90 s côté chat. Un dépassement rend `MESSAGE_DELAI` (chat) ou le repli hors ligne (Tuteur). | ctest |
| SP-60 | Aucune configuration ni donnée JSON écrite par les plugins ne contient `null` (ADR-0019). | ctest |
| SP-61 | L'entrée `famille` de `deployments.json` vaut `host` `0.0.0.0`, `serverPort` 9050, `webPort` 9051. Sur le serveur `famille`, `ip -4 -o addr` ne montre aucune adresse publique. | cmd |
| SP-62 | L'adresse du site est `http://192.168.0.101:9051/` sur le réseau local. Le client Angular construit l'URL MCP avec `location.hostname` et le port 9050, pour servir aussi par le VPN. | rev, e2e |
| SP-63 | Après `kc_apply`, `/etc/firefox/policies/policies.json` du PC de l'enfant contient `PasswordManagerEnabled: false` et `OfferToSaveLogins: false`. | pc |

### 3.9 Bascule

| Id | Exigence | V |
|---|---|---|
| SP-64 | `tuteur_importer` copie `<racineFamille>/import/<eleve>/journal.sqlite` et `profil.json` sous `<racineDonnees tuteur>/<eleve>/`. Une cible qui contient déjà une séance rend `interdit`. Après la copie, l'outil supprime de la table `etat` du journal copié la ligne `cle = 'assistant.session_id'`. | ctest, inst |
| SP-65 | `chat_importer` copie les lignes de la table `conversation` de `<racineFamille>/import/<eleve>/journal.sqlite` dans `chat.sqlite`. Une cible qui contient déjà un message rend `interdit`. | ctest, inst |
| SP-66 | La clé `assistant.session_id` de la table `etat` n'est pas importée. Le premier message après l'import ouvre une nouvelle session `claude`. | ctest |
| SP-67 | Après retrait, aucun processus n'écoute sur 8800, 8801, 8803, 4300. | cmd |
| SP-68 | Dans la session de l'enfant, `curl -s -o /dev/null -w '%{http_code}' http://192.168.0.101:9051/` rend `200`. | pc |
| SP-69 | Sur le PC de l'enfant, `WebsiteFilter.Block` de `policies.json` ne contient aucun motif qui couvre `http://192.168.0.101:9051/`, et `/etc/hosts` ne cite pas `192.168.0.101`. | pc |
| SP-70 | Le lanceur « Mon tuteur » du PC de l'enfant ouvre `http://192.168.0.101:9051/` dans Firefox. Il existe au menu (`/usr/share/applications/site-famille.desktop`) et sur le bureau (`<bureau>/Mon-Tuteur.desktop`, écrasé). Vérifié à la fin de T-25. | pc |
| SP-71 | Après T-28, aucun fichier `.desktop` du PC de l'enfant ne cite `python3 -m tuteur`, et `/opt/tuteur` n'existe plus. | pc |
| SP-72 | Valeurs par défaut des répertoires : `<racineDonnees tuteur>` vaut `<racineFamille>/tuteur` ; `<racineDonnees kid>` vaut `<racineFamille>/chat`. L'historique d'un élève est `<racineFamille>/chat/<eleve>/chat.sqlite`. | ctest |

## 4. Critères d'acceptation

**CA-1 — Arrivée enfant (SP-12, SP-13)**
- Given un compte de rôle `enfant` sur l'instance `famille`
- When il se connecte puis ouvre `/parent/protections`
- Then il arrive sur `/enfant/seance`, puis la route parent le renvoie sur `/enfant/seance`.

**CA-2 — Refus RBAC enfant (SP-1, SP-2)**
- Given une session de rôle `enfant`
- When elle appelle `kc_status`, `tuteur_profil_set`, `chat_journal`, puis `bash_execute`
- Then RBAC refuse chaque appel.

**CA-3 — Refus RBAC parent (SP-1)**
- Given une session de rôle `parent`
- When elle appelle `tuteur_seance` puis `chat_envoyer`
- Then RBAC refuse les deux appels.

**CA-4 — Connexion enfant (SP-3)**
- Given un compte `enfant` dont le rôle ne porte que les deux plugins de SP-1
- When il se connecte sur le site
- Then `rbac_login`, `rbac_my_permissions` et `rbac_my_roles` réussissent.

**CA-5 — Identité depuis la session (SP-5)**
- Given une session `enfant` du compte `a`
- When elle appelle `tuteur_themes` avec l'argument `enfant = "b"`
- Then l'outil rend `requete` et n'ouvre aucune donnée de `b`.

**CA-6 — Compte hors registre (SP-4, SP-5)**
- Given une session `admin` dont le compte n'est pas clé de `enfants.json`
- When elle appelle `tuteur_themes`
- Then l'outil rend `requete`.

**CA-7 — Argument obligatoire du parent (SP-6)**
- Given une session de rôle `parent`
- When elle appelle `tuteur_bilan` sans `enfant`, puis avec le nom d'un compte `parent`
- Then les deux appels rendent `requete`.

**CA-8 — Cloisonnement (SP-33)**
- Given deux comptes `enfant` `a` et `b`, chacun avec une séance terminée
- When `a` appelle `chat_historique` et `tuteur_fin` de sa séance
- Then aucun résultat ne contient de donnée de `b`.

**CA-9 — Réponse cachée (SP-32)**
- Given une séance démarrée par `tuteur_seance`
- When on parcourt le résultat JSON complet
- Then aucune réponse attendue n'y figure ; elle apparaît dans le résultat de `tuteur_reponse` de l'item.

**CA-10 — Protection `claude` (SP-29, SP-31)**
- Given un faux exécutable `claude` dans `PATH` qui écrit ses arguments
- When `chat_envoyer` envoie `"; rm -rf ~"`
- Then le faux `claude` reçoit ce texte en un seul argument, et la ligne se termine par `--disallowed-tools` puis `OUTILS_INTERDITS`.

**CA-11 — Injection SSH (SP-35, SP-36)**
- Given un faux `IRemoteHost` qui compte ses appels
- When `kc_host_set` reçoit `hote = "x; reboot"`, puis `kc_list_get` reçoit `liste = "../passwd"`
- Then les deux appels rendent `argument` et le faux hôte compte zéro appel.

**CA-12 — Délai SSH (SP-39)**
- Given un faux `ssh` qui dort 25 s
- When le parent appelle `kc_status`
- Then l'outil rend `distant` après 20 s au plus.

**CA-13 — Équivalence des exercices (SP-45, SP-46)**
- Given le corpus `generateurs.json` produit au commit `72bfb48`
- When `ctest --test-dir build -R generateurs_test` s'exécute
- Then chaque exercice C++ est identique à l'entrée du corpus, pour toutes les graines et difficultés.

**CA-14 — Compatibilité du journal (SP-48)**
- Given un `journal.sqlite` écrit par le Python
- When le C++ l'ouvre, ajoute une séance, puis le referme
- Then `PRAGMA integrity_check` rend `ok` et le schéma est celui de `journal.py`.

**CA-15 — Parent multi-enfants (SP-20)**
- Given un compte `parent` et deux enfants dans le registre
- When le parent change d'enfant dans le sélecteur de `/parent/rapport`
- Then l'appel `tuteur_rapport` part avec le nouvel `enfant` et le graphe change.

**CA-16 — Apparence conservée (SP-17)**
- Given un compte `enfant` qui choisit l'apparence `sombre`
- When il se déconnecte puis se reconnecte
- Then `tuteur_apparence_get` rend `sombre` et la page l'applique.

**CA-17 — Aucun Python (SP-52, SP-53)**
- Given l'instance `famille` en service avec une séance et un chat actifs
- When on lance `pgrep -a python` et `ldd` sur chaque bibliothèque de plugin
- Then aucun processus Python lancé par pragma n'existe et aucune bibliothèque ne cite `libpython`.

**CA-18 — Import (SP-64, SP-65, SP-66)**
- Given `journal.sqlite` et `profil.json` d'un PC d'enfant copiés sous `<racineFamille>/import/<eleve>/`
- When le parent appelle `tuteur_importer`, `chat_importer`, puis encore `tuteur_importer`
- Then les deux premiers appels réussissent, `chat_journal` rend l'ancien historique, et le troisième appel rend `interdit`.

**CA-19 — Accès depuis le PC de l'enfant (SP-63, SP-68 à SP-70)**
- Given `get.sh` exécuté sur le PC de l'enfant depuis la branche `main` qui contient T-25
- When l'enfant clique sur « Mon tuteur » de son bureau, puis sur celui du menu
- Then Firefox ouvre `http://192.168.0.101:9051/` et ne propose pas d'enregistrer le mot de passe saisi.

**CA-20 — Retrait (SP-67)**
- Given la phase de bascule terminée
- When on lance `ss -ltnp`
- Then aucun port parmi 8800, 8801, 8803, 4300 n'est en écoute.

**CA-21 — Plus d'ancien lanceur (SP-71)**
- Given T-28 terminée
- When on lance `grep -rl 'python3 -m tuteur' /usr/share/applications ~/Bureau ~/Desktop` dans la session de l'enfant
- Then la commande ne trouve aucun fichier.

## 5. Impacts code

Constats faits en lecture le 18 octobre 2026.

### 5.1 Dépôt kids_control (ce workspace)

| Fichier | Fait | Impact |
|---|---|---|
| `manager.py` | 530 lignes ; `ThreadingHTTPServer` sur `127.0.0.1:8800` ; constantes `REMOTE_DIR`, `TIMEKPRA`, `FILES`, `HOST_RE`, `USER_RE`, `STATUS_SCRIPT` (lignes 28-52) ; fonctions `ssh`, `api_status`, `api_get_file`, `api_save_file`, `api_apply`, `tk`, `api_tk_*` (lignes 74-188) | source du portage `KidsControlPlugin` ; retiré en T-28 |
| `manager.py`, `CONFIG_PATH` | `~/.config/kids-control/manager.json` mémorise un seul hôte | remplacé par `<racineFamille>/enfants.json` |
| `config/firefox-policies.template.json` | clés `WebsiteFilter` (`Block` vide), `ExtensionSettings`, `DNSOverHTTPS`, `BlockAboutConfig`, `BlockAboutProfiles`, `Homepage`, `OverrideFirstRunPage` | ajout de `PasswordManagerEnabled: false` et `OfferToSaveLogins: false` (SP-63) |
| `config/site-famille.desktop` | absent | nouveau lanceur « Mon tuteur » vers `http://192.168.0.101:9051/` (SP-70) |
| `install.sh` | génère et installe `policies.json` (lignes 18, 65-94) | installe aussi `config/site-famille.desktop` dans `/usr/share/applications/` |
| `config/blocked-domains.txt`, `config/safesearch-hosts.txt`, `config/blocked-url-patterns.txt` | aucune entrée sur `192.168.0.101` | inchangés ; contrôle par SP-69 |
| `uninstall.sh` | retire les fichiers posés par `install.sh` | retire aussi le lanceur du menu |
| `get.sh` | télécharge l'archive de la branche `main` de `ptskn/kids-control` et remplace `/opt/kids-control` (lignes 6-38) | seule voie de mise à jour de `/opt/kids-control` : `kc_apply` relance la copie installée de `install.sh` (`manager.py`, ligne 117) |
| `README.md`, `README.fr.md` | décrivent `manager.py` | mise à jour en T-28 |

`STATUS_SCRIPT` lance `python3` sur le PC de l'enfant pour compter les filtres uBlock. SP-52 vise le serveur `famille` seulement : le script reste tel quel.

### 5.2 Dépôt tuteur (`/mnt/hdd2to/im/production/tuteur`, HEAD `72bfb48`)

| Élément | Impact |
|---|---|
| `tuteur/` : `application.py`, `assistant.py`, `correcteur.py`, `domaine.py`, `generateurs.py`, `ia.py`, `journal.py`, `planificateur.py`, `profil.py`, `protection.py`, `rapport.py`, `config.py`, `contenu/` | source du portage C++ ; correspondance en table 6.3 de `docs/spec-site-famille.md` ; retiré en T-28 |
| `tuteur/application.py`, ligne 347 | `CLE_SESSION = "assistant.session_id"`, stockée dans la table `etat` du journal | non importée (SP-66) |
| `tuteur/config.py`, lignes 25-27 | défauts `~/.config/tuteur/config.toml`, `~/.local/share/tuteur/journal.sqlite`, `~/.config/tuteur/profil.json` | le PC de l'enfant surcharge le journal par `config.toml` |
| `tuteur/ui/serveur.py`, `api_rapport.py`, `enfant.html`, `bilan.html` | source des outils MCP et des composants Angular ; retirés en T-28 |
| `parent-web/src/app/` : `app.ts`, `app.config.ts`, `app.html`, `dates.ts`, `graphe.ts`, `modele.ts`, `options.ts`, `rapport.service.ts` | repris dans `famille/parent/rapport/` ; seul le transport change |
| `parent-web/src/app/` : `app.spec.ts`, `dates.spec.ts` | seuls tests existants ; repris en T-23 |
| `tests/` : 12 fichiers `test_*.py` | portés en ctest ; source des assertions de SP-51 |
| `deploy/Mon-Tuteur.desktop` | ligne 5 : `Exec=env PYTHONPATH=@DEST@ /usr/bin/python3 -m tuteur lancer` | remplacé par `config/site-famille.desktop` (T-25), retiré en T-28 |
| `deploy/install-enfant.sh` | installe `/opt/tuteur`, crée `/var/lib/tuteur/journal.sqlite`, écrit `config.toml` (`journal = /var/lib/tuteur/journal.sqlite`) et `profil.json` | source des chemins d'import (T-26) ; retiré en T-28 |
| `deploy/mettre-a-jour.sh` | met à jour `/opt/tuteur` depuis GitHub | retiré en T-28 |
| `deploy/rapport-parent.sh` | lance le rapport parent | retiré en T-28 |
| `deploy/CLAUDE-enfant.md` | règles de `~/.claude/CLAUDE.md` de l'enfant | conservé (hors périmètre) |
| nouveau script de corpus | seul ajout dans ce dépôt ; produit aussi `prompts.json` et `journal-1an.sqlite` | T-2 |

Sur le PC de l'enfant, les données à importer sont `/var/lib/tuteur/journal.sqlite` et `~<utilisateur>/.config/tuteur/profil.json`. L'utilisateur Linux est celui du registre.

### 5.3 `WebSites/` et pragma

| Chemin | État | Impact |
|---|---|---|
| `/home/ptskn/Desktop/code/WebSites/pragma-workspace/Puybaret/` | aucun `CMakeLists.txt` racine ; un par plugin | `SalesIntelligencePlugin/CMakeLists.txt` sert de modèle à chaque plugin (`find_package(PragmaSDK)` si `mcp::plugin-sdk` manque) |
| `pragma-workspace/Puybaret/team/rbac/roles.json` | carte `plugins` par rôle, aucun compte | modèle de `Famille/team/rbac/roles.json` |
| `pragma-workspace/Famille/` | absent | à créer : `CMakeLists.txt` racine nouveau, `commun/`, cinq plugins, `team/rbac/roles.json` |
| `mcp-clients/projects/mcp-web-core` | présent ; `rbac.facade.ts` appelle `rbac_login` (l. 56), `rbac_my_permissions` (l. 90), `rbac_my_roles` (l. 97) | consommé tel quel |
| `mcp-clients/projects/puybaret` | présent ; `serverUrl` fixe dans `src/environments/` | modèle de `plugins.ts`, `app.routes.ts`, `shell.config.ts` ; `serverUrl` calculé dans `famille` (SP-62) |
| `mcp-clients/projects/famille` | absent | à créer |
| `/home/ptskn/Desktop/code/deployed/deployments.json` | entrées `abylsen`, `imachine`, `demo` ; aucune entrée `famille` | ajout de l'entrée de SP-61 |
| `/home/ptskn/Desktop/code/Apps/pragma/PORTS.md` | 9050 et 9051 absents | réservation, après accord client |
| `/home/ptskn/Desktop/code/Apps/pragma/sdk/public/include/Mcp/IRbacService.h` | aucune lecture de rôle | aucune modification ; le registre de SP-4 remplace cette lecture |

Le serveur `famille` est la machine `i-machine`. Ses adresses IPv4 sont `192.168.0.101` (réseau local, route statique) et `100.99.206.29` (VPN Tailscale).

## 6. Découpage en tâches

Chaque tâche suit le cycle TDD : test rouge, code, test vert, commit. Une tâche rouge bloque ses dépendantes.

| Id | Tâche | Exigences | Dépend de |
|---|---|---|---|
| T-1 | Réserver 9050 et 9051 dans `/home/ptskn/Desktop/code/Apps/pragma/PORTS.md`. | SP-61 | accord client |
| T-2 | Écrire le script du corpus dans le dépôt tuteur, avec `prompts.json` et `journal-1an.sqlite`. L'exécuter deux fois au commit `72bfb48` et comparer. | SP-50, SP-58 | — |
| T-3 | Copier le corpus sous `Famille/TuteurPlugin/tests/corpus/`. | SP-30, SP-45 à SP-49 | T-2 |
| T-4 | Créer `Famille/CMakeLists.txt` (`add_subdirectory` de `commun/` et des plugins) et `commun/CMakeLists.txt` sur le modèle `SalesIntelligencePlugin`. ctest vide vert. | SP-56 | — |
| T-5 | `commun/pyrandom` : test de concordance avec `pyrandom.json`, puis implémentation. | SP-45 | T-3, T-4 |
| T-6 | `commun/texte` : normalisation Unicode, `fmt`, dates ISO. | SP-46 | T-4 |
| T-7 | `commun/protection` et `commun/claude` : prompts, `OUTILS_INTERDITS`, exécution par `execvp` avec délai. | SP-29 à SP-31, SP-49, SP-59 | T-3, T-4 |
| T-8 | `commun/profil`, `commun/registre` (`enfants.json`, motif d'identifiant) et `commun/erreurs` (table 3.1.2), sans `null`. | SP-4, SP-7, SP-9, SP-60 | T-4 |
| T-9 | `TuteurPlugin/domain` : `domaine`, puis `catalogue` et `adapters/TomlCatalogue`. | SP-28 | T-6 |
| T-10 | `domain/generateurs` puis `domain/correcteur` : concordance avec le corpus. | SP-46 | T-5, T-6, T-9 |
| T-11 | `domain/planificateur`, `adapters/SqliteJournal`, `domain/rapport`. | SP-47, SP-48, SP-57 | T-10 |
| T-12 | `domain/ITuteurIA`, `adapters/ClaudeCliTuteur`, `HorsLigneTuteur`, `domain/application`. | SP-47, SP-59 | T-7, T-11 |
| T-13 | `KidChatPlugin/domain/Chat` et `adapters/SqliteChatStore`, avec faux `claude`. | SP-34, SP-49, SP-59 | T-7 |
| T-14 | `KidsControlPlugin` : port `IRemoteHost`, `adapters/SshRemoteHost`, validations, délais, outils `kc_*`. | SP-6, SP-35 à SP-43 | T-8 |
| T-15 | Outils `tuteur_*` de `TuteurPlugin` et `TuteurParentPlugin`, dont `tuteur_apparence_*` et `tuteur_importer`. | SP-5, SP-6, SP-17, SP-18, SP-28, SP-32, SP-33, SP-64 | T-8, T-12 |
| T-16 | Outils `chat_*` de `KidChatPlugin` et `KidChatParentPlugin`, dont `chat_importer`. | SP-5, SP-6, SP-26, SP-33, SP-65, SP-66 | T-13, T-15 |
| T-17 | Porter chaque assertion des 12 `test_*.py` ; relire la table de correspondance. | SP-51 | T-12, T-13 |
| T-18 | `Famille/team/rbac/roles.json` ; entrée `famille` de `deployments.json` ; chargement des cinq plugins. | SP-1, SP-8, SP-10, SP-61 | T-1, T-14, T-15, T-16 |
| T-19 | Comptes de test (deux `enfant`, un `parent`) ; tests MCP sur l'instance. | SP-1 à SP-3, SP-5, SP-6, SP-11, SP-27, SP-33, SP-44 | T-18 |
| T-20 | `mcp-clients/projects/famille` : squelette, `serverUrl` calculé, routes, gardes, redirection par rôle. | SP-12, SP-13, SP-20, SP-62 | T-18 |
| T-21 | Module `enfant` : `seance`, `themes`, `chat`, sélecteur d'apparence. | SP-14 à SP-19 | T-20 |
| T-22 | Module `parent` : `protections`, `temps-ecran`, `bilan`, `profil`, `chat`. | SP-21, SP-22, SP-24 à SP-26 | T-20 |
| T-23 | `parent/rapport` : reprise de `parent-web`, de `app.spec.ts` et `dates.spec.ts`. Écriture des tests de `graphe.ts`, `options.ts`, `rapport.service.ts`. | SP-23 | T-20 |
| T-24 | Specs Playwright : `smoke`, `components`, `intentions`, « aucune route parent pour l'enfant ». | SP-3, SP-12 à SP-26 | T-21 à T-23 |
| T-25 | kids_control : deux politiques Firefox, `config/site-famille.desktop`, installation par `install.sh` et retrait par `uninstall.sh`, tests sous `KIDS_CONTROL_ROOT`. Publier sur `main`, puis lancer `get.sh` sur le PC de l'enfant. Écraser `<bureau>/Mon-Tuteur.desktop` par le nouveau lanceur. | SP-63, SP-68 à SP-70 | T-24 |
| T-26 | Import : lire les clés `journal` et `profil` de `~<utilisateur>/.config/tuteur/config.toml` du PC (`config.py`, lignes 59-62), à défaut prendre les chemins de la section 5.2. Copier par `scp` les deux fichiers vers `<racineFamille>/import/<eleve>/`, puis appeler `tuteur_importer` et `chat_importer`. | SP-64 à SP-66 | T-19 |
| T-27 | Contrôles du serveur : `pgrep`, `ldd`, `nm`, `ss`, `ip`, `grep` des appels d'exécution. | SP-52 à SP-55, SP-61 | T-18 |
| T-28 | Une semaine en parallèle. Retrait ensuite de `manager.py`, du paquet `tuteur/`, de `parent-web/` et de `deploy/` sauf `CLAUDE-enfant.md`. Suppression de `/opt/tuteur` et du raccourci `Mon-Tuteur.desktop` sur le PC. Mise à jour des README. | SP-67, SP-71 | T-25, T-26, T-27 |

T-14 ne dépend que de T-8 : la tâche avance en parallèle de T-5 à T-13.

## 7. Risques et questions ouvertes

### 7.1 Risques

| Risque | Effet | Parade |
|---|---|---|
| Écart de portage C++ / Python | exercices ou corrections différents, sans signal visible | corpus et ctest ; concordance de 100 % exigée avant la tâche suivante |
| `generateurs.py` (984 lignes) | concentre la majorité du risque de portage | T-10 seule, corpus de 200 graines × 3 difficultés par modèle |
| Erreur d'identité | un enfant voit les données d'un autre | SP-5, CA-5, CA-6, CA-8, tests sur l'instance |
| Registre désynchronisé des comptes RBAC | un compte `enfant` absent du registre ne peut rien faire | refus `requete` explicite ; ajout par `kc_host_set` (SP-11) |
| Clé du registre sans compte RBAC | `kc_host_set` accepte un nom mal saisi : aucun plugin ne peut lister les comptes (le SDK n'expose `IRbacService` à aucun plugin) | après chaque `kc_host_set`, se connecter avec le compte enfant et vérifier que `tuteur_themes` réussit |
| Semaine en parallèle | l'ancien Tuteur n'a plus de lanceur sur le PC dès T-25 | retour arrière : remettre `deploy/Mon-Tuteur.desktop` sur le bureau ; `/opt/tuteur` reste installé jusqu'à T-28 |
| Accès de l'enfant à un plugin d'exécution | contournement de la protection | SP-1, SP-2, CA-2 |
| Box qui redirige un port vers `i-machine` | site exposé à Internet malgré SP-61 | relecture de la configuration de la box à la mise en service |
| Serveur `famille` arrêté | site indisponible pour toute la famille | accepté par le client (plan v0.3, décision 1) |
| Séances en mémoire | un redémarrage de l'instance perd les séances en cours | comportement actuel de `serveur.py`, accepté |
| Flags `claude` prouvés sous le compte enfant seulement | échec des appels sous le compte du serveur | retest en T-7 sous le compte du serveur `famille` |
| `PasswordManagerEnabled: false` sur le PC de l'enfant | plus aucun mot de passe enregistré dans Firefox pour ce compte | accepté : l'enfant n'a pas d'autre compte à mémoriser |

### 7.2 Questions ouvertes

| Question | Tâche bloquée | Défaut retenu si aucune réponse |
|---|---|---|
| Format de l'identifiant d'élève imposé par RBAC | T-8 | motif de SP-7 |
| Arborescence des données `<racine>/<eleve>/` | T-11 | arborescence de la section 7 de `docs/spec-site-famille.md` |
| Valeur de `racineFamille` | T-8 | `<répertoire de données de l'instance famille>/famille` |
| Liste des apparences proposées à l'enfant | T-21 | `clair`, `sombre`, `ocean`, `foret` (SP-17) |
| Bibliothèque TOML : `toml++` copiée ou conversion unique en JSON | T-9 | `toml++` en en-têtes, sous `commun/third_party/` |
| Normalisation Unicode : table explicite ou ICU | T-6 | table explicite U+00C0 à U+017F, plus `œ`, `æ` |
| Colonnes nullables du journal (`fin`, `duree_s`, `derniere_revision`, `erreur`, `valeur`) face à ADR-0019 | T-11 | exception documentée ; un changement casserait SP-48 |
| Limite de 2000 caractères d'un message de chat | T-13 | 2000 (SP-34) |
| Accord client sur la réservation de 9050 et 9051 | T-1, T-18 | aucun : accord requis |
| Nombre d'enfants, hôtes SSH et comptes Linux réels | T-19, T-26 | données d'exploitation, saisies à la mise en service |
| Lanceur pendant la semaine en parallèle : remplacer celui du bureau, ou garder deux lanceurs de noms distincts | T-25 | remplacer (SP-70) |

## 8. Notes de reprise

SP-39 reprend les délais `ssh` mesurés dans `manager.py`. Ils remplacent l'hypothèse de 15 s de `docs/spec-site-famille.md`.

Le registre de SP-4 remplace la notion de « rôle de l'appelant » de la v1.0. Les plugins enfant lisent `_username` ; les plugins parent exigent `enfant`. Aucun plugin n'a besoin de lire un rôle.

## 9. Changements depuis la v1.0

Réponses aux écarts de `docs/challenge-site-famille.md` :

| Écart | Correction |
|---|---|
| 1. Rôle de l'appelant | registre `enfants.json` (SP-4) ; plugins enfant et parent disjoints (SP-1, SP-5, SP-6) |
| 2. Outils par plugin | table 3.1.1 ; SP-8 ; CA-3 |
| 3. Connexion de l'enfant | SP-3, CA-4 ; refus par défaut en SP-2 |
| 4. Codes d'erreur | table 3.1.2 ; codes fixés en SP-35, SP-36, SP-41, SP-42 |
| 5. Thème visuel | `tuteur_apparence_*` et `preferences.json` (SP-17, SP-18, CA-16) |
| 6. Import | chemins source, outils, machine et `session_id` (SP-64 à SP-66, T-26, CA-18) |
| 7. Adresse et mot de passe | SP-61 à SP-63, SP-68, méthode `pc` |
| 8. Firefox | deux politiques au périmètre ; page d'accueil inchangée (section 2) |
| 9. `deploy/` | sort de chaque fichier (section 5.2, T-25, T-28) |
| 10. Chemins | chemins absolus en section 5.3 |
| 11. Modèle CMake | `SalesIntelligencePlugin/CMakeLists.txt` ; racine nouvelle (T-4) |
| 12. Tests Angular | deux specs existantes, trois à écrire (T-23) |
| 13. Jeu de données de performance | `journal-1an.sqlite` (SP-58) ; mesure en SP-57 |
| 14. Sous-processus | SP-54 (recherche des appels) et SP-55 (ports) |
| 15. SP-2 ouvert | remplacé par un refus par défaut vérifiable |
| 16. Référence des prompts | `prompts.json` (SP-30) |
| 17. Limite du chat | marquée nouvelle (SP-34) |
| 18. Cible de redirection | `/enfant/seance` (SP-13) |
| 19. Textes repris | écrans délimités (SP-19) |

## 10. Changements depuis la v1.1

Réponses aux écarts de `docs/challenge-site-famille-v1.1.md` :

| Écart | Correction |
|---|---|
| 1. Mise à jour du PC absente | `get.sh` en section 5.1 ; publication sur `main` et `get.sh` en T-25 ; CA-19 |
| 2. SP-70 impossible à la fin de T-25 | SP-70 limitée au nouveau lanceur ; SP-71 et CA-21 pour T-28 |
| 3. Deux lanceurs « Mon tuteur » | le raccourci du bureau est écrasé (SP-70, T-25) ; question en section 7.2 |
| 4. Chemin du profil incomplet | T-26 lit `journal` et `profil` de `config.toml` |
| 5. `session_id` copié | suppression après copie (SP-64) |
| 6. `code_parent` | non porté, remplacé par le rôle `parent` (SP-25) |
| 7. Répertoires sans défaut | SP-72 |
| 8. Relecture de `enfants.json` | relecture sur changement de date (SP-4) |
| 9. Clé du registre sans compte | risque et parade en section 7.1 |
