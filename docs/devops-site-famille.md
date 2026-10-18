# Rapports / DevOps — pipeline site famille

## Contexte

Ce run produit la spec `specs/site-famille.md` (planification). L'application
Angular et les cinq plugins C++ décrits n'existent pas encore. Ils forment les
tâches T-1 à T-28, non entamées.

## Branche et publication

Le dépôt est mono-branche : `main`. Aucune branche `develop` ni branche de run
n'existe ici. Le run commite sur la branche courante `main`.

Le commit `130c6b7` porte la spec validée v1.2. Le fichier sur disque reste
identique à HEAD. Le run ne pousse pas et n'ouvre aucune Pull Request. La
plateforme publie la PR en fin de run.

## Commits du run

Sept commits depuis la base héritée `cd0856e` :

- `ad63a8a` collecte
- `d6b8545` redaction : spec canonique
- `cf0df37` challenge
- `c478d79` redaction : spec v1.1
- `85f6461` memory : identité et registre
- `c9afde4` challenge
- `130c6b7` validation : spec v1.2

## État du build

Aucun descripteur de build n'existe : ni `CMakeLists.txt`, ni `package.json`, ni
`Makefile`. Le build de la plateforme rend « success » sans rien compiler : il
ne trouve aucun dossier `src` à construire.

## État des tests

Aucun dossier de tests n'existe. Contrôles de syntaxe du code hérité :

- `python3 -m py_compile manager.py` : OK.
- `bash -n install.sh get.sh uninstall.sh` : OK.

## Reste à faire côté CI

Le système de build arrive avec T-1 et T-18 :

- un `CMakeLists.txt` par plugin sous `WebSites/pragma-workspace/Famille/` ;
- l'espace de travail Angular pour la page web.

Ajoute alors la cible de build C++ et les tests de caractérisation du portage
(corpus de référence du commit `72bfb48`).

## Working tree

Working tree propre à la fin de l'étape. Le run ne laisse aucun fichier non
commité.
