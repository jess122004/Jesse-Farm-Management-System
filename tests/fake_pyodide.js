// Stand-in for pyodide.js in tests: same API surface index.html uses, calls forwarded to the real bridge.py.
function rpc(fn, args) {
  const x = new XMLHttpRequest();
  x.open("POST", "/__rpc", false);
  x.send(JSON.stringify({ fn, args }));
  if (x.status !== 200) throw new Error("rpc failed " + x.status);
  return x.responseText;
}
window.__syncs = 0;
window.loadPyodide = async function () {
  return {
    loadPackage: async () => {},
    runPython: () => {},
    FS: {
      filesystems: { IDBFS: {} },
      mkdirTree: () => {},
      mount: () => {},
      syncfs: (populate, cb) => { window.__syncs++; setTimeout(() => cb(null), 5); },
      writeFile: (path, data) => {
        if (!path.startsWith("/tmp/")) return;
        const x = new XMLHttpRequest();
        x.open("POST", "/__write?path=" + path, false);
        x.send(data);
      },
    },
    pyimport: () => ({
      start: p => rpc("start", [p]),
      handle: (...a) => rpc("handle", a),
      load_demo: () => rpc("load_demo", []),
      export_db: () => rpc("export_db", []),
      import_db: p => rpc("import_db", [p]),
      erase_all: () => rpc("erase_all", []),
    }),
  };
};
