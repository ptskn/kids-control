# Specs / Site famille sur pragma

Clé : `site-famille` (pas de ticket Jira). Version 1.0 du 18 octobre 2026.
Sources : `docs/spec-site-famille.md` v0.2, `docs/plan-site-famille.md` v0.3, `docs/collecte-site-famille.md`.
Ce fichier est la spec canonique du pipeline. Les tables détaillées du portage restent dans `docs/spec-site-famille.md`, section 6. Ce fichier y renvoie sans les recopier.

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

Constats sur la plateforme :

- un plugin pragma est une bibliothèque C++ compilée contre le SDK ; il n'existe pas de plugin Python ;
- une permission RBAC porte sur un plugin entier ; la séparation enfant / parent passe donc par des plugins distincts ;
- `mcp-clients/projects/mcp-web-core` fournit login, `authGuard`, `adminGuard`, `pluginGuard(plugin)` et `AppShellComponent` ;
- `pragma-workspace/Puybaret/` sert de modèle pour des plugins hors dépôt pragma et pour `team/rbac/roles.json`.

## 2. Périmètre et hors-périmètre

### 2.1 Périmètre

- Cinq plugins C++ sous `WebSites/pragma-workspace/Famille/` : `KidsControlPlugin`, `TuteurPlugin`, `TuteurParentPlugin`, `KidChatPlugin`, `KidChatParentPlugin`.
- La bibliothèque statique `famille_commun` (`Famille/commun/`) : `pyrandom`, `texte`, `protection`, `profil`, `claude`.
- Le portage C++ du domaine du Tuteur au commit `72bfb48` et du chat (`assistant.py`).
- Le corpus de référence, produit une fois par le Python au commit `72bfb48`.
- L'application Angular `famille` sous `WebSites/mcp-clients/projects/famille/`.
- Les rôles `enfant` et `parent` dans `Famille/team/rbac/roles.json`.
- L'entrée `famille` du déploiement pragma.
- L'adaptation du PC de l'enfant : accès au site, raccourci, page d'accueil.
- La migration des journaux et profils existants, puis le retrait des anciennes interfaces.

### 2.2 Hors-périmètre

- Les mécanismes de blocage du PC de l'enfant : `install.sh`, uBlock, `/etc/hosts`, Timekpr. Seule leur commande à distance change.
- Toute évolution du contenu pédagogique : le portage reprend catalogue, générateurs et correcteur sans modification.
- L'accès public depuis Internet et un reverse proxy public.
- `TuteurAnthropic` (`ia = "anthropic-api"`) : non porté.
- Les commandes `tuteur lancer` et `tuteur console` : non portées.
- Les mentions du prénom hors des dépôts du site (`/mnt/hdd2to/Auregane/`, `AureganePlugin`, `tuteur/CLAUDE.local.md`).

## 3. Exigences

Chaque exigence porte sa méthode de vérification (colonne V). Codes : `ctest` (test unitaire C++), `e2e` (Playwright contre l'instance), `inst` (appel MCP sur l'instance `famille`), `cmd` (commande shell sur le serveur), `rev` (relecture d'un fichier).

### 3.1 Identité et RBAC

| Id | Exigence | V |
|---|---|---|
| SP-1 | Le rôle `enfant` reçoit `TuteurPlugin` et `KidChatPlugin`, et aucun autre plugin. | inst |
| SP-2 | Le rôle `enfant` ne reçoit jamais `AssistantPlugin`, `BashPlugin`, ni un plugin d'exécution ou de fichiers. | inst |
| SP-3 | Le rôle `parent` reçoit les cinq plugins du site. | inst |
| SP-4 | Pour un appelant de rôle `enfant`, chaque outil lit l'élève dans la session RBAC. Un argument `enfant` fourni est refusé avec le code `requete`. | ctest, inst |
| SP-5 | Pour un appelant de rôle `parent`, l'argument `enfant` est obligatoire. Une valeur qui ne désigne pas un compte de rôle `enfant` rend le code `requete`. | ctest, inst |
| SP-6 | Un identifiant d'élève respecte `^[a-z][a-z0-9_-]{0,31}$`. Toute autre valeur rend le code `requete`, sans accès disque. | ctest |
| SP-7 | Les rôles sont versionnés dans `Famille/team/rbac/roles.json`. Le dépôt ne contient aucun compte nominatif. | rev |
| SP-8 | Ajouter un enfant ne demande aucune modification de code : créer le compte, lui donner le rôle `enfant`, renseigner hôte et profil. | inst |

### 3.2 Pages enfant

| Id | Exigence | V |
|---|---|---|
| SP-9 | Après connexion, un compte `enfant` arrive sur `/enfant/seance`. | e2e |
| SP-10 | Un compte `enfant` qui ouvre une route `/parent/*` ou `/admin-rbac` est redirigé hors de cette route. | e2e |
| SP-11 | `/enfant/themes` affiche les thèmes et compétences du niveau de l'élève (`tuteur_themes`). | e2e |
| SP-12 | `/enfant/seance` enchaîne démarrage, réponses, aide, explication et fin de séance (`tuteur_seance`, `tuteur_reponse`, `tuteur_aide`, `tuteur_expliquer`, `tuteur_fin`). | e2e |
| SP-13 | `/enfant/chat` envoie un message, affiche la conversation en cours et en commence une nouvelle (`chat_envoyer`, `chat_historique`, `chat_reset`). | e2e |
| SP-14 | Le thème visuel choisi par l'enfant est conservé entre deux connexions du même compte. | e2e |
| SP-15 | Les textes affichés à l'enfant sont identiques à ceux de `enfant.html` au commit `72bfb48`. | rev |

### 3.3 Pages parent

| Id | Exigence | V |
|---|---|---|
| SP-16 | Après connexion, un compte `parent` arrive sur `/parent`. Chaque page parent affiche un sélecteur d'enfant ; le choix part en argument `enfant`. | e2e |
| SP-17 | `/parent/protections` affiche l'état du PC (`kc_status`), lit et enregistre les listes `channels`, `domains`, `patterns`, puis lance `kc_apply` et affiche sa sortie. | e2e |
| SP-18 | `/parent/temps-ecran` lit et modifie jours, limites, plage horaire et bonus (`kc_screen_*`). | e2e |
| SP-19 | `/parent/rapport` affiche le rapport ECharts par période, pas et discipline (`tuteur_rapport`). | e2e |
| SP-20 | `/parent/bilan` affiche le bilan des 14 derniers jours (`tuteur_bilan`). | e2e |
| SP-21 | `/parent/profil` lit et modifie prénom affiché, âge, classe, niveaux et consignes (`tuteur_profil_get`, `tuteur_profil_set`). | e2e |
| SP-22 | `/parent/chat` affiche l'historique complet du chat de l'enfant choisi, en lecture seule (`chat_journal`). | e2e |
| SP-23 | Le parent associe chaque enfant à un hôte SSH et à un utilisateur Linux (`kc_host_get`, `kc_host_set`). | inst |
| SP-24 | `tuteur_verifier` rend les messages de `Catalogue.verifier` sur le catalogue chargé. | ctest |

### 3.4 Protection de l'enfant

| Id | Exigence | V |
|---|---|---|
| SP-25 | Toute commande `claude` construite par un plugin se termine par `--disallowed-tools` suivi de chaque entrée de `OUTILS_INTERDITS`. | ctest |
| SP-26 | Les prompts système `prompt_tuteur` et `prompt_assistant` sont identiques, à l'octet près, à ceux de `protection.py` au commit `72bfb48`. | ctest |
| SP-27 | Un sous-processus `claude` s'exécute sans shell (`execvp` sur un tableau d'arguments). Le texte de l'enfant n'apparaît que dans l'argument du message. | ctest |
| SP-28 | Aucun résultat de `tuteur_seance` ne contient la réponse attendue d'un item. `tuteur_reponse` la rend une fois l'item terminé. | ctest |
| SP-29 | Deux élèves ont des séances, des journaux, des profils et des historiques de chat séparés. | ctest, inst |
| SP-30 | `chat_envoyer` refuse un message vide ou de plus de 2000 caractères avec le code `argument`. | ctest |

### 3.5 Commande à distance du PC (`KidsControlPlugin`)

| Id | Exigence | V |
|---|---|---|
| SP-31 | L'hôte respecte `^[A-Za-z0-9@._:-]+$` et l'utilisateur `^[a-z_][a-z0-9_-]*$` (lignes 36-37 de `manager.py`). Une valeur hors motif est refusée sans appel `ssh`. | ctest |
| SP-32 | `liste` n'accepte que `channels`, `domains`, `patterns`, associées aux fichiers `blocked-channels.txt`, `blocked-domains.txt`, `blocked-url-patterns.txt` sous `/opt/kids-control/config/`. | ctest |
| SP-33 | `kc_list_save` ajoute un saut de ligne final à un contenu non vide qui n'en a pas. | ctest |
| SP-34 | `ssh` s'exécute avec `-o BatchMode=yes -o ConnectTimeout=6`. Le plugin ne stocke aucun mot de passe. | ctest |
| SP-35 | Délais repris de `manager.py` : 20 s pour `kc_status`, 300 s pour `kc_apply`, 30 s pour `kc_screen_*`, 60 s pour les autres appels `ssh`. Un dépassement rend le code `distant`. | ctest |
| SP-36 | `STATUS_SCRIPT` est repris à l'octet près ; `kc_status` rend les clés `reachable`, `filters`, `applied`, `hosts`, `firefox`, `canapply`, `canscreen`, `writable`, `host`, `error`. | ctest |
| SP-37 | Bornes de `kc_screen_schedule` : `jours` triés, uniques, entre 1 et 7 ; une limite par jour, entre 0 et 86400 s ; `0 <= heure_debut < heure_fin <= 24`. Bornes de `kc_screen_bonus` : `operation` vaut `+` ou `-`, `secondes` entre 1 et 14400. | ctest |
| SP-38 | L'utilisateur Linux visé par `kc_screen_*` est celui associé à l'enfant, jamais un argument de l'outil. | ctest |
| SP-39 | `kc_status` sur le PC réel d'un enfant rend `reachable=true`. | inst |

### 3.6 Équivalence du portage

| Id | Exigence | V |
|---|---|---|
| SP-40 | `pyrandom` reproduit les 50 × 1000 sorties de `pyrandom.json` pour `random`, `randint`, `randrange`, `choice`, `shuffle`, `sample`. | ctest |
| SP-41 | `generateurs` et `correcteur` concordent à 100 % avec `generateurs.json` et `correcteur.json`. | ctest |
| SP-42 | `planificateur`, `rapport` et `application` concordent avec `planificateur.json`, `rapport.json` et `application.json`. Flottants comparés à 1e-9 près. | ctest |
| SP-43 | Le C++ lit les journaux Python du corpus sans migration. Un journal écrit par le C++ passe `PRAGMA integrity_check` et garde le schéma de `journal.py`. | ctest |
| SP-44 | Chaque commande `claude` construite concorde avec `claude_argv.json`. | ctest |
| SP-45 | Deux exécutions du script du corpus produisent des fichiers identiques octet par octet. | cmd |
| SP-46 | Chaque assertion d'un test Python de `tests/` a son équivalent dans le test ctest correspondant (table 6.6 de `docs/spec-site-famille.md`). | rev |

### 3.7 Exigences non fonctionnelles

| Id | Exigence | V |
|---|---|---|
| SP-47 | Sur le serveur `famille` en service, `pgrep -a python` ne liste aucun processus lancé par pragma. | cmd |
| SP-48 | `ldd` et `nm -C` sur les bibliothèques des plugins ne montrent aucune dépendance à `libpython`. | cmd |
| SP-49 | Les plugins n'ouvrent aucun port réseau. Seuls `claude` et `ssh` sont lancés en sous-processus. | cmd |
| SP-50 | `domain/` ne dépend ni de SQLite, ni de la bibliothèque TOML, ni de `claude`. Aucune logique pédagogique dans `tools/` ni dans Angular. | rev |
| SP-51 | Hors appel `claude`, `tuteur_seance`, `tuteur_reponse` et `tuteur_rapport` répondent en moins de 200 ms sur un journal d'un an. | ctest |
| SP-52 | Délais des sous-processus `claude` : 40 s côté Tuteur, 90 s côté chat. Un dépassement rend `MESSAGE_DELAI` (chat) ou le repli hors ligne (Tuteur). | ctest |
| SP-53 | Aucune configuration ni donnée JSON écrite par les plugins ne contient `null` (ADR-0019). | ctest |
| SP-54 | L'instance écoute sur le réseau local seulement. Le mot de passe parent n'est jamais mémorisé sur le PC d'un enfant. | cmd |

### 3.8 Bascule

| Id | Exigence | V |
|---|---|---|
| SP-55 | Le journal SQLite et le profil du PC de l'enfant sont importés sous le compte de cet enfant. L'historique de la table `conversation` va dans `chat.sqlite`. | inst |
| SP-56 | Après retrait, aucun processus n'écoute sur 8800, 8801, 8803, 4300. | cmd |
| SP-57 | Dans la session de l'enfant, l'adresse du site n'est bloquée ni par `/etc/hosts`, ni par les politiques Firefox, ni par le DNS familial. | e2e |

## 4. Critères d'acceptation

**CA-1 — Arrivée enfant (SP-9, SP-10)**
- Given un compte de rôle `enfant` sur l'instance `famille`
- When il se connecte puis ouvre `/parent/protections`
- Then il arrive d'abord sur `/enfant/seance`, puis la route parent le redirige.

**CA-2 — Refus RBAC enfant (SP-1, SP-2)**
- Given une session de rôle `enfant`
- When elle appelle `kc_status`, `tuteur_profil_set`, `chat_journal`, puis un outil de `AssistantPlugin`
- Then RBAC refuse chaque appel.

**CA-3 — Identité depuis la session (SP-4)**
- Given une session de rôle `enfant` du compte `a`
- When elle appelle `tuteur_themes` avec l'argument `enfant = "b"`
- Then l'outil rend une erreur de code `requete` et n'ouvre aucune donnée de `b`.

**CA-4 — Argument obligatoire du parent (SP-5)**
- Given une session de rôle `parent`
- When elle appelle `tuteur_bilan` sans `enfant`, puis avec le nom d'un compte `parent`
- Then les deux appels rendent le code `requete`.

**CA-5 — Cloisonnement (SP-29)**
- Given deux comptes `enfant` `a` et `b`, chacun avec une séance terminée
- When `a` appelle `chat_historique` et `tuteur_fin` de sa séance
- Then aucun résultat ne contient de donnée de `b`.

**CA-6 — Réponse cachée (SP-28)**
- Given une séance démarrée par `tuteur_seance`
- When on parcourt le résultat JSON complet
- Then aucune réponse attendue n'y figure ; elle apparaît dans le résultat de `tuteur_reponse` de l'item.

**CA-7 — Protection `claude` (SP-25, SP-27)**
- Given un faux exécutable `claude` dans `PATH` qui écrit ses arguments
- When `chat_envoyer` envoie `"; rm -rf ~"`
- Then le faux `claude` reçoit ce texte en un seul argument, et la ligne se termine par `--disallowed-tools` puis `OUTILS_INTERDITS`.

**CA-8 — Injection SSH (SP-31, SP-32)**
- Given un faux `IRemoteHost` qui compte ses appels
- When `kc_host_set` reçoit `hote = "x; reboot"`, puis `kc_list_get` reçoit `liste = "../passwd"`
- Then les deux appels rendent le code `argument` et le faux hôte compte zéro appel.

**CA-9 — Délai SSH (SP-35)**
- Given un faux `ssh` qui dort 25 s
- When le parent appelle `kc_status`
- Then l'outil rend le code `distant` après 20 s au plus.

**CA-10 — Équivalence des exercices (SP-40, SP-41)**
- Given le corpus `generateurs.json` produit au commit `72bfb48`
- When `ctest --test-dir build -R generateurs_test` s'exécute
- Then chaque exercice C++ est identique à l'entrée du corpus, pour toutes les graines et difficultés.

**CA-11 — Compatibilité du journal (SP-43)**
- Given un `journal.sqlite` écrit par le Python
- When le C++ l'ouvre, ajoute une séance, puis le referme
- Then `PRAGMA integrity_check` rend `ok` et le schéma est celui de `journal.py`.

**CA-12 — Parent multi-enfants (SP-3, SP-16)**
- Given un compte `parent` et deux comptes `enfant`
- When le parent change d'enfant dans le sélecteur de `/parent/rapport`
- Then l'appel `tuteur_rapport` part avec le nouvel `enfant` et le graphe change.

**CA-13 — Aucun Python (SP-47, SP-48)**
- Given l'instance `famille` en service avec une séance et un chat actifs
- When on lance `pgrep -a python` et `ldd` sur chaque bibliothèque de plugin
- Then aucun processus Python lancé par pragma n'existe et aucune bibliothèque ne cite `libpython`.

**CA-14 — Retrait (SP-56)**
- Given la phase de bascule terminée
- When on lance `ss -ltnp`
- Then aucun port parmi 8800, 8801, 8803, 4300 n'est en écoute.

## 5. Impacts code

Constats faits en lecture le 18 octobre 2026.

### 5.1 Dépôt kids_control (ce workspace)

| Fichier | Fait | Impact |
|---|---|---|
| `manager.py` | 530 lignes ; `ThreadingHTTPServer` sur `127.0.0.1:8800` ; constantes `REMOTE_DIR`, `TIMEKPRA`, `FILES`, `HOST_RE`, `USER_RE`, `STATUS_SCRIPT` (lignes 28-52) ; fonctions `ssh`, `api_status`, `api_get_file`, `api_save_file`, `api_apply`, `tk`, `api_tk_*` (lignes 74-188) | source du portage `KidsControlPlugin` ; retiré à la bascule |
| `manager.py`, `CONFIG_PATH` | `~/.config/kids-control/manager.json` mémorise un seul hôte | remplacé par la clé `enfants` de la configuration du plugin |
| `config/firefox-policies.template.json` | politiques Firefox du PC | page d'accueil `/enfant` optionnelle ; vérification que l'adresse du site n'est pas bloquée |
| `config/blocked-domains.txt`, `config/safesearch-hosts.txt` | blocages DNS et `/etc/hosts` | vérification que l'adresse du site n'est pas bloquée (SP-57) |
| `install.sh`, `uninstall.sh`, `get.sh` | inchangés | aucun impact |
| `README.md`, `README.fr.md` | décrivent `manager.py` | mise à jour à la bascule |

Point d'attention : `STATUS_SCRIPT` lance `python3` sur le PC de l'enfant pour compter les filtres uBlock. SP-47 vise le serveur `famille` seulement ; le script reste donc tel quel.

### 5.2 Dépôt tuteur (`/mnt/hdd2to/im/production/tuteur`, HEAD `72bfb48`)

| Élément | Impact |
|---|---|
| `tuteur/` : `application.py`, `assistant.py`, `correcteur.py`, `domaine.py`, `generateurs.py`, `ia.py`, `journal.py`, `planificateur.py`, `profil.py`, `protection.py`, `rapport.py`, `config.py`, `contenu/` | source du portage C++ ; correspondance en table 6.3 de `docs/spec-site-famille.md` |
| `tuteur/ui/serveur.py`, `api_rapport.py`, `enfant.html`, `bilan.html` | source des outils MCP et des composants Angular |
| `parent-web/src/app/` : `rapport.service.ts`, `graphe.ts`, `options.ts`, `dates.ts`, `modele.ts`, `app.ts` et leurs `.spec.ts` | repris dans `famille/parent/rapport/` ; seul le transport change |
| `tests/` : 12 fichiers `test_*.py` | portés en ctest ; source des assertions de SP-46 |
| nouveau script de corpus | seul ajout dans ce dépôt ; le paquet `tuteur/` n'est pas modifié |

### 5.3 `WebSites/` (`/home/ptskn/Desktop/code/WebSites/`)

| Chemin | État | Impact |
|---|---|---|
| `pragma-workspace/Puybaret/` | présent | modèle de `CMakeLists.txt` autonome et de `team/rbac/roles.json` |
| `pragma-workspace/Famille/` | absent | à créer : `commun/`, cinq plugins, `team/rbac/roles.json` |
| `mcp-clients/projects/mcp-web-core` | présent | consommé tel quel (login, gardes, shell) |
| `mcp-clients/projects/puybaret` | présent | modèle de `plugins.ts`, `app.routes.ts`, `shell.config.ts` |
| `mcp-clients/projects/famille` | absent | à créer |
| `deployed/deployments.json` (dépôt pragma) | aucune entrée `famille` | ajout de l'entrée, ports 9050 et 9051 |
| `pragma/PORTS.md` | ports 9050 et 9051 non réservés | réservation, après accord client |

## 6. Découpage en tâches

Chaque tâche suit le cycle TDD : test rouge, code, test vert, commit. Une tâche rouge bloque ses dépendantes.

| Id | Tâche | Exigences | Dépend de |
|---|---|---|---|
| T-1 | Réserver 9050 et 9051 dans `pragma/PORTS.md`. | — | accord client |
| T-2 | Écrire le script du corpus dans le dépôt tuteur ; l'exécuter au commit `72bfb48` deux fois ; comparer. | SP-45 | — |
| T-3 | Copier le corpus sous `Famille/TuteurPlugin/tests/corpus/`. | SP-40 à SP-44 | T-2 |
| T-4 | Créer `Famille/CMakeLists.txt` et `commun/` sur le modèle Puybaret ; ctest vide vert. | SP-50 | — |
| T-5 | `commun/pyrandom` : test de concordance avec `pyrandom.json`, puis implémentation. | SP-40 | T-3, T-4 |
| T-6 | `commun/texte` : normalisation Unicode, `fmt`, dates ISO. | SP-41 | T-4 |
| T-7 | `commun/protection` et `commun/claude` : prompts, `OUTILS_INTERDITS`, exécution par `execvp` avec délai. | SP-25 à SP-27, SP-44, SP-52 | T-3, T-4 |
| T-8 | `commun/profil` : lecture et écriture de `profil.json`, sans `null`. | SP-21, SP-53 | T-4 |
| T-9 | `TuteurPlugin/domain` : `domaine`, puis `catalogue` et `adapters/TomlCatalogue`. | SP-24 | T-6 |
| T-10 | `domain/generateurs` puis `domain/correcteur` : concordance avec le corpus. | SP-41 | T-5, T-6, T-9 |
| T-11 | `domain/planificateur`, `adapters/SqliteJournal`, `domain/rapport`. | SP-42, SP-43, SP-51 | T-10 |
| T-12 | `domain/ITuteurIA`, `adapters/ClaudeCliTuteur`, `HorsLigneTuteur`, `domain/application`. | SP-42, SP-52 | T-7, T-11 |
| T-13 | `KidChatPlugin/domain/Chat` et `adapters/SqliteChatStore`, avec faux `claude`. | SP-30, SP-44, SP-52 | T-7 |
| T-14 | `KidsControlPlugin` : port `IRemoteHost`, `adapters/SshRemoteHost`, validations, délais, outils `kc_*`. | SP-31 à SP-38 | T-4 |
| T-15 | Outils `tuteur_*` de `TuteurPlugin` et `TuteurParentPlugin` (résolution par `IPluginResolver`). | SP-4 à SP-6, SP-24, SP-28, SP-29 | T-8, T-12 |
| T-16 | Outils `chat_*` de `KidChatPlugin` et `KidChatParentPlugin`. | SP-4, SP-5, SP-22, SP-29 | T-13 |
| T-17 | Porter chaque assertion des 12 `test_*.py` ; relecture de la table de correspondance. | SP-46 | T-12, T-13 |
| T-18 | `Famille/team/rbac/roles.json` ; entrée `famille` du déploiement ; chargement des cinq plugins. | SP-1 à SP-3, SP-7, SP-49, SP-54 | T-1, T-14, T-15, T-16 |
| T-19 | Comptes de test (deux `enfant`, un `parent`) ; tests MCP sur l'instance. | SP-1 à SP-5, SP-8, SP-23, SP-29, SP-39 | T-18 |
| T-20 | `mcp-clients/projects/famille` : squelette, routes, gardes, redirection par rôle. | SP-9, SP-10, SP-16 | T-18 |
| T-21 | Module `enfant` : `seance`, `themes`, `chat`, service `ThemeVisuel`. | SP-11 à SP-15 | T-20 |
| T-22 | Module `parent` : `protections`, `temps-ecran`, `bilan`, `profil`, `chat`. | SP-17, SP-18, SP-20 à SP-22 | T-20 |
| T-23 | `parent/rapport` : reprise de `parent-web` et de ses specs. | SP-19 | T-20 |
| T-24 | Specs Playwright : `smoke`, `components`, `intentions`, « aucune route parent pour l'enfant ». | SP-9 à SP-22 | T-21 à T-23 |
| T-25 | PC de l'enfant : accès au site, raccourci, page d'accueil optionnelle. | SP-57 | T-24 |
| T-26 | Import des journaux, profils et historiques de chat existants. | SP-55 | T-19 |
| T-27 | Contrôles du serveur : `pgrep`, `ldd`, `nm`, `ss`. | SP-47 à SP-49, SP-54 | T-18 |
| T-28 | Une semaine en parallèle, puis retrait de `manager.py`, du paquet `tuteur/`, de `parent-web/` et `deploy/rapport-parent.sh` ; mise à jour des README. | SP-56 | T-25, T-26, T-27 |

T-14 ne dépend que du SDK : la tâche avance en parallèle de T-5 à T-13.

## 7. Risques et questions ouvertes

### 7.1 Risques

| Risque | Effet | Parade |
|---|---|---|
| Écart de portage C++ / Python | exercices ou corrections différents, sans signal visible | corpus et ctest ; concordance de 100 % exigée avant la tâche suivante |
| `generateurs.py` (984 lignes) | concentre la majorité du risque de portage | T-10 seule, corpus de 200 graines × 3 difficultés par modèle |
| Erreur d'identité | un enfant voit les données d'un autre | SP-4, CA-3, CA-5, tests sur l'instance |
| Accès de l'enfant à un plugin d'exécution | contournement de la protection | SP-1, SP-2, CA-2 |
| Serveur `famille` arrêté | site indisponible pour toute la famille | accepté par le client (plan v0.3, décision 1) |
| Séances en mémoire | un redémarrage de l'instance perd les séances en cours | comportement actuel de `serveur.py`, accepté |
| Flags `claude` prouvés sous le compte enfant seulement | échec des appels sous le compte du serveur | retest en T-7 sous le compte du serveur `famille` |

### 7.2 Questions ouvertes

| Question | Tâche bloquée | Défaut retenu si aucune réponse |
|---|---|---|
| Format de l'identifiant d'élève imposé par RBAC | T-15 | motif de SP-6 |
| Arborescence des données `<racine>/<eleve>/` | T-11 | arborescence de la section 7 de `docs/spec-site-famille.md` |
| Bibliothèque TOML : `toml++` copiée ou conversion unique en JSON | T-9 | `toml++` en en-têtes, sous `commun/third_party/` |
| Normalisation Unicode : table explicite ou ICU | T-6 | table explicite U+00C0 à U+017F, plus `œ`, `æ` |
| Colonnes nullables du journal (`fin`, `duree_s`, `derniere_revision`, `erreur`, `valeur`) face à ADR-0019 | T-11 | exception documentée ; un changement casserait SP-43 |
| Limite de 2000 caractères d'un message de chat | T-13 | 2000 (SP-30) |
| Accord client sur la réservation de 9050 et 9051 | T-1, T-18 | aucun : accord requis |
| Nombre d'enfants, hôtes SSH et comptes Linux réels | T-19, T-26 | données d'exploitation, saisies à la mise en service |

SP-35 ferme le point « délai `ssh` hors `kc_apply` » de `docs/spec-site-famille.md` (hypothèse 15 s) : il reprend les valeurs mesurées dans `manager.py`.
