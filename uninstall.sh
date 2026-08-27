#!/usr/bin/env bash
# kids-control — remove every protection installed by install.sh.
# Usage: sudo ./uninstall.sh
# Test mode: KIDS_CONTROL_ROOT=/tmp/testroot ./uninstall.sh
set -euo pipefail

ROOT="${KIDS_CONTROL_ROOT:-}"
MARK_BEGIN="# BEGIN kids_control"
MARK_END="# END kids_control"

HOSTS_FILE="$ROOT/etc/hosts"
POLICY_PATHS=("$ROOT/etc/firefox/policies/policies.json" "$ROOT/usr/lib/firefox/distribution/policies.json")
UBLOCK_MANAGED="$ROOT/usr/lib/mozilla/managed-storage/uBlock0@raymondhill.net.json"
NM_DNS_CONF="$ROOT/etc/NetworkManager/conf.d/90-kids-control-dns.conf"
RESOLVED_CONF="$ROOT/etc/systemd/resolved.conf.d/90-kids-control-dns.conf"

info(){ printf '\033[1;34m[kids-control]\033[0m %s\n' "$*"; }

if [ -z "$ROOT" ] && [ "$(id -u)" -ne 0 ]; then
  echo "This script must be run with sudo." >&2
  exit 1
fi

# ─── /etc/hosts: remove the marked block ────────────────────────────────
if [ -f "$HOSTS_FILE" ] && grep -qF "$MARK_BEGIN" "$HOSTS_FILE"; then
  TMP="$(mktemp)"
  sed "/^${MARK_BEGIN}\$/,/^${MARK_END}\$/d" "$HOSTS_FILE" > "$TMP"
  install -m 644 "$TMP" "$HOSTS_FILE"
  rm -f "$TMP"
  info "kids-control block removed from $HOSTS_FILE"
fi

# ─── Firefox policies: restore or delete ────────────────────────────────
for dest in "${POLICY_PATHS[@]}"; do
  if [ -f "$dest.kids_control.bak" ]; then
    mv "$dest.kids_control.bak" "$dest"
    info "Restored: $dest (from backup)"
  elif [ -f "$dest" ] && grep -q kids.control "$dest"; then
    rm -f "$dest"
    info "Deleted: $dest"
  fi
done

# ─── Managed uBlock + family DNS ────────────────────────────────────────
for f in "$UBLOCK_MANAGED" "$NM_DNS_CONF" "$RESOLVED_CONF"; do
  if [ -f "$f" ]; then rm -f "$f"; info "Deleted: $f"; fi
done

if [ -z "$ROOT" ]; then
  if systemctl is-active --quiet systemd-resolved; then
    systemctl restart systemd-resolved
  fi
  if systemctl is-active --quiet NetworkManager; then
    systemctl reload NetworkManager 2>/dev/null || systemctl restart NetworkManager
  fi
  resolvectl flush-caches 2>/dev/null || true
fi

echo
info "Protections removed. Remaining optional steps (not automatic):"
info "  - Screen time:        sudo apt remove timekpr-next"
info "  - Reinstall flatpak:  sudo apt install flatpak mintinstall"
info "Restart Firefox to apply."
