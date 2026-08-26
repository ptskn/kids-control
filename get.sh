#!/usr/bin/env bash
# kids-control bootstrap — download the latest version and run the installer.
# Usage:  curl -fsSL https://raw.githubusercontent.com/ptskn/kids-control/main/get.sh | sudo bash
set -euo pipefail

REPO="ptskn/kids-control"
TARBALL="https://github.com/$REPO/archive/refs/heads/main.tar.gz"
INSTALL_DIR="/opt/kids-control"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run me as root:" >&2
  echo "  curl -fsSL https://raw.githubusercontent.com/$REPO/main/get.sh | sudo bash" >&2
  exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "[kids-control] Downloading $REPO…"
if command -v curl >/dev/null; then
  curl -fsSL "$TARBALL" | tar -xz -C "$TMP" --strip-components=1
elif command -v wget >/dev/null; then
  wget -qO- "$TARBALL" | tar -xz -C "$TMP" --strip-components=1
else
  echo "curl or wget is required." >&2
  exit 1
fi

# Preserve customized blocklists from a previous install
if [ -d "$INSTALL_DIR/config" ]; then
  for f in blocked-domains.txt blocked-url-patterns.txt safesearch-hosts.txt; do
    [ -f "$INSTALL_DIR/config/$f" ] && cp "$INSTALL_DIR/config/$f" "$TMP/config/$f"
  done
fi

rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -a "$TMP/." "$INSTALL_DIR/"
chmod 755 "$INSTALL_DIR"

"$INSTALL_DIR/install.sh"

echo
echo "[kids-control] Installed in $INSTALL_DIR"
echo "[kids-control]   Customize:  edit $INSTALL_DIR/config/*.txt then run: sudo $INSTALL_DIR/install.sh"
echo "[kids-control]   Uninstall:  sudo $INSTALL_DIR/uninstall.sh"
