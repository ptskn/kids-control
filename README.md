# kids-control

**Parental controls for a child's Linux computer** (Debian/Ubuntu family) — block TikTok, YouTube Shorts and social networks, force SafeSearch and YouTube Restricted Mode, filter adult content at the DNS level, and manage screen time. All with plain system mechanisms a child account cannot undo.

*Version française : [README.fr.md](README.fr.md)*

## Install

One command, on the child's computer:

```bash
curl -fsSL https://raw.githubusercontent.com/ptskn/kids-control/main/get.sh | sudo bash
```

Then restart the session. That's it.

The project is installed in `/opt/kids-control`. Re-running the command updates it while **preserving your customized blocklists**.

## What it does

| Layer | Mechanism | Blocks |
|---|---|---|
| 1 | System-wide Firefox policies (`policies.json`) | TikTok & social networks, **YouTube Shorts** (regular YouTube stays available), extension installs, DNS-over-HTTPS, `about:config`; force-installs uBlock Origin (hides the Shorts UI); locks the homepage to [Qwant Junior](https://www.qwantjunior.com/) |
| 2 | `/etc/hosts` | TikTok & social networks in **every** app; forces **Google SafeSearch** and **YouTube Restricted Mode** (stable Google IPs) |
| 3 | Cloudflare Family DNS (`1.1.1.3`) via NetworkManager | Adult content + malware, in every app |
| 4 | [Timekpr-nExT](https://mjasnik.gitlab.io/timekpr-next/) | Daily screen-time limits and allowed hours |
| 5 | Hardening | Removes alternative browsers and `flatpak` (which allows no-sudo installs) |

## Requirements

- A **Debian/Ubuntu-family distribution** (`apt`-based): Linux Mint (primary target, tested), LMDE, Debian, Zorin, Pop!_OS, elementary…
- Firefox installed as a **.deb** (the default everywhere in this family except Ubuntu). On **Ubuntu's snap Firefox**, the blocking policies still apply (the snap reads `/etc/firefox/policies`), but the cosmetic hiding of Shorts thumbnails may not — direct `/shorts/` links stay blocked either way.
- The child has their **own non-sudo account**. This is the keystone — without it, everything is bypassable.
- Not for Fedora/Arch/openSUSE without adaptation (package manager and Firefox paths differ).

## Customize

Edit the lists in `/opt/kids-control/config/`, then re-run `sudo /opt/kids-control/install.sh`:

- `blocked-domains.txt` — one domain per line, blocked everywhere (hosts + Firefox).
- `blocked-url-patterns.txt` — URL patterns blocked in Firefox only, to block a *section* of a site (e.g. `*://*.youtube.com/shorts/*`).
- `safesearch-hosts.txt` — SafeSearch entries; add your local Google domain (e.g. `google.de`).
- `firefox-policies.template.json` — change the locked homepage, etc.

Both scripts are idempotent — re-run them as often as you like.

## Screen time

Menu → **Timekpr-nExT (administration)** → select the child's account → set the daily allowance and the allowed hours. The child sees a discreet countdown; the session locks when time is up.

## Verify (in the child's session)

1. Firefox `about:policies` → policies listed as active; `about:addons` → uBlock Origin present and not removable; `about:config` → blocked.
2. `https://www.tiktok.com` → blocked page; in a terminal, `getent hosts tiktok.com` → `0.0.0.0`.
3. `https://www.youtube.com/shorts/<any id>` → blocked; the YouTube home page has no Shorts shelf or tab; a regular video plays fine.
4. A Google search for an adult term → SafeSearch locked; YouTube → Restricted Mode active.
5. Firefox settings → "DNS over HTTPS" greyed out/disabled.
6. `flatpak` and `chromium` → command not found; `sudo` refused from the child's account.

## Uninstall

```bash
sudo /opt/kids-control/uninstall.sh
```

Restores `/etc/hosts`, any pre-existing `policies.json`, and the DNS settings. Removing Timekpr and reinstalling flatpak/Software Manager are left to you (the script prints the commands).

## Known limitations

- A "portable" Firefox (a tarball extracted in the child's home) would ignore the policies — but the hosts + DNS layers still block TikTok and adult content.
- YouTube Restricted Mode also hides comments (YouTube behavior).
- SafeSearch is only forced on Google (`google.com`/`google.fr` by default — add your local domain); other engines are filtered by the family DNS, and the homepage is locked to Qwant Junior.
- Removing `flatpak` may also remove Mint's Software Manager (`mintinstall`) — reversible: `sudo apt install flatpak mintinstall`.
- Firefox's *default search engine* can only be enforced on ESR builds (Mozilla limitation); hence the locked homepage instead.
- Router/network-level DNS filtering is out of scope, but recommended once other devices (tablet, phone) show up — e.g. NextDNS or AdGuard DNS with a kids profile.

## Development

Test mode writes under a prefix and skips system actions (apt, NetworkManager):

```bash
KIDS_CONTROL_ROOT=/tmp/testroot ./install.sh
KIDS_CONTROL_ROOT=/tmp/testroot ./uninstall.sh
```

## License

[MIT](LICENSE)
