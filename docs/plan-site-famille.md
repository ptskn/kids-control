# Plan : site famille sur pragma (kids_control, Tuteur, chat, rapport parent)

Version 0.3, 17 octobre 2026. Document de travail : Acté / À décider / Hypothèse.

Changement depuis la v0.2 : Acté (client), aucun Python à l'exécution. Le Tuteur et le chat sont portés en C++ et en Angular. Les règles du portage sont dans `docs/spec-site-famille.md` v0.2, section 6.

## 1. Quoi

Un site Angular unique, servi par une instance pragma, avec connexion RBAC.
Le rôle de l'utilisateur connecté choisit les pages :

- Rôle `enfant` : Deux applications, par compte enfant. Le Tuteur (soutien scolaire : séance, choix de thème). Le chat `kid` (conversation libre avec l'assistant).
- Rôle `parent` : Protections kids_control, temps d'écran, rapport et bilan du Tuteur, profil de chaque élève, historique du chat.

Plusieurs enfants, de niveaux scolaires différents, utilisent le même site. Chaque enfant a son compte RBAC, son journal, son profil et son historique de chat.

Le site remplace trois interfaces locales :

| Interface actuelle | Emplacement | Port |
|---|---|---|
| `manager.py` (stdlib, SSH vers le PC de l'enfant) | kids_control | 8800 |
| `tuteur/ui/serveur.py` + `enfant.html` + `bilan.html` | tuteur | 8801 |
| `parent-web/` (Angular, ECharts) + `tuteur rapport` | tuteur | 4300, 8803 |

## 2. Constats sur l'existant

- Acté : Un plugin pragma est une bibliothèque C++ (`create_mcp_plugin()`, outils dérivés de `PluginTool`), compilée contre le SDK `dist/sdk`. Il n'existe pas de plugin Python.
- Acté : Une permission RBAC porte sur un PLUGIN entier (`RolePermission { plugin_name, granted }`), pas sur un outil. La séparation enfant/parent passe donc par des plugins distincts.
- Acté : `mcp-clients/` contient la bibliothèque `mcp-web-core` : Connexion WebSocket, login, `authGuard`, `adminGuard`, `pluginGuard(plugin)`, console admin RBAC, `AppShellComponent`. L'application `puybaret` sert de modèle.
- Acté : `pragma-workspace/Puybaret/` sert de modèle pour des plugins hors dépôt pragma (`CMakeLists.txt` autonome, `find_package(PragmaSDK)`) et pour les rôles versionnés (`team/rbac/roles.json`).
- Acté : Le Tuteur garde un état de séance en mémoire (`Application`) et sérialise les requêtes par un verrou global. Un plugin C++ reste chargé en mémoire et peut garder cet état.
- Acté : Les générateurs tirent leurs exercices d'un `random.Random` initialisé par la graine texte `nom:graine:difficulte`. L'identifiant d'exercice du journal permet de rejouer l'exercice. Le C++ doit reproduire ce générateur.
- Acté : Le Tuteur compte environ 3 700 lignes de Python, 102 fonctions de test et 3 fichiers TOML de catalogue.
- Acté : `manager.py` ne contient que des commandes `ssh` (statut, trois listes, `install.sh`, `timekpra`). Aucune logique métier ne justifie de garder Python côté kids_control.
- Acté : Le Tuteur a pour seule source `/mnt/hdd2to/im/production/tuteur/` (commit `72bfb48`).
- Acté (client) : Le Tuteur est l'application de soutien scolaire. Le chat est une seconde application, distincte.
- Acté : `/mnt/hdd2to/kid/` était prévu comme dépôt Python du chat. Le dossier part d'une copie de `ptskn/tuteur` (`ee985c7`, remote `origin` encore sur `ptskn/tuteur`). Aucun code du chat n'y existe. Avec le portage C++, son devenir est un point ouvert de la spec (section 10).
- Acté : Le code du chat existe déjà dans le Tuteur : `tuteur/assistant.py` (appel `claude`, session) et `tuteur/protection.py` (`prompt_assistant`, `OUTILS_INTERDITS`), exposés par l'onglet « Mon assistant ».
- Acté (client) : Le prénom de l'enfant n'apparaît nulle part : code, chemins, dépôts, noms de plugins, textes affichés. Le terme générique est `kid`.

## 3. Architecture cible

```
Navigateur enfant ──┐                 Déploiement pragma « famille » (deployments.json, 9050/9051)
Navigateur parent ──┼── HTTP + /mcp ──► site Angular (same-origin) + proxy WS /mcp
                    │                  PragmaServer
                    │                    RBACPlugin            (identités, rôles)
                    │                    TuteurPlugin          (rôle enfant, domaine C++, journal SQLite)
                    │                    TuteurParentPlugin    (rôle parent)
                    │                    KidChatPlugin         (rôle enfant, domaine C++, chat SQLite)
                    │                    KidChatParentPlugin   (rôle parent)
                    │                        │ sous-processus claude (protection famille_commun)
                    │                    KidsControlPlugin     (rôle parent)
                    │                        │ ssh BatchMode
                    └────────────────────► PC de chaque enfant : /opt/kids-control, timekpra
```

### 3.1 Plugins

Emplacement : `/home/ptskn/Desktop/code/WebSites/pragma-workspace/Famille/`, un dossier par plugin, build autonome contre le SDK.

| Plugin | Rôle RBAC | Outils | Remplace |
|---|---|---|---|
| `KidsControlPlugin` | parent | `kc_status`, `kc_list_get`, `kc_list_save`, `kc_apply`, `kc_host_get`, `kc_host_set`, `kc_screen_users`, `kc_screen_info`, `kc_screen_schedule`, `kc_screen_bonus` | `manager.py` |
| `TuteurPlugin` | enfant, parent | `tuteur_themes`, `tuteur_seance`, `tuteur_reponse`, `tuteur_aide`, `tuteur_expliquer`, `tuteur_fin` | `/api/*` de `serveur.py` côté enfant |
| `TuteurParentPlugin` | parent | `tuteur_rapport`, `tuteur_bilan`, `tuteur_profil_get`, `tuteur_profil_set` | `/bilan`, `/api/profil`, `api_rapport.py` |
| `KidChatPlugin` | enfant, parent | `chat_envoyer`, `chat_historique`, `chat_reset` | `/api/chat*` de `serveur.py`, onglet « Mon assistant » |
| `KidChatParentPlugin` | parent | `chat_journal` | aucun (nouveau) |

- `KidsControlPlugin` : Réécriture C++ directe des appels `ssh` de `manager.py`. Mêmes validations (`HOST_RE`, `USER_RE`, liste blanche des trois fichiers). La config du plugin associe chaque enfant à un hôte SSH et à un utilisateur Linux. Chaque outil `kc_*` prend un argument `enfant`. `~/.config/kids-control/manager.json` disparaît.
- Identité de l'élève : Pour le rôle `enfant`, le plugin prend l'élève dans la session RBAC, jamais dans les arguments. Pour le rôle `parent`, l'outil prend un argument `enfant`, validé contre la liste des comptes enfants.
- `TuteurPlugin` : Contient le domaine du Tuteur porté en C++ (générateurs, correcteur, planificateur, journal, rapport, catalogue TOML). Il garde une `tuteur::Application` par élève en mémoire.
- `TuteurParentPlugin` : Résout `TuteurPlugin` par `IPluginResolver` (motif ADR-0007 de Puybaret) et appelle les mêmes instances.
- `famille_commun` : Bibliothèque statique partagée : `protection` (port de `protection.py`), `profil`, construction et exécution de la commande `claude`, générateur compatible `random.Random`.
- `KidChatPlugin` : Contient le domaine du chat porté en C++ (`assistant.py` et la partie conversation de `application.py`).
- `KidChatParentPlugin` : Résout `KidChatPlugin` par `IPluginResolver`. `chat_journal` rend l'historique d'un enfant, en lecture seule.
- `code_parent` devient inutile : Le rôle RBAC protège `tuteur_profil_set`.

### 3.2 Portage Python → C++ et Angular

Acté (client) : Aucun Python à l'exécution. Le portage suit la section 6 de la spec.

- Référence : dépôt tuteur au commit `72bfb48`. À entrée égale, le C++ rend la même sortie que le Python.
- Corpus de référence : produit une seule fois par le Python de référence, versionné, comparé par ctest.
- Générateur : `famille_commun/pyrandom` reproduit `random.Random` de CPython. Les identifiants d'exercice du journal restent rejouables.
- Journal : schéma SQLite inchangé. Le C++ ouvre les journaux existants sans migration.
- Pages : `enfant.html` et `bilan.html` deviennent des composants Angular. `parent-web` est repris dans l'application `famille`.

### 3.3 Site Angular

Nouvelle application `famille` dans le monorepo `/home/ptskn/Desktop/code/WebSites/mcp-clients/`, consommatrice de `mcp-web-core`.

```
/login                      LoginComponent (lib)
/                           redirection selon getAccessiblePlugins :
                              KidsControlPlugin présent → /parent, sinon → /enfant
/enfant/seance              pluginGuard(TuteurPlugin)
/enfant/themes              pluginGuard(TuteurPlugin)
/enfant/chat                pluginGuard(KidChatPlugin)
/parent/protections         pluginGuard(KidsControlPlugin)   listes, apply, statut
/parent/temps-ecran         pluginGuard(KidsControlPlugin)   Timekpr
/parent/rapport             pluginGuard(TuteurParentPlugin)  ECharts, repris de tuteur/parent-web
/parent/profil              pluginGuard(TuteurParentPlugin)
/parent/chat                pluginGuard(KidChatParentPlugin)  historique du chat, lecture seule
/admin-rbac                 adminGuard (lib)
```

- Les pages parent affichent un sélecteur d'enfant. Le choix passe en argument `enfant` à chaque outil.
- Le rapport reprend `rapport.service.ts`, `graphe.ts`, `options.ts`, `dates.ts` de `tuteur/parent-web` ; seul le transport change (`/api/rapport` → outil `tuteur_rapport`).
- Les pages enfant reprennent `enfant.html` en composants Angular. Le thème choisi par l'élève est conservé.
- Le `ChatComponent` générique de la lib n'est PAS utilisé côté enfant : Le chat de l'enfant passe par `chat_envoyer`, donc par le module `protection` de `famille_commun`.

### 3.4 Rôles

Fichier `pragma-workspace/Famille/team/rbac/roles.json`, format Puybaret.

| Rôle | Plugins accordés | Plugins refusés |
|---|---|---|
| `enfant` | `TuteurPlugin`, `KidChatPlugin` | tous les autres, dont `AssistantPlugin`, `BashPlugin`, `KidsControlPlugin`, `TuteurParentPlugin`, `KidChatParentPlugin` |
| `parent` | `TuteurPlugin`, `TuteurParentPlugin`, `KidsControlPlugin`, `KidChatPlugin`, `KidChatParentPlugin` | aucun utile au site |

L'assignation nominative se fait à la mise en service par `rbac_assign_role`. Aucun compte en dur dans le dépôt. Ajouter un enfant revient à créer un compte, lui donner le rôle `enfant`, puis renseigner son hôte et son niveau scolaire.

## 4. Décisions

1. Acté (client) : Le site tourne sur un serveur pragma supplémentaire, déployé comme `abylsen`, `imachine` et `demo`. Entrée `famille` dans `deployed/deployments.json`, ports proposés `serverPort` 9050 et `webPort` 9051 (libres le 17/10/2026, à réserver dans `pragma/PORTS.md`). Conséquences :
   - Le Tuteur, le chat et leurs données tournent sur ce serveur. Le journal SQLite quitte le PC de l'enfant.
   - Plus de `scp` ni de tunnel pour le rapport.
   - Le site est indisponible quand ce serveur est arrêté.
2. Acté (client) : Le moteur IA est celui du serveur `famille`, comme pour les autres déploiements. Les flags `claude` sont prouvés sous le compte enfant seulement : Les retester sous le compte du serveur (phase 1).
3. Acté (client) : Connexion par le login RBAC standard de pragma, sans mécanisme propre au site. Le mot de passe parent n'est jamais mémorisé sur le PC d'un enfant.
4. Acté (client) : Instance dédiée `famille`, portée par le déploiement du point 1. Aucun plugin du site dans l'instance `imachine`.
5. Acté (client) : Réseau local seulement, pas de nginx public. Accès parent hors domicile par VPN.
6. Acté (client) : Plusieurs enfants, de niveaux scolaires différents. Un compte RBAC par enfant. Journal, profil, niveau, historique du chat et hôte kids_control sont propres à chaque compte (sections 3.1 à 3.4).
7. Acté (client) : `manager.py`, `serveur.py` et `parent-web/` restent jusqu'à la phase 7, puis disparaissent.
8. Acté (client) : Le chat `kid` est une application à part, à côté du Tuteur. Il a ses plugins et sa route `/enfant/chat`. Condition fixe : Le chat passe par le module `protection` de `famille_commun` (port de `protection.py`), et le rôle `enfant` ne reçoit jamais `AssistantPlugin`.
9. Acté (client) : Le plugin du chat s'appelle `KidChatPlugin`.
10. Acté (client) : L'onglet « Mon assistant » du Tuteur disparaît à la phase 7. Un seul chat, une seule protection à maintenir.
11. Acté (client) : Le parent lit l'historique du chat de chaque enfant. Outil `chat_journal` dans `KidChatParentPlugin`, réservé au rôle `parent`.
12. Acté (client) : Les mentions du prénom hors du workspace (`/mnt/hdd2to/Auregane/`, `AureganePlugin`, `tuteur/CLAUDE.local.md`) restent en l'état.

## 5. Phases

Chaque phase se termine par sa vérification. Une phase rouge bloque la suivante.

### Phase 0 : Décisions

1. Tranche les points de la section 4. Fait le 17/10/2026.
2. Réserve 9050 et 9051 dans `pragma/PORTS.md`.

Vérification : Chaque point de la section 4 est marqué Acté. `PORTS.md` contient l'instance `famille`.

### Phase 1 : Corpus de référence (dépôt tuteur, P0 de la spec)

1. Écris le script du corpus dans le dépôt tuteur, sans modifier le paquet `tuteur/`.
2. Exécute-le au commit `72bfb48`.
3. Copie le corpus dans `pragma-workspace/Famille/TuteurPlugin/tests/corpus/`.

Vérification : Les fichiers de la section 6.6 de la spec existent. Deux exécutions du script produisent des fichiers identiques.

### Phase 2 : `famille_commun` et domaine du Tuteur (P1 à P3, P5, P6)

1. Crée `pragma-workspace/Famille/commun/` : `pyrandom`, `texte`, `protection`, `profil`, `claude`.
2. Porte `domaine`, `catalogue`, `generateurs`, `correcteur`, dans cet ordre.
3. Porte `planificateur`, `SqliteJournal`, `rapport`, puis `ITuteurIA` et `application`.
4. Porte chaque fichier de `tests/` en ctest (table 6.6 de la spec).
5. Reteste les flags `claude` sous le compte du serveur `famille`.

Vérification : `ctest --test-dir build --output-on-failure` vert. Concordance de 100 % avec le corpus (A-1 à A-5 de la spec).

### Phase 2 bis : Domaine du chat (P4)

1. Porte `assistant.py` et la partie conversation de `application.py` dans `KidChatPlugin/domain/`.
2. Ajoute `SqliteChatStore`, avec un `chat.sqlite` par élève.
3. Porte `test_assistant.py` en ctest, avec un faux exécutable `claude`.

Vérification : ctest vert. La commande `claude` construite concorde avec `claude_argv.json`.

### Phase 3 : `KidsControlPlugin`

1. Crée `pragma-workspace/Famille/KidsControlPlugin/` : `domain/IRemoteHost` (port), `adapters/SshRemoteHost`, `tools/`.
2. Reprends `STATUS_SCRIPT` et les validations de `manager.py` à l'identique.
3. Ajoute les tests ctest avec un faux `IRemoteHost` : Injection refusée dans l'hôte et l'utilisateur, fichier hors liste blanche refusé.

Vérification : ctest vert. `kc_status` sur le vrai PC de l'enfant rend `reachable=yes`.

### Phase 3 bis : Outils MCP Tuteur et chat (P7)

1. Ajoute les outils `tuteur_*` dans `TuteurPlugin` et `TuteurParentPlugin`.
2. `TuteurParentPlugin` résout `TuteurPlugin` par `IPluginResolver`.
3. Ajoute les outils `chat_*` dans `KidChatPlugin` et `KidChatParentPlugin`.
4. Ajoute les tests ctest : Identité prise dans la session pour le rôle `enfant`, deux élèves séparés, réponse attendue absente avant la fin d'un item, message vide refusé.

Vérification : ctest vert. Appel des outils depuis le client MCP avec un compte de test.

### Phase 4 : Instance et rôles

1. Crée `pragma-workspace/Famille/team/rbac/roles.json` (section 3.4).
2. Ajoute l'entrée `famille` (9050/9051) dans `deployed/deployments.json`. Déploie l'instance, charge RBACPlugin et les cinq plugins.
3. Crée deux comptes `enfant` de niveaux différents et un compte `parent`, tous de test.

Vérification : Avec un compte `enfant`, `kc_status`, `tuteur_profil_set` et `chat_journal` sont refusés par RBAC. Avec un compte `enfant`, `AssistantPlugin` est refusé. Un compte `enfant` ne voit ni le journal ni le chat de l'autre. Avec le compte `parent`, les cinq plugins répondent pour chaque enfant.

### Phase 5 : Application Angular `famille`

1. Génère `projects/famille` dans `mcp-clients`, sur le modèle `puybaret` (`plugins.ts`, `app.routes.ts`, `shell.config.ts`).
2. Écris les modules `enfant` et `parent` (section 3.3).
3. Porte le rapport ECharts depuis `tuteur/parent-web`.
4. Ajoute les specs Playwright : `smoke`, `components`, `intentions`, plus un test « le compte enfant ne voit aucune route parent ».

Vérification : `ng test famille` vert, `npm run e2e` vert contre l'instance `famille`.

### Phase 6 : Adaptation de kids_control (PC de l'enfant)

1. Vérifie que l'adresse du site n'est bloquée ni par `/etc/hosts`, ni par les politiques Firefox, ni par le DNS familial.
2. Mets la page d'accueil Firefox sur `/enfant` si le parent le souhaite (`firefox-policies.template.json`).
3. Remplace le raccourci `Mon-Tuteur.desktop` par un lien vers le site.

Vérification : Dans la session de l'enfant, le site s'ouvre, la connexion `enfant` mène à `/enfant/seance`, `/parent/protections` redirige.

### Phase 7 : Bascule et retrait

1. Migre le journal SQLite et le profil du PC de l'enfant vers le serveur `famille`, sous le compte de cet enfant.
2. Fais une semaine d'usage réel avec les deux interfaces en parallèle.
3. Retire `manager.py` et les éléments de la section 6.8 de la spec : paquet `tuteur/`, `tests/`, `pyproject.toml`, `parent-web/`, `deploy/rapport-parent.sh`. Mets à jour les README et CLAUDE.md.

Vérification : Le rapport parent sur le site montre les séances de la semaine. Aucun processus n'écoute sur 8800, 8801, 8803, 4300.

## 6. Risques

- Protection de l'enfant : Tout chemin vers Claude passe par le module `protection` de `famille_commun`. Le rôle `enfant` ne reçoit jamais `AssistantPlugin` ni un plugin d'exécution. Le test RBAC de la phase 4 le vérifie.
- Disponibilité : Le site dépend du serveur `famille` (point 1).
- Cloisonnement entre enfants : Une erreur d'identité montre le journal ou le chat d'un enfant à un autre. Le plugin prend l'élève dans la session RBAC, jamais dans les arguments ; les tests des phases 3 bis et 4 le vérifient.
- Concurrence : Un mutex par élève sérialise les appels au domaine. Deux onglets du même enfant partagent la même séance, comme aujourd'hui.
- ADR pragma : `Hexagonal`, `PluginConventions`, `Angular`, `tests` s'appliquent aux nouveaux plugins et à l'application. Le dépôt tuteur garde ses propres conventions (hors lab).
- Équivalence du portage : Un écart entre C++ et Python change les exercices ou les corrections sans signal visible. Le corpus de référence et ctest le détectent ; une phase sans concordance de 100 % bloque la suivante.
- Volume : Environ 3 700 lignes de Python et 102 fonctions de test à porter. `generateurs.py` (984 lignes) concentre le risque.
