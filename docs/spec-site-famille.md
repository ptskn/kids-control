# Spécification : site famille sur pragma

Version 0.2, 17 octobre 2026. Source : `docs/plan-site-famille.md` v0.3 (décisions de la section 4).
Statut des points : Acté (décision client ou constat sur le code), Hypothèse (à confirmer avant la phase concernée).

Changements depuis la v0.1 :

- Acté (client) : aucun Python à l'exécution. Le code Python du Tuteur passe en C++ (plugins) et en Angular (pages).
- Les sections 5.1 et 5.2 (protocole stdio, `tuteur service`, `kid service`) disparaissent.
- Nouvelle section 6 : règles du portage.
- N-1 à N-4, N-6, A-1 à A-5 et A-7 sont réécrits.

## 1. Objet

Le site famille est une application Angular servie par l'instance pragma `famille`.
Il remplace `manager.py` (port 8800), `tuteur/ui/serveur.py` (8801), `api_rapport.py` (8803) et `parent-web/` (4300).
Le plan décrit l'ordre de réalisation. Cette spécification décrit le comportement attendu, les interfaces et les règles du portage.

Le site ne lance aucun processus Python. Le domaine du Tuteur et du chat est porté en C++ dans les plugins. Les pages HTML du Tuteur sont portées en Angular.

Hors périmètre :

- les mécanismes de blocage sur le PC de l'enfant (`install.sh`, uBlock, `/etc/hosts`, Timekpr) ;
- toute évolution du contenu pédagogique : le portage reproduit le catalogue, les générateurs et le correcteur sans les modifier ;
- l'accès public depuis Internet.

## 2. Acteurs et comptes

| Acteur | Compte | Rôle RBAC |
|---|---|---|
| Enfant | un compte RBAC par enfant | `enfant` |
| Parent | un compte RBAC par parent | `parent` |
| Administrateur | compte admin pragma | admin |

- Le nom du compte enfant sert d'identifiant d'élève (`eleve`) dans tous les plugins.
- Un identifiant d'élève respecte `^[a-z][a-z0-9_-]{0,31}$`. Hypothèse : à aligner sur la contrainte RBAC si elle est plus stricte.
- Aucun prénom n'apparaît dans le code, les chemins, les noms de plugins ou les textes fixes. Le prénom affiché vient du profil de l'élève.

## 3. Exigences fonctionnelles

### 3.1 Enfant

| Id | Exigence |
|---|---|
| F-E1 | Après connexion, l'enfant arrive sur `/enfant/seance`. |
| F-E2 | L'enfant voit la liste des thèmes et compétences de son niveau scolaire (`tuteur_themes`). |
| F-E3 | L'enfant démarre une séance, sur un thème choisi ou sur le choix du planificateur (`tuteur_seance`). |
| F-E4 | L'enfant répond à chaque item et reçoit la correction (`tuteur_reponse`). |
| F-E5 | L'enfant demande une aide ou une explication sur un item (`tuteur_aide`, `tuteur_expliquer`). |
| F-E6 | L'enfant termine la séance et voit sa progression (`tuteur_fin`). |
| F-E7 | L'enfant converse avec l'assistant sur `/enfant/chat` (`chat_envoyer`). |
| F-E8 | L'enfant voit la conversation en cours et peut en commencer une nouvelle (`chat_historique`, `chat_reset`). |
| F-E9 | Le thème visuel choisi par l'enfant est conservé entre deux connexions. |

### 3.2 Parent

| Id | Exigence |
|---|---|
| F-P1 | Après connexion, le parent arrive sur `/parent`. Un sélecteur d'enfant figure sur chaque page parent. |
| F-P2 | Le parent voit l'état du PC de l'enfant choisi : joignable, nombre de filtres, date d'application, Firefox, droits sudo (`kc_status`). |
| F-P3 | Le parent lit et modifie les trois listes : chaînes, domaines, motifs d'URL (`kc_list_get`, `kc_list_save`). |
| F-P4 | Le parent applique les listes sur le PC (`kc_apply`) et voit la sortie de `install.sh`. |
| F-P5 | Le parent lit et modifie le temps d'écran : jours, limites, plage horaire, bonus (`kc_screen_*`). |
| F-P6 | Le parent voit le rapport sur une période, par pas et par discipline (`tuteur_rapport`). |
| F-P7 | Le parent voit le bilan des 14 derniers jours (`tuteur_bilan`). |
| F-P8 | Le parent lit et modifie le profil de l'élève : prénom affiché, âge, classe, niveaux, consignes (`tuteur_profil_get`, `tuteur_profil_set`). |
| F-P9 | Le parent lit l'historique complet du chat de l'enfant, en lecture seule (`chat_journal`). |
| F-P10 | Le parent associe chaque enfant à un hôte SSH et à un utilisateur Linux (`kc_host_get`, `kc_host_set`). |

### 3.3 Administration

| Id | Exigence |
|---|---|
| F-A1 | L'ajout d'un enfant suit trois étapes : créer le compte, lui donner le rôle `enfant`, renseigner hôte et profil. Aucune modification de code. |
| F-A2 | Les rôles sont versionnés dans `pragma-workspace/Famille/team/rbac/roles.json`. |
| F-A3 | `tuteur_verifier` contrôle le catalogue chargé (port de `tuteur verifier`). Réservé au rôle `parent`. |

## 4. Exigences de sécurité

| Id | Exigence |
|---|---|
| S-1 | Le rôle `enfant` reçoit `TuteurPlugin` et `KidChatPlugin`, et aucun autre plugin. |
| S-2 | Le rôle `enfant` ne reçoit jamais `AssistantPlugin`, `BashPlugin`, ni un plugin d'exécution ou de fichiers. |
| S-3 | Tout appel à `claude` issu du site passe par le module `Protection` de `famille_commun` (port de `protection.py`) : prompt système de `prompt_tuteur` ou `prompt_assistant`, et `--disallowed-tools` suivi de chaque entrée de `OUTILS_INTERDITS`. |
| S-4 | Pour un appelant de rôle `enfant`, le plugin lit l'élève dans la session RBAC. Un argument `enfant` fourni par la page est refusé. |
| S-5 | Pour un appelant de rôle `parent`, l'argument `enfant` est obligatoire et doit désigner un compte de rôle `enfant`. |
| S-6 | La réponse attendue d'un item ne figure dans aucun résultat d'outil tant que l'item n'est pas terminé. Elle figure ensuite dans le résultat de `tuteur_reponse`, comme dans `application.py`. |
| S-7 | `KidsControlPlugin` applique les validations de `manager.py` : `HOST_RE`, `USER_RE`, liste blanche `channels`, `domains`, `patterns`, bornes des valeurs Timekpr. |
| S-8 | `ssh` s'exécute en `BatchMode=yes`. Aucun mot de passe n'est stocké par le plugin. |
| S-9 | Le site écoute sur le réseau local seulement. Le parent accède depuis l'extérieur par VPN. |
| S-10 | Le mot de passe parent n'est jamais mémorisé sur le PC d'un enfant. |
| S-11 | Un sous-processus `claude` s'exécute sans shell (`execvp` sur un tableau d'arguments). Aucun texte de l'enfant n'entre dans la ligne de commande hors de l'argument du message. |

## 5. Interfaces

### 5.1 Domaine du Tuteur

Le domaine expose la classe C++ `tuteur::Application`, port de `tuteur/application.py`. Une instance existe par élève. `TuteurPlugin` les garde en mémoire et les crée à la première requête de l'élève.

| Méthode C++ | Arguments | Python d'origine |
|---|---|---|
| `themes()` | aucun | `Application.themes` |
| `config()` | aucun | bloc `/api/config` de `serveur.py` |
| `demarrerSeance(theme, competence)` | textes, vides permis | `demarrer_seance` |
| `repondre(seanceId, index, reponse, dureeS)` | `dureeS` facultatif | `repondre` |
| `aider(seanceId, index, question)` | | `aider` |
| `expliquer(seanceId, index)` | | `expliquer` |
| `terminer(seanceId)` | | `terminer` |
| `bilan(jours)` | défaut 14 | `bilan` |
| `profilPublic()` | aucun | `profil_public` |
| `modifierProfil(profil)` | objet JSON | `modifier_profil`, sans `code` |
| `rapport(du, au, pas, discipline)` | AAAA-MM-JJ ; `auto`, `jour`, `semaine`, `mois` | `rapport.calculer` ; défaut : 30 derniers jours |
| `verifier()` | aucun | `Catalogue.verifier` |

- Chaque méthode rend un `nlohmann::json` de même structure que le dictionnaire Python : mêmes clés, mêmes types, même ordre des listes.
- `profilPublic()` ne rend plus `code_requis` ni `chemin`. `code_parent` disparaît de la configuration.
- `discuter`, `nouvelle_conversation` et `historique_conversation` ne sont pas portés dans `tuteur::Application`. Le chat relève de `KidChatPlugin` (5.2).
- Les exceptions du domaine suivent la correspondance de 5.4 : `std::invalid_argument` pour `KeyError` et `ValueError`, `tuteur::Interdit` pour `PermissionError`.
- Un mutex par élève sérialise les appels, comme le verrou global de `serveur.py`. Deux élèves ne se bloquent pas.

### 5.2 Domaine du chat

Le domaine expose la classe C++ `kid::Chat`, port de `tuteur/assistant.py` et de la partie conversation de `application.py`.

| Méthode C++ | Arguments | Données rendues |
|---|---|---|
| `envoyer(message)` | texte, 1 à 2000 caractères | `texte`, `erreur` |
| `historique(limite)` | défaut 40 | `messages` depuis la dernière coupure « nouvelle conversation » |
| `reset()` | aucun | `ok` |
| `journal(du, au, limite)` | `du`, `au` facultatifs ; `limite` défaut 500 | `messages` complets, coupures comprises |

- Un message est `{"role": "enfant" | "assistant" | "systeme", "texte", "erreur", "horodatage"}`.
- `envoyer` reprend la logique de `Assistant.repondre` : `--resume <session_id>` si une session existe ; en cas d'échec de reprise, un second essai sans session ; `MESSAGE_DELAI` après 90 s ; `MESSAGE_PANNE` sur code retour non nul ou sortie non JSON ; `nettoyer_markdown` sur le texte rendu.
- Hypothèse : la limite de 2000 caractères de `message`. À confirmer en phase P4.

### 5.3 Outils MCP

Convention : `enfant` désigne l'argument obligatoire pour le rôle `parent` et refusé pour le rôle `enfant` (S-4, S-5).

| Plugin | Outil | Arguments | Appel |
|---|---|---|---|
| `TuteurPlugin` | `tuteur_themes` | `enfant` | `themes` |
| | `tuteur_config` | `enfant` | `config` |
| | `tuteur_seance` | `enfant`, `theme`, `competence` | `demarrerSeance` |
| | `tuteur_reponse` | `enfant`, `seance_id`, `index`, `reponse`, `duree_s` | `repondre` |
| | `tuteur_aide` | `enfant`, `seance_id`, `index`, `question` | `aider` |
| | `tuteur_expliquer` | `enfant`, `seance_id`, `index` | `expliquer` |
| | `tuteur_fin` | `enfant`, `seance_id` | `terminer` |
| `TuteurParentPlugin` | `tuteur_rapport` | `enfant`, `du`, `au`, `pas`, `discipline` | `rapport` |
| | `tuteur_bilan` | `enfant`, `jours` | `bilan` |
| | `tuteur_profil_get` | `enfant` | `profilPublic` |
| | `tuteur_profil_set` | `enfant`, `profil` | `modifierProfil` |
| | `tuteur_verifier` | aucun | `verifier` |
| `KidChatPlugin` | `chat_envoyer` | `enfant`, `message` | `envoyer` |
| | `chat_historique` | `enfant`, `limite` | `historique` |
| | `chat_reset` | `enfant` | `reset` |
| `KidChatParentPlugin` | `chat_journal` | `enfant`, `du`, `au`, `limite` | `journal` |
| `KidsControlPlugin` | `kc_status` | `enfant` | `STATUS_SCRIPT` par `ssh bash -s` |
| | `kc_list_get` | `enfant`, `liste` (`channels`, `domains`, `patterns`) | `cat` du fichier |
| | `kc_list_save` | `enfant`, `liste`, `contenu` | `cat >` du fichier, saut de ligne final ajouté |
| | `kc_apply` | `enfant` | `sudo -n /opt/kids-control/install.sh`, délai 300 s |
| | `kc_host_get` | `enfant` | lecture de l'association enfant → hôte |
| | `kc_host_set` | `enfant`, `hote`, `utilisateur` | écriture de l'association |
| | `kc_screen_users` | `enfant` | comptes UID 1000 à 59999 du PC |
| | `kc_screen_info` | `enfant` | `timekpra --userinfo` |
| | `kc_screen_schedule` | `enfant`, `jours`, `limites`, `heure_debut`, `heure_fin` | `timekpra --setalloweddays`, `--settimelimits`, `--setallowedhours` |
| | `kc_screen_bonus` | `enfant`, `operation` (`+`, `-`), `secondes` (1 à 14400) | `timekpra --settimeleft` |

- `TuteurParentPlugin` résout `TuteurPlugin` par `IPluginResolver` et appelle les mêmes instances `tuteur::Application`. `KidChatParentPlugin` résout `KidChatPlugin` de la même façon.
- L'utilisateur Linux visé par `kc_screen_*` est celui associé à l'enfant (`kc_host_set`). Il n'est pas passé en argument.
- Bornes de `kc_screen_schedule` (reprises de `api_tk_schedule`) : `jours` triés, uniques, entre 1 et 7 ; une limite par jour, entre 0 et 86400 s ; `0 <= heure_debut < heure_fin <= 24`.

### 5.4 Erreurs des outils

Un outil en erreur rend un résultat d'outil en erreur, avec un code et un message.

| Code | Cas | Équivalent HTTP de `serveur.py` |
|---|---|---|
| `requete` | `enfant` absent, invalide ou interdit pour le rôle (S-4, S-5) | 400 / 404 |
| `argument` | argument manquant ou hors bornes, `seance_id` ou `index` inconnu | 400 |
| `interdit` | opération refusée par le domaine | 403 |
| `distant` | échec `ssh` (code retour, délai) | aucun |
| `interne` | toute autre exception | 500 |

### 5.5 Configuration des plugins

| Plugin | Clé | Contenu |
|---|---|---|
| `TuteurPlugin` | `racineDonnees` | répertoire des données par élève |
| | `catalogue` | répertoire des fichiers TOML du catalogue ; défaut : `share/catalogue` installé avec le plugin |
| | `ia` | `auto`, `claude-cli` ou `hors-ligne` ; défaut `auto` |
| | `modele` | modèle `claude` du Tuteur ; défaut `claude-sonnet-5` |
| | `nbItems` | items par séance ; défaut 12 |
| | `commandeClaude` | chemin de `claude` ; défaut : recherche dans `PATH` puis `~/.local/bin` |
| `KidChatPlugin` | `racineDonnees` | répertoire des historiques par élève |
| | `modele` | modèle `claude` du chat ; défaut `sonnet` |
| | `commandeClaude` | comme pour `TuteurPlugin` |
| `KidsControlPlugin` | `enfants` | objet `{ "<compte>": { "hote": "user@host", "utilisateur": "<login>" } }` |

- Les variables `TUTEUR_*` et `~/.config/tuteur/config.toml` ne sont pas lues par les plugins.
- Conformément à ADR-0019, une valeur absente s'exprime par l'absence de la clé, jamais par `null`.

## 6. Portage Python → C++ et Angular

### 6.1 Règles

- Acté (client) : aucun processus Python à l'exécution, ni dans les plugins, ni sur le serveur `famille`.
- La référence du comportement est le dépôt tuteur au commit `72bfb48`.
- À entrée égale, le C++ rend la même sortie que le Python : même exercice, même correction, même planification, même rapport, même commande `claude`.
- Le Python de référence s'exécute une seule fois, en phase P0, pour produire le corpus de référence (6.6). Le corpus est versionné. Les tests C++ ne lancent pas Python.
- Le contenu pédagogique ne change pas pendant le portage. Toute évolution attend la fin de la phase 7 du plan.

### 6.2 Organisation du code

Emplacement : `/home/ptskn/Desktop/code/WebSites/pragma-workspace/Famille/`.

```
Famille/
  commun/               bibliothèque statique famille_commun
    protection/         OUTILS_INTERDITS, bloc_identite, prompt_tuteur, prompt_assistant
    profil/             Profil, lecture et écriture de profil.json
    claude/             construction de la commande claude, exécution avec délai
    texte/              normalisation Unicode, fmt, dates ISO
    pyrandom/           générateur compatible random.Random de CPython
  TuteurPlugin/
    domain/             domaine, catalogue, generateurs, correcteur, planificateur,
                        rapport, application, ports IJournal et ITuteurIA
    adapters/           SqliteJournal, ClaudeCliTuteur, HorsLigneTuteur, TomlCatalogue
    tools/              outils tuteur_*
    share/catalogue/    francais.toml, mathematiques.toml, themes.toml (copie de 72bfb48)
    tests/              ctest, dont corpus/
  TuteurParentPlugin/
  KidChatPlugin/
    domain/             Chat, port IChatStore
    adapters/           SqliteChatStore
    tools/
  KidChatParentPlugin/
  KidsControlPlugin/
  team/rbac/roles.json
```

- Les plugins suivent les ADR pragma `Hexagonal`, `PluginConventions` et `tests`.
- `domain/` ne dépend ni de SQLite, ni de la bibliothèque TOML, ni de `claude`. Ces dépendances restent dans `adapters/`.

### 6.3 Correspondance des modules C++

| Python (72bfb48) | Lignes | Cible C++ | Point d'équivalence |
|---|---|---|---|
| `domaine.py` | 181 | `TuteurPlugin/domain/domaine` | `NIVEAUX`, `fenetre_niveaux`, boîtes de Leitner, `StrEnum` → `enum class` avec conversion texte |
| `profil.py` | 107 | `commun/profil` | format de `profil.json` inchangé |
| `protection.py` | 84 | `commun/protection` | textes des prompts identiques à l'octet près ; `OUTILS_INTERDITS` identique |
| `config.py` | 73 | supprimé | remplacé par la configuration des plugins (5.5) |
| `contenu/chargeur.py` | 198 | `domain/catalogue` + `adapters/TomlCatalogue` | mêmes messages de `verifier`, même détection des cycles de prérequis |
| `generateurs.py` | 984 | `domain/generateurs` | registre par nom ; même `id` `nom:graine:difficulte` ; voir 6.5 |
| `correcteur.py` | 112 | `domain/correcteur` | normalisation Unicode et expressions régulières, voir 6.5 |
| `planificateur.py` | 304 | `domain/planificateur` | même suite de tirages `PyRandom` |
| `journal.py` | 237 | `adapters/SqliteJournal` | schéma SQLite inchangé, migration `choix` comprise |
| `rapport.py` | 312 | `domain/rapport` | lecture par `IJournal` ; mêmes clés de période (`_cle`) |
| `ia.py` | 229 | `domain/ITuteurIA` + `adapters/ClaudeCliTuteur`, `HorsLigneTuteur` | délai 40 s ; repli hors ligne sur toute panne ; `TuteurAnthropic` non porté |
| `assistant.py` | 122 | `KidChatPlugin/domain/Chat` + `commun/claude` | délai 90 s ; second essai sans session ; `nettoyer_markdown` |
| `application.py` | 478 | `domain/application` | une instance par élève ; partie conversation déplacée dans `Chat` |
| `ui/serveur.py` | 132 | `tools/` des plugins | routes `/api/*` → outils MCP |
| `ui/api_rapport.py` | 72 | `TuteurParentPlugin/tools/tuteur_rapport` | |
| `__main__.py` | 247 | supprimé | `verifier` → `tuteur_verifier` ; `bilan`, `rapport`, `profil` → outils parent ; `lancer`, `console` non portés |
| `manager.py` (kids_control) | 530 | `KidsControlPlugin` | `STATUS_SCRIPT` repris à l'octet près |

### 6.4 Correspondance des interfaces Angular

Application `famille` du monorepo `mcp-clients`, consommatrice de `mcp-web-core`.

| Source | Lignes | Cible Angular | Transport |
|---|---|---|---|
| `tuteur/ui/enfant.html`, onglet séance | 384 (fichier entier) | `enfant/seance/` | `tuteur_seance`, `tuteur_reponse`, `tuteur_aide`, `tuteur_expliquer`, `tuteur_fin` |
| `tuteur/ui/enfant.html`, choix de thème | | `enfant/themes/` | `tuteur_themes` |
| `tuteur/ui/enfant.html`, onglet « Mon assistant » | | `enfant/chat/` | `chat_envoyer`, `chat_historique`, `chat_reset` |
| `tuteur/ui/enfant.html`, thèmes visuels | | service `ThemeVisuel` | stockage local du navigateur, par compte (F-E9) |
| `tuteur/ui/bilan.html`, bilan | 137 (fichier entier) | `parent/bilan/` | `tuteur_bilan` |
| `tuteur/ui/bilan.html`, profil | | `parent/profil/` | `tuteur_profil_get`, `tuteur_profil_set` |
| `parent-web/src/app/` (`app`, `modele`, `graphe`, `options`, `dates`) | ~840 | `parent/rapport/` | `tuteur_rapport` à la place de `GET /api/rapport` |
| `manager.py`, page HTML embarquée | | `parent/protections/`, `parent/temps-ecran/` | outils `kc_*` |
| aucune | | `parent/chat/` | `chat_journal` |

- Le code JavaScript inline de `enfant.html` et `bilan.html` passe en TypeScript strict, en composants autonomes.
- `parent-web` est déjà en Angular : seuls `rapport.service.ts` et le composant racine changent.
- Les textes affichés à l'enfant sont repris à l'identique.

### 6.5 Points d'équivalence

Générateur pseudo-aléatoire. `commun/pyrandom` reproduit `random.Random` de CPython 3.12 et 3.13 :

- Graine texte (`random.Random(f"{nom}:{graine}:{difficulte}")`, version 2) : entier = octets UTF-8 du texte suivis de leur SHA-512, lus en grand-boutiste. L'entier alimente `init_by_array` de MT19937, mots de 32 bits de poids faible en premier.
- `random()` : `(a >> 5) * 67108864 + (b >> 6)`, divisé par 2^53.
- `getrandbits(k)` pour k ≤ 32 : tirage 32 bits décalé de `32 - k`.
- `_randbelow(n)` : `k = bit_length(n)`, tirage `getrandbits(k)` répété tant que le résultat est ≥ n.
- `randrange(n)`, `randint(a, b)`, `choice`, `shuffle` (indice décroissant, `_randbelow(i + 1)`) et `sample` (méthode « pool » pour les petites populations) suivent l'implémentation de CPython.
- Méthodes utilisées par le Tuteur : `randint` (81 appels), `choice` (33), `random` (7), `shuffle` (4), `randrange` (2), `sample` (1). Les autres méthodes ne sont pas portées.

Une graine identique produit donc le même exercice en Python et en C++. Les identifiants d'exercice déjà présents dans le journal restent rejouables.

Texte et nombres :

- `fmt` : séparateur de milliers et virgule décimale identiques ; arrondi `%.2f` de `snprintf`, identique à `f"{n:.2f}"` sur la même valeur binaire.
- `sans_accents` (NFD puis retrait des marques `Mn`) et `str.lower()` : Hypothèse, table de correspondance explicite pour U+00C0 à U+017F et `œ`, `æ`, sans ICU. Le corpus de référence couvre tous les caractères du catalogue.
- Expressions régulières de `correcteur.py` et `nettoyer_markdown` : portées en `std::regex` ECMAScript sur du texte UTF-8. La classe `[a-zà-ÿ€%°]` devient une liste explicite de points de code.
- Dates : `date.isoformat()` et `datetime.now().isoformat(timespec="seconds")` en heure locale, format inchangé.

Données :

- Journal : le C++ ouvre un `journal.sqlite` produit par le Python sans migration, et le Python ouvre un journal écrit par le C++. Bibliothèque `libsqlite3` du système.
- Catalogue : les fichiers TOML de `72bfb48` sont repris sans modification. Hypothèse : bibliothèque `toml++` en en-têtes seuls, copiée dans `commun/third_party/`.
- JSON : `nlohmann::json` du SDK pragma. Comparaison des sorties : structurelle, flottants à 1e-9 près.

Commande `claude` :

- Tableau d'arguments identique à celui de `ia.py` et `assistant.py`, dans le même ordre. `--disallowed-tools` reste le dernier argument, suivi de `OUTILS_INTERDITS`.
- Répertoire courant : répertoire personnel du compte du serveur. `PATH` complété par `~/.local/bin`.

### 6.6 Corpus de référence et tests

Corpus de référence (`TuteurPlugin/tests/corpus/`, JSON versionnés), produit en phase P0 par un script lancé une fois dans le dépôt tuteur à `72bfb48` :

| Fichier | Contenu |
|---|---|
| `generateurs.json` | pour chaque modèle du catalogue, difficultés 1 à 3, graines 0 à 199 : champs de l'`Exercice` |
| `pyrandom.json` | pour 50 graines texte : 1000 sorties de chaque méthode de 6.5 |
| `correcteur.json` | pour chaque exercice de `generateurs.json` : réponse attendue, 5 variantes, `Resultat` |
| `planificateur.json` | 30 états de maîtrise × 3 graines × dates fixes : liste des items et motifs |
| `rapport.json` | 2 journaux de test × pas `jour`, `semaine`, `mois`, `auto` : sortie de `calculer` |
| `application.json` | 5 séances scriptées en mode `hors-ligne` : suite des appels et des réponses |
| `claude_argv.json` | commandes construites pour le Tuteur et le chat, avec et sans session |
| `journaux/*.sqlite` | journaux de test lus par `rapport.json` et par le test de compatibilité |

Correspondance des tests Python (102 fonctions de test) :

| Test Python | Test ctest |
|---|---|
| `test_domaine.py` | `domaine_test` |
| `test_profil.py` | `profil_test` |
| `test_protection.py` | `protection_test` |
| `test_contenu.py` | `catalogue_test` |
| `test_generateurs.py` | `generateurs_test` + comparaison à `generateurs.json` |
| `test_correcteur.py` | `correcteur_test` + comparaison à `correcteur.json` |
| `test_planificateur.py` | `planificateur_test` + comparaison à `planificateur.json` |
| `test_journal.py` | `journal_test` + ouverture des `journaux/*.sqlite` |
| `test_rapport.py` | `rapport_test` + comparaison à `rapport.json` |
| `test_ia.py` | `ia_test` + comparaison à `claude_argv.json` |
| `test_assistant.py` | `KidChatPlugin` `chat_test` |
| `test_application.py` | `application_test` + rejeu de `application.json` |
| `parent-web/src/app/*.spec.ts` | specs Angular de `parent/rapport/` |

- Chaque assertion d'un test Python a son équivalent dans le test ctest correspondant.
- Les tests qui lancent `claude` utilisent un faux exécutable `claude` placé dans `PATH` par le test.

### 6.7 Ordre du portage

| Phase | Contenu | Dépend de |
|---|---|---|
| P0 | Script du corpus de référence, exécuté à `72bfb48` ; corpus versionné | aucune |
| P1 | `commun/` : `pyrandom`, `texte`, `protection`, `profil`, `claude` | P0 |
| P2 | `domaine`, `catalogue` + `TomlCatalogue` | P1 |
| P3 | `generateurs`, `correcteur` | P2 |
| P4 | `KidChatPlugin` domaine + `SqliteChatStore` | P1 |
| P5 | `planificateur`, `SqliteJournal`, `rapport` | P3 |
| P6 | `ITuteurIA`, `application` | P5 |
| P7 | outils MCP des quatre plugins Tuteur et chat | P4, P6 |
| P8 | application Angular `famille` | P7 et `KidsControlPlugin` |

- `KidsControlPlugin` ne dépend que du SDK. Son portage avance en parallèle de P1 à P7.
- Une phase se termine quand ses tests ctest passent et que ses fichiers du corpus concordent.

### 6.8 Retraits

Après la phase 7 du plan, les éléments suivants quittent l'usage :

- le paquet `tuteur/`, `tests/`, `pyproject.toml`, `tuteur/ui/`, `parent-web/`, `deploy/rapport-parent.sh` du dépôt tuteur ;
- `manager.py` du dépôt kids_control ;
- le dossier `/mnt/hdd2to/kid/` comme dépôt Python du chat (point ouvert, section 10).

## 7. Données

| Donnée | Emplacement | Propriétaire |
|---|---|---|
| Journal des séances | `<racineDonnees tuteur>/<eleve>/journal.sqlite` | `TuteurPlugin` |
| Profil de l'élève | `<racineDonnees tuteur>/<eleve>/profil.json` | `TuteurPlugin` |
| Historique du chat et session `claude` | `<racineDonnees kid>/<eleve>/chat.sqlite` | `KidChatPlugin` |
| Catalogue | `<catalogue>/*.toml` | `TuteurPlugin`, lecture seule |
| Association enfant → hôte | configuration de `KidsControlPlugin` | `KidsControlPlugin` |
| Comptes et rôles | base RBAC de l'instance `famille` | `RBACPlugin` |

- Hypothèse : l'arborescence `<racine>/<eleve>/`. À confirmer en phase P5.
- Le plugin crée le répertoire d'un élève à sa première requête.
- Le schéma de `journal.sqlite` est celui de `journal.py` à `72bfb48`, sans changement.
- Migration (phase 7 du plan) : le journal et le profil actuels du PC de l'enfant vont sous le compte de cet enfant. L'historique de chat actuel (table `conversation` du journal du Tuteur) va dans `chat.sqlite`.

## 8. Exigences non fonctionnelles

| Id | Exigence |
|---|---|
| N-1 | Aucun processus Python sur le serveur `famille`. Les seuls sous-processus des plugins sont `claude` et `ssh`. |
| N-2 | Les séances en cours vivent dans la mémoire de `TuteurPlugin`. Un redémarrage de l'instance les perd, comme un redémarrage de `serveur.py`. |
| N-3 | Les plugins n'ouvrent aucun port réseau. |
| N-4 | Délais maximaux des sous-processus : 40 s pour `claude` côté Tuteur, 90 s côté chat, 300 s pour `kc_apply`. Hypothèse : 15 s pour les autres appels `ssh`. |
| N-5 | Les plugins suivent les ADR pragma `Hexagonal`, `PluginConventions`, `tests`. L'application suit l'ADR `Angular`. |
| N-6 | Le domaine du Tuteur et du chat est en C++, dans `domain/` des plugins et dans `famille_commun`. Aucune logique pédagogique dans `tools/` ni dans Angular. |
| N-7 | Le temps de réponse de `tuteur_seance`, `tuteur_reponse` et `tuteur_rapport` sur 1 an de journal reste sous 200 ms, hors appel `claude`. |

## 9. Critères d'acceptation

| Id | Vérification | Exigences |
|---|---|---|
| A-1 | ctest `pyrandom_test` : les 50 × 1000 sorties concordent avec `pyrandom.json`. | 6.5 |
| A-2 | ctest `generateurs_test` et `correcteur_test` : 100 % de concordance avec `generateurs.json` et `correcteur.json`. | 6.1, 6.5 |
| A-3 | ctest `planificateur_test`, `rapport_test`, `application_test` : concordance avec les fichiers du corpus. | 6.1, F-E3 à F-E6, F-P6, F-P7 |
| A-4 | ctest `journal_test` : le C++ lit les journaux Python du corpus ; un journal écrit par le C++ passe `PRAGMA integrity_check` et garde le schéma de `journal.py`. | 7 |
| A-5 | ctest `ia_test`, `chat_test` : chaque commande `claude` construite se termine par `--disallowed-tools` suivi de chaque entrée de `OUTILS_INTERDITS`, et concorde avec `claude_argv.json`. | S-3, S-11 |
| A-6 | ctest `TuteurPlugin` : un appelant `enfant` qui passe `enfant` en argument reçoit une erreur `requete`. | S-4 |
| A-7 | ctest `TuteurPlugin` : aucun résultat de `tuteur_seance` ne contient la réponse attendue d'un item ; deux élèves ont des séances et des journaux séparés. | S-6, S-4 |
| A-8 | ctest `KidsControlPlugin` : hôte, utilisateur et liste hors motif refusés, sans appel à `IRemoteHost`. | S-7 |
| A-9 | Instance `famille`, compte `enfant` : `kc_status`, `tuteur_profil_set`, `chat_journal` et `AssistantPlugin` sont refusés par RBAC. | S-1, S-2 |
| A-10 | Instance `famille`, deux comptes `enfant` : aucun ne lit le journal, le profil ou le chat de l'autre. | S-4 |
| A-11 | Instance `famille`, compte `parent` : chaque outil des cinq plugins répond pour chacun des deux enfants. | F-P1 à F-P10, S-5 |
| A-12 | `kc_status` sur le PC réel de l'enfant rend `reachable=true`. | F-P2 |
| A-13 | Playwright : le compte `enfant` arrive sur `/enfant/seance` ; chaque route `/parent/*` le redirige. | F-E1, S-1 |
| A-14 | Après la phase 7 du plan, aucun processus n'écoute sur 8800, 8801, 8803, 4300. | 1 |
| A-15 | Sur le serveur `famille` en service, `pgrep -a python` ne liste aucun processus lancé par pragma. | N-1 |
| A-16 | `nm -C` sur les bibliothèques des plugins : aucune dépendance à `libpython`. | N-1 |

## 10. Points ouverts

| Point | Phase |
|---|---|
| Format exact de l'identifiant d'élève imposé par RBAC (section 2). | P5 |
| Arborescence des données par élève (section 7). | P5 |
| Bibliothèque TOML : `toml++` copiée dans le dépôt, ou conversion unique du catalogue en JSON (6.5). | P2 |
| Normalisation Unicode : table explicite ou dépendance ICU (6.5). | P1 |
| Colonnes nullables héritées du journal (`fin`, `duree_s`, `derniere_revision`, `erreur`, `valeur`) face à ADR-0019 : exception documentée ou valeurs par défaut. Un changement casse la compatibilité de A-4. | P5 |
| Abandon de `TuteurAnthropic` (`ia = "anthropic-api"`). | P6 |
| Longueur maximale d'un message de chat (5.2). | P4 |
| Délai des appels `ssh` hors `kc_apply` (N-4). | P7 |
| Devenir du dossier `/mnt/hdd2to/kid/` : il n'est plus le dépôt Python du chat. | P4 |
| Réservation de 9050 et 9051 dans `pragma/PORTS.md` (hors workspace, accord client attendu). | 0 |
