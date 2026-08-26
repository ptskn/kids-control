#!/usr/bin/env python3
"""kids-control manager — local web UI that manages a kids-control
installation on the child's computer over SSH.

Usage:
    python3 manager.py [user@child-pc] [--port 8800]

The SSH target is remembered in ~/.config/kids-control/manager.json and can
be changed from the UI, so the argument is only needed the first time (or to
switch machines). The web server binds to 127.0.0.1 only; everything goes
through your system ssh (key-based auth, BatchMode). Stdlib only.

One-time setup on the child's computer for one-click Apply and screen-time
control:
    sudo chown -R $USER /opt/kids-control/config
    echo "$USER ALL=(root) NOPASSWD: /opt/kids-control/install.sh, /usr/bin/timekpra" \
        | sudo tee /etc/sudoers.d/kids-control
"""
import argparse
import json
import os
import re
import subprocess
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REMOTE_DIR = "/opt/kids-control"
TIMEKPRA = "/usr/bin/timekpra"
CONFIG_PATH = os.path.expanduser("~/.config/kids-control/manager.json")
FILES = {
    "channels": "blocked-channels.txt",
    "domains": "blocked-domains.txt",
    "patterns": "blocked-url-patterns.txt",
}
HOST_RE = re.compile(r"^[A-Za-z0-9@._:-]+$")
USER_RE = re.compile(r"^[a-z_][a-z0-9_-]*$")
REMOTE = None  # user@host, set in main() / via /api/config

STATUS_SCRIPT = r"""
f=/usr/lib/mozilla/managed-storage/uBlock0@raymondhill.net.json
echo "reachable=yes"
echo "filters=$(python3 -c "import json;print(len(json.load(open('$f'))['data']['toOverwrite']['filters']))" 2>/dev/null || echo '?')"
echo "applied=$(stat -c %y "$f" 2>/dev/null | cut -d. -f1)"
echo "hosts=$(grep -c '^0\.0\.0\.0' /etc/hosts 2>/dev/null || echo 0)"
echo "firefox=$(pgrep -x firefox >/dev/null 2>&1 && echo running || echo stopped)"
np=$(sudo -n -l 2>/dev/null | grep NOPASSWD || true)
echo "canapply=$(echo "$np" | grep -qF /opt/kids-control/install.sh && echo yes || echo no)"
echo "canscreen=$(echo "$np" | grep -qF /usr/bin/timekpra && echo yes || echo no)"
echo "writable=$(test -w /opt/kids-control/config/blocked-channels.txt && echo yes || echo no)"
"""


def load_config():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def remember(**kv):
    cfg = load_config()
    cfg.update({k: v for k, v in kv.items() if v})
    save_config(cfg)


def ssh(cmd, stdin=None, timeout=60):
    if not REMOTE:
        return 255, "", "no host configured"
    try:
        p = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=6", REMOTE, cmd],
            input=stdin, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "ssh timeout"


# ─── protections API ─────────────────────────────────────────────────────

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


# ─── screen time API (timekpr-next) ──────────────────────────────────────

def tk(cmd, timeout=30):
    code, out, err = ssh(f"sudo -n {TIMEKPRA} {cmd} 2>&1", timeout=timeout)
    return code, (out + err).strip()


def api_tk_users():
    code, out, err = ssh("awk -F: '$3>=1000 && $3<60000 {print $1}' /etc/passwd")
    users = sorted(u for u in out.split() if USER_RE.match(u))
    return {"ok": code == 0, "users": users,
            "child": load_config().get("child"),
            "error": err.strip()}


def api_tk_info(user):
    if not USER_RE.match(user):
        return {"ok": False, "error": "bad user"}
    code, out = tk(f"--userinfo '{user}'")
    if code != 0:
        return {"ok": False, "error": out[:400]}
    info = {}
    for line in out.splitlines():
        k, sep, v = line.partition(":")
        k = k.strip()
        if sep and k and k == k.upper() and re.fullmatch(r"[A-Z0-9_]+", k):
            info[k] = v.strip()
    remember(child=user)
    return {"ok": True, "info": info}


def api_tk_schedule(user, days, limits, hour_from, hour_to):
    if not USER_RE.match(user):
        return {"ok": False, "error": "bad user"}
    try:
        days = [int(d) for d in days]
        limits = [int(x) for x in limits]
        hour_from, hour_to = int(hour_from), int(hour_to)
    except (TypeError, ValueError):
        return {"ok": False, "error": "bad values"}
    if not days or sorted(set(days)) != days or days[0] < 1 or days[-1] > 7 \
       or len(limits) != len(days) or any(not 0 <= x <= 86400 for x in limits) \
       or not 0 <= hour_from < hour_to <= 24:
        return {"ok": False, "error": "bad values"}
    hours = ";".join(str(h) for h in range(hour_from, hour_to))
    steps = [
        ("allowed days", f"--setalloweddays '{user}' '" + ";".join(map(str, days)) + "'"),
        ("daily limits", f"--settimelimits '{user}' '" + ";".join(map(str, limits)) + "'"),
        ("allowed hours", f"--setallowedhours '{user}' 'ALL' '{hours}'"),
    ]
    log = []
    for label, cmd in steps:
        code, out = tk(cmd)
        log.append(f"[{label}] {out or 'ok'}")
        if code != 0:
            return {"ok": False, "error": "\n".join(log)}
    return {"ok": True, "output": "\n".join(log)}


def api_tk_bonus(user, op, seconds):
    if not USER_RE.match(user) or op not in ("+", "-") \
       or not isinstance(seconds, int) or not 0 < seconds <= 14400:
        return {"ok": False, "error": "bad values"}
    code, out = tk(f"--settimeleft '{user}' '{op}' {seconds}")
    return {"ok": code == 0, "output": out}


# ─── UI ──────────────────────────────────────────────────────────────────

PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>kids-control manager</title>
<style>
  :root { --bg-primary:#0d1117; --bg-secondary:#161b22; --bg-tertiary:#21262d;
          --border-color:#30363d; --text-primary:#c9d1d9; --text-secondary:#8b949e;
          --accent-green:#3fb950; --accent-red:#f85149; --accent-blue:#58a6ff;
          --accent-yellow:#d29922; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
         background:var(--bg-primary); color:var(--text-primary); }
  .wrap { max-width:920px; margin:0 auto; padding:20px 16px 60px; }
  h1 { font-size:20px; margin:0 0 10px; display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
  input, select { background:var(--bg-primary); color:var(--text-primary);
          border:1px solid var(--border-color); border-radius:6px; padding:5px 9px; font-size:13px; }
  input:focus, select:focus, textarea:focus { outline:none; border-color:var(--accent-blue); }
  #host { width:230px; font:12px ui-monospace,Consolas,monospace; }
  .chips { display:flex; flex-wrap:wrap; gap:6px; margin:12px 0 18px; }
  .chip { background:var(--bg-tertiary); border:1px solid var(--border-color); border-radius:999px;
          padding:4px 11px; font-size:12px; color:var(--text-secondary); }
  .chip b { color:var(--text-primary); font-weight:600; }
  .chip b.ok { color:var(--accent-green); } .chip b.bad { color:var(--accent-red); }
  .card { background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:6px;
          padding:14px; margin-bottom:12px; }
  .card h2 { margin:0 0 3px; font-size:14px; }
  .card p.hint { margin:0 0 8px; font-size:12px; color:var(--text-secondary); }
  .card p.hint code, .banner code { background:var(--bg-tertiary); padding:1px 5px; border-radius:4px; font-size:11px; }
  textarea { width:100%; min-height:140px; font:12px/1.5 ui-monospace,'SF Mono',Consolas,monospace;
             background:var(--bg-primary); color:var(--text-primary);
             border:1px solid var(--border-color); border-radius:6px; padding:9px; resize:vertical; }
  button { background:var(--bg-tertiary); color:var(--text-primary);
           border:1px solid var(--border-color); border-radius:6px;
           padding:6px 14px; font-size:13px; font-weight:500; cursor:pointer;
           margin-top:8px; transition:all .15s; }
  button:hover { background:var(--border-color); }
  button:disabled { opacity:.5; cursor:not-allowed; }
  button.primary { background:var(--accent-blue); border-color:var(--accent-blue); color:#0d1117; }
  button.primary:hover { background:#1f6feb; color:#fff; }
  button.big { font-size:14px; padding:9px 22px; }
  button.small { padding:4px 10px; font-size:12px; margin-top:0; }
  .save-state { margin-left:10px; font-size:12px; color:var(--accent-green); }
  #applyout { background:var(--bg-primary); border:1px solid var(--border-color); color:var(--text-primary);
              font:11px/1.5 ui-monospace,Consolas,monospace; border-radius:6px; padding:10px;
              white-space:pre-wrap; display:none; max-height:300px; overflow:auto; margin-top:10px; }
  .banner { border-left:3px solid var(--accent-red); background:rgba(248,81,73,.1);
            padding:9px 13px; border-radius:6px; font-size:12px; margin-bottom:14px; display:none; }
  .reminder { color:var(--accent-green); font-size:13px; margin-top:8px; display:none; }
  .tk-row { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin:8px 0; font-size:13px; }
  .tk-grid { display:grid; grid-template-columns:repeat(7,1fr); gap:6px; margin:10px 0; }
  .tk-day { background:var(--bg-primary); border:1px solid var(--border-color); border-radius:6px;
            padding:7px 6px; text-align:center; font-size:12px; }
  .tk-day label { display:block; color:var(--text-secondary); margin-bottom:4px; }
  .tk-day input[type=number] { width:100%; margin-top:5px; padding:3px 5px; font-size:12px; }
  #tk-today { color:var(--accent-yellow); font-size:13px; }
  ::-webkit-scrollbar { width:8px; height:8px; }
  ::-webkit-scrollbar-track { background:var(--bg-primary); }
  ::-webkit-scrollbar-thumb { background:var(--border-color); border-radius:4px; }
  ::-webkit-scrollbar-thumb:hover { background:var(--text-secondary); }
</style></head><body><div class="wrap">
  <h1>kids-control
    <input id="host" placeholder="user@child-pc" spellcheck="false">
    <button class="small" onclick="saveHost()">Set host</button>
  </h1>
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
    <h2>Screen time (Timekpr-nExT)</h2>
    <p class="hint">Changes apply immediately on the child's session — no Apply, no Firefox restart needed.</p>
    <div class="tk-row">
      Child account: <select id="tk-user" onchange="tkLoad()"></select>
      <span id="tk-today"></span>
      <span class="save-state" id="tk-state"></span>
    </div>
    <div class="tk-grid" id="tk-grid"></div>
    <div class="tk-row">
      Allowed hours (all days): from <input type="number" id="tk-from" min="0" max="23" value="8" style="width:60px">
      to <input type="number" id="tk-to" min="1" max="24" value="20" style="width:60px">
      <button class="small primary" onclick="tkSave()">Save schedule</button>
    </div>
    <div class="tk-row">
      Today only: <button class="small" onclick="tkBonus('+',15)">+15 min</button>
      <button class="small" onclick="tkBonus('+',30)">+30 min</button>
      <button class="small" onclick="tkBonus('-',15)">−15 min</button>
    </div>
  </div>

  <div class="card">
    <h2>Apply on the child's computer</h2>
    <p class="hint">Re-runs install.sh over SSH: regenerates Firefox policies, uBlock filters and /etc/hosts from the saved lists.</p>
    <button class="primary big" id="applybtn" onclick="apply()">Apply now</button>
    <div class="reminder" id="reminder">✔ Applied. Firefox must be fully closed and reopened on the child's session to load the new filters.</div>
    <pre id="applyout"></pre>
  </div>
</div><script>
const $ = id => document.getElementById(id);
const DAYS = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
async function j(url, body) {
  const opts = body ? {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)} : undefined;
  const r = await fetch(url, opts); return r.json();
}
function chip(label, val, good) {
  const cls = good === undefined ? "" : (good ? "ok" : "bad");
  return `<span class="chip">${label} <b class="${cls}">${val}</b></span>`;
}
const SETUP = 'Setup needed on the child\\'s computer:<br>' +
  '<code>sudo chown -R $USER /opt/kids-control/config</code><br>' +
  '<code>echo "$USER ALL=(root) NOPASSWD: /opt/kids-control/install.sh, /usr/bin/timekpra" | sudo tee /etc/sudoers.d/kids-control</code>';
async function refresh() {
  const s = await j("/api/status");
  if (s.host) $("host").value = s.host;
  if (!s.reachable) {
    $("chips").innerHTML = chip("connection", s.host ? "unreachable" : "no host set", false);
    $("banner").style.display = "block";
    let msg = s.host ? ("SSH connection failed: " + (s.error || "unknown error")) : "Enter the child's computer SSH target above (user@host) and press Set host.";
    if ((s.error || "").includes("Permission denied"))
      msg += " — your SSH key is not available in this environment (locked or missing ssh-agent). Launch from a terminal where ssh works, or point SSH_AUTH_SOCK to your agent.";
    $("banner").textContent = msg;
    return;
  }
  $("chips").innerHTML =
    chip("connection", "ok", true) +
    chip("uBlock filters", s.filters) +
    chip("hosts entries", s.hosts) +
    chip("firefox", s.firefox, s.firefox === "stopped" ? undefined : true) +
    chip("last apply", s.applied || "?") +
    chip("apply", s.canapply, s.canapply === "yes") +
    chip("screen time", s.canscreen, s.canscreen === "yes");
  $("applybtn").disabled = s.canapply !== "yes";
  const needSetup = s.canapply !== "yes" || s.writable !== "yes" || s.canscreen !== "yes";
  $("banner").style.display = needSetup ? "block" : "none";
  if (needSetup) $("banner").innerHTML = SETUP;
}
async function saveHost() {
  const r = await j("/api/config", {host: $("host").value.trim()});
  if (!r.ok) { alert(r.error); return; }
  refresh(); ["channels","domains","patterns"].forEach(load); tkUsers();
}
async function load(key) {
  const r = await j("/api/file/" + key);
  $("ta-" + key).value = r.ok ? r.content : ("# error: " + r.error);
}
async function save(key) {
  const st = $("st-" + key);
  st.textContent = "saving…";
  const r = await j("/api/file/" + key, {content: $("ta-" + key).value});
  st.textContent = r.ok ? "saved ✔ (remember to Apply)" : ("error: " + r.error);
  setTimeout(() => { st.textContent = ""; }, 6000);
}
async function apply() {
  const btn = $("applybtn"); btn.disabled = true; btn.textContent = "Applying…";
  $("reminder").style.display = "none";
  const r = await j("/api/apply", {});
  $("applyout").style.display = "block";
  $("applyout").textContent = r.output || (r.ok ? "done" : "failed");
  if (r.ok) $("reminder").style.display = "block";
  btn.disabled = false; btn.textContent = "Apply now";
  refresh();
}
function tkGrid() {
  $("tk-grid").innerHTML = DAYS.map((d,i) =>
    `<div class="tk-day"><label>${d}</label>` +
    `<input type="checkbox" id="tk-d${i+1}">` +
    `<input type="number" id="tk-l${i+1}" min="0" max="1440" placeholder="min"></div>`).join("");
}
async function tkUsers() {
  const r = await j("/api/timekpr/users");
  const sel = $("tk-user"); sel.innerHTML = "";
  (r.users || []).forEach(u => sel.add(new Option(u, u)));
  if (r.child && r.users.includes(r.child)) sel.value = r.child;
  if (sel.value) tkLoad();
}
const fmt = s => { s = parseInt(s); return isNaN(s) ? "?" : Math.floor(s/3600) + "h" + String(Math.floor(s%3600/60)).padStart(2,"0"); };
async function tkLoad() {
  const u = $("tk-user").value; if (!u) return;
  $("tk-state").textContent = "loading…"; $("tk-today").textContent = "";
  const r = await j("/api/timekpr/info?user=" + encodeURIComponent(u));
  if (!r.ok) { $("tk-state").textContent = "error: " + r.error; return; }
  $("tk-state").textContent = "";
  const inf = r.info;
  $("tk-today").textContent = `today: ${fmt(inf.TIME_SPENT_DAY)} used / ${fmt(inf.TIME_LEFT_DAY)} left`;
  const days = (inf.ALLOWED_WEEKDAYS || "").split(";").filter(Boolean).map(Number);
  const lims = (inf.LIMITS_PER_WEEKDAYS || "").split(";").filter(Boolean).map(Number);
  for (let d = 1; d <= 7; d++) {
    const idx = days.indexOf(d);
    $("tk-d" + d).checked = idx >= 0;
    $("tk-l" + d).value = idx >= 0 && lims[idx] !== undefined ? Math.round(lims[idx]/60) : "";
  }
}
async function tkSave() {
  const u = $("tk-user").value; if (!u) return;
  const days = [], limits = [];
  for (let d = 1; d <= 7; d++) if ($("tk-d" + d).checked) {
    days.push(d); limits.push((parseInt($("tk-l" + d).value) || 0) * 60);
  }
  if (!days.length) { $("tk-state").textContent = "check at least one day"; return; }
  $("tk-state").textContent = "saving…";
  const r = await j("/api/timekpr/schedule",
    {user:u, days, limits, hour_from:+$("tk-from").value, hour_to:+$("tk-to").value});
  $("tk-state").textContent = r.ok ? "saved ✔ (applies immediately)" : "error: " + r.error;
}
async function tkBonus(op, min) {
  const u = $("tk-user").value; if (!u) return;
  const r = await j("/api/timekpr/bonus", {user:u, op, seconds:min*60});
  $("tk-state").textContent = r.ok ? "done ✔" : "error: " + r.error;
  tkLoad();
}
tkGrid(); refresh(); ["channels","domains","patterns"].forEach(load); tkUsers();
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

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(length)) if length else {}
        except ValueError:
            return None

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == "/":
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif url.path == "/api/status":
            self._json(api_status())
        elif url.path == "/api/config":
            self._json({"ok": True, "host": REMOTE})
        elif url.path == "/api/timekpr/users":
            self._json(api_tk_users())
        elif url.path == "/api/timekpr/info":
            user = urllib.parse.parse_qs(url.query).get("user", [""])[0]
            self._json(api_tk_info(user))
        elif url.path.startswith("/api/file/"):
            key = url.path.rsplit("/", 1)[1]
            if key not in FILES:
                return self._json({"ok": False, "error": "unknown file"}, 404)
            self._json(api_get_file(key))
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        global REMOTE
        data = self._body()
        if data is None:
            return self._json({"ok": False, "error": "bad request"}, 400)
        if self.path == "/api/config":
            host = str(data.get("host", "")).strip()
            if not HOST_RE.match(host):
                return self._json({"ok": False, "error": "invalid host"}, 400)
            REMOTE = host
            remember(host=host)
            self._json({"ok": True, "host": REMOTE})
        elif self.path.startswith("/api/file/"):
            key = self.path.rsplit("/", 1)[1]
            if key not in FILES:
                return self._json({"ok": False, "error": "unknown file"}, 404)
            if "content" not in data:
                return self._json({"ok": False, "error": "bad request"}, 400)
            self._json(api_save_file(key, str(data["content"])))
        elif self.path == "/api/apply":
            self._json(api_apply())
        elif self.path == "/api/timekpr/schedule":
            self._json(api_tk_schedule(str(data.get("user", "")), data.get("days"),
                                       data.get("limits"), data.get("hour_from"),
                                       data.get("hour_to")))
        elif self.path == "/api/timekpr/bonus":
            self._json(api_tk_bonus(str(data.get("user", "")), data.get("op"),
                                    data.get("seconds")))
        else:
            self._json({"error": "not found"}, 404)

    def log_message(self, fmt, *args):  # keep the terminal quiet
        pass


def main():
    global REMOTE
    ap = argparse.ArgumentParser(description="kids-control remote manager (web UI over SSH)")
    ap.add_argument("remote", nargs="?",
                    help="SSH target of the child's computer (remembered; only needed the first time)")
    ap.add_argument("--port", type=int, default=8800)
    ap.add_argument("--no-browser", action="store_true", help="don't open the browser automatically")
    args = ap.parse_args()
    REMOTE = args.remote or load_config().get("host")
    if args.remote:
        remember(host=args.remote)
    url = f"http://127.0.0.1:{args.port}"
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError:
        print(f"Already running at {url} — opening the browser.")
        if not args.no_browser:
            webbrowser.open(url)
        return
    print(f"kids-control manager: {url}  (managing {REMOTE or 'no host yet — set it in the UI'} — Ctrl+C to stop)")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
