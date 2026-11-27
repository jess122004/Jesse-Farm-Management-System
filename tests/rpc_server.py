"""Test server: serves the site, and runs the real bridge.py for a stand-in Pyodide (see fake_pyodide.js)."""
import json
import os
import shutil
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

SITE, DATA = sys.argv[1], sys.argv[2]
shutil.rmtree(DATA, ignore_errors=True)
os.makedirs(DATA)
os.environ["JESSE_DATA"] = DATA
sys.path.insert(0, SITE)
import bridge  # noqa: E402

FILES = {}  # path in the fake browser FS -> real path


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=SITE, **k)

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n)
        if self.path.startswith("/__write"):
            real = os.path.join(DATA, "upload-" + os.path.basename(self.path.split("=", 1)[1]))
            open(real, "wb").write(raw)
            FILES[self.path.split("=", 1)[1]] = real
            out = "ok"
        else:
            msg = json.loads(raw)
            fn, args = msg["fn"], msg["args"]
            if fn == "start":
                args = [os.path.join(SITE, "jesse_core.py")]
            if fn == "import_db":
                args = [FILES[args[0]]]
            out = getattr(bridge, fn)(*args)
        data = out.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


ThreadingHTTPServer(("127.0.0.1", 8765), H).serve_forever()
