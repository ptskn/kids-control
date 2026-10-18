# Revues / Challenge de la spec site famille v1.1

Objet : `specs/site-famille.md` v1.1, commit `c478d79`.
Méthode : relecture de chaque exigence, puis confrontation des faits cités aux fichiers réels le 18 octobre 2026.
Verdict : PASS. La spec peut engager les tâches T-1 à T-24. Les écarts 1 à 4 sont à corriger avant T-25 et T-26.

## 1. Corrections de la v1.0 vérifiées

Les 19 écarts de `docs/challenge-site-famille.md` ont une réponse en section 9. Les faits nouveaux sont exacts :

- `McpServer.cpp`, lignes 586-596 : injection de `_username` et `_is_admin`. Le serveur purge ces clés avant : un client ne peut pas les forger.
- `RbacService.h` : `isRbacTool` exempte `rbac_login`, `rbac_my_permissions` et `rbac_my_roles` (SP-3).
- `resolveEffectivePlugins` ne retient que `granted` : RBAC refuse un plugin absent de la carte (SP-2).
- `IPluginResolver` existe dans le SDK et sert déjà entre plugins (`ICompanyInfoProvider.h`).
- `journal.py` contient les tables `etat` et `conversation` ; `application.py:347` définit `CLE_SESSION` (SP-65, SP-66).
- `install-enfant.sh` crée `/var/lib/tuteur/journal.sqlite` et `~/.config/tuteur/profil.json` (section 5.2).
- `deployments.json` contient `abylsen`, `imachine` et `demo`, tous en `0.0.0.0` (SP-61).
- `i-machine` porte `192.168.0.101/24` sur `eno1` et `100.99.206.29/32` sur `tailscale0` (SP-62).
- `install.sh` écrit `/etc/firefox/policies/policies.json` (ligne 18) ; `manager.py` lance `install.sh` à distance en `api_apply` (SP-63).
- Aucun motif de `blocked-url-patterns.txt` ne couvre `192.168.0.101` (SP-69).

## 2. Écarts majeurs (à corriger avant T-25)

1. **Mise à jour de `/opt/kids-control` absente.** `kc_apply` lance `sudo -n /opt/kids-control/install.sh` sur le PC (`manager.py`, ligne 117). Ce script lit la copie installée de `config/`, pas le dépôt. Le nouveau gabarit Firefox et `config/site-famille.desktop` n'arrivent sur le PC que par `get.sh`, qui télécharge la branche `main` de GitHub. Correction : ajouter à T-25 la publication sur `main` puis l'exécution de `get.sh` sur le PC. `get.sh` conserve les quatre listes de blocage (lignes 29-34).

2. **SP-70 rouge à la fin de la tâche T-25.** Cette tâche vérifie SP-70 en entier. Or l'ancien raccourci reste en place jusqu'au retrait. `install-enfant.sh` le pose sur le bureau de l'enfant (`$BUREAU/Mon-Tuteur.desktop`, lignes 85-86). Correction : vérifier la seconde phrase de SP-70 en T-28 seulement.

3. **Deux lanceurs « Mon tuteur » pendant la semaine en parallèle.** Le nouveau lanceur va dans `/usr/share/applications/`, donc dans le menu. L'ancien reste sur le bureau, sous le même nom. CA-19 « clique sur Mon tuteur » ne dit pas lequel. Correction : nommer l'emplacement du nouveau lanceur visé par CA-19, ou lui donner un autre nom pendant T-28.

4. **Chemin source du profil incomplet.** `config.py` lit le profil depuis `TUTEUR_PROFIL`, puis depuis la clé `profil` de `config.toml` (lignes 27 et 62). La section 5.2 ne retient que le chemin par défaut. Correction : en T-26, lire la clé `profil` de `~<utilisateur>/.config/tuteur/config.toml` avant la copie.

## 3. Écarts mineurs

5. **SP-64 copie la session `claude`.** `tuteur_importer` copie `journal.sqlite` entier, donc les tables `etat` et `conversation`. La clé `assistant.session_id` entre ainsi dans les données du Tuteur. La lettre de SP-66 l'exclut. Correction : dire si `tuteur_importer` vide ces deux tables après la copie.

6. **`code_parent` sans sort.** `application.modifier_profil` exige `code_parent` quand la configuration le fixe (lignes 104-107). `tuteur_profil_set` n'a pas d'argument `code`. Correction : écrire que RBAC remplace ce code et exclure ce cas du corpus `application.json`.

7. **Racines de données non fixées.** `<racineDonnees tuteur>` et le répertoire de `chat.sqlite` n'ont pas de valeur par défaut, contrairement à `<racineFamille>` (section 7.2). Correction : ajouter les deux défauts à la table des questions ouvertes.

8. **Relecture du registre non précisée.** SP-11 exige l'ajout d'un enfant sans modification de code. La spec ne dit pas si `TuteurPlugin` et `KidChatPlugin` relisent `enfants.json` à chaque appel. Un registre gardé en mémoire au chargement impose un redémarrage. Correction : fixer la relecture à chaque appel, ou un redémarrage dans SP-11.

9. **`kc_host_set` sans contrôle du compte.** L'outil crée une clé pour toute valeur conforme au motif de SP-7. Aucun compte RBAC n'est exigé. Correction : vérifier le nom dans `rbac_usernames`, ou accepter ce cas dans la table des risques.
