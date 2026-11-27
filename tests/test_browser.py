"""Clicks through index.html in real Chrome (Python runs in the test server instead of Pyodide)."""
import os
import sys

from playwright.sync_api import sync_playwright

FAKE = open(os.path.join(os.path.dirname(__file__), "fake_pyodide.js")).read()
SHOTS = sys.argv[1]
UPLOAD = sys.argv[2]
os.makedirs(SHOTS, exist_ok=True)
FAIL = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAIL.append(msg)


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    ctx = browser.new_context(viewport={"width": 1280, "height": 820}, accept_downloads=True)
    ctx.route("https://cdn.jsdelivr.net/**", lambda r: r.fulfill(body=FAKE, content_type="text/javascript"))
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto("http://127.0.0.1:8765/")
    page.wait_for_selector("#frame", state="visible", timeout=20000)
    f = page.frame_locator("#frame")
    page.wait_for_timeout(300)
    check("#/device" in page.url, "empty database opens the Backup & device page")
    page.screenshot(path=f"{SHOTS}/1-device-first-run.png")

    f.get_by_text("Load demonstration data").click()
    page.wait_for_selector("#toast", state="visible")
    check("demo@jesse.farm" in page.inner_text("#toast"), "demo loaded toast")
    f.locator("#email").fill("demo@jesse.farm")
    f.locator("#password").fill("demo1234")
    f.get_by_role("button", name="Sign in").click()
    f.get_by_role("heading", name="Dashboard").wait_for()
    check(page.url.endswith("#/"), "signed in, dashboard")
    page.wait_for_timeout(300)
    page.screenshot(path=f"{SHOTS}/2-dashboard.png")

    f.locator("aside nav a[href=\"/animals\"]").click()
    f.get_by_role("heading", name="Livestock").wait_for()
    check(page.url.endswith("#/animals"), "nav link -> #/animals")
    f.locator("table a").first.click()
    f.get_by_text("Medical history").wait_for()
    check("#/animals/" in page.url, "animal detail")
    page.go_back()
    f.get_by_role("heading", name="Livestock").wait_for()
    check(page.url.endswith("#/animals"), "browser Back works")

    # GET filter form (chips + search)
    f.locator("#q").fill("Boran")
    f.get_by_role("button", name="Search").click()
    page.wait_for_timeout(400)
    check("q=Boran" in page.url, "GET search form keeps query in the address")

    # register an animal (POST form with redirect)
    f.get_by_text("+ Register animal").click()
    f.locator("#name").fill("Browser test cow")
    f.locator("#acquisition_date").fill("2026-11-01")
    f.get_by_role("button", name="Register animal").click()
    f.get_by_text("Animal registered.").wait_for()
    check(True, "POST form, redirect and flash message")
    # delete with the confirm() dialog (accepted by the handler above)
    f.get_by_role("button", name="Delete").click()
    f.get_by_text("deleted.").wait_for()
    check(page.url.endswith("#/animals"), "delete with confirm dialog")

    # farm switcher uses form.submit() from onchange
    f.locator('select[name="farm_id"]').select_option(index=1)
    f.get_by_text("Now working on").wait_for()
    check(True, "farm switcher (onchange form.submit)")

    # CSV download
    f.locator("aside nav a[href=\"/animals\"]").click()
    with page.expect_download() as dl:
        f.get_by_text("Export CSV").click()
    check(dl.value.suggested_filename.endswith(".csv"), f"CSV download {dl.value.suggested_filename}")

    # reports page anchors
    f.locator("aside nav a", has_text="Reports").click()
    f.get_by_role("heading", name="Reports").wait_for()
    f.locator("a.chip", has_text="Breeding").click()
    check(page.url.endswith("#/reports"), "in-page anchor does not navigate away")
    page.screenshot(path=f"{SHOTS}/3-reports.png")

    # device page from the nav: backup download, then restore uploaded db
    f.locator("aside nav a", has_text="Backup & device").click()
    with page.expect_download() as dl:
        f.get_by_text("Download backup (.db)").click()
    check(dl.value.suggested_filename.startswith("jesse-backup-"), "backup download")
    page.screenshot(path=f"{SHOTS}/4-device-signed-in.png")
    with page.expect_file_chooser() as fc:
        f.get_by_text("Restore from a backup file").click()
    fc.value.set_files(UPLOAD)
    f.get_by_role("heading", name="Sign in").wait_for()
    check("restored" in page.inner_text("#toast"), "restore from uploaded file -> sign in")
    check(page.evaluate("localStorage.getItem('jesse.sid')") is None, "session cleared after restore")

    # sign in to the restored database, reload: still signed in
    f.locator("#email").fill("demo@jesse.farm")
    f.locator("#password").fill("demo1234")
    f.get_by_role("button", name="Sign in").click()
    f.get_by_role("heading", name="Dashboard").wait_for()
    page.reload()
    page.wait_for_selector("#frame", state="visible", timeout=20000)
    f.get_by_role("heading", name="Dashboard").wait_for()
    check(True, "reload keeps you signed in")

    # second tab is refused
    p2 = ctx.new_page()
    p2.goto("http://127.0.0.1:8765/")
    p2.wait_for_selector("#booterr", state="visible", timeout=10000)
    check("already open" in p2.inner_text("#booterr"), "second tab is blocked")
    p2.screenshot(path=f"{SHOTS}/5-second-tab.png")
    p2.close()

    # sign out
    f.get_by_role("button", name="Sign out").click()
    f.get_by_role("heading", name="Sign in").wait_for()
    check(True, "sign out")
    n = page.evaluate("window.__syncs"); check(n >= 4, f"storage saved after every change ({n} saves since reload)")

    # phone size
    m = browser.new_context(viewport={"width": 390, "height": 800}, is_mobile=True, has_touch=True)
    m.route("https://cdn.jsdelivr.net/**", lambda r: r.fulfill(body=FAKE, content_type="text/javascript"))
    mp = m.new_page()
    mp.goto("http://127.0.0.1:8765/#/login")
    mp.wait_for_selector("#frame", state="visible", timeout=20000)
    mf = mp.frame_locator("#frame")
    mf.locator("#email").fill("demo@jesse.farm")
    mf.locator("#password").fill("demo1234")
    mf.get_by_role("button", name="Sign in").click()
    mf.get_by_role("heading", name="Dashboard").wait_for()
    mp.wait_for_timeout(300)
    mp.screenshot(path=f"{SHOTS}/6-phone.png")
    mf.locator(".menu-btn").tap()
    mp.wait_for_timeout(400)
    mp.screenshot(path=f"{SHOTS}/7-phone-menu.png")
    check(True, "phone layout")

    check(not errors, f"no JavaScript errors {errors}")
    browser.close()

print("\nRESULT:", "ALL PASSED" if not FAIL else f"{len(FAIL)} FAILED: {FAIL}")
sys.exit(1 if FAIL else 0)
