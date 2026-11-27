"""
JESSE FARM MANAGEMENT SYSTEM - Streamlit version.

Run locally:      streamlit run app.py
Deploy:           Streamlit Community Cloud, main file = app.py

All the system's rules (database, validation, permissions, money, breeding, stock...) still live in
jesse_core.py, unchanged. This file only draws the screens with Streamlit and passes what the user
typed to the same functions the original web pages used, so the behaviour is identical.
"""
import datetime as dt
import os
import sys
import threading
import types

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jesse_core  # noqa: E402,F401  (registers the jesse_farm package)
from jesse_farm import config, countries, db, security, ui, web  # noqa: E402
from jesse_farm.views import animals as v_animals  # noqa: E402
from jesse_farm.views import auth as v_auth  # noqa: E402
from jesse_farm.views import breeding as v_breeding  # noqa: E402
from jesse_farm.views import common  # noqa: E402
from jesse_farm.views import exports as v_exports  # noqa: E402
from jesse_farm.views import farms as v_farms  # noqa: E402
from jesse_farm.views import feeding as v_feeding  # noqa: E402
from jesse_farm.views import finance as v_finance  # noqa: E402
from jesse_farm.views import health as v_health  # noqa: E402
from jesse_farm.views import inventory as v_inventory  # noqa: E402
from jesse_farm.views import reports as v_reports  # noqa: E402
from jesse_farm.views import sales as v_sales  # noqa: E402
from jesse_farm.views import settings as v_settings  # noqa: E402
from jesse_farm.views import tasks as v_tasks  # noqa: E402

st.set_page_config(page_title=config.APP_SHORT, page_icon="🐄", layout="wide")
ss = st.session_state
TODAY = dt.date.today
OLDEST = dt.date(1970, 1, 1)
FAR = dt.date(2100, 12, 31)


# ============================================================================ setup
@st.cache_resource
def _init_database():
    db.init_db(log=lambda *a: None)
    if os.environ.get("JESSE_DEMO") == "1":
        from jesse_farm.demo import create_demo
        create_demo()
    return True


_init_database()

# Collect every Form the original code creates, so its error messages can be shown in Streamlit.
if not hasattr(ui, "_st_local"):
    ui._st_local = threading.local()
    _orig_form_init = ui.Form.__init__

    def _form_init(self, data, _orig=_orig_form_init):
        _orig(self, data)
        forms = getattr(ui._st_local, "forms", None)
        if forms is not None:
            forms.append(self)

    ui.Form.__init__ = _form_init


class StRequest(web.Request):
    """The original Request object, but the signed-in user and farm come from Streamlit's session."""

    def __init__(self, method="GET", form=None, lists=None, query=None):
        self.handler = types.SimpleNamespace(headers={})
        self.method = method
        self.path = "/"
        self.query = {k: "" if v is None else str(v) for k, v in (query or {}).items()}
        self.raw_query = ""
        self.form = {k: "" if v is None else str(v) for k, v in (form or {}).items()}
        self.form_lists = {k: [str(x) for x in v] for k, v in (lists or {}).items()}
        for k, v in self.form.items():
            self.form_lists.setdefault(k, [v])
        self.conn = db.connect()
        self.session = {"token": "streamlit", "csrf": "streamlit", "flash": ""}
        self.user = self.farm = self.role = None
        self.new_cookie = None
        uid = ss.get("uid")
        if uid:
            self.user = self.one("SELECT * FROM users WHERE id=?", (uid,))
        if not self.user:
            ss.pop("uid", None)
            self.session = None
            return
        if ss.get("fid"):
            self._set_farm(ss["fid"])
        if not self.farm:
            first = self.one("SELECT farm_id FROM memberships WHERE user_id=? ORDER BY id LIMIT 1", (self.user["id"],))
            if first:
                self.switch_farm(first["farm_id"])
            else:
                ss.pop("fid", None)

    def switch_farm(self, farm_id):
        if not self._set_farm(farm_id):
            return False
        ss["fid"] = farm_id
        return True

    def login(self, user_id):
        ss["uid"] = user_id
        ss.pop("fid", None)

    def logout(self):
        sign_out_state()

    def flash(self, text, bad=False):
        ss.setdefault("flashes", []).append((bad, text))

    def pop_flash(self):
        return ""


def sign_out_state():
    for k in list(ss.keys()):
        del ss[k]


# ============================================================================ navigation
PAGES = [("dashboard", "▦ Dashboard"), ("animals", "🐄 Livestock"), ("breeding", "♀ Breeding"), ("health", "✚ Animal health"),
         ("feeding", "🌾 Feeding"), ("inventory", "📦 Inventory"), ("tasks", "✓ Tasks"), ("sales", "🧾 Livestock sales"),
         ("finance", "💰 Finance"), ("reports", "📊 Reports"), ("farms", "🏡 My farms"), ("settings", "⚙ Settings")]
PAGE_KEYS = [p for p, _ in PAGES]


def go(page=None, view="list", rid=None, preset=None):
    """Open a page (and optionally a record) on the next run."""
    if page:
        ss["_nav"] = page
    ss["view"] = view
    ss["rid"] = rid
    ss["preset"] = preset or {}
    ss["gen"] = ss.get("gen", 0) + 1  # fresh widget keys, so old table selections are forgotten
    st.rerun()


def go_location(location):
    """Turn a redirect address of the original web app (e.g. /animals/12) into a Streamlit page."""
    path, _, query = (location or "/").partition("?")
    parts = [p for p in path.split("/") if p]
    if parts and parts[0] == "login":
        sign_out_state()
        st.rerun()
    if not parts:
        go("dashboard")
    page = parts[0] if parts[0] in PAGE_KEYS else "dashboard"
    view, rid = "list", None
    if len(parts) > 1:
        if parts[1].isdigit():
            view, rid = "detail", int(parts[1])
        elif parts[1] in ("new", "team", "edit", "pnl"):
            view = parts[1]
    preset = {}
    if query:
        for pair in query.split("&"):
            k, _, v = pair.partition("=")
            preset[k] = v
    go(page, view, rid, preset)


def key(name):
    return f"{name}_{ss.get('gen', 0)}"


# ============================================================================ calling the original logic
def act(fn, *args, form=None, lists=None, query=None):
    """Send a form to one of the original page functions, exactly as the browser used to.

    Success -> the function redirects; we follow the redirect. Problems -> the error messages are shown."""
    ui._st_local.forms = []
    req = StRequest("POST", form, lists, query)
    target, errors = None, {}
    try:
        fn(req, *[str(a) for a in args])
        for f in ui._st_local.forms:
            errors.update(f.errors)
        if not errors:
            errors["_"] = "Please check the details and try again."
    except web.Redirect as r:
        target = r.location
    except web.Forbidden as f:
        errors["_"] = f.message
    except web.NotFound:
        errors["_"] = "That record doesn't exist, or it belongs to another farm."
    except Exception as exc:  # the original code rolls back; tell the user what happened
        errors["_"] = f"Something went wrong, nothing was saved: {exc}"
    finally:
        ui._st_local.forms = None
        req.conn.close()
    if target is not None:
        go_location(target)
    for name, msg in errors.items():
        generic = msg.startswith("Choose one of") or msg.startswith("Please check")
        st.error(f"{name.replace('_id', '').replace('_', ' ').capitalize()}: {msg}" if generic and name != "_" else msg)
    return False


def show_flashes():
    for bad, text in ss.pop("flashes", []):
        (st.error if bad else st.success)(text)


# ============================================================================ small widgets
def iso(d):
    return d.isoformat() if d else ""


def as_date(value):
    return ui.parse_date(value) if value else None


def pick(label, options, default=None, blank=None, k=None, help=None):
    """Selectbox over (value, text[, group]) tuples; returns the value as text ('' for the blank option)."""
    values, labels = [], {}
    if blank is not None:
        values.append("")
        labels[""] = blank
    for o in options:
        v = str(o[0])
        values.append(v)
        labels[v] = f"{o[2]} · {o[1]}" if len(o) > 2 and o[2] else str(o[1])
    d = "" if default is None else str(default)
    index = values.index(d) if d in values else 0
    if not values:
        values, labels = [""], {"": blank or "— nothing to choose —"}
    return st.selectbox(label, values, index=index, format_func=lambda v: labels.get(v, v), key=k, help=help)


def date_in(label, value=None, k=None, past_only=True, required=False, help=None):
    v = as_date(value) if isinstance(value, str) else value
    if required and v is None:
        v = TODAY()
    return st.date_input(label, value=v, min_value=OLDEST, max_value=TODAY() if past_only else FAR,
                         format="DD/MM/YYYY", key=k, help=help)


def num_in(label, value=None, k=None, step=None, help=None):
    v = None if value in (None, "") else float(value)
    return st.number_input(label, value=v, min_value=0.0, step=step, key=k, help=help, placeholder="")


def num_text(v):
    if v is None:
        return ""
    return str(int(v)) if float(v).is_integer() else str(v)


def table(rows, empty="Nothing to show yet."):
    if not rows:
        st.info(empty)
        return
    st.dataframe(pd.DataFrame(rows).astype(str), hide_index=True, use_container_width=True)


def table_pick(rows, ids, name, empty="Nothing to show yet.", hint="Click a row to open it."):
    """A table where clicking a row returns that row's record id."""
    if not rows:
        st.info(empty)
        return None
    if hint:
        st.caption(hint)
    ev = st.dataframe(pd.DataFrame(rows).astype(str), hide_index=True, use_container_width=True,
                      on_select="rerun", selection_mode="single-row", key=key(name))
    chosen = ev.selection.rows if ev and hasattr(ev, "selection") else []
    return ids[chosen[0]] if chosen else None


def bars(pairs, horizontal=True, ylabel="Count"):
    if not pairs:
        st.info("No data yet.")
        return
    df = pd.DataFrame({"": [p[0] for p in pairs], ylabel: [p[1] or 0 for p in pairs]}).set_index("")
    st.bar_chart(df, horizontal=horizontal)


def pair_chart(series, names=("Income", "Expenses")):
    """series: {YYYY-MM: [a, b]}"""
    df = pd.DataFrame([{"Month": m, names[0]: v[0] or 0, names[1]: v[1] or 0} for m, v in series.items()]).set_index("Month")
    st.bar_chart(df, stack=False, color=["#2e7d32", "#c62828"])


def metrics(items):
    cols = st.columns(len(items))
    for c, (label, value) in zip(cols, items):
        c.metric(label, value)


def confirm(label, k, question):
    """A button that asks 'are you sure?' before returning True."""
    if ss.get("confirm") == k:
        st.warning(question)
        c1, c2, _ = st.columns([1, 1, 4])
        if c1.button("Yes, continue", key=k + "_yes", type="primary"):
            ss.pop("confirm", None)
            return True
        if c2.button("Cancel", key=k + "_no"):
            ss.pop("confirm", None)
            st.rerun()
        return False
    if st.button(label, key=k):
        ss["confirm"] = k
        st.rerun()
    return False


def csv_button(R, name):
    if not R.can("export") or name not in v_exports.EXPORTS:
        return
    perm, sql = v_exports.EXPORTS[name]
    if perm and not R.can(perm):
        return
    cur = R.conn.execute(sql, (R.fid,))
    data = v_exports.to_csv([c[0] for c in cur.description], cur.fetchall())
    st.download_button("⬇ Export CSV", data.encode("utf-8"), f"jesse-{name}-{R.country}-{TODAY().isoformat()}.csv",
                       "text/csv", key=key("csv_" + name))


def back(label="← Back to list"):
    if st.button(label, key=key("back")):
        go(view="list")


def L(choices, value):
    return ui.label(choices, value)


# ============================================================================ sign in / register
def page_auth():
    st.title("🐄 JESSE FARM MANAGEMENT SYSTEM")
    st.caption("Livestock records, health, breeding and money for farms in Zambia and Rwanda")
    show_flashes()
    t1, t2 = st.tabs(["Sign in", "Create an account"])
    with t1:
        with st.form("login"):
            email = st.text_input("Email", autocomplete="email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Sign in", type="primary", use_container_width=True):
                conn = db.connect()
                user = conn.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
                conn.close()
                if user and security.check_password(password, user["password_hash"]):
                    ss["uid"] = user["id"]
                    go("dashboard")
                st.error("Incorrect email or password.")
    with t2:
        st.caption("Next you will register your farm in Zambia or Rwanda.")
        with st.form("register"):
            c1, c2 = st.columns(2)
            first = c1.text_input("First name *")
            last = c2.text_input("Last name")
            email = st.text_input("Email *")
            phone = st.text_input("Phone (optional)", placeholder="+260… or +250…")
            pw = st.text_input("Password *", type="password", help="At least 8 characters, not only numbers")
            pw2 = st.text_input("Confirm password *", type="password")
            if st.form_submit_button("Create account", type="primary", use_container_width=True):
                act(v_auth.register, form={"first_name": first, "last_name": last, "email": email, "phone": phone,
                                           "password": pw, "confirm": pw2})
    conn = db.connect()
    no_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
    demo_loaded = conn.execute("SELECT 1 FROM users WHERE email='demo@jesse.farm'").fetchone() is not None
    conn.close()
    if demo_loaded:
        st.info("Demonstration data is loaded. Sign in with **demo@jesse.farm** / **demo1234**.")
    elif no_users:
        with st.expander("Try it with demonstration data"):
            st.write("Loads two fictional farms (Zambia and Rwanda) with animals, health, breeding, sales and money. "
                     "Sign in afterwards with demo@jesse.farm / demo1234.")
            if st.button("Load demonstration data"):
                from jesse_farm.demo import create_demo
                create_demo()
                st.rerun()


# ============================================================================ register / switch farm
def farm_form(R, code, data, prefix, editing=False):
    c = countries.country(code)
    st.info(f"Country: **{c['name']}** · money is recorded in **{c['currency']}** ({c['currency_name']})")
    with st.form(prefix):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Farm name *", value=data.get("name") or "", placeholder="e.g. Kafue Valley Farm")
            loc_default = f"{data.get('province')}|{data.get('district')}" if data.get("district") else ""
            location = pick("District (grouped by province) *", countries.district_options(code), loc_default, blank="— choose district —")
            local_area = st.text_input(c["area_label"], value=data.get("local_area") or "", help=c["area_hint"])
            address = st.text_input("Address / directions", value=data.get("address") or "")
            size = num_in("Farm size (hectares)", data.get("size_ha"), step=0.5)
            scale = pick("Scale", v_farms.SCALE, data.get("farm_scale") or "small",
                         help="Rwanda's 2026 law classifies farmers by scale; the criteria come by ministerial order." if code == "RW" else None)
        with c2:
            ownership = pick("Ownership", v_farms.OWNERSHIP, data.get("ownership") or "individual")
            owner = st.text_input("Registered owner name", value=data.get("owner_name") or "")
            reg = st.text_input("Registration / premises number (optional)", value=data.get("registration_no") or "")
            phone = st.text_input("Farm phone", value=data.get("phone") or "")
            email = st.text_input("Farm email", value=data.get("email") or "")
        if st.form_submit_button("Save farm details" if editing else "Register farm", type="primary", use_container_width=True):
            return {"country_code": code, "name": name, "location": location, "local_area": local_area, "address": address,
                    "size_ha": num_text(size), "farm_scale": scale, "ownership": ownership, "owner_name": owner,
                    "registration_no": reg, "phone": phone, "email": email}
    return None


def farm_new(R):
    st.header("Register a farm")
    if ss.get("preset", {}).get("welcome"):
        st.write("Welcome! Start by registering your farm. Choose the country it is in — this sets the currency, "
                 "the district list and the country-specific rules.")
    names = {code: f"{c['name']} — money in {c['currency']}, {len(c['provinces'])} provinces, "
                   f"{sum(len(v) for v in c['provinces'].values())} districts" for code, c in countries.COUNTRIES.items()}
    code = st.radio("Which country is the farm in?", list(names), format_func=names.get, key=key("newfarm_country"))
    values = farm_form(R, code, {}, f"farm_new_{code}")
    if values:
        act(v_farms.farm_new, form=values)


# ============================================================================ dashboard
def page_dashboard(R):
    fid, code, t = R.fid, R.country, TODAY()
    ti, soon = t.isoformat(), (t + dt.timedelta(days=14)).isoformat()
    st.title("Dashboard")
    st.caption(f"Hello {R.user['first_name']} — {ui.fmt_date(t, code)}")
    active = R.one("SELECT COUNT(*) c FROM livestock WHERE farm_id=? AND status='active'", (fid,))["c"]
    by_type = R.all("SELECT animal_type k, COUNT(*) c FROM livestock WHERE farm_id=? AND status='active' GROUP BY k ORDER BY c DESC", (fid,))
    health_due = R.all("""SELECT h.*, l.name, l.tag_number, l.id lid FROM health_records h JOIN livestock l ON l.id=h.livestock_id
                          WHERE l.farm_id=? AND l.status='active' AND h.next_due_date BETWEEN ? AND ? ORDER BY h.next_due_date LIMIT 8""",
                       (fid, ti, soon))
    overdue = R.one("""SELECT COUNT(*) c FROM health_records h JOIN livestock l ON l.id=h.livestock_id
                       WHERE l.farm_id=? AND l.status='active' AND h.next_due_date < ? AND h.next_due_date >= ?""",
                    (fid, ti, (t - dt.timedelta(days=60)).isoformat()))["c"]
    births = R.all("""SELECT b.*, l.name, l.tag_number FROM breeding_events b JOIN livestock l ON l.id=b.female_id
                      WHERE b.farm_id=? AND b.status IN ('served','pregnant') AND b.expected_date <= ? ORDER BY b.expected_date LIMIT 6""",
                   (fid, (t + dt.timedelta(days=30)).isoformat()))
    tasks = R.all("SELECT * FROM tasks WHERE farm_id=? AND status!='completed' AND due_date <= ? ORDER BY due_date LIMIT 6",
                  (fid, (t + dt.timedelta(days=7)).isoformat()))
    low = R.all("SELECT * FROM products WHERE farm_id=? AND quantity <= reorder_level ORDER BY name LIMIT 6", (fid,))
    notifiable = R.all("""SELECT h.*, l.name, l.tag_number FROM health_records h JOIN livestock l ON l.id=h.livestock_id
                          WHERE l.farm_id=? AND h.notifiable=1 AND h.date >= ? ORDER BY h.date DESC LIMIT 3""",
                       (fid, (t - dt.timedelta(days=30)).isoformat()))
    pass_on = R.all("SELECT * FROM livestock WHERE farm_id=? AND pass_on_due=1 AND status='active'", (fid,))

    if not R.farm["district"]:
        st.warning("This farm has no district yet. Add its location under My farms → Edit this farm.")
    for n in notifiable:
        st.error(f"Notifiable disease recorded: {n['disease']} in {common.animal_name(n)} on {ui.fmt_date(n['date'], code)}. "
                 f"{countries.country(code)['notifiable_note']}")
    if overdue:
        st.warning(f"{overdue} vaccination(s) or treatment(s) are past their due date (see Animal health → Past due).")
    for a in pass_on:
        st.info(f"Girinka: {common.animal_name(a)} came through the Girinka programme. Remember to pass on its first female calf.")

    items = [("Active animals", active), ("Health care due (14 days)", len(health_due)),
             ("Births expected (30 days)", len(births)), ("Products low in stock", len(low))]
    month_start = t.replace(day=1).isoformat()
    if R.can("finance"):
        inc = R.one("SELECT COALESCE(SUM(amount),0) s FROM transactions WHERE farm_id=? AND kind='income' AND date>=?", (fid, month_start))["s"]
        exp = R.one("SELECT COALESCE(SUM(amount),0) s FROM transactions WHERE farm_id=? AND kind='expense' AND date>=?", (fid, month_start))["s"]
        items.append(("Profit this month", ui.money(inc - exp, code)))
    metrics(items)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Herd by species")
        bars([(L(common.ANIMAL_TYPES, r["k"]), r["c"]) for r in by_type])
    with c2:
        months = ui.months_back(6)
        if R.can("finance"):
            st.subheader(f"Income and expenses, last 6 months ({countries.country(code)['currency']})")
            series = {m: [0, 0] for m in months}
            for r in R.all("SELECT substr(date,1,7) m, kind, SUM(amount) s FROM transactions WHERE farm_id=? AND date >= ? GROUP BY m, kind",
                           (fid, months[0] + "-01")):
                if r["m"] in series:
                    series[r["m"]][0 if r["kind"] == "income" else 1] = r["s"]
            pair_chart(series)
        else:
            st.subheader("Births, last 6 months")
            rows = {r["m"]: r["c"] for r in R.all("""SELECT substr(outcome_date,1,7) m, SUM(born_alive) c FROM breeding_events
                    WHERE farm_id=? AND status='delivered' AND outcome_date >= ? GROUP BY m""", (fid, months[0] + "-01"))}
            bars([(m, rows.get(m, 0) or 0) for m in months], horizontal=False, ylabel="Born")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Upcoming vaccinations & treatments")
        table([{"Animal": common.animal_name(h), "Treatment": h["title"], "Type": L(common.HEALTH_TYPES, h["record_type"]),
                "Due": ui.fmt_date(h["next_due_date"], code)} for h in health_due], "Nothing due in the next 14 days.")
        st.subheader("Tasks this week")
        table([{"Task": x["title"], "Due": ui.fmt_date(x["due_date"], code),
                "": "Overdue" if x["due_date"] and x["due_date"] < ti else L(common.PRIORITIES, x["priority"])} for x in tasks],
              "No tasks due this week.")
    with c2:
        st.subheader("Expected births")
        table([{"Mother": common.animal_name(b), "Mated": ui.fmt_date(b["mating_date"], code),
                "Expected": ui.fmt_date(b["expected_date"], code)} for b in births], "No births expected in the next 30 days.")
        st.subheader("Running low")
        table([{"Product": p["name"], "Left": f"{ui.fmt_num(p['quantity'])} {p['unit']}"} for p in low], "All stock above warning levels.")


# ============================================================================ livestock
def page_animals(R):
    view = ss.get("view", "list")
    if view == "new":
        return animal_form(R)
    if view == "edit":
        return animal_form(R, common.get_animal(R, ss["rid"]))
    if view == "detail":
        return animal_detail(R, ss["rid"])
    code = R.country
    h1, h2, h3 = st.columns([4, 1, 1])
    h1.title("Livestock")
    if R.can("animals") and h2.button("+ Register animal", type="primary"):
        go(view="new")
    with h3:
        csv_button(R, "animals")
    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
    q = c1.text_input("Search", placeholder="Name, number, breed or ID", key="an_q")
    with c2:
        status = pick("Status", [("active", "Active"), ("exited", "Sold / died / exited"), ("all", "All")], "active", k="an_status")
    with c3:
        kind = pick("Species", common.ANIMAL_TYPES, "", blank="All species", k="an_type")
    with c4:
        gender = pick("Sex", common.GENDERS, "", blank="Both", k="an_gender")
    sql, params = "SELECT * FROM livestock WHERE farm_id=?", [R.fid]
    if status == "active":
        sql += " AND status='active'"
    elif status == "exited":
        sql += " AND status!='active'"
    if kind:
        sql += " AND animal_type=?"
        params.append(kind)
    if gender:
        sql += " AND gender=?"
        params.append(gender)
    if q.strip():
        sql += " AND (name LIKE ? OR tag_number LIKE ? OR breed LIKE ? OR official_id LIKE ?)"
        params += [f"%{q.strip()}%"] * 4
    rows = R.all(sql + " ORDER BY created_at DESC, id DESC LIMIT 1000", params)
    st.caption(f"{len(rows)} animal(s)")
    chosen = table_pick([{"Animal": a["name"] or a["tag_number"], "Number": a["tag_number"], "Species": L(common.ANIMAL_TYPES, a["animal_type"]),
                          "Breed": a["breed"] or "—", "Sex": L(common.GENDERS, a["gender"]), "Age": ui.age_text(a["date_of_birth"], a["exit_date"]),
                          "Weight": f"{ui.fmt_num(a['weight_kg'], 1)} kg" if a["weight_kg"] else "—",
                          "Status": L(common.ANIMAL_STATUS, a["status"])} for a in rows],
                        [a["id"] for a in rows], "animals", "No animals match. Register an animal with the button above.")
    if chosen:
        go(view="detail", rid=chosen)


def animal_form(R, animal=None):
    R.require("animals")
    code = R.country
    c = countries.country(code)
    pre = ss.get("preset", {})
    data = dict(animal) if animal else {"acquisition_date": TODAY().isoformat(), "animal_type": "cattle", "gender": "female",
                                        "acquisition_method": "born"}
    back("← Back" if animal else "← Back to list")
    st.header("Edit animal" if animal else "Register animal")
    if not animal:
        st.caption(f"An animal number such as {v_animals.make_tag(code, 'cattle', TODAY().isoformat(), 7)} is created when you save.")
    keep = animal["id"] if animal else None
    mothers = [o for o in common.animal_options(R, True, "female", keep) if o[0] != keep]
    fathers = [o for o in common.animal_options(R, True, "male", keep) if o[0] != keep]
    with st.form(key(f"animal_form_{keep}")):
        c1, c2, c3 = st.columns(3)
        with c1:
            kind = pick("Species", common.ANIMAL_TYPES, data.get("animal_type"))
            name = st.text_input("Name (optional)", value=data.get("name") or "")
            official = st.text_input(c["id_label"], value=data.get("official_id") or "", help=c["id_hint"])
        with c2:
            breed = st.text_input("Breed", value=data.get("breed") or "", placeholder="e.g. Angoni, Ankole, Boer")
            dob = date_in("Date of birth", data.get("date_of_birth"), help="Leave empty if unknown")
            weight = None if animal else num_in("Weight now (kg)", step=0.1)
        with c3:
            gender = pick("Sex", common.GENDERS, data.get("gender"))
            colour = st.text_input("Colour / markings", value=data.get("colour") or "")
        st.markdown("**How the animal came to the farm**")
        c1, c2, c3 = st.columns(3)
        with c1:
            method = pick("Acquired by", common.acquisition_choices(code), data.get("acquisition_method"))
            dam = pick("Mother (dam)", mothers, data.get("dam_id") or pre.get("dam"), blank="— unknown / not on farm —")
        with c2:
            acq = date_in("Date acquired / born *", data.get("acquisition_date"), required=True)
            sire = pick("Father (sire)", fathers, data.get("sire_id"), blank="— unknown / not on farm —")
        with c3:
            price = num_in(f"Purchase price ({c['currency']})", data.get("purchase_price"), help="Only for purchases; recorded as an expense")
            seller = st.text_input("Seller / giver", value=data.get("seller") or "")
        notes = st.text_area("Notes", value=data.get("notes") or "")
        if st.form_submit_button("Save changes" if animal else "Register animal", type="primary", use_container_width=True):
            form = {"name": name, "animal_type": kind, "breed": breed, "gender": gender, "date_of_birth": iso(dob), "colour": colour,
                    "official_id": official, "acquisition_method": method, "acquisition_date": iso(acq),
                    "purchase_price": num_text(price), "seller": seller, "dam_id": dam, "sire_id": sire, "notes": notes,
                    "weight_kg": num_text(weight)}
            if animal:
                act(v_animals.animal_edit, animal["id"], form=form)
            else:
                act(v_animals.animal_new, form=form)


def animal_detail(R, aid):
    a = common.get_animal(R, aid)
    code = R.country
    c = countries.country(code)
    fin = R.can("finance")
    back()
    st.title(common.animal_name(a))
    st.caption(f"{L(common.ANIMAL_TYPES, a['animal_type'])} · {a['breed'] or 'breed not set'} · **{L(common.ANIMAL_STATUS, a['status'])}**")
    show_flashes()
    # actions
    cols = st.columns(6)
    if R.can("animals") and cols[0].button("✏ Edit"):
        go(view="edit", rid=a["id"])
    if R.can("health") and a["status"] == "active" and cols[1].button("+ Health record"):
        go("health", "new", preset={"animal": a["id"]})
    if R.can("breeding") and a["gender"] == "female" and a["status"] == "active" and cols[2].button("+ Breeding"):
        go("breeding", "new", preset={"female": a["id"]})
    if R.can("finance") and a["status"] == "active" and cols[3].button("Sell this animal"):
        go("sales", "new", preset={"animal": a["id"]})
    if R.can("delete") and a["status"] not in ("active", "sold") and cols[4].button("Undo exit"):
        act(v_animals.animal_reactivate, a["id"])
    if R.can("delete"):
        with cols[5]:
            if confirm("🗑 Delete", f"del_animal_{a['id']}", "Delete this animal and its health records?"):
                act(v_animals.animal_delete, a["id"])

    if a["pass_on_due"]:
        st.info("Girinka animal: its first female calf should be passed on to another family.")
        if R.can("animals") and st.button("Mark as passed on"):
            act(v_animals.animal_passed_on, a["id"])

    dam = R.one("SELECT * FROM livestock WHERE id=?", (a["dam_id"],)) if a["dam_id"] else None
    sire = R.one("SELECT * FROM livestock WHERE id=?", (a["sire_id"],)) if a["sire_id"] else None
    sale = R.one("SELECT s.*, i.price FROM sale_items i JOIN sales s ON s.id=i.sale_id WHERE i.livestock_id=?", (a["id"],))
    info = [("Animal number", a["tag_number"]), ("Species", L(common.ANIMAL_TYPES, a["animal_type"])), ("Breed", a["breed"] or "—"),
            ("Sex", L(common.GENDERS, a["gender"])), ("Date of birth", ui.fmt_date(a["date_of_birth"], code)),
            ("Age", ui.age_text(a["date_of_birth"], a["exit_date"])), ("Colour / markings", a["colour"] or "—"),
            (c["id_label"], a["official_id"] or "—"), ("Latest weight", f"{ui.fmt_num(a['weight_kg'], 1)} kg" if a["weight_kg"] else "—"),
            ("Acquired", f"{ui.fmt_date(a['acquisition_date'], code)} · {L(common.acquisition_choices(code), a['acquisition_method'])}"),
            ("Mother", common.animal_name(dam) if dam else "—"), ("Father", common.animal_name(sire) if sire else "—")]
    if a["purchase_price"] and fin:
        info.append(("Purchase price", ui.money(a["purchase_price"], code) + (f" from {a['seller']}" if a["seller"] else "")))
    if a["status"] != "active":
        info.append(("Left the herd", f"{ui.fmt_date(a['exit_date'], code)} · {L(common.ANIMAL_STATUS, a['status'])}"
                     + (f" — {a['exit_reason']}" if a["exit_reason"] else "")))
    if sale:
        info.append(("Sale", f"Receipt {sale['receipt_no']} to {sale['buyer_name']}" + (f" · {ui.money(sale['price'], code)}" if fin else "")))
    st.subheader("Profile")
    st.dataframe(pd.DataFrame(info, columns=["", "Details"]), hide_index=True, use_container_width=True)
    if a["notes"]:
        st.caption(a["notes"])

    st.subheader("Medical history")
    health = R.all("SELECT * FROM health_records WHERE livestock_id=? ORDER BY date DESC, id DESC", (a["id"],))
    hid = table_pick([{"Date": ui.fmt_date(h["date"], code), "Record": h["title"] + (" ⚠ notifiable" if h["notifiable"] else ""),
                       "Type": L(common.HEALTH_TYPES, h["record_type"]), "Disease / diagnosis": h["disease"] or h["diagnosis"] or "—",
                       "Next due": ui.fmt_date(h["next_due_date"], code) if h["next_due_date"] else "—",
                       **({"Cost": ui.money(h["cost"], code)} if fin else {})} for h in health],
                     [h["id"] for h in health], "animal_health", "No health records yet.")
    if hid:
        go("health", "detail", hid)

    left, right = st.columns(2)
    with left:
        st.subheader("Weight history")
        if R.can("animals") and a["status"] == "active":
            with st.form(key(f"weight_{a['id']}")):
                w1, w2 = st.columns(2)
                w = w1.number_input("Weight (kg)", min_value=0.0, value=None, step=0.1, key=key("weight_kg"))
                wd = w2.date_input("Date", value=TODAY(), min_value=OLDEST, max_value=TODAY(), format="DD/MM/YYYY", key=key("weight_date"))
                if st.form_submit_button("Add weight"):
                    act(v_animals.animal_weight, a["id"], form={"weight_kg": num_text(w), "date": iso(wd)})
        weights = R.all("SELECT * FROM weights WHERE livestock_id=? ORDER BY date DESC, id DESC LIMIT 20", (a["id"],))
        table([{"Date": ui.fmt_date(x["date"], code), "Weight": f"{ui.fmt_num(x['weight_kg'], 1)} kg"} for x in weights], "No weights recorded.")
        if len(weights) > 1:
            st.line_chart(pd.DataFrame([{"Date": x["date"], "kg": x["weight_kg"]} for x in weights]).set_index("Date"))
    with right:
        st.subheader("Breeding")
        breeding = R.all("""SELECT b.* FROM breeding_events b WHERE b.female_id=? OR b.male_id=? ORDER BY b.mating_date DESC""", (a["id"], a["id"]))
        bid = table_pick([{"Mated": ui.fmt_date(b["mating_date"], code), "Method": "AI" if b["method"] == "ai" else "Natural",
                           "Result": b["status"].replace("_", " ").capitalize(), "Expected": ui.fmt_date(b["expected_date"], code),
                           "Born alive": b["born_alive"] or "—"} for b in breeding], [b["id"] for b in breeding], "animal_breeding",
                         "No breeding records.")
        if bid:
            go("breeding", "detail", bid)
        st.subheader("Offspring")
        offspring = R.all("SELECT * FROM livestock WHERE dam_id=? OR sire_id=? ORDER BY date_of_birth DESC", (a["id"], a["id"]))
        oid = table_pick([{"Offspring": common.animal_name(o), "Born": ui.fmt_date(o["date_of_birth"], code),
                           "Sex": L(common.GENDERS, o["gender"]), "Status": L(common.ANIMAL_STATUS, o["status"])} for o in offspring],
                         [o["id"] for o in offspring], "animal_offspring", "No offspring recorded.")
        if oid:
            go(view="detail", rid=oid)

    if a["status"] == "active" and R.can("animals"):
        st.subheader("Record death, slaughter or giving away")
        with st.form(key(f"exit_{a['id']}")):
            e1, e2, e3 = st.columns(3)
            with e1:
                what = pick("What happened", v_animals.EXIT_REASONS, "dead")
            ed = e2.date_input("Date", value=TODAY(), min_value=OLDEST, max_value=TODAY(), format="DD/MM/YYYY", key=key("exit_date"))
            note = e3.text_input("Cause / note", placeholder="e.g. East Coast fever, lightning")
            sure = st.checkbox("Yes, this animal has left the herd")
            if st.form_submit_button("Record"):
                if not sure:
                    st.error("Tick the box to confirm.")
                else:
                    act(v_animals.animal_exit, a["id"], form={"exit_status": what, "exit_date": iso(ed), "exit_reason": note})


# ============================================================================ breeding
def page_breeding(R):
    view = ss.get("view", "list")
    if view == "new":
        return breeding_form(R)
    if view == "edit":
        return breeding_form(R, v_breeding.get_event(R, ss["rid"]))
    if view == "detail":
        return breeding_detail(R, ss["rid"])
    code = R.country
    h1, h2 = st.columns([5, 1])
    h1.title("Breeding & reproduction")
    if R.can("breeding") and h2.button("+ Record mating", type="primary"):
        go(view="new")
    show = st.radio("Show", ["open", "done", "all"], horizontal=True, key="br_show",
                    format_func={"open": "Open (mated / pregnant)", "done": "Finished", "all": "All"}.get)
    sql = """SELECT b.*, f.name fname, f.tag_number ftag, f.animal_type, m.name mname, m.tag_number mtag
             FROM breeding_events b JOIN livestock f ON f.id=b.female_id LEFT JOIN livestock m ON m.id=b.male_id WHERE b.farm_id=?"""
    sql += {"open": " AND b.status IN ('served','pregnant') ORDER BY b.expected_date",
            "done": " AND b.status NOT IN ('served','pregnant') ORDER BY b.mating_date DESC"}.get(show, " ORDER BY b.mating_date DESC")
    rows = R.all(sql, (R.fid,))
    p = v_breeding.performance(R)
    metrics([("Open pregnancies / services", sum(1 for r in rows if r["status"] in v_breeding.OPEN) if show != "done" else "—"),
             ("Conception rate (checked services)", v_breeding.pct(p["conception_rate"])),
             ("Young born alive (all time)", p["born_alive"]),
             ("Average interval between births", f"{p['interval']:.0f} days" if p["interval"] else "—")])
    t = TODAY()
    out = []
    for r in rows:
        due = ""
        if r["status"] in v_breeding.OPEN and r["expected_date"]:
            days = (ui.parse_date(r["expected_date"]) - t).days
            due = f"{days} days" if days >= 0 else f"{-days} days overdue"
        sire = (r["mname"] or r["mtag"]) if r["male_id"] else (r["sire_details"] or "—")
        out.append({"Female": r["fname"] or r["ftag"], "Species": L(common.ANIMAL_TYPES, r["animal_type"]), "Sire": sire,
                    "Method": L(v_breeding.METHODS, r["method"]), "Mated": ui.fmt_date(r["mating_date"], code),
                    "Expected birth": ui.fmt_date(r["expected_date"], code), "Status": L(v_breeding.STATUSES, r["status"]), "Due in": due})
    chosen = table_pick(out, [r["id"] for r in rows], "breeding", "No breeding records. Record a mating or insemination with the button above.")
    st.caption("Expected birth dates use average gestation lengths (cattle 283, goats and sheep 150, pigs 114, rabbits 31 days; "
               "source: MSD Veterinary Manual). Real dates vary by a few days.")
    csv_button(R, "breeding")
    if chosen:
        go(view="detail", rid=chosen)


def breeding_form(R, ev=None):
    R.require("breeding")
    pre = ss.get("preset", {})
    data = dict(ev) if ev else {"mating_date": TODAY().isoformat(), "method": "natural", "status": "served", "female_id": pre.get("female", "")}
    back()
    st.header("Edit breeding record" if ev else "Record mating")
    keep_f, keep_m = (ev["female_id"], ev["male_id"]) if ev else (None, None)
    editable_status = not ev or ev["status"] in ("served", "pregnant", "not_pregnant")
    status_choices = v_breeding.STATUSES[:3] if editable_status else [(ev["status"], L(v_breeding.STATUSES, ev["status"]))]
    with st.form(key(f"breeding_form_{ev['id'] if ev else 'new'}")):
        c1, c2 = st.columns(2)
        with c1:
            female = pick("Female *", common.animal_options(R, True, "female", keep_f), data.get("female_id"), blank="— choose —")
            method = pick("Method", v_breeding.METHODS, data.get("method"))
            mating = date_in("Mating / insemination date *", data.get("mating_date"), required=True)
            check = date_in("Pregnancy check date", data.get("check_date"))
        with c2:
            male = pick("Male on this farm (optional)", common.animal_options(R, True, "male", keep_m), data.get("male_id"),
                        blank="— none / outside bull or AI —")
            sire = st.text_input("Sire details", value=data.get("sire_details") or "", help="Outside bull name or AI straw code")
            status = pick("Pregnancy status", status_choices, data.get("status"))
            expected = date_in("Expected birth (only for species without a standard)", data.get("expected_date"), past_only=False,
                               help="Calculated automatically for cattle, goats, sheep, pigs, rabbits and poultry")
        notes = st.text_area("Notes", value=data.get("notes") or "")
        if st.form_submit_button("Save", type="primary", use_container_width=True):
            form = {"female_id": female, "male_id": male, "method": method, "sire_details": sire, "mating_date": iso(mating),
                    "status": status, "check_date": iso(check), "expected_date": iso(expected), "notes": notes}
            if ev:
                act(v_breeding.breeding_edit, ev["id"], form=form)
            else:
                act(v_breeding.breeding_new, form=form)


def breeding_detail(R, eid):
    ev = v_breeding.get_event(R, eid)
    code = R.country
    mother = common.get_animal(R, ev["female_id"])
    male = R.one("SELECT * FROM livestock WHERE id=?", (ev["male_id"],)) if ev["male_id"] else None
    back()
    st.title(f"Breeding: {common.animal_name(mother)}")
    show_flashes()
    c1, c2, c3 = st.columns([1, 1, 4])
    if R.can("breeding") and c1.button("✏ Edit"):
        go(view="edit", rid=ev["id"])
    if c2.button("Open mother"):
        go("animals", "detail", mother["id"])
    if R.can("delete"):
        with c3:
            if confirm("🗑 Delete", f"del_breed_{ev['id']}", "Delete this breeding record? Offspring already registered stay."):
                act(v_breeding.breeding_delete, ev["id"])
    info = [("Female", common.animal_name(mother)), ("Sire", common.animal_name(male) if male else (ev["sire_details"] or "—")),
            ("Method", L(v_breeding.METHODS, ev["method"])), ("Mating date", ui.fmt_date(ev["mating_date"], code)),
            ("Pregnancy check", ui.fmt_date(ev["check_date"], code)), ("Expected birth", ui.fmt_date(ev["expected_date"], code)),
            ("Status", L(v_breeding.STATUSES, ev["status"]))]
    if ev["outcome_date"]:
        info.append(("Outcome date", ui.fmt_date(ev["outcome_date"], code)))
        info.append(("Days from mating", str((ui.parse_date(ev["outcome_date"]) - ui.parse_date(ev["mating_date"])).days)))
    if ev["status"] == "delivered":
        info.append(("Born alive / dead", f"{ev['born_alive']} / {ev['born_dead']}"))
    st.dataframe(pd.DataFrame(info, columns=["", "Details"]), hide_index=True, use_container_width=True)
    if ev["notes"]:
        st.caption(ev["notes"])
    if ev["outcome_date"]:
        young = R.all("SELECT * FROM livestock WHERE dam_id=? AND date_of_birth=? ORDER BY id", (mother["id"], ev["outcome_date"]))
        if young:
            st.subheader("Offspring from this birth")
            yid = table_pick([{"Young": common.animal_name(y), "Sex": y["gender"]} for y in young], [y["id"] for y in young], "young")
            if yid:
                go("animals", "detail", yid)
    if ev["status"] in v_breeding.OPEN and R.can("breeding"):
        st.subheader("Record the outcome")
        with st.form(key(f"outcome_{ev['id']}")):
            c1, c2, c3 = st.columns(3)
            with c1:
                result = pick("Result", [("delivered", "Gave birth"), ("aborted", "Lost the pregnancy"), ("not_pregnant", "Was not pregnant")], "delivered")
                males = st.number_input("Males born alive", min_value=0, step=1, value=0)
            with c2:
                od = st.date_input("Date", value=TODAY(), min_value=OLDEST, max_value=TODAY(), format="DD/MM/YYYY", key=key("outcome_date"))
                females = st.number_input("Females born alive", min_value=0, step=1, value=0)
            with c3:
                dead = st.number_input("Born dead", min_value=0, step=1, value=0)
            st.caption("Each young born alive is added to the livestock register with its mother and father linked.")
            if st.form_submit_button("Save outcome", type="primary"):
                act(v_breeding.breeding_outcome, ev["id"], form={"result": result, "outcome_date": iso(od), "males": males,
                                                                 "females": females, "born_dead": dead})


# ============================================================================ health
def page_health(R):
    view = ss.get("view", "list")
    if view == "new":
        return health_form(R)
    if view in ("detail", "edit"):
        return health_edit(R, ss["rid"])
    code = R.country
    h1, h2, h3 = st.columns([4, 1, 1])
    h1.title("Animal health")
    if R.can("health") and h2.button("+ Health record", type="primary"):
        go(view="new")
    with h3:
        csv_button(R, "health")
    c1, c2 = st.columns([3, 2])
    show = c1.radio("Show", ["upcoming", "overdue", "all", "notifiable"], horizontal=True, key="he_show",
                    index=["upcoming", "overdue", "all", "notifiable"].index(ss.get("preset", {}).get("show", "upcoming"))
                    if ss.get("preset", {}).get("show") in ("upcoming", "overdue", "all", "notifiable") else 0,
                    format_func={"upcoming": "Upcoming", "overdue": "Past due", "all": "All records", "notifiable": "Notifiable diseases"}.get)
    with c2:
        kind = pick("Type", common.HEALTH_TYPES, "", blank="All types", k="he_type")
    t = TODAY().isoformat()
    base = """SELECT h.*, l.name, l.tag_number, l.animal_type, l.id lid FROM health_records h
              JOIN livestock l ON l.id=h.livestock_id WHERE l.farm_id=?"""
    params = [R.fid]
    if kind:
        base += " AND h.record_type=?"
        params.append(kind)
    if show == "upcoming":
        rows = R.all(base + " AND l.status='active' AND h.next_due_date >= ? ORDER BY h.next_due_date", params + [t])
    elif show == "overdue":
        st.info("These follow-ups are past their due date. Record the new treatment, or edit the old record to clear its next due date.")
        rows = R.all(base + " AND l.status='active' AND h.next_due_date < ? ORDER BY h.next_due_date DESC", params + [t])
    elif show == "notifiable":
        rows = R.all(base + " AND h.notifiable=1 ORDER BY h.date DESC", params)
    else:
        rows = R.all(base + " ORDER BY h.date DESC, h.id DESC LIMIT 500", params)
    fin = R.can("finance")
    chosen = table_pick([{"Date": ui.fmt_date(h["date"], code), "Animal": common.animal_name(h),
                          "Record": h["title"] + (" ⚠ notifiable" if h["notifiable"] else ""), "Type": L(common.HEALTH_TYPES, h["record_type"]),
                          "Disease": h["disease"] or "—",
                          "Next due": (ui.fmt_date(h["next_due_date"], code) + (" (past due)" if h["next_due_date"] < t else "")) if h["next_due_date"] else "—",
                          **({"Cost": ui.money(h["cost"], code)} if fin else {})} for h in rows],
                        [h["id"] for h in rows], "health",
                        "Nothing here. Record vaccinations and treatments; add a next due date to get reminders on the dashboard.")
    if chosen:
        go(view="detail", rid=chosen)


def health_form(R, record=None):
    code = R.country
    c = countries.country(code)
    pre = ss.get("preset", {})
    data = dict(record) if record else {"date": TODAY().isoformat(), "record_type": "vaccination", "livestock_id": pre.get("animal", "")}
    back()
    st.header("Edit health record" if record else "New health record")
    diseases = sorted(set(countries.COMMON_DISEASES + c["notifiable"]))
    with st.form(key(f"health_form_{record['id'] if record else 'new'}")):
        scope, species = "one", "cattle"
        if not record:
            c1, c2 = st.columns(2)
            with c1:
                scope = pick("Apply to", [("one", "One animal"), ("species", "All active animals of a species (e.g. herd vaccination)")], "one")
            with c2:
                species = pick("Species (when applying to all)", common.ANIMAL_TYPES, "cattle")
        c1, c2 = st.columns(2)
        with c1:
            animal = pick("Animal", common.animal_options(R, True, keep_id=record["livestock_id"] if record else None),
                          data.get("livestock_id"), blank="— choose —")
            kind = pick("Type", common.HEALTH_TYPES, data.get("record_type"))
            title = st.text_input("Title *", value=data.get("title") or "", placeholder="e.g. ECF immunisation, FMD vaccine, deworming")
            current = data.get("disease") or ""
            picked = pick("Disease (pick from list)", [(d, d) for d in diseases], current if current in diseases else "", blank="— none / other —",
                          help="Diseases notifiable in Zambia are flagged automatically" if code == "ZM" else None)
            typed = st.text_input("…or type another disease", value="" if current in diseases else current)
        with c2:
            d = date_in("Date *", data.get("date"), required=True)
            due = date_in("Next dose / follow-up due", data.get("next_due_date"), past_only=False, help="Shows as a reminder on the dashboard")
            wd = date_in("Milk / meat withdrawal until", data.get("withdrawal_until"), past_only=False, help="From the medicine label")
            vet = st.text_input("Vet / para-vet", value=data.get("vet_name") or "")
            cost = num_in(f"Cost per animal ({c['currency']})", data.get("cost") or None, help="Recorded as a veterinary expense")
        diagnosis = st.text_area("Diagnosis / signs", value=data.get("diagnosis") or "")
        treatment = st.text_area("Treatment / medicine and dose", value=data.get("treatment") or "")
        if st.form_submit_button("Save changes" if record else "Save record", type="primary", use_container_width=True):
            form = {"scope": scope, "species": species, "livestock_id": animal, "record_type": kind, "title": title,
                    "disease": typed.strip() or picked, "date": iso(d), "next_due_date": iso(due), "withdrawal_until": iso(wd),
                    "vet_name": vet, "cost": num_text(cost), "diagnosis": diagnosis, "treatment": treatment}
            if record:
                act(v_health.health_edit, record["id"], form=form)
            else:
                act(v_health.health_new, form=form)
    if record and R.can("delete"):
        if confirm("🗑 Delete record", f"del_health_{record['id']}", "Delete this health record?"):
            act(v_health.health_delete, record["id"])


def health_edit(R, rid):
    r = v_health.get_record(R, rid)
    if R.can("health"):
        return health_form(R, r)
    code = R.country
    a = R.one("SELECT * FROM livestock WHERE id=?", (r["livestock_id"],))
    back()
    st.header(r["title"])
    st.dataframe(pd.DataFrame([("Animal", common.animal_name(a)), ("Type", L(common.HEALTH_TYPES, r["record_type"])),
                               ("Date", ui.fmt_date(r["date"], code)), ("Disease", r["disease"] or "—"),
                               ("Diagnosis", r["diagnosis"] or "—"), ("Treatment", r["treatment"] or "—"),
                               ("Next due", ui.fmt_date(r["next_due_date"], code)),
                               ("Withdrawal until", ui.fmt_date(r["withdrawal_until"], code))], columns=["", "Details"]),
                 hide_index=True, use_container_width=True)


# ============================================================================ feeding
def page_feeding(R):
    if ss.get("view") == "new":
        return feeding_form(R)
    code = R.country
    h1, h2, h3 = st.columns([4, 1, 1])
    h1.title("Feeding & nutrition")
    if R.can("feeding") and h2.button("+ Record feeding", type="primary"):
        go(view="new")
    with h3:
        csv_button(R, "feeding")
    t = TODAY()
    c1, c2, c3 = st.columns(3)
    start = c1.date_input("From", value=t - dt.timedelta(days=30), min_value=OLDEST, max_value=FAR, format="DD/MM/YYYY", key="fe_from")
    end = c2.date_input("To", value=t, min_value=OLDEST, max_value=FAR, format="DD/MM/YYYY", key="fe_to")
    with c3:
        species = pick("Species", common.ANIMAL_TYPES, "", blank="All species", k="fe_type")
    sql = """SELECT r.*, l.name lname, l.tag_number ltag FROM feeding_records r LEFT JOIN livestock l ON l.id=r.livestock_id
             WHERE r.farm_id=? AND r.date BETWEEN ? AND ?"""
    params = [R.fid, iso(start), iso(end)]
    if species:
        sql += " AND (r.animal_type=? OR l.animal_type=?)"
        params += [species, species]
    rows = R.all(sql + " ORDER BY r.date DESC, r.id DESC", params)
    fin = R.can("finance")
    total = sum(r["cost"] for r in rows)
    days = max((end - start).days + 1, 1)
    items = [("Feedings recorded", len(rows))]
    if fin:
        items += [("Feed cost in period", ui.money(total, code)), ("Average feed cost per day", ui.money(total / days, code))]
    metrics(items)
    by_feed = {}
    for r in rows:
        k = f"{r['feed_name']} ({r['unit']})"
        by_feed[k] = by_feed.get(k, 0) + r["quantity"]
    st.subheader("Feed used in this period")
    bars(sorted(by_feed.items(), key=lambda x: -x[1]), ylabel="Quantity")
    st.caption("If the feed comes from your stock, the stock goes down automatically and the cost is worked out from the product price.")
    st.subheader("Feeding records")
    out = [{"Date": ui.fmt_date(r["date"], code), "Feed": r["feed_name"], "Quantity": f"{ui.fmt_num(r['quantity'])} {r['unit']}",
            "Fed to": common.animal_name({"name": r["lname"], "tag_number": r["ltag"], "id": r["livestock_id"]}) if r["livestock_id"]
            else f"{L(common.ANIMAL_TYPES, r['animal_type']) or 'All animals'} × {r['animal_count']}",
            **({"Cost": ui.money(r["cost"], code)} if fin else {})} for r in rows]
    chosen = table_pick(out, [r["id"] for r in rows], "feeding", "No feeding recorded in this period.",
                        "Click a row to delete it." if R.can("delete") else "")
    if chosen and R.can("delete"):
        st.warning("Delete this feeding record? Any stock it used is put back.")
        c1, c2, _ = st.columns([1, 1, 4])
        if c1.button("Yes, delete", type="primary"):
            act(v_feeding.feeding_delete, chosen)
        if c2.button("Cancel"):
            go(view="list")


def feeding_form(R):
    R.require("feeding")
    code = R.country
    back()
    st.header("Record feeding")
    feeds = R.all("SELECT * FROM products WHERE farm_id=? AND kind='feed' ORDER BY name", (R.fid,))
    targets = [("all", "All animals", "Groups")] + [(f"type:{k}", f"All {n.lower()}", "Groups") for k, n in common.ANIMAL_TYPES]
    targets += [(f"animal:{o[0]}", o[1], f"One animal — {o[2]}") for o in common.animal_options(R)]
    with st.form(key("feeding_form")):
        c1, c2 = st.columns(2)
        with c1:
            d = date_in("Date *", TODAY().isoformat(), required=True)
            target = pick("Fed to", targets, "all")
            product = pick("Feed from stock", [(p["id"], f"{p['name']} — {ui.fmt_num(p['quantity'])} {p['unit']} in stock") for p in feeds], "",
                           blank="— not from stock (type the name below) —", help="Feed products are added under Inventory with kind 'Feed'")
            feed_name = st.text_input("Feed name (if not from stock)", placeholder="e.g. Napier grass, maize bran")
        with c2:
            qty = num_in("Quantity given *", step=1.0)
            unit = st.text_input("Unit (if not from stock)", value="kg")
            count = st.number_input("Number of animals fed", min_value=1, step=1, value=1)
            cost = num_in(f"Cost ({countries.country(code)['currency']}) — only if not from stock")
        notes = st.text_area("Notes")
        if st.form_submit_button("Save feeding", type="primary", use_container_width=True):
            act(v_feeding.feeding_new, form={"date": iso(d), "target": target, "product_id": product, "feed_name": feed_name,
                                             "quantity": num_text(qty), "unit": unit, "animal_count": count, "cost": num_text(cost),
                                             "notes": notes})


# ============================================================================ inventory
def page_inventory(R):
    view = ss.get("view", "list")
    if view == "new":
        return product_form(R)
    if view == "edit":
        return product_form(R, v_inventory.get_product(R, ss["rid"]))
    if view == "detail":
        return product_detail(R, ss["rid"])
    code = R.country
    h1, h2, h3 = st.columns([4, 1, 1])
    h1.title("Inventory")
    if R.can("inventory") and h2.button("+ Add product", type="primary"):
        go(view="new")
    with h3:
        csv_button(R, "inventory")
    c1, c2, c3 = st.columns([3, 2, 2])
    q = c1.text_input("Search", placeholder="Product name", key="in_q")
    with c2:
        kind = pick("Kind", common.PRODUCT_KINDS, "", blank="All kinds", k="in_kind")
    low = c3.checkbox("Low stock only", value=bool(ss.get("preset", {}).get("low")), key="in_low")
    sql = "SELECT p.* FROM products p WHERE p.farm_id=?"
    params = [R.fid]
    if q.strip():
        sql += " AND (p.name LIKE ? OR p.description LIKE ?)"
        params += [f"%{q.strip()}%"] * 2
    if kind:
        sql += " AND p.kind=?"
        params.append(kind)
    if low:
        sql += " AND p.quantity <= p.reorder_level"
    rows = R.all(sql + " ORDER BY p.kind, p.name", params)
    fin = R.can("finance")
    t = TODAY().isoformat()
    value = sum(r["quantity"] * r["unit_price"] for r in rows)
    st.caption(f"{len(rows)} product(s)" + (f" · stock value {ui.money(value, code)}" if fin else ""))
    out = []
    for p in rows:
        tags = (["Low"] if p["quantity"] <= p["reorder_level"] else []) + (["Expired"] if p["expiry_date"] and p["expiry_date"] < t else [])
        out.append({"Product": p["name"], "Kind": L(common.PRODUCT_KINDS, p["kind"]), "In stock": f"{ui.fmt_num(p['quantity'])} {p['unit']}",
                    "Warn below": f"{ui.fmt_num(p['reorder_level'])} {p['unit']}", "Expires": ui.fmt_date(p["expiry_date"], code),
                    **({"Value": ui.money(p["quantity"] * p["unit_price"], code)} if fin else {}), "": " ".join(tags)})
    chosen = table_pick(out, [p["id"] for p in rows], "inventory", "No products. Add feed, medicines and equipment.")
    if chosen:
        go(view="detail", rid=chosen)


def product_form(R, product=None):
    R.require("inventory")
    code = R.country
    cats = R.all("SELECT * FROM categories WHERE farm_id=? ORDER BY name", (R.fid,))
    data = dict(product) if product else {"unit": "kg", "kind": "feed"}
    back()
    st.header("Edit product" if product else "Add product")
    with st.form(key(f"product_{product['id'] if product else 'new'}")):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Product name *", value=data.get("name") or "", placeholder="e.g. Dairy meal, Hay, ECF vaccine")
            kind = pick("Kind", common.PRODUCT_KINDS, data.get("kind"), help="Feed products can be used in feeding records")
            cat = pick("Category", [(c["id"], c["name"]) for c in cats], data.get("category_id"), blank="— none —")
            new_cat = st.text_input("…or new category")
            unit = st.text_input("Unit *", value=data.get("unit") or "", help="e.g. " + ", ".join(v_inventory.UNITS))
        with c2:
            qty = None if product else num_in("Opening quantity (already on the farm)",
                                              help="Not recorded as an expense. Record new purchases with 'Update stock'.")
            reorder = num_in("Warn me when stock falls below", data.get("reorder_level"))
            price = num_in(f"Usual price per unit ({countries.country(code)['currency']})", data.get("unit_price"),
                           help="Used to value stock and to cost feeding")
            expiry = date_in("Expiry date", data.get("expiry_date"), past_only=False)
        desc = st.text_area("Description", value=data.get("description") or "")
        if st.form_submit_button("Save changes" if product else "Add product", type="primary", use_container_width=True):
            form = {"name": name, "kind": kind, "category_id": cat, "new_category": new_cat, "unit": unit, "quantity": num_text(qty),
                    "reorder_level": num_text(reorder), "unit_price": num_text(price), "expiry_date": iso(expiry), "description": desc}
            if product:
                act(v_inventory.product_edit, product["id"], form=form)
            else:
                act(v_inventory.product_new, form=form)


def product_detail(R, pid):
    p = v_inventory.get_product(R, pid)
    code = R.country
    fin = R.can("finance")
    back()
    st.title(p["name"])
    show_flashes()
    c1, c2, _ = st.columns([1, 1, 4])
    if R.can("inventory") and c1.button("✏ Edit"):
        go(view="edit", rid=p["id"])
    if R.can("delete"):
        with c2:
            if confirm("🗑 Delete", f"del_prod_{p['id']}", "Delete this product and its history?"):
                act(v_inventory.product_delete, p["id"])
    low = p["quantity"] <= p["reorder_level"]
    items = [("In stock" + (" — below warning level" if low else ""), f"{ui.fmt_num(p['quantity'])} {p['unit']}")]
    if fin:
        items.append(("Stock value", ui.money(p["quantity"] * p["unit_price"], code)))
    metrics(items)
    if R.can("inventory"):
        st.subheader("Update stock")
        with st.form(key(f"adjust_{p['id']}")):
            c1, c2, c3 = st.columns(3)
            with c1:
                direction = pick("What happened", [("use", "Used (−)"), ("add", "Bought / received (+)"), ("loss", "Lost, spoiled or expired (−)")], "use")
            amount = c2.number_input(f"Amount ({p['unit']})", min_value=0.0, value=None)
            cost = c3.number_input(f"Total paid ({countries.country(code)['currency']}) — purchases only", min_value=0.0, value=None,
                                   help="Recorded as an expense") if fin else None
            reason = st.text_input("Note", placeholder="e.g. supplier name, or what it was used for")
            st.caption("Feed given to animals is best recorded under Feeding, which also reduces stock.")
            if st.form_submit_button("Update stock", type="primary"):
                act(v_inventory.product_adjust, p["id"], form={"direction": direction, "amount": num_text(amount),
                                                               "total_cost": num_text(cost), "reason": reason})
    info = [("Kind", L(common.PRODUCT_KINDS, p["kind"])), ("Category", p["category_name"] or "—"),
            ("Warn when below", f"{ui.fmt_num(p['reorder_level'])} {p['unit']}"), ("Expiry date", ui.fmt_date(p["expiry_date"], code))]
    if fin:
        info.insert(2, ("Price per unit", ui.money(p["unit_price"], code)))
    st.subheader("Details")
    st.dataframe(pd.DataFrame(info, columns=["", "Details"]), hide_index=True, use_container_width=True)
    if p["description"]:
        st.caption(p["description"])
    st.subheader("Stock history")
    moves = R.all("""SELECT m.*, u.first_name FROM stock_movements m LEFT JOIN users u ON u.id=m.user_id
                     WHERE m.product_id=? ORDER BY m.id DESC LIMIT 100""", (p["id"],))
    table([{"Date": ui.fmt_date(m["created_at"], code), "What": m["reason"], "By": m["first_name"] or "",
            "Change": ("+" if m["change"] > 0 else "") + ui.fmt_num(m["change"]),
            **({"Cost": ui.money(m["unit_cost"] * abs(m["change"]), code) if m["unit_cost"] and m["change"] > 0 else "—"} if fin else {})}
           for m in moves], "No stock changes yet.")


# ============================================================================ tasks
def page_tasks(R):
    view = ss.get("view", "list")
    if view == "new":
        return task_form(R)
    if view in ("edit", "detail"):
        return task_form(R, v_tasks.get_task(R, ss["rid"]))
    code = R.country
    h1, h2, h3 = st.columns([4, 1, 1])
    h1.title("Tasks")
    if R.can("tasks") and h2.button("+ New task", type="primary"):
        go(view="new")
    with h3:
        csv_button(R, "tasks")
    show = st.radio("Show", ["open", "overdue", "mine", "completed"], horizontal=True, key="ta_show",
                    format_func={"open": "Open", "overdue": "Overdue", "mine": "Assigned to me", "completed": "Completed"}.get)
    t = TODAY().isoformat()
    sql = """SELECT t.*, u.first_name assignee, l.name lname, l.tag_number ltag FROM tasks t
             LEFT JOIN users u ON u.id=t.assigned_to LEFT JOIN livestock l ON l.id=t.livestock_id WHERE t.farm_id=?"""
    params = [R.fid]
    if show == "overdue":
        sql += " AND t.status!='completed' AND t.due_date < ?"
        params.append(t)
    elif show == "mine":
        sql += " AND t.status!='completed' AND t.assigned_to=?"
        params.append(R.user["id"])
    elif show == "completed":
        sql += " AND t.status='completed'"
    else:
        sql += " AND t.status!='completed'"
    sql += (" ORDER BY t.completed_at DESC LIMIT 200" if show == "completed" else
            " ORDER BY (t.due_date IS NULL), t.due_date, CASE t.priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END")
    rows = R.all(sql, params)
    if not rows:
        st.info("No tasks here. Plan feeding, dipping, vet visits and repairs.")
    for x in rows:
        done = x["status"] == "completed"
        late = not done and x["due_date"] and x["due_date"] < t
        c0, c1, c2, c3, c4 = st.columns([0.6, 4, 1.5, 1.5, 1])
        if R.can("tasks"):
            if c0.button("✅" if done else "⬜", key=key(f"tick_{x['id']}"), help="Mark as not done" if done else "Mark as done"):
                act(v_tasks.task_toggle, x["id"])
        else:
            c0.write("✅" if done else "⬜")
        animal = common.animal_name({"name": x["lname"], "tag_number": x["ltag"], "id": x["livestock_id"]}) if x["livestock_id"] else ""
        tags = L(common.PRIORITIES, x["priority"]) + (" · ⚠ Overdue" if late else "") + (" · In progress" if x["status"] == "in_progress" else "")
        c1.markdown(("~~" + x["title"] + "~~" if done else f"**{x['title']}**") + (f"  \n_{animal}_" if animal else ""))
        c2.write(ui.fmt_date(x["due_date"], code))
        c3.write(f"{x['assignee'] or '—'}  \n{tags}")
        if R.can("tasks") and c4.button("Edit", key=key(f"edit_task_{x['id']}")):
            go(view="edit", rid=x["id"])


def task_form(R, task=None):
    R.require("tasks")
    people = v_tasks.members(R)
    data = dict(task) if task else {"priority": "medium", "status": "pending", "due_date": TODAY().isoformat()}
    back()
    st.header("Edit task" if task else "New task")
    with st.form(key(f"task_{task['id'] if task else 'new'}")):
        title = st.text_input("Task *", value=data.get("title") or "", placeholder="e.g. Dip cattle, repair kraal fence")
        desc = st.text_area("Details", value=data.get("description") or "")
        c1, c2 = st.columns(2)
        with c1:
            priority = pick("Priority", common.PRIORITIES, data.get("priority"))
            due = date_in("Due date", data.get("due_date"), past_only=False)
            status = pick("Status", common.TASK_STATUS, data.get("status"))
        with c2:
            assigned = pick("Assign to", [(m["id"], f"{m['first_name']} {m['last_name'] or ''}".strip()) for m in people],
                            data.get("assigned_to"), blank="— nobody —")
            animal = pick("Related animal", common.animal_options(R, keep_id=task["livestock_id"] if task else None),
                          data.get("livestock_id"), blank="— none —")
        if st.form_submit_button("Save task", type="primary", use_container_width=True):
            form = {"title": title, "description": desc, "priority": priority, "due_date": iso(due), "status": status,
                    "assigned_to": assigned, "livestock_id": animal}
            if task:
                act(v_tasks.task_edit, task["id"], form=form)
            else:
                act(v_tasks.task_new, form=form)
    if task and R.can("delete"):
        if confirm("🗑 Delete task", f"del_task_{task['id']}", "Delete this task?"):
            act(v_tasks.task_delete, task["id"])


# ============================================================================ sales
def page_sales(R):
    R.require("finance")
    view = ss.get("view", "list")
    if view == "new":
        return sale_form(R)
    if view == "detail":
        return sale_detail(R, ss["rid"])
    code = R.country
    h1, h2, h3 = st.columns([4, 1, 1])
    h1.title("Livestock sales")
    if h2.button("+ Record sale", type="primary"):
        go(view="new")
    with h3:
        csv_button(R, "sales")
    t = TODAY()
    c1, c2, _ = st.columns([1, 1, 2])
    start = c1.date_input("From", value=t.replace(month=1, day=1), min_value=OLDEST, max_value=FAR, format="DD/MM/YYYY", key="sa_from")
    end = c2.date_input("To", value=t, min_value=OLDEST, max_value=FAR, format="DD/MM/YYYY", key="sa_to")
    rows = R.all("""SELECT s.*, (SELECT COUNT(*) FROM sale_items i WHERE i.sale_id=s.id) n FROM sales s
                    WHERE s.farm_id=? AND s.date BETWEEN ? AND ? ORDER BY s.date DESC, s.id DESC""", (R.fid, iso(start), iso(end)))
    total = sum(r["total"] for r in rows)
    heads = sum(r["n"] for r in rows)
    metrics([("Sales", len(rows)), ("Animals sold", heads), ("Revenue from livestock sales", ui.money(total, code)),
             ("Average price per animal", ui.money(total / heads, code) if heads else "—")])
    chosen = table_pick([{"Receipt": r["receipt_no"], "Date": ui.fmt_date(r["date"], code), "Buyer": r["buyer_name"],
                          "Phone": r["buyer_phone"] or "—", "Animals": r["n"], "Payment": L(v_sales.PAYMENT, r["payment_method"]),
                          "Total": ui.money(r["total"], code)} for r in rows], [r["id"] for r in rows], "sales", "No sales in this period.")
    if chosen:
        go(view="detail", rid=chosen)


def sale_form(R):
    code = R.country
    c = countries.country(code)
    back()
    st.header("Record a livestock sale")
    animals = R.all("SELECT * FROM livestock WHERE farm_id=? AND status='active' ORDER BY animal_type, name, tag_number", (R.fid,))
    if not animals:
        st.info("No active animals to sell.")
        return
    by_id = {a["id"]: a for a in animals}
    pre = ss.get("preset", {}).get("animal")
    default = [int(pre)] if str(pre or "").isdigit() and int(pre) in by_id else []
    st.subheader("1. Animals sold")
    chosen = st.multiselect("Animals", list(by_id), default=default, key=key("sale_animals"),
                            format_func=lambda i: f"{L(common.ANIMAL_TYPES, by_id[i]['animal_type'])} · {common.animal_name(by_id[i])}"
                            + (f" · {by_id[i]['breed']}" if by_id[i]["breed"] else "")
                            + (f" · {by_id[i]['weight_kg']} kg" if by_id[i]["weight_kg"] else ""))
    with st.form(key("sale_form")):
        prices = {}
        for aid in chosen:
            prices[aid] = st.number_input(f"Price for {common.animal_name(by_id[aid])} ({c['currency']})", min_value=0.0, value=None,
                                          key=key(f"price_{aid}"))
        st.subheader("2. Buyer and payment")
        c1, c2 = st.columns(2)
        with c1:
            d = date_in("Sale date *", TODAY().isoformat(), required=True)
            buyer = st.text_input("Buyer name *")
            phone = st.text_input("Buyer phone")
        with c2:
            address = st.text_input("Buyer address / ID number")
            payment = pick("Payment", v_sales.PAYMENT, "cash")
            permit = st.text_input(c["movement_label"], help="If the animals are moved off the farm")
        notes = st.text_area("Notes")
        if st.form_submit_button("Record sale and make receipt", type="primary", use_container_width=True):
            form = {"date": iso(d), "buyer_name": buyer, "buyer_phone": phone, "buyer_address": address, "payment_method": payment,
                    "permit_no": permit, "notes": notes}
            for aid, p in prices.items():
                form[f"price_{aid}"] = num_text(p)
            act(v_sales.sale_new, form=form, lists={"animal": [str(a) for a in chosen]})


def sale_detail(R, sid):
    s = v_sales.get_sale(R, sid)
    items = R.all("SELECT * FROM sale_items WHERE sale_id=?", (s["id"],))
    code = R.country
    c = countries.country(code)
    back()
    st.title(f"Sale {s['receipt_no']}")
    show_flashes()
    page = ui.bare_page(f"Receipt {s['receipt_no']}", f'<div style="padding:20px">{v_sales.receipt_html(R, s, items)}'
                        '<p class="noprint" style="text-align:center"><button class="btn" onclick="window.print()">Print / save as PDF</button></p></div>')
    c1, c2, _ = st.columns([2, 1, 3])
    c1.download_button("⬇ Printable receipt (open, then Print / save as PDF)", page.encode("utf-8"), f"receipt-{s['receipt_no']}.html", "text/html")
    if R.can("delete"):
        with c2:
            if confirm("🗑 Delete sale", f"del_sale_{s['id']}", "Delete this sale? The animals become active again and the income is removed."):
                act(v_sales.sale_delete, s["id"])
    farm = R.farm
    with st.container(border=True):
        a, b = st.columns(2)
        a.markdown(f"**{farm['name']}**  \n{farm['district'] or ''}{', ' + farm['province'] if farm['province'] else ''}, {c['name']}  \n"
                   f"{farm['phone'] or ''} {farm['email'] or ''}")
        b.markdown(f"**SALES RECEIPT**  \nNo. {s['receipt_no']}  \nDate: {ui.fmt_date(s['date'], code)}")
        st.markdown(f"**Sold to:** {s['buyer_name']}" + (f" · {s['buyer_phone']}" if s["buyer_phone"] else "")
                    + (f"  \n{s['buyer_address']}" if s["buyer_address"] else ""))
        table([{"Item": i["description"], "Amount": ui.money(i["price"], code)} for i in items] + [{"Item": "TOTAL", "Amount": ui.money(s["total"], code)}])
        st.markdown(f"Payment: {L(v_sales.PAYMENT, s['payment_method'])}" + (f"  \n{c['movement_label']}: {s['permit_no']}" if s["permit_no"] else ""))
        if s["notes"]:
            st.caption(s["notes"])
    linked = [i for i in items if i["livestock_id"]]
    if linked:
        st.subheader("Animals on this receipt")
        aid = table_pick([{"Animal": i["description"]} for i in linked], [i["livestock_id"] for i in linked], "sale_animals_tbl")
        if aid:
            go("animals", "detail", aid)


# ============================================================================ finance
def page_finance(R):
    R.require("finance")
    view = ss.get("view", "list")
    if view == "new":
        return tx_form(R, kind=ss.get("preset", {}).get("kind", "expense"))
    if view in ("edit", "detail"):
        tx = R.one("SELECT * FROM transactions WHERE id=? AND farm_id=?", (ss["rid"], R.fid))
        if not tx:
            raise web.NotFound()
        return tx_form(R, tx=tx)
    if view == "pnl":
        return finance_pnl(R)
    code = R.country
    cur = countries.country(code)
    h1, h2, h3, h4, h5 = st.columns([3, 1, 1, 1, 1])
    h1.title("Finance")
    if h2.button("+ Income", type="primary"):
        go(view="new", preset={"kind": "income"})
    if h3.button("+ Expense", type="primary"):
        go(view="new", preset={"kind": "expense"})
    if h4.button("Profit & loss"):
        go(view="pnl")
    with h5:
        csv_button(R, "transactions")
    t = TODAY()
    period = st.radio("Period", ["month", "year", "all", "custom"], index=1, horizontal=True, key="fi_period",
                      format_func={"month": "This month", "year": "This year", "all": "All time", "custom": "Custom dates"}.get)
    if period == "month":
        start, end = t.replace(day=1).isoformat(), t.isoformat()
    elif period == "all":
        start, end = "0000-01-01", "9999-12-31"
    elif period == "custom":
        c1, c2, _ = st.columns([1, 1, 2])
        start = iso(c1.date_input("From", value=t.replace(month=1, day=1), min_value=OLDEST, max_value=FAR, format="DD/MM/YYYY", key="fi_from"))
        end = iso(c2.date_input("To", value=t, min_value=OLDEST, max_value=FAR, format="DD/MM/YYYY", key="fi_to"))
    else:
        start, end = t.replace(month=1, day=1).isoformat(), t.isoformat()
    rows, inc, exp = v_finance.totals(R, R.fid, start, end)
    profit = inc - exp
    metrics([("Income", ui.money(inc, code)), ("Expenses", ui.money(exp, code)),
             ("Profit" if profit >= 0 else "Loss", ui.money(profit, code)), ("Profit margin", f"{profit / inc * 100:.0f}%" if inc else "—")])
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Income by category")
        table([{"Income from": L(common.ALL_CATEGORIES, r["category"]), "Entries": r["n"], "Amount": ui.money(r["s"], code)}
               for r in rows if r["kind"] == "income"], "No income in this period.")
    with c2:
        st.subheader("Expenses by category")
        table([{"Spent on": L(common.ALL_CATEGORIES, r["category"]), "Entries": r["n"], "Amount": ui.money(r["s"], code)}
               for r in rows if r["kind"] == "expense"], "No expenses in this period.")
    st.subheader(f"Income and expenses by month, last 12 months ({cur['currency']})")
    months = ui.months_back(12)
    series = {m: [0, 0] for m in months}
    for r in R.all("SELECT substr(date,1,7) m, kind, SUM(amount) s FROM transactions WHERE farm_id=? AND date >= ? GROUP BY m, kind",
                   (R.fid, months[0] + "-01")):
        if r["m"] in series:
            series[r["m"]][0 if r["kind"] == "income" else 1] = r["s"]
    pair_chart(series)
    st.subheader("Ledger")
    kind = st.radio("Entries", ["", "income", "expense"], horizontal=True, key="fi_kind",
                    format_func={"": "All entries", "income": "Income", "expense": "Expenses"}.get)
    sql, params = "SELECT * FROM transactions WHERE farm_id=? AND date BETWEEN ? AND ?", [R.fid, start, end]
    if kind:
        sql += " AND kind=?"
        params.append(kind)
    tx = R.all(sql + " ORDER BY date DESC, id DESC LIMIT 300", params)
    out = []
    for r in tx:
        src = v_finance.SOURCE_LINKS.get(r["source_type"], ("Manual entry (click to edit)", None))[0]
        out.append({"Date": ui.fmt_date(r["date"], code), "Category": L(common.ALL_CATEGORIES, r["category"]), "Description": r["description"],
                    "Paid by / to": r["party"] or "", "Amount": ("+" if r["kind"] == "income" else "−") + ui.money(r["amount"], code), "Source": src})
    chosen = table_pick(out, [r["id"] for r in tx], "ledger", "No entries. Record income such as milk sales, or expenses such as labour and transport.")
    st.caption(f"All amounts in {cur['currency_name']} ({cur['currency']}). Entries with a source were added automatically from sales, "
               "purchases, health records and stock purchases; change them from that record.")
    if chosen:
        row = next(r for r in tx if r["id"] == chosen)
        if row["source_type"]:
            st.info("This entry was created from another record. Change or delete that record instead.")
        else:
            go(view="edit", rid=chosen)


def tx_form(R, kind="expense", tx=None):
    code = R.country
    c = countries.country(code)
    kind = tx["kind"] if tx else (kind if kind in ("income", "expense") else "expense")
    cats = common.INCOME_CATEGORIES if kind == "income" else common.EXPENSE_CATEGORIES
    data = dict(tx) if tx else {"date": TODAY().isoformat(), "category": cats[0][0]}
    back()
    st.header(("Edit " if tx else "Record ") + kind)
    with st.form(key(f"tx_{tx['id'] if tx else kind}")):
        c1, c2 = st.columns(2)
        with c1:
            d = date_in("Date *", data.get("date"), required=True)
            cat = pick("Category", cats, data.get("category"))
        with c2:
            amount = num_in(f"Amount ({c['currency']}) *", data.get("amount"), help="Rwandan francs have no decimals" if c["decimals"] == 0 else None)
            party = st.text_input("Paid by" if kind == "income" else "Paid to", value=data.get("party") or "")
        desc = st.text_input("Description *", value=data.get("description") or "",
                             placeholder="e.g. Milk sold to dairy co-operative, March" if kind == "income" else "e.g. Herdsman wages, March")
        if st.form_submit_button("Save", type="primary", use_container_width=True):
            form = {"kind": kind, "date": iso(d), "category": cat, "amount": num_text(amount), "description": desc, "party": party}
            if tx:
                act(v_finance.tx_edit, tx["id"], form=form)
            else:
                act(v_finance.tx_new, form=form)
    if tx and R.can("delete"):
        if confirm("🗑 Delete entry", f"del_tx_{tx['id']}", "Delete this entry?"):
            act(v_finance.tx_delete, tx["id"])


def finance_pnl(R):
    code = R.country
    back("← Back to finance")
    st.title("Profit & loss")
    years = sorted({int(r["y"]) for r in R.all("SELECT DISTINCT substr(date,1,4) y FROM transactions WHERE farm_id=?", (R.fid,))
                    if str(r["y"]).isdigit()} | {TODAY().year}, reverse=True)
    year = st.selectbox("Year", years, key="pnl_year")
    months = [f"{year}-{m:02d}" for m in range(1, 13)]
    grid = {}
    for r in R.all("""SELECT substr(date,1,7) m, kind, category, SUM(amount) s FROM transactions
                      WHERE farm_id=? AND substr(date,1,4)=? GROUP BY m, kind, category""", (R.fid, str(year))):
        grid.setdefault((r["kind"], r["category"]), {})[r["m"]] = r["s"]
    out, inc_tot, exp_tot = [], [0] * 12, [0] * 12

    def line(name, values):
        row = {"Line": name}
        for m, v in zip(months, values):
            row[ui.month_label(m)] = ui.money(v, code, False) if v else "–"
        row["Year"] = ui.money(sum(values), code, False)
        return row

    for kind, cats, tot in (("income", common.INCOME_CATEGORIES, inc_tot), ("expense", common.EXPENSE_CATEGORIES, exp_tot)):
        for k, name in cats:
            vals = [grid.get((kind, k), {}).get(m, 0) for m in months]
            if any(vals):
                out.append(line(name, vals))
                for i, v in enumerate(vals):
                    tot[i] += v
        out.append(line("TOTAL INCOME" if kind == "income" else "TOTAL EXPENSES", tot))
    out.append(line("PROFIT / LOSS", [a - b for a, b in zip(inc_tot, exp_tot)]))
    inc, exp = sum(inc_tot), sum(exp_tot)
    metrics([(f"Income {year}", ui.money(inc, code)), (f"Expenses {year}", ui.money(exp, code)),
             (f"Profit {year}" if inc >= exp else f"Loss {year}", ui.money(inc - exp, code))])
    st.subheader(f"Profit and loss {year} — {R.farm['name']} ({countries.country(code)['currency']})")
    table(out)
    st.caption("Cash basis: income and costs are counted on the date money was received or paid.")
    st.download_button("⬇ Download as CSV", pd.DataFrame(out).to_csv(index=False).encode("utf-8"), f"profit-loss-{year}.csv", "text/csv")


# ============================================================================ reports
def page_reports(R):
    st.title("Reports")
    t = TODAY()
    scope_opts = [("farm", f"This farm: {R.farm['name']}")]
    mine_all = R.my_farms()
    for c in countries.COUNTRIES.values():
        mine = [f for f in mine_all if f["country_code"] == c["code"]]
        if len(mine) > 1 or (mine and mine[0]["id"] != R.fid):
            scope_opts.append((f"country:{c['code']}", f"All my farms in {c['name']} ({len(mine)})"))
    c1, c2, c3, c4 = st.columns([3, 1.5, 1.5, 2])
    with c1:
        scope = pick("Farm / country", scope_opts, "farm", k="re_scope")
    start = c2.date_input("From", value=t.replace(month=1, day=1), min_value=OLDEST, max_value=FAR, format="DD/MM/YYYY", key="re_from")
    end = c3.date_input("To", value=t, min_value=OLDEST, max_value=FAR, format="DD/MM/YYYY", key="re_to")
    with c4:
        species = pick("Species", common.ANIMAL_TYPES, "", blank="All species", k="re_type")
    if start > end:
        start, end = end, start
    q = {"scope": scope, "from": iso(start), "to": iso(end), "type": species}
    QR = StRequest("GET", query=q)
    try:
        farms, fids, code, scope = v_reports.scope_from_query(QR)
        fin = all(security.can(f["role"], "finance") for f in farms)
        d = v_reports.report_data(QR, fids, iso(start), iso(end), species)
        if all(security.can(f["role"], "export") for f in farms):
            resp = v_exports.export(QR, "report")
            st.download_button("⬇ Download report (CSV)", resp.body, resp.filename, "text/csv")
    finally:
        QR.conn.close()
    cur = countries.country(code)["currency"]
    st.caption(f"Report for **{', '.join(f['name'] for f in farms)}** ({countries.country(code)['name']}), "
               f"{ui.fmt_date(iso(start), code)} to {ui.fmt_date(iso(end), code)}"
               f"{', ' + L(common.ANIMAL_TYPES, species) + ' only' if species else ''}. Money in {cur}.")
    tabs = ["Population", "Health", "Breeding", "Feeding", "Inventory"] + (["Sales", "Income & profit"] if fin else [])
    T = st.tabs(tabs)
    with T[0]:
        mortality = d["deaths"] / (d["total_active"] + d["deaths"]) * 100 if (d["total_active"] + d["deaths"]) else None
        metrics([("Active animals", d["total_active"]), ("Born in period", d["births"]), ("Died in period", d["deaths"]),
                 ("Deaths as share of herd", v_breeding.pct(mortality))])
        a, b = st.columns(2)
        with a:
            st.subheader("Active animals by species")
            bars([(L(common.ANIMAL_TYPES, r["k"]), r["c"]) for r in d["population"]])
        with b:
            st.subheader("All animals by status")
            bars([(L(common.ANIMAL_STATUS, r["k"]), r["c"]) for r in d["status"]])
        st.subheader("Births and deaths by month")
        pair_chart({m: [v["born"], v["died"]] for m, v in d["movements"].items()}, names=("Born", "Died"))
        st.subheader("Herd movements")
        table([{"Month": ui.month_label(m), "Born": v["born"], "Bought / received": v["bought"], "Sold": v["sold"], "Died": v["died"],
                "Slaughtered / given": v["other_exit"]} for m, v in d["movements"].items()])
        if d["death_causes"]:
            st.subheader("Recorded causes of death")
            bars([(r["k"], r["c"]) for r in d["death_causes"]])
    with T[1]:
        items = [("Health records in period", sum(r["c"] for r in d["health_types"])), ("Notifiable disease records", d["notifiable"])]
        if fin:
            items.append(("Treatment costs", ui.money(d["health_cost"], code)))
        metrics(items)
        a, b = st.columns(2)
        with a:
            st.subheader("Records by type")
            bars([(L(common.HEALTH_TYPES, r["k"]), r["c"]) for r in d["health_types"]])
        with b:
            st.subheader("Most recorded diseases")
            bars([(r["k"] + (" ⚠" if r["n"] else ""), r["c"]) for r in d["diseases"]])
            if code == "ZM" and any(r["n"] for r in d["diseases"]):
                st.caption("⚠ = notifiable in Zambia (SI 81 of 2019)")
        st.subheader("Vaccination and treatment schedule, next 60 days")
        table([{"Due": ui.fmt_date(h["next_due_date"], code), "Animal": common.animal_name(h), "Vaccination / treatment": h["title"]}
               for h in d["schedule"]], "Nothing scheduled in the next 60 days.")
    with T[2]:
        b = d["breeding"]
        metrics([("Matings / inseminations", b["services"]), ("Conception rate", v_breeding.pct(b["conception_rate"])),
                 ("Young born alive", b["born_alive"])])
        metrics([("Born alive (share)", v_breeding.pct(b["survival"])), ("Young per birth", f"{b['litter']:.1f}" if b["litter"] else "—"),
                 ("Interval between births", f"{b['interval']:.0f} d" if b["interval"] else "—")])
        st.caption("Conception rate = services that resulted in pregnancy ÷ services whose result is known. Matings in the selected period.")
    with T[3]:
        items = [("Feeds used", len(d["feed_by_name"]))]
        if fin:
            items.append(("Feed cost in period", ui.money(d["feed_cost"], code)))
            if d["total_active"]:
                items.append(("Feed cost per active animal", ui.money(d["feed_cost"] / d["total_active"], code)))
        metrics(items)
        a, b = st.columns(2)
        with a:
            st.subheader("Quantity of each feed")
            bars([(r["k"], r["q"]) for r in d["feed_by_name"]], ylabel="Quantity")
        if fin:
            with b:
                st.subheader(f"Feed cost by species ({cur})")
                bars([("All animals" if r["k"] == "all" else L(common.ANIMAL_TYPES, r["k"]), r["s"] or 0) for r in d["feed_by_species"]], ylabel=cur)
    with T[4]:
        inv = d["inventory"]
        items = [("Products", inv["n"]), ("Low in stock", inv["low"] or 0)]
        if fin:
            items.append(("Stock value now", ui.money(inv["v"], code)))
        metrics(items)
        st.subheader("Low stock")
        table([{"Product": p["name"], "In stock": f"{ui.fmt_num(p['quantity'])} {p['unit']}",
                "Warning level": f"{ui.fmt_num(p['reorder_level'])} {p['unit']}"} for p in d["low_stock"]], "Nothing is low in stock.")
    if fin:
        with T[5]:
            metrics([("Animals sold", d["sales_heads"]), ("Sales revenue", ui.money(d["sales_total"], code)),
                     ("Average price per animal", ui.money(d["sales_total"] / d["sales_heads"], code) if d["sales_heads"] else "—")])
            st.subheader("Sales by species")
            table([{"Species": L(common.ANIMAL_TYPES, r["k"]), "Sold": r["c"], "Revenue": ui.money(r["s"], code),
                    "Average": ui.money(r["s"] / r["c"], code)} for r in d["sales"]], "No sales in this period.")
        with T[6]:
            profit = d["income"] - d["expense"]
            metrics([("Income", ui.money(d["income"], code)), ("Expenses", ui.money(d["expense"], code)),
                     ("Profit" if profit >= 0 else "Loss", ui.money(profit, code)),
                     ("Profit margin", f"{profit / d['income'] * 100:.0f}%" if d["income"] else "—")])
            if species:
                st.caption("Money figures cover the whole farm; the species filter does not apply to them.")
            st.subheader(f"Income and expenses by month ({cur})")
            pair_chart(d["fin_months"])
            a, b = st.columns(2)
            with a:
                st.subheader("By category")
                table([{"Type": "Income" if r["kind"] == "income" else "Expense", "Category": L(common.ALL_CATEGORIES, r["category"]),
                        "Amount": ui.money(r["s"], code)} for r in d["fin_cats"]], "No money recorded.")
            with b:
                st.subheader("Profitability by farm")
                table([{"Farm": r["name"], "Income": ui.money(r["inc"] or 0, code), "Expenses": ui.money(r["exp"] or 0, code),
                        "Profit": ui.money((r["inc"] or 0) - (r["exp"] or 0), code)} for r in d["per_farm"]])
    else:
        st.caption("Money sections are hidden because your role does not include finance on every farm in this report.")


# ============================================================================ farms
def page_farms(R):
    view = ss.get("view", "list")
    if view == "new":
        back()
        return farm_new(R)
    if view == "edit":
        return farm_edit(R)
    if view == "team":
        return farm_team(R)
    h = st.columns([3, 1.4, 1, 1])
    h[0].title("My farms")
    if h[1].button("+ Register another farm", type="primary"):
        go(view="new")
    if R.can("manage_farm"):
        if h[2].button("Edit this farm"):
            go(view="edit")
        if h[3].button("Team"):
            go(view="team")
    show_flashes()
    for f in R.my_farms():
        c = countries.country(f["country_code"])
        n = R.one("SELECT COUNT(*) c FROM livestock WHERE farm_id=? AND status='active'", (f["id"],))["c"]
        with st.container(border=True):
            a, b, cc, d = st.columns([3, 3, 2, 1])
            a.markdown(f"**{f['name']}**  \n{c['name']} · {c['currency']}")
            b.markdown(f"{f['district'] + ', ' + f['province'] if f['district'] else 'District not set'}  \n"
                       f"Your role: {dict(security.ROLES).get(f['role'], f['role'])}")
            cc.metric("Active animals", n)
            if f["id"] == R.fid:
                d.success("Current")
            elif d.button("Open", key=key(f"open_farm_{f['id']}")):
                ss["fid"] = f["id"]
                ss.setdefault("flashes", []).append((False, f"Now working on {f['name']}."))
                go("dashboard")
    st.caption("Each farm keeps its own animals, records and money. A Zambian farm reports in ZMW and a Rwandan farm in RWF; "
               "the system never converts between them.")
    c = countries.country(R.country)
    st.subheader(f"Rules that apply to farms in {c['name']}")
    for name, text, url in c["rules"]:
        st.markdown(f"- [{name}]({url}) — {text}")
    st.caption("Summaries for orientation only, not legal advice. Check the current rules with your veterinary office.")


def farm_edit(R):
    R.require("manage_farm")
    back()
    st.header("Edit farm")
    values = farm_form(R, R.country, dict(R.farm), key(f"farm_edit_{R.fid}"), editing=True)
    if values:
        act(v_farms.farm_edit, form=values)
    st.subheader("Danger zone")
    st.write("Deleting a farm removes all its animals, records and money permanently. Make a backup first (Settings → Backup).")
    if confirm("🗑 Delete this farm", f"del_farm_{R.fid}", "Delete this farm and ALL its records permanently?"):
        act(v_farms.farm_delete)


def farm_team(R):
    R.require("manage_farm")
    back()
    st.header("Farm team")
    show_flashes()
    members = R.all("""SELECT u.*, m.role farm_role, m.id mid FROM users u JOIN memberships m ON m.user_id=u.id
                       WHERE m.farm_id=? ORDER BY m.role='owner' DESC, u.first_name""", (R.fid,))
    for m in members:
        a, b, c, d = st.columns([2, 3, 2, 1])
        a.write(f"{m['first_name']} {m['last_name'] or ''}")
        b.write(m["email"])
        c.write(dict(security.ROLES).get(m["farm_role"]))
        if m["id"] != R.user["id"]:
            with d:
                if confirm("Remove", f"rm_member_{m['mid']}", f"Remove {m['first_name']} from this farm?"):
                    act(v_farms.farm_team_remove, m["mid"])
    st.subheader("Add a person")
    with st.form(key("team_add")):
        c1, c2 = st.columns(2)
        with c1:
            email = st.text_input("Email *", help="If they already have an account, only email and role are needed")
            first = st.text_input("First name (new accounts)")
            password = st.text_input("Temporary password (new accounts)", type="password")
        with c2:
            role = pick("Role", security.ROLES[1:], "worker")
            last = st.text_input("Last name (new accounts)")
        if st.form_submit_button("Add to farm", type="primary"):
            act(v_farms.farm_team, form={"email": email, "role": role, "first_name": first, "last_name": last, "password": password})
    st.subheader("What each role can do")
    table([{"Permission": lbl, **{n: ("✔" if p in security.PERMISSIONS[r] else "—") for r, n in security.ROLES}}
           for p, lbl in security.PERMISSION_LABELS.items()])
    st.caption("Everyone on a farm can view its animal, health, breeding, feeding, stock and task records.")


# ============================================================================ settings
def page_settings(R):
    u = R.user
    st.title("Settings")
    show_flashes()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("My profile")
        with st.form("profile"):
            st.text_input("Email", value=u["email"], disabled=True, help="Your sign-in name")
            first = st.text_input("First name *", value=u["first_name"])
            last = st.text_input("Last name", value=u["last_name"] or "")
            phone = st.text_input("Phone", value=u["phone"] or "")
            if st.form_submit_button("Save profile", type="primary"):
                act(v_settings.settings, form={"first_name": first, "last_name": last, "phone": phone})
    with c2:
        st.subheader("Password")
        with st.form("password", clear_on_submit=True):
            cur = st.text_input("Current password", type="password")
            new = st.text_input("New password", type="password", help="At least 8 characters, not only numbers")
            conf = st.text_input("Confirm new password", type="password")
            if st.form_submit_button("Change password", type="primary"):
                act(v_settings.settings_password, form={"current": cur, "new": new, "confirm": conf})
    if u["is_admin"]:
        st.subheader("Backup and recovery (administrator)")
        st.write("A backup is a complete copy of the database (all farms). **On Streamlit Cloud the database is reset whenever the "
                 "app restarts**, so download a backup regularly and restore it here when needed.")
        b1, b2 = st.columns(2)
        with b1:
            if st.button("Make a backup now"):
                act(v_settings.settings_backup)
            for name in db.list_backups()[:15]:
                path = os.path.join(config.BACKUP_DIR, name)
                with open(path, "rb") as fh:
                    st.download_button(f"⬇ {name} ({os.path.getsize(path) / 1024:.0f} KB)", fh.read(), name,
                                       "application/octet-stream", key=key("dl_" + name))
        with b2:
            up = st.file_uploader("Restore from a backup file (.db)", type=["db"])
            if up is not None and confirm("Restore this backup", "restore_db",
                                          "Replace ALL current data with this backup? The current database is backed up first."):
                os.makedirs(config.BACKUP_DIR, exist_ok=True)
                tmp = os.path.join(config.BACKUP_DIR, "uploaded-restore.tmp")
                with open(tmp, "wb") as fh:
                    fh.write(up.getbuffer())
                try:
                    db.restore_db(tmp)
                    sign_out_state()
                    ss["flashes"] = [(False, "Backup restored. Sign in again.")]
                    st.rerun()
                except Exception as exc:
                    st.error(f"That file could not be restored: {exc}")
                finally:
                    if os.path.exists(tmp):
                        os.remove(tmp)
    st.subheader("Account")
    st.caption("Language: English. The interface text is kept in jesse_farm/i18n.py, so other languages such as Kinyarwanda "
               "or Bemba can be added later.")
    if confirm("Delete my account", "del_account", "Delete your account? Farms where you are the only member are deleted with all their records."):
        act(v_settings.delete_account)


# ============================================================================ main
def main():
    if "_nav" in ss:
        ss["page"] = ss.pop("_nav")
    R = StRequest()
    try:
        if not R.user:
            page_auth()
            return
        with st.sidebar:
            st.markdown(f"### 🐄 {config.APP_SHORT}")
            st.caption(f"Signed in as {R.user['first_name']} {R.user['last_name'] or ''}")
            if R.farm:
                farms = R.my_farms()
                ids = [f["id"] for f in farms]
                names = {f["id"]: f"{f['name']} ({countries.country(f['country_code'])['currency']})" for f in farms}
                chosen = st.selectbox("Farm", ids, index=ids.index(R.fid), format_func=names.get, key=key("farm_switch"))
                if chosen != R.fid:
                    ss["fid"] = chosen
                    go("dashboard")
                allowed = [p for p in PAGES if p[0] not in ("sales", "finance") or R.can("finance")]
                keys = [p for p, _ in allowed]
                if ss.get("page") not in keys:
                    ss["page"] = "dashboard"
                st.radio("Menu", keys, format_func=dict(allowed).get, key="page", label_visibility="collapsed",
                         on_change=lambda: ss.update(view="list", rid=None, preset={}, confirm=None))
            if st.button("Sign out", use_container_width=True):
                sign_out_state()
                st.rerun()
        if not R.farm:
            st.title("Register your farm")
            ss["preset"] = {"welcome": "1"}
            farm_new(R)
            return
        st.caption(f"{R.farm['name']} · {countries.country(R.country)['name']} · money in {countries.country(R.country)['currency']}")
        if ss.get("view", "list") == "list":
            show_flashes()
        page = ss.get("page", "dashboard")
        try:
            {"dashboard": page_dashboard, "animals": page_animals, "breeding": page_breeding, "health": page_health,
             "feeding": page_feeding, "inventory": page_inventory, "tasks": page_tasks, "sales": page_sales,
             "finance": page_finance, "reports": page_reports, "farms": page_farms, "settings": page_settings}[page](R)
        except web.Forbidden as f:
            st.error(f.message)
        except web.NotFound:
            st.error("That record doesn't exist, or it belongs to another farm.")
            if st.button("Back to the list"):
                go(view="list")
    finally:
        R.conn.close()


main()
