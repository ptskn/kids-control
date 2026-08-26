# kids-control

**Contrôle parental pour le PC Linux d'un enfant** (famille Debian/Ubuntu) — bloque TikTok, les YouTube Shorts et les réseaux sociaux, force SafeSearch et le mode restreint YouTube, filtre les contenus adultes au niveau DNS, et gère le temps d'écran. Uniquement avec des mécanismes système qu'un compte enfant ne peut pas défaire.

*English version: [README.md](README.md)*

## Installer

Une seule commande, sur le PC de l'enfant :

```bash
curl -fsSL https://raw.githubusercontent.com/ptskn/kids-control/main/get.sh | sudo bash
```

Puis redémarrer la session. C'est tout.

Le projet est installé dans `/opt/kids-control`. Relancer la commande le met à jour en **préservant vos listes personnalisées**.

## Ce que ça fait

| Couche | Mécanisme | Bloque |
|---|---|---|
| 1 | Politiques Firefox système (`policies.json`) | TikTok & réseaux sociaux, **YouTube Shorts** (YouTube normal reste accessible), installation d'extensions, DNS-over-HTTPS, `about:config` ; uBlock Origin installé de force (masque l'interface Shorts) ; accueil verrouillé sur [Qwant Junior](https://www.qwantjunior.com/) |
| 2 | `/etc/hosts` | TikTok & réseaux sociaux dans **toutes** les applis ; force **SafeSearch Google** et le **mode restreint YouTube** |
| 3 | DNS familial Cloudflare (`1.1.1.3`) | Contenus adultes + malware, partout |
| 4 | [Timekpr-nExT](https://mjasnik.gitlab.io/timekpr-next/) | Durée quotidienne et plages horaires |
| 5 | Durcissement | Retire les navigateurs alternatifs et `flatpak` (installs sans sudo) |

## Prérequis

- Une distribution de la **famille Debian/Ubuntu** (basée `apt`) : Linux Mint (cible principale, testée), LMDE, Debian, Zorin, Pop!_OS, elementary…
- Firefox installé en **.deb** (le défaut partout dans cette famille, sauf Ubuntu). Avec le **Firefox snap d'Ubuntu**, les politiques de blocage s'appliquent quand même (le snap lit `/etc/firefox/policies`), mais le masquage cosmétique des vignettes Shorts peut ne pas suivre — les liens `/shorts/` directs restent bloqués dans tous les cas.
- L'enfant a son **propre compte sans sudo** — c'est la clé de voûte.
- Pas pour Fedora/Arch/openSUSE sans adaptation (gestionnaire de paquets et chemins Firefox différents).

## Personnaliser

Éditer les listes dans `/opt/kids-control/config/`, puis relancer `sudo /opt/kids-control/install.sh` :

- `blocked-domains.txt` — un domaine par ligne, bloqué partout.
- `blocked-url-patterns.txt` — patterns d'URL bloqués dans Firefox seulement (ex. `*://*.youtube.com/shorts/*`).
- `safesearch-hosts.txt` — entrées SafeSearch (ajoutez votre domaine Google local).
- `firefox-policies.template.json` — page d'accueil verrouillée, etc.

## Temps d'écran

Menu → **Timekpr-nExT (administration)** → compte de l'enfant → durée quotidienne et plages autorisées.

## Vérifier (dans la session de l'enfant)

1. `about:policies` → politiques actives ; `about:addons` → uBlock non désinstallable ; `about:config` bloqué.
2. `tiktok.com` → bloqué ; `getent hosts tiktok.com` → `0.0.0.0`.
3. `youtube.com/shorts/<id>` → bloqué ; accueil YouTube sans étagère/onglet Shorts ; une vidéo normale se lit.
4. Recherche Google d'un terme adulte → SafeSearch verrouillé ; YouTube → mode restreint actif.
5. Réglages Firefox → « DNS via HTTPS » grisé/désactivé.
6. `flatpak` et `chromium` → introuvables ; `sudo` refusé depuis son compte.

## Tout retirer

```bash
sudo /opt/kids-control/uninstall.sh
```

## Limites connues

- Un Firefox « portable » dans son dossier personnel ignorerait les politiques — mais hosts + DNS bloquent toujours TikTok et les contenus adultes.
- Le mode restreint YouTube masque aussi les commentaires.
- SafeSearch n'est forcé que sur Google ; les autres moteurs sont filtrés par le DNS familial.
- Le retrait de `flatpak` peut retirer la Logithèque (`mintinstall`) — réversible : `sudo apt install flatpak mintinstall`.
- Le moteur par défaut de Firefox ne peut être imposé que sur ESR (limitation Mozilla) — d'où la page d'accueil verrouillée.
- Filtrage au niveau du routeur : hors périmètre, recommandé si d'autres appareils arrivent (NextDNS, AdGuard DNS).

## Licence

[MIT](LICENSE)
