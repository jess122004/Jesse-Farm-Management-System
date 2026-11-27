"""
JESSE FARM MANAGEMENT SYSTEM - browser edition (runs in Pyodide, i.e. Python compiled to WebAssembly).

jesse_core.py is used UNCHANGED. This file replaces only the parts that need a real computer:
  * the http.server web server  -> handle(): the page in the browser passes each click or form here
  * the database file on disk    -> a file in the browser's IndexedDB storage (mounted at /data)
  * command-line backup/restore  -> a "Backup & device" page with download / restore buttons

Small adjustments are made to the module sources before they are imported (see _patch). Every adjustment
is checked, so if jesse_core.py changes and a patch no longer fits, start() fails loudly instead of silently.
"""
import base64
import io
import json
import os
import sqlite3
import sys

DATA_DIR = os.environ.get("JESSE_DATA", "/data")
DB_FILE = os.path.join(DATA_DIR, "jesse_farm.db")
os.environ["JESSE_DB"] = DB_FILE  # config.py reads this

_ready = False


# ---------------------------------------------------------------------------------------------- loading
def _replace(src, old, new, what):
    if old not in src:
        raise RuntimeError(f"bridge.py: could not apply patch '{what}' - jesse_core.py has changed")
    return src.replace(old, new)


def _patch(M):
    """Browser-specific adjustments to the module sources (text replacements, each verified)."""
    # 1. WAL journal mode needs shared memory that browsers do not offer; use the classic rollback journal.
    M["jesse_farm.db"] = _replace(M["jesse_farm.db"], 'conn.execute("PRAGMA journal_mode = WAL")',
                                  'conn.execute("PRAGMA journal_mode = DELETE")', "journal mode")
    # 2. Restoring a backup is done on the Backup & device page, not with "python run.py --restore".
    M["jesse_farm.views.settings"] = _replace(
        M["jesse_farm.views.settings"],
        "<p class=\"muted\">To restore, stop the system and run <code>python run.py --restore backups\\\\FILE.db</code>.\n"
        "            The current database is backed up automatically before it is replaced.</p>",
        "<p class=\"muted\">To restore a backup, or to download the whole database, open "
        "<a href=\"/device\">Backup &amp; device</a>.</p>",
        "settings restore note")
    # 3. A link from the sign-in page to demo data / restore.
    M["jesse_farm.views.auth"] = _replace(
        M["jesse_farm.views.auth"],
        "'<p style=\"text-align:center\">New here? <a href=\"/register\">Create an account</a></p>'",
        "'<p style=\"text-align:center\">New here? <a href=\"/register\">Create an account</a></p>'"
        " + '<p style=\"text-align:center\" class=\"muted\"><a href=\"/device\">Try the demo data, or restore a backup</a></p>'",
        "sign-in page link")


def _pbkdf2_hmac(hash_name, password, salt, iterations, dklen=None):
    """Standard PBKDF2-HMAC (RFC 8018), used only if this Python build has no OpenSSL version.
    Gives byte-for-byte the same result, so passwords made on the desktop version still work."""
    import hashlib
    inner, outer = hashlib.new(hash_name), hashlib.new(hash_name)
    block = inner.block_size
    key = password if len(password) <= block else hashlib.new(hash_name, password).digest()
    key = key + b"\x00" * (block - len(key))
    inner.update(bytes(x ^ 0x36 for x in key))
    outer.update(bytes(x ^ 0x5C for x in key))

    def prf(msg):
        i, o = inner.copy(), outer.copy()
        i.update(msg)
        o.update(i.digest())
        return o.digest()

    dklen = dklen or outer.digest_size
    out, n = b"", 1
    while len(out) < dklen:
        u = prf(salt + n.to_bytes(4, "big"))
        acc = int.from_bytes(u, "big")
        for _ in range(iterations - 1):
            u = prf(u)
            acc ^= int.from_bytes(u, "big")
        out += acc.to_bytes(len(u), "big")
        n += 1
    return out[:dklen]


def start(core_path):
    """Load jesse_core.py (parts 1 and 2 only: the modules and the loader), patch, import, create the database."""
    global _ready
    import hashlib
    if not hasattr(hashlib, "pbkdf2_hmac"):
        hashlib.pbkdf2_hmac = _pbkdf2_hmac
    with open(core_path, encoding="utf-8") as fh:
        src = fh.read()
    marker = "# ============================================================================ PART 3"
    if marker not in src:
        raise RuntimeError("bridge.py: PART 3 marker not found in jesse_core.py")
    head = src.split(marker)[0]
    g = {"__name__": "jesse_core", "__file__": core_path}
    exec(compile(head, core_path, "exec"), g)
    _patch(g["MODULES"])

    os.makedirs(DATA_DIR, exist_ok=True)
    from jesse_farm import config, db, i18n, ui
    from jesse_farm.views import (animals, auth, breeding, dashboard, exports, farms, feeding, finance,  # noqa: F401
                                  health, inventory, reports, sales, settings, tasks)

    config.BACKUP_DIR = os.path.join(DATA_DIR, "backups")  # kept in browser storage too
    i18n.STRINGS["en"]["device"] = "Backup & device"
    ui.NAV.append(("device", "/device", "💾"))
    _register_device_page()

    if os.path.exists(DB_FILE):
        _to_rollback_journal(DB_FILE)
    db.init_db(log=lambda *a: None)
    _ready = True
    return status()


# ---------------------------------------------------------------------------------------------- requests
class _Headers(dict):
    def get(self, key, default=None):
        return super().get(key.lower(), default)


def _make_handler():
    from jesse_farm.web import Handler

    class BrowserHandler(Handler):
        """The original request handler. Only send() changes: the reply goes back to the page, not a socket."""

        def __init__(self, method, url, body, cookie, referer):  # noqa: D401 - no socket, so no super().__init__
            self.command = method
            self.path = url
            data = body.encode("utf-8")
            self.headers = _Headers({"cookie": cookie or "", "content-length": str(len(data)),
                                     "referer": "http://jesse.local" + (referer or "/"), "host": "jesse.local"})
            self.rfile = io.BytesIO(data)
            self.result = None

        def send(self, status, body=b"", location=None, cookie=None, content_type="text/html; charset=utf-8", filename=None):
            self.result = {"status": status, "body": body if isinstance(body, bytes) else body.encode("utf-8"),
                           "location": location, "cookie": cookie, "content_type": content_type, "filename": filename}

    return BrowserHandler


_Handler = None


def handle(method, url, body="", cookie="", referer="/"):
    """Answer one request. Returns JSON text: status, html or file (base64), redirect location, cookie."""
    global _Handler
    if _Handler is None:
        _Handler = _make_handler()
    h = _Handler(method, url, body or "", cookie, referer)
    h.dispatch(method)
    r = h.result or {"status": 500, "body": b"No reply", "location": None, "cookie": None,
                     "content_type": "text/plain", "filename": None}
    out = {"status": r["status"], "location": r["location"], "cookie": r["cookie"], "filename": r["filename"],
           "content_type": r["content_type"]}
    if r["filename"]:
        out["file_b64"] = base64.b64encode(r["body"]).decode("ascii")
    else:
        out["html"] = r["body"].decode("utf-8", "replace")
    return json.dumps(out)


# ---------------------------------------------------------------------------------------------- data on this device
def _to_rollback_journal(path):
    """A database saved in WAL mode (as the desktop version does) is switched to the classic journal by
    setting header bytes 18-19 to 1 - SQLite's documented file format. Only safe when no -wal file is left,
    which is the case for a single uploaded .db file and for files written by this browser edition."""
    for extra in ("-wal", "-shm"):
        if os.path.exists(path + extra):
            os.remove(path + extra)
    with open(path, "r+b") as fh:
        head = fh.read(100)
        if len(head) < 100 or not head.startswith(b"SQLite format 3\x00"):
            raise ValueError("This file is not a SQLite database.")
        if head[18] == 2 or head[19] == 2:
            fh.seek(18)
            fh.write(b"\x01\x01")


def status():
    conn = sqlite3.connect(DB_FILE)
    try:
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        demo = conn.execute("SELECT 1 FROM users WHERE email='demo@jesse.farm'").fetchone() is not None
        farms = conn.execute("SELECT COUNT(*) FROM farms").fetchone()[0]
    finally:
        conn.close()
    return json.dumps({"users": users, "farms": farms, "demo": demo})


def load_demo():
    from jesse_farm.demo import create_demo
    return json.dumps({"loaded": bool(create_demo())})


def export_db():
    """A consistent copy of the whole database, made with SQLite's online backup."""
    tmp = "/tmp/jesse-export.db" if os.path.isdir("/tmp") else DB_FILE + ".export"
    if os.path.exists(tmp):
        os.remove(tmp)
    src, dst = sqlite3.connect(DB_FILE), sqlite3.connect(tmp)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    with open(tmp, "rb") as fh:
        data = fh.read()
    os.remove(tmp)
    return base64.b64encode(data).decode("ascii")


def import_db(path):
    """Replace the database with an uploaded file: a backup from this or the desktop version, or an old
    livestock_app.py database (it is upgraded). The current database is backed up first."""
    from jesse_farm import db
    try:
        _to_rollback_journal(path)
        check = sqlite3.connect(path)
        try:
            has_farms = check.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='farms'").fetchone()
        finally:
            check.close()
        if not has_farms:
            return json.dumps({"ok": False, "message": "This database is not from JESSE FMS or livestock_app.py (no farms table)."})
        safety = db.restore_db(path)
        _to_rollback_journal(DB_FILE)
        msg = "Backup restored. Sign in with an account from that database."
        if safety:
            msg += f" Your previous data was kept as {os.path.basename(safety)} (Settings → Backup)."
        return json.dumps({"ok": True, "message": msg})
    except (sqlite3.DatabaseError, ValueError) as exc:
        return json.dumps({"ok": False, "message": f"Could not restore: {exc}"})
    finally:
        if os.path.exists(path):
            os.remove(path)


def erase_all():
    from jesse_farm import config, db
    for name in os.listdir(DATA_DIR):
        p = os.path.join(DATA_DIR, name)
        if name.startswith("jesse_farm.db") and os.path.isfile(p):
            os.remove(p)
    if os.path.isdir(config.BACKUP_DIR):
        for name in os.listdir(config.BACKUP_DIR):
            os.remove(os.path.join(config.BACKUP_DIR, name))
    db.init_db(log=lambda *a: None)
    return status()


# ---------------------------------------------------------------------------------------------- the device page
def _register_device_page():
    from jesse_farm.ui import bare_page, card, e, layout
    from jesse_farm.web import route

    @route("/device", ("GET",), public=True, needs_farm=False)
    def device(req):
        st = json.loads(status())
        intro = card(
            "<p>This copy of JESSE FMS runs entirely in your browser. Your farms, animals and money are saved "
            "<b>only on this device, in this browser</b>. Nothing is sent to a server, and other devices cannot see it.</p>"
            "<ul><li>Download a backup regularly and keep it somewhere safe (USB stick, email to yourself).</li>"
            "<li>Clearing this browser's site data, or using a private window, deletes the data.</li>"
            "<li>To move to another device, download a backup here and restore it there.</li>"
            "<li>The backup file also opens in the desktop version (<code>python run.py --restore FILE.db</code>).</li></ul>",
            "Where your data is")
        btn = 'class="btn" type="button"'
        data = card(
            f'<p class="muted">{st["farms"]} farm(s) and {st["users"]} account(s) on this device.</p>'
            f'<div class="actions"><button {btn} data-shell="export">Download backup (.db)</button>'
            f'<button class="btn sec" type="button" data-shell="import">Restore from a backup file…</button></div>'
            '<p class="muted">Restore accepts a backup from this page, from Settings, from the desktop version '
            '(<code>jesse_farm.db</code>), or an old <code>livestock.db</code> from livestock_app.py, which is upgraded. '
            'Your current data is backed up first.</p>',
            "Backup and restore")
        if st["demo"]:
            demo = card("<p>Demonstration data is loaded. Sign in with <b>demo@jesse.farm</b> / <b>demo1234</b>. "
                        "Other demo accounts: manager@jesse.farm / manager1234, worker@jesse.farm / worker1234, "
                        "vet@jesse.farm / vet12345.</p><p class='muted'>All demo names, prices and events are fictional.</p>",
                        "Demonstration data")
        else:
            demo = card("<p>Load two fictional farms, one in Zambia and one in Rwanda, with animals, health, breeding, "
                        "feeding, sales and money, plus demo accounts for each role.</p>"
                        f'<button {btn} data-shell="demo">Load demonstration data</button>', "Try it with demonstration data")
        danger = card("<p>Delete every farm, account and backup stored in this browser.</p>"
                      '<button class="btn danger" type="button" data-shell="erase">Erase all data on this device</button>',
                      "Danger zone")
        body = intro + data + demo + danger
        if req.user:
            return layout(req, "Backup & device", body, "device") if req.farm else bare_page(
                "Backup & device", f'<div class="auth" style="max-width:720px"><h1>Backup &amp; device</h1>{body}'
                                   '<p><a href="/farms/new">Register a farm</a></p></div>', req)
        return bare_page("Backup & device", '<div class="auth" style="max-width:720px"><div class="logo">JESSE FARM<br>'
                         f'MANAGEMENT SYSTEM</div><h1>Backup &amp; device</h1>{body}'
                         '<p style="text-align:center"><a class="btn sec" href="/login">Go to sign in</a> '
                         '<a class="btn sec" href="/register">Create an account</a></p></div>')

    return device


if __name__ == "__main__":  # quick manual check on a normal computer: python bridge.py jesse_core.py
    print(start(sys.argv[1] if len(sys.argv) > 1 else "jesse_core.py"))
