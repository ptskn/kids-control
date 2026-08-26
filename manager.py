#!/usr/bin/env python3
"""kids-control manager — local web UI that manages a kids-control
installation on the child's computer over SSH.

Usage:
    python3 manager.py user@child-pc [--port 8800]

Runs a small web server bound to 127.0.0.1 (never exposed to the network)
and talks to the child's computer with your system ssh (key-based auth,
BatchMode). Python standard library only.

One-time setup on the child's computer for one-click Apply:
    sudo chown -R $USER /opt/kids-control/config
    echo "$USER ALL=(root) NOPASSWD: /opt/kids-control/install.sh" \
        | sudo tee /etc/sudoers.d/kids-control
"""
import argparse
import json
import subprocess
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REMOTE_DIR = "/opt/kids-control"
FILES = {
    "channels": "blocked-channels.txt",
    "domains": "blocked-domains.txt",
    "patterns": "blocked-url-patterns.txt",
}
REMOTE = None  # user@host, set in main()

STATUS_SCRIPT = r"""
f=/usr/lib/mozilla/managed-storage/uBlock0@raymondhill.net.json
echo "reachable=yes"
echo "filters=$(python3 -c "import json;print(len(json.load(open('$f'))['data']['toOverwrite']['filters']))" 2>/dev/null || echo '?')"
echo "applied=$(stat -c %y "$f" 2>/dev/null | cut -d. -f1)"
echo "hosts=$(grep -c '^0\.0\.0\.0' /etc/hosts 2>/dev/null || echo 0)"
echo "firefox=$(pgrep -x firefox >/dev/null 2>&1 && echo running || echo stopped)"
echo "canapply=$(sudo -n -l /opt/kids-control/install.sh >/dev/null 2>&1 && echo yes || echo no)"
echo "writable=$(test -w /opt/kids-control/config/blocked-channels.txt && echo yes || echo no)"
"""


def ssh(cmd, stdin=None, timeout=60):
    try:
        p = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=6", REMOTE, cmd],
            input=stdin, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "ssh timeout"


def api_status():
    code, out, err = ssh("bash -s", stdin=STATUS_SCRIPT, timeout=20)
    status = {"host": REMOTE, "reachable": False, "error": err.strip()}
    if code == 0:
        for line in out.splitlines():
            if "=" in line:
                k, _, v = line.partition("=")
                status[k] = v
        status["reachable"] = status.get("reachable") == "yes"
    return status


def api_get_file(key):
    code, out, err = ssh(f"cat {REMOTE_DIR}/config/{FILES[key]}")
    if code != 0:
        return {"ok": False, "error": err.strip() or "read failed"}
    return {"ok": True, "content": out}


def api_save_file(key, content):
    if content and not content.endswith("\n"):
        content += "\n"
    code, _, err = ssh(f"cat > {REMOTE_DIR}/config/{FILES[key]}", stdin=content)
    if code != 0:
        return {"ok": False, "error": err.strip() or "write failed"}
    return {"ok": True}


def api_apply():
    code, out, err = ssh(f"sudo -n {REMOTE_DIR}/install.sh 2>&1", timeout=300)
    return {"ok": code == 0, "output": out + (("\n" + err.strip()) if err.strip() else "")}


PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>kids-control manager</title>
<style>
  :root { --accent:#4f46e5; --ok:#16a34a; --bad:#dc2626; --muted:#6b7280;
          --bg:#f4f5f7; --card:#ffffff; --border:#e5e7eb; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:system-ui,sans-serif; background:var(--bg); color:#111827; }
  .wrap { max-width:920px; margin:0 auto; padding:24px 16px 60px; }
  h1 { font-size:22px; margin:0 0 4px; } h1 small { color:var(--muted); font-weight:400; }
  .chips { display:flex; flex-wrap:wrap; gap:8px; margin:14px 0 22px; }
  .chip { background:var(--card); border:1px solid var(--border); border-radius:999px;
          padding:5px 12px; font-size:13px; }
  .chip b.ok { color:var(--ok); } .chip b.bad { color:var(--bad); }
  .card { background:var(--card); border:1px solid var(--border); border-radius:12px;
          padding:16px; margin-bottom:16px; }
  .card h2 { margin:0 0 4px; font-size:15px; }
  .card p.hint { margin:0 0 10px; font-size:13px; color:var(--muted); }
  textarea { width:100%; min-height:150px; font:13px/1.5 ui-monospace,monospace;
             border:1px solid var(--border); border-radius:8px; padding:10px; resize:vertical; }
  button { background:var(--accent); color:#fff; border:0; border-radius:8px;
           padding:8px 16px; font-size:14px; cursor:pointer; margin-top:8px; }
  button:disabled { background:#c7c9d1; cursor:default; }
  button.big { font-size:16px; padding:12px 26px; }
  .save-state { margin-left:10px; font-size:13px; }
  #applyout { background:#0f172a; color:#d1e7ff; font:12px/1.5 ui-monospace,monospace;
              border-radius:8px; padding:12px; white-space:pre-wrap; display:none;
              max-height:300px; overflow:auto; margin-top:10px; }
  .banner { border-left:4px solid var(--bad); background:#fef2f2; padding:10px 14px;
            border-radius:8px; font-size:13px; margin-bottom:16px; display:none; }
  .banner code { background:#fff; padding:1px 5px; border-radius:4px; }
  .reminder { color:var(--ok); font-size:14px; margin-top:8px; display:none; }
</style></head><body><div class="wrap">
  <h1>kids-control <small id="host"></small></h1>
  <div class="chips" id="chips">Loading status…</div>
  <div class="banner" id="banner"></div>

  <div class="card">
    <h2>Blocked YouTube channels</h2>
    <p class="hint">One <code>@Handle</code> per line (from the channel URL). Channel page blocked + every video card hidden.</p>
    <textarea id="ta-channels" spellcheck="false"></textarea>
    <button onclick="save('channels')">Save channels</button><span class="save-state" id="st-channels"></span>
  </div>
  <div class="card">
    <h2>Blocked domains</h2>
    <p class="hint">One domain per line — blocked in every app (hosts) and in Firefox.</p>
    <textarea id="ta-domains" spellcheck="false"></textarea>
    <button onclick="save('domains')">Save domains</button><span class="save-state" id="st-domains"></span>
  </div>
  <div class="card">
    <h2>Blocked URL patterns</h2>
    <p class="hint">Firefox match patterns, to block a section of a site (e.g. <code>*://*.youtube.com/shorts/*</code>).</p>
    <textarea id="ta-patterns" spellcheck="false"></textarea>
    <button onclick="save('patterns')">Save patterns</button><span class="save-state" id="st-patterns"></span>
  </div>

  <div class="card">
    <h2>Apply on the child's computer</h2>
    <p class="hint">Re-runs install.sh over SSH: regenerates Firefox policies, uBlock filters and /etc/hosts from the saved lists.</p>
    <button class="big" id="applybtn" onclick="apply()">Apply now</button>
    <div class="reminder" id="reminder">✔ Applied. Firefox must be fully closed and reopened on the child's session to load the new filters.</div>
    <pre id="applyout"></pre>
  </div>
</div><script>
const $ = id => document.getElementById(id);
async function j(url, opts) { const r = await fetch(url, opts); return r.json(); }

function chip(label, val, good) {
  const cls = good === undefined ? "" : (good ? "ok" : "bad");
  return `<span class="chip">${label} <b class="${cls}">${val}</b></span>`;
}
async function refresh() {
  const s = await j("/api/status");
  $("host").textContent = "— " + s.host;
  if (!s.reachable) {
    $("chips").innerHTML = chip("connection", "unreachable", false);
    $("banner").style.display = "block";
    $("banner").textContent = "SSH connection failed: " + (s.error || "unknown error");
    return;
  }
  $("chips").innerHTML =
    chip("connection", "ok", true) +
    chip("uBlock filters", s.filters) +
    chip("hosts entries", s.hosts) +
    chip("firefox", s.firefox, s.firefox === "stopped" ? undefined : true) +
    chip("last apply", s.applied || "?") +
    chip("one-click apply", s.canapply, s.canapply === "yes");
  $("applybtn").disabled = s.canapply !== "yes";
  if (s.canapply !== "yes" || s.writable !== "yes") {
    $("banner").style.display = "block";
    $("banner").innerHTML = "Setup needed on the child's computer for editing/applying:<br>" +
      "<code>sudo chown -R $USER /opt/kids-control/config</code><br>" +
      "<code>echo \\"$USER ALL=(root) NOPASSWD: /opt/kids-control/install.sh\\" | sudo tee /etc/sudoers.d/kids-control</code>";
  } else { $("banner").style.display = "none"; }
}
async function load(key) {
  const r = await j("/api/file/" + key);
  $("ta-" + key).value = r.ok ? r.content : ("# error: " + r.error);
}
async function save(key) {
  const st = $("st-" + key);
  st.textContent = "saving…";
  const r = await j("/api/file/" + key, {method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify({content: $("ta-" + key).value})});
  st.textContent = r.ok ? "saved ✔ (remember to Apply)" : ("error: " + r.error);
  setTimeout(() => { st.textContent = ""; }, 6000);
}
async function apply() {
  const btn = $("applybtn"); btn.disabled = true; btn.textContent = "Applying…";
  $("reminder").style.display = "none";
  const r = await j("/api/apply", {method:"POST"});
  $("applyout").style.display = "block";
  $("applyout").textContent = r.output || (r.ok ? "done" : "failed");
  if (r.ok) $("reminder").style.display = "block";
  btn.disabled = false; btn.textContent = "Apply now";
  refresh();
}
refresh(); load("channels"); load("domains"); load("patterns");
</script></body></html>
"""


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/status":
            self._json(api_status())
        elif self.path.startswith("/api/file/"):
            key = self.path.rsplit("/", 1)[1]
            if key not in FILES:
                return self._json({"ok": False, "error": "unknown file"}, 404)
            self._json(api_get_file(key))
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        if self.path.startswith("/api/file/"):
            key = self.path.rsplit("/", 1)[1]
            if key not in FILES:
                return self._json({"ok": False, "error": "unknown file"}, 404)
            try:
                content = json.loads(raw)["content"]
            except (ValueError, KeyError):
                return self._json({"ok": False, "error": "bad request"}, 400)
            self._json(api_save_file(key, content))
        elif self.path == "/api/apply":
            self._json(api_apply())
        else:
            self._json({"error": "not found"}, 404)

    def log_message(self, fmt, *args):  # keep the terminal quiet
        pass


def main():
    global REMOTE
    ap = argparse.ArgumentParser(description="kids-control remote manager (web UI over SSH)")
    ap.add_argument("remote", help="SSH target of the child's computer, e.g. parent@192.168.0.42")
    ap.add_argument("--port", type=int, default=8800)
    ap.add_argument("--no-browser", action="store_true", help="don't open the browser automatically")
    args = ap.parse_args()
    REMOTE = args.remote
    url = f"http://127.0.0.1:{args.port}"
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError:
        print(f"Already running at {url} — opening the browser.")
        if not args.no_browser:
            webbrowser.open(url)
        return
    print(f"kids-control manager: {url}  (managing {REMOTE} — Ctrl+C to stop)")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
