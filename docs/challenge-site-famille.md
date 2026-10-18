# Revues / Challenge de la spec site famille

Objet : `specs/site-famille.md` v1.0, commit `d6b8545`.
Méthode : relecture de chaque exigence, puis confrontation des impacts code aux fichiers réels le 18 octobre 2026.
Verdict : FAIL. La spec ne peut pas engager le développement de T-15, T-16, T-18 à T-22 et T-26 en l'état.

## 1. Constats confirmés

Les faits suivants sont exacts dans les sources :

- `manager.py` : 530 lignes ; constantes aux lignes 28-52 ; options `ssh` en ligne 79 ; délais 20 s (l. 89), 300 s (l. 117), 30 s (l. 123), 60 s (l. 74).
- Bornes de SP-37 : identiques à `api_tk_schedule` (l. 152-178) et `api_tk_bonus` (l. 180-186).
- Clés de SP-36 : les huit clés de `STATUS_SCRIPT` plus `host` et `error` ajoutées par `api_status` (l. 90).
- Dépôt tuteur : HEAD `72bfb48`, 12 fichiers `test_*.py`, `generateurs.py` de 984 lignes.
- Délais `claude` de SP-52 : 40 s (`ia.py:113`) et 90 s (`assistant.py:31`) ; `MESSAGE_DELAI` existe (`assistant.py:44`).
- `mcp-web-core` fournit `authGuard`, `adminGuard`, `pluginGuard` et `AppShellComponent`.

## 2. Écarts bloquants

1. **Rôle de l'appelant non calculable.** SP-4, SP-5 et CA-4 reposent sur « appelant de rôle `enfant` » et « compte de rôle `enfant` ». `IRbacService.h` (lignes 28-50) expose `getSessionUser`, `canAccessPlugin`, `getAccessiblePlugins` et `isAdmin`, mais aucune lecture des rôles d'un compte. Correction : définir la règle exacte. Exemple : « enfant = compte sans accès à `TuteurParentPlugin` » et « compte enfant valide = clé de `enfants` dans la configuration ». Ajouter cette dépendance SDK en section 5.

2. **Répartition des outils entre plugins absente.** La spec canonique ne dit pas quel outil appartient à quel plugin. CA-2 suppose `tuteur_profil_set` et `chat_journal` hors des plugins enfant, sans l'écrire. SP-3 donne `TuteurPlugin` au parent, mais SP-4 et SP-5 ne disent pas ce que rend `tuteur_seance` appelé par un parent. Correction : ajouter une table « outil | plugin | rôles | argument `enfant` (interdit, obligatoire) ».

3. **SP-1 contredit le client Angular.** `rbac.facade.ts` appelle `rbac_login` (l. 56), `rbac_my_permissions` (l. 90) et `rbac_my_roles` (l. 97). Un rôle `enfant` qui ne reçoit « aucun autre plugin » ne peut pas se connecter si ces outils sont soumis aux permissions. `isRbacTool` suggère une exemption, sans preuve dans la spec. Correction : citer l'exemption des outils RBAC dans SP-1. Indiquer aussi l'accès par défaut d'un plugin absent de `roles.json` (`onNewPluginDiscovered`).

4. **Codes d'erreur non définis et contradictoires.** La spec emploie `requete`, `argument` et `distant` sans les définir. Leur définition est en section 5.4 de `docs/spec-site-famille.md`, non citée. CA-8 attend `argument` pour un hôte invalide ; SP-31 ne donne aucun code. Correction : recopier la table des codes et fixer le code de chaque refus de SP-31 et SP-32.

5. **SP-14 sans support.** Aucun outil ni champ ne conserve le thème visuel : SP-11 à SP-13 et SP-21 n'en parlent pas. Le test e2e ne sait pas quel état contrôler. Correction : nommer le champ de profil ou l'outil qui stocke ce choix.

6. **SP-55 non exécutable.** La spec ne donne pas l'emplacement actuel du journal et du profil sur le PC de l'enfant. Elle ne nomme pas l'outil d'import. Sa machine d'exécution, qui touche SP-47, manque aussi. Le chat garde enfin le `session_id` de `--resume` sur disque (ligne 10 de `assistant.py`). SP-55 ne l'importe pas. Correction : chemins source, outil, machine, et sort du `session_id`.

7. **SP-57 et SP-54 non testables.** L'adresse du site (nom ou IP, port) n'est fixée nulle part. La méthode `e2e` (Playwright contre l'instance) ne s'exécute pas dans la session de l'enfant. SP-54 ne dit ni l'adresse d'écoute, ni le mécanisme qui empêche la mémorisation du mot de passe. Correction : fixer l'URL et l'adresse d'écoute, puis nommer la politique Firefox (`PasswordManager`, `OfferToSaveLogins`) et sa vérification.

8. **Contradiction de périmètre sur Firefox.** La section 2.2 exclut les politiques Firefox (« seule leur commande à distance change »). La section 5.1 modifie `config/firefox-policies.template.json` pour la page d'accueil. SP-54 exige aussi une nouvelle politique. Correction : sortir les politiques Firefox du hors-périmètre ou retirer ces changements.

## 3. Écarts majeurs

9. **Impacts du dépôt tuteur incomplets.** `deploy/` contient `Mon-Tuteur.desktop`, dont la ligne `Exec` lance `python3 -m tuteur lancer`, ainsi que `install-enfant.sh`, `mettre-a-jour.sh` et `CLAUDE-enfant.md`. La spec ne cite que `rapport-parent.sh` (T-28). Correction : dire le sort de chaque fichier ; T-25 remplace le raccourci `Mon-Tuteur.desktop`.

10. **Chemins faux en section 5.3.** `deployments.json` n'est pas dans le dépôt pragma : il est sous `/home/ptskn/Desktop/code/deployed/`. `PORTS.md` est sous `/home/ptskn/Desktop/code/Apps/pragma/`. Correction : chemins absolus.

11. **Modèle CMake absent.** `Puybaret/` n'a pas de `CMakeLists.txt` racine, seulement un par plugin. T-4 crée `Famille/CMakeLists.txt` « sur le modèle Puybaret » sans modèle réel. Correction : citer le fichier modèle exact ou décrire la racine attendue.

12. **Specs Angular surestimées.** La section 5.2 annonce les `.spec.ts` de six fichiers de `parent-web/src/app/`. Seuls `app.spec.ts` et `dates.spec.ts` existent. Correction : lister ces deux fichiers ; T-23 écrit les tests manquants de `graphe.ts`, `options.ts` et `rapport.service.ts`.

13. **SP-51 sans jeu de données.** « Un journal d'un an » ne fixe pas le nombre de séances ni de réponses. La machine et le percentile manquent aussi. Correction : décrire la fixture générée et la mesure (exemple : p95 sur 100 appels).

14. **SP-49 sans procédure.** La méthode `cmd` ne dit pas comment prouver que les plugins lancent seulement `claude` et `ssh`. Correction : `strace -f -e trace=execve` pendant le scénario de CA-13, ou un test ctest sur les adaptateurs.

## 4. Écarts mineurs

15. **SP-2 non vérifiable.** « Un plugin d'exécution ou de fichiers » est une classe ouverte ; un appel `inst` ne la parcourt pas. SP-1 couvre déjà le besoin. Correction : fermer la liste ou supprimer la clause.

16. **Référence de SP-26 hors corpus.** T-2 et T-3 ne listent aucun fichier de référence pour les prompts. Correction : ajouter les prompts au corpus (exemple : `prompts.json`).

17. **SP-30 introduit un comportement.** La limite de 2000 caractères n'existe pas dans `assistant.py`. Correction : la marquer comme nouvelle, hors équivalence du portage.

18. **SP-10 et CA-1 sans cible.** « Redirigé hors de cette route » ne dit pas la destination. Correction : écrire `/enfant/seance`.

19. **SP-15 ambigu.** Le texte ne dit pas si SP-15 vise aussi les libellés du chat et les nouveaux écrans (sélecteur, connexion). Correction : délimiter les textes repris.
