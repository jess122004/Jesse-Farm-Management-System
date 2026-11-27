# JESSE FARM MANAGEMENT SYSTEM — browser edition

Livestock records, health, breeding, feeding, stock, sales and money for farms in Zambia and Rwanda.
This edition runs **entirely in the web browser**, so it can be hosted free on GitHub Pages. There is no server.

**Live:** `https://YOUR-USERNAME.github.io/YOUR-REPOSITORY/`
**Demo:** open the link, choose *Load demonstration data*, then sign in with `demo@jesse.farm` / `demo1234`.

## How it works

| File | What it does |
| --- | --- |
| `jesse_core.py` | The complete system, **unchanged** from the desktop version (all modules in one file). |
| `bridge.py` | Runs `jesse_core.py` in the browser. It replaces the `http.server` socket with a function call, keeps the SQLite database in browser storage and adds the *Backup & device* page. |
| `index.html` | Loads [Pyodide](https://pyodide.org) (Python compiled to WebAssembly), mounts browser storage (IndexedDB) and sends every link click and form to `bridge.py`. |
| `tests/` | `test_bridge.py` loads every page and submits the main forms; `test_browser.py` clicks through the real page in Chrome. |

Your data is stored only in the browser you use. Download a backup from **Backup & device** regularly.
A backup from the browser opens in the desktop version, and the reverse also works.

## Publish on GitHub Pages (about 10 minutes)

1. Create a GitHub account if needed, then a **new public repository** (e.g. `jesse-fms`). Free GitHub Pages needs a public repository.
2. On the empty repository page, click **uploading an existing file**. Drag in **everything in this folder, including the
   hidden `.github` folder** (on Windows, turn on *View → Show hidden items*; on a Mac press Cmd+Shift+. in the folder).
   Click **Commit changes**.
3. Go to **Settings → Pages**. Under *Build and deployment → Source*, choose **GitHub Actions**.
4. Open the **Actions** tab. The workflow *Test and publish to GitHub Pages* runs the tests and then publishes
   the site (about 2 minutes). Run it with **Run workflow** if it has not started.
5. The site is at `https://YOUR-USERNAME.github.io/YOUR-REPOSITORY/`. Put that link at the top of this README.

**If the `.github` folder did not upload**, use the simpler route instead. In step 3, choose
*Deploy from a branch*, then branch **main** and folder **/ (root)**, then **Save**. The site appears after
1–2 minutes, but the tests no longer run before each publish.

Every later change you commit to `main` is published again automatically.

> **Never upload `.db` files.** They contain farm records, email addresses and password hashes, and a public
> repository is visible to everyone. `.gitignore` blocks them when you use git.

## Run the tests on your computer

```
python tests/test_bridge.py .                      # every page and the main forms (Python 3.11+)
python tests/test_bridge.py . path/to/jesse_farm.db   # also restores and checks your own database
```

## Limits of the browser edition

* Data is not shared between devices or people. Each browser keeps its own copy, and you move it with backup and restore.
* Sign-in and roles control who uses the app *in that browser*. They do not protect the data from someone who has the device.
* The first visit needs internet (Python downloads, about 10 MB). Later visits are faster because the browser caches it.
* Only one tab at a time can have the app open.
