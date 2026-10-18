# Collecte / Site famille sur pragma

Dossier de collecte. Date : 18 octobre 2026. Étape « collecte » du pipeline.
Source de la demande : besoin client collé dans la mission (pas de clé Jira).
But de ce dossier : réunir la matière brute, sans décider ni concevoir.

## 1. Demande

### 1.1 Besoin client (verbatim)

```text
le site web en python, j'aimerais bien qu'au lieu d'être une appli locale,
ça soit un site web angular. avec rbac. donc j'ai bien envie d'en faire un
plugin pragma, et de faire un serveur web dans
/home/ptskn/Desktop/code/WebSites/ qui regroupe kids_control et Tuteur et le
reporting parent. donc en gros qu'un serveur pragma offre rbac et page web
pour enfant et parent en fonction du rôle. fais un plan
```

### 1.2 Reformulation factuelle

Le client demande cinq choses.

| Id | Demande |
|---|---|
| D-1 | Remplacer l'application locale actuelle par un site web Angular. |
| D-2 | Protéger l'accès par RBAC. |
| D-3 | Porter la logique en plugin(s) pragma. |
| D-4 | Héberger le site dans `/home/ptskn/Desktop/code/WebSites/`. |
| D-5 | Regrouper trois domaines : kids_control, Tuteur, reporting parent. |
| D-6 | Servir des pages enfant et parent selon le rôle, via un serveur pragma. |
| D-7 | Produire un plan. |

### 1.3 Livrable demandé

Le client demande un plan (D-7). Ce plan existe déjà dans le workspace.

Le fichier `docs/plan-site-famille.md` porte la version 0.3. La spécification
associée est `docs/spec-site-famille.md`, version 0.2. Les deux documents
couvrent D-1 à D-6.

La demande D-7 porte donc sur la validation ou la mise à jour d'un plan
existant, pas sur une création de zéro.

La note de reprise automatique du run affirme « aucun dossier docs/ et aucune
spec à reprendre ». Ce constat est faux : le dossier `docs/` contient la spec
et le plan ci-dessus.

## 2. Matière disponible

### 2.1 Existant dans ce workspace (kids_control)

| Élément | Fait mesuré |
|---|---|
| `manager.py` | 530 lignes ; interface web locale, standard library Python |
| Liaison réseau | `ThreadingHTTPServer` sur `127.0.0.1`, port `8800` |
| Validation hôte | `HOST_RE = ^[A-Za-z0-9@._:-]+$` (ligne 36) |
| Validation utilisateur | `USER_RE = ^[a-z_][a-z0-9_-]*$` (ligne 37) |
| Transport | `ssh` vers le PC de l'enfant ; `sudo -n install.sh`, délai 300 s |
| Écran | `timekpra` : users, info, schedule, bonus |
| `config/` | 6 fichiers, 135 lignes (listes de blocage, politiques Firefox, uBlock) |
| Scripts | `install.sh`, `uninstall.sh`, `get.sh` ; mode test `KIDS_CONTROL_ROOT` |

`manager.py` ne contient que des appels `ssh`. Aucune logique métier locale.

### 2.2 Spec et plan déjà rédigés (dans `docs/`)

| Fichier | Version | Taille | Portée |
|---|---|---|---|
| `spec-site-famille.md` | 0.2 | 30 Ko | comportement, interfaces, règles de portage |
| `plan-site-famille.md` | 0.3 | 19 Ko | ordre de réalisation en 8 phases |

Ces documents définissent déjà : 5 plugins C++, une application Angular
`famille`, deux rôles RBAC (`enfant`, `parent`), un corpus de référence et
16 critères d'acceptation. Le besoin client est déjà traité par ces documents.

### 2.3 Sources externes référencées (constat d'existence)

Vérification en lecture seule, hors de ce workspace.

| Source | Chemin | État constaté |
|---|---|---|
| Racine web | `/home/ptskn/Desktop/code/WebSites/` | présente |
| Monorepo Angular | `WebSites/mcp-clients/projects/` | présent : `mcp-web-core`, `puybaret` |
| Modèle plugins | `WebSites/pragma-workspace/Puybaret/` | présent |
| Cible plugins | `WebSites/pragma-workspace/Famille/` | absente (à créer) |
| App cible | `mcp-clients/projects/famille/` | absente (à créer) |
| Dépôt Tuteur | `/mnt/hdd2to/im/production/tuteur` | présent ; HEAD = `72bfb48` |
| Commit de référence | `72bfb48` | valide ; égal au HEAD actuel du Tuteur |
| Ancien dépôt chat | `/mnt/hdd2to/kid/` | absent |

### 2.4 Volume de portage (d'après la spec et le plan)

| Donnée | Valeur |
|---|---|
| Lignes de Python du Tuteur | environ 3 700 |
| Fonctions de test Python | 102 |
| Fichiers TOML de catalogue | 3 |
| Fichier le plus lourd | `generateurs.py`, 984 lignes |

## 3. Contraintes

### 3.1 Contraintes client (actées dans le plan v0.3, section 4)

| Id | Contrainte |
|---|---|
| C-1 | Aucun processus Python à l'exécution, ni plugin ni serveur. |
| C-2 | Le Tuteur et le chat passent en C++ (plugins) et Angular (pages). |
| C-3 | Un serveur pragma dédié `famille`, déployé comme les autres instances. |
| C-4 | Connexion par le login RBAC standard de pragma. |
| C-5 | Réseau local seulement. Accès parent hors domicile par VPN. |
| C-6 | Un compte RBAC par enfant. Données propres à chaque compte. |
| C-7 | Le chat `kid` reste une application distincte du Tuteur. |
| C-8 | Le prénom de l'enfant n'apparaît ni dans le code, ni dans les chemins. |

### 3.2 Contraintes de sécurité (spec, section 4)

| Id | Contrainte |
|---|---|
| S-1 | Le rôle `enfant` reçoit `TuteurPlugin` et `KidChatPlugin`, rien d'autre. |
| S-2 | Le rôle `enfant` ne reçoit jamais `AssistantPlugin` ni `BashPlugin`. |
| S-3 | Tout appel `claude` passe par le module `Protection` de `famille_commun`. |
| S-4 | Pour le rôle `enfant`, l'élève vient de la session RBAC, pas des arguments. |
| S-7 | `KidsControlPlugin` reprend les validations de `manager.py`. |
| S-8 | `ssh` s'exécute en `BatchMode=yes`. Aucun mot de passe stocké. |

### 3.3 Contraintes de portage (spec, section 6)

| Id | Contrainte |
|---|---|
| P-1 | À entrée égale, le C++ rend la même sortie que le Python de référence. |
| P-2 | Le générateur C++ reproduit `random.Random` de CPython (exercices rejouables). |
| P-3 | Le schéma SQLite du journal reste inchangé, sans migration. |
| P-4 | Un corpus de référence, produit une fois par le Python, est versionné. |
| P-5 | Le contenu pédagogique ne change pas pendant le portage. |

### 3.4 Contraintes de cadre (ADR et plateforme)

| Id | Contrainte |
|---|---|
| R-1 | Plugins : ADR `Hexagonal`, `PluginConventions`, `tests`. App : ADR `Angular`. |
| R-2 | Une permission RBAC porte sur un plugin entier, pas sur un outil. |
| R-3 | Séparation enfant/parent par plugins distincts (conséquence de R-2). |
| R-4 | ADR-0019 : aucun `null` dans les données ni les catalogues JSON. |
| R-5 | Rédaction des livrables : ADR-0018 et ADR-0020. |

## 4. Inconnues

### 4.1 Points ouverts de la spec (section 10)

| Inconnue | Phase prévue | État à ce jour |
|---|---|---|
| Format exact de l'identifiant d'élève imposé par RBAC | P5 | ouvert |
| Arborescence des données par élève `<racine>/<eleve>/` | P5 | ouvert, hypothèse posée |
| Bibliothèque TOML : `toml++` copiée, ou conversion en JSON | P2 | ouvert |
| Normalisation Unicode : table explicite ou dépendance ICU | P1 | ouvert |
| Colonnes nullables du journal face à ADR-0019 | P5 | ouvert |
| Abandon de `TuteurAnthropic` (`ia = "anthropic-api"`) | P6 | ouvert |
| Longueur maximale d'un message de chat | P4 | ouvert, hypothèse 2000 |
| Délai des appels `ssh` hors `kc_apply` | P7 | ouvert, hypothèse 15 s |
| Réservation des ports 9050 et 9051 dans `pragma/PORTS.md` | 0 | accord client attendu |

### 4.2 Points tranchés par les constats de cette collecte

| Point ouvert initial | Constat |
|---|---|
| Devenir du dossier `/mnt/hdd2to/kid/` | le dossier est absent ; sans objet |
| Existence du commit de référence `72bfb48` | présent ; égal au HEAD du dépôt Tuteur |
| Existence de la racine `WebSites/` et des modèles | présents (`Puybaret`, `mcp-web-core`, `puybaret`) |

### 4.3 Questions non couvertes par la spec

| Inconnue | Raison |
|---|---|
| Nombre d'enfants à gérer à la mise en service | non chiffré dans les documents |
| Hôtes SSH et comptes Linux réels de chaque enfant | hors des documents ; données d'exploitation |
| Ports 9050 et 9051 réellement libres au jour du déploiement | à revérifier avant la phase 4 |

## 5. Synthèse de collecte

- Le besoin client (D-1 à D-7) est déjà couvert par `spec-site-famille.md` v0.2
  et `plan-site-famille.md` v0.3, présents dans ce workspace.
- L'existant à remplacer est `manager.py` (530 lignes, SSH seul) plus les
  interfaces du dépôt Tuteur (`72bfb48`).
- Les sources externes nécessaires au portage existent, sauf les dossiers cibles
  `Famille/` et `famille/`, qui restent à créer.
- Neuf points restent ouverts dans la spec ; les faits en tranchent trois.
- La demande D-7 (« fais un plan ») porte sur un plan qui existe déjà ; l'étape
  suivante statue sur sa validation ou sa mise à jour.
