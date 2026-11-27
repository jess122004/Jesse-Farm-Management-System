"""Drives bridge.handle() exactly the way index.html does (cookies, redirects, form posts) and checks every page."""
import json
import os
import re
import shutil
import sys
import urllib.parse
from html.parser import HTMLParser

DATA = "/tmp/jesse-test"
shutil.rmtree(DATA, ignore_errors=True)
os.environ["JESSE_DATA"] = DATA
SITE = sys.argv[1]
sys.path.insert(0, SITE)
import bridge  # noqa: E402

print("start:", bridge.start(os.path.join(SITE, "jesse_core.py")))

FAIL = []


class Browser:
    def __init__(self):
        self.cookie = ""
        self.url = "/"

    def req(self, method, url, data=None):
        body = urllib.parse.urlencode(data or {}, doseq=True)
        for _ in range(6):
            r = json.loads(bridge.handle(method, url, body, self.cookie, self.url))
            if r["cookie"]:
                val = r["cookie"].split(";")[0]
                self.cookie = "" if ("Max-Age=0" in r["cookie"] or val == "sid=") else val
            if r["status"] == 303:
                method, url, body = "GET", r["location"], ""
                continue
            break
        if not r.get("filename"):
            self.url = url
        r["url"] = url
        return r

    def get(self, url):
        return self.req("GET", url)

    def csrf(self, html):
        m = re.search(r'name="csrf" value="([^"]+)"', html)
        return m.group(1) if m else ""

    def post(self, url, data, page=None):
        html = self.get(page or "/settings")["html"]
        d = dict(data)
        d["csrf"] = self.csrf(html)
        return self.req("POST", url, d)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href", "").startswith("/"):
            self.links.append(a["href"])


def check(cond, msg):
    if not cond:
        FAIL.append(msg)
        print("  FAIL:", msg)


def crawl(b, start="/", limit=400):
    seen, queue, n = set(), [start], 0
    while queue and n < limit:
        url = queue.pop(0)
        if url in seen or "/delete" in url or url.startswith("/logout"):
            continue
        seen.add(url)
        r = b.get(url)
        n += 1
        check(r["status"] in (200, 403), f"GET {url} -> {r['status']}")
        if r.get("html"):
            check("Something went wrong" not in r["html"], f"error page at {url}")
            p = Links()
            p.feed(r["html"])
            queue += [h for h in p.links if h not in seen]
    return seen


b = Browser()
# --- first run: device page, demo data
r = b.get("/")
check(r["url"] == "/login" and "Sign in" in r["html"], "/ redirects to sign-in when signed out")
check("/device" in r["html"], "sign-in page links to the device page")
r = b.get("/device")
check(r["status"] == 200 and 'data-shell="demo"' in r["html"], "device page offers demo data")
print("demo:", bridge.load_demo())
r = b.post("/login", {"email": "demo@jesse.farm", "password": "demo1234"}, page="/login")
check(r["url"] == "/" and "Dashboard" in r["html"], "demo sign-in reaches dashboard")
check("Backup &amp; device" in r["html"] or "Backup & device" in r["html"], "nav shows Backup & device")

pages = crawl(b)
print(f"crawled {len(pages)} pages as owner (Zambia farm)")

# --- switch farm (the onchange form) and crawl the Rwanda farm
html = b.get("/farms")["html"]
fids = re.findall(r'name="farm_id" value="(\d+)"', html)
r = b.post("/farms/switch", {"farm_id": fids[0]}, page="/farms")
check("Now working on" in r["html"], "farm switch")
print("switched to:", re.search(r'<div class="farm"><b>([^<]+)', r["html"]).group(1))
pages2 = crawl(b)
print(f"crawled {len(pages2)} pages on second farm")

# --- write flows
r = b.post("/animals/new", {"animal_type": "goat", "gender": "female", "acquisition_method": "purchased",
                            "acquisition_date": "2026-10-01", "purchase_price": "45000", "name": "Test goat", "weight_kg": "30"},
           page="/animals/new")
check(r["url"].startswith("/animals/") and "Animal registered" in r["html"], "register animal")
aid = r["url"].rsplit("/", 1)[1]
r = b.post(f"/animals/{aid}/weight", {"weight_kg": "31.5", "date": "2026-11-20"}, page=f"/animals/{aid}")
check("Weight recorded" in r["html"], "add weight")
r = b.post("/health/new", {"scope": "one", "livestock_id": aid, "record_type": "treatment", "title": "Deworm",
                           "date": "2026-11-21", "cost": "3000", "disease": "Internal parasites (worms)"}, page="/health/new")
check("Health record saved" in r["html"], "health record")
r = b.post("/finance/new?kind=income", {"kind": "income", "date": "2026-11-22", "category": "milk", "amount": "12000",
                                        "description": "Milk"}, page="/finance/new?kind=income")
check("Saved." in r["html"], "finance entry")
r = b.post("/tasks/new", {"title": "Check fence", "priority": "high", "status": "pending", "due_date": "2026-11-30"}, page="/tasks/new")
check("Task saved" in r["html"], "task")
r = b.post("/sales/new", {"animal": [aid], f"price_{aid}": "60000", "date": "2026-11-25", "buyer_name": "Test buyer",
                          "payment_method": "cash"}, page="/sales/new")
check("Sale recorded" in r["html"], "sale")
r = b.post("/animals/new", {"animal_type": "goat", "gender": "female", "acquisition_method": "born",
                            "acquisition_date": "2026-11-31"}, page="/animals/new")
check(r["status"] == 200 and "must be a real date" in r["html"], "validation error shown")
r = b.get("/export/animals.csv")
check(r.get("filename", "").endswith(".csv") and r["file_b64"], "CSV export is a download")
r = b.post("/settings/backup", {}, page="/settings")
check("Backup saved" in r["html"], "backup from settings")
name = re.search(r'href="/settings/backups/([^"]+)"', r["html"]).group(1)
r = b.get(f"/settings/backups/{name}")
check(r.get("filename") == name, "download settings backup")
check("Backup &amp; device" in b.get("/settings")["html"], "settings points to device page")

# --- roles: worker cannot see finance
w = Browser()
w.post("/login", {"email": "worker@jesse.farm", "password": "worker1234"}, page="/login")
check(w.get("/finance")["status"] == 403, "worker blocked from finance")
crawl(w)

# --- sign out
r = b.post("/logout", {}, page="/")
check(r["url"] == "/login" and b.cookie == "", "sign out clears cookie")

# --- export, restore user's databases, erase
exported = bridge.export_db()
check(len(exported) > 1000, "export_db")
for f in sys.argv[2:]:
    tmp = os.path.join(DATA, "upload.db")
    shutil.copy(f, tmp)
    res = json.loads(bridge.import_db(tmp))
    check(res["ok"], f"import {os.path.basename(f)}: {res['message']}")
    print("import", os.path.basename(f), "->", res["message"], bridge.status())
    with open(bridge.DB_FILE, "rb") as fh:
        hd = fh.read(20)
    check(hd[18] == 1 and hd[19] == 1, "restored db is in rollback-journal mode")
    # crawl it with a fresh admin session made by resetting a password
    import sqlite3
    from jesse_farm.security import hash_password
    c = sqlite3.connect(bridge.DB_FILE)
    email = c.execute("SELECT email FROM users ORDER BY id LIMIT 1").fetchone()[0]
    c.execute("UPDATE users SET password_hash=? WHERE email=?", (hash_password("testpass99"), email))
    c.commit()
    c.close()
    x = Browser()
    r = x.post("/login", {"email": email, "password": "testpass99"}, page="/login")
    check(r["status"] == 200, f"sign in to imported {f}")
    print("  crawled", len(crawl(x)), "pages of", os.path.basename(f), "as", email)
bad = os.path.join(DATA, "bad.db")
open(bad, "wb").write(b"not a database" * 20)
check(not json.loads(bridge.import_db(bad))["ok"], "rejects non-database file")
print("erase:", bridge.erase_all())

print("\nRESULT:", "ALL PASSED" if not FAIL else f"{len(FAIL)} FAILED")
sys.exit(1 if FAIL else 0)
