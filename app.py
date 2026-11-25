#!/usr/bin/env python3
"""
JESSE FARM MANAGEMENT SYSTEM - Livestock Management System for Zambia and Rwanda
Complete source code in ONE file.

Student: HIRWA MIRINDI JESSE (2214010176) - Bachelor's degree in Computer Science, Wuhan Institute of Technology

HOW TO RUN (needs only Python 3.11 or newer, nothing to install):
    python jesse_farm_management_system.py --demo     # with demonstration farms in Zambia and Rwanda
    python jesse_farm_management_system.py            # empty system for real use
    python jesse_farm_management_system.py --help     # all options (--port, --backup, --restore, ...)
The browser opens at http://127.0.0.1:8000. Demo login: demo@jesse.farm / demo1234
The database (jesse_farm.db) and the backups folder are created next to this file.

HOW THIS FILE IS ORGANISED
The system is normally a Python package (jesse_farm/) plus run.py. To keep everything in one file, each module's
source code is stored below, unchanged, in the dictionary MODULES (module name -> source code). A small loader at
the bottom registers them with Python's import system, so the modules import each other exactly as in the package
version. Part 3 (at the end) is the original run.py: the command-line entry point.

Modules in this file (4366 lines of code in total):
    jesse_farm (package)
    jesse_farm.app
    jesse_farm.config
    jesse_farm.countries
    jesse_farm.db
    jesse_farm.demo
    jesse_farm.i18n
    jesse_farm.security
    jesse_farm.ui
    jesse_farm.views (package)
    jesse_farm.views.animals
    jesse_farm.views.auth
    jesse_farm.views.breeding
    jesse_farm.views.common
    jesse_farm.views.dashboard
    jesse_farm.views.exports
    jesse_farm.views.farms
    jesse_farm.views.feeding
    jesse_farm.views.finance
    jesse_farm.views.health
    jesse_farm.views.inventory
    jesse_farm.views.reports
    jesse_farm.views.sales
    jesse_farm.views.settings
    jesse_farm.views.tasks
    jesse_farm.web
    run (entry point, Part 3)
"""
import importlib.abc
import importlib.util
import os
import sys

# ============================================================================ PART 1: SOURCE CODE OF EVERY MODULE
MODULES = {}
PACKAGES = set()

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm  (package)
# --------------------------------------------------------------------------------------------------------------
PACKAGES.add('jesse_farm')
MODULES['jesse_farm'] = r'''"""JESSE FARM MANAGEMENT SYSTEM application package."""
'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.app
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.app'] = r'''"""Starts the web server."""
import socket
import sys
import threading
import webbrowser
from http.server import ThreadingHTTPServer

from . import config, db
from .web import Handler

# Importing the view modules registers their pages (the @route decorators run on import).
from .views import (animals, auth, breeding, dashboard, exports, farms, feeding, finance, health,  # noqa: F401
                    inventory, reports, sales, settings, tasks)


def lan_ip():
    """The computer's address on the local network, so a phone on the same Wi-Fi can connect."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # no data is sent; this only selects the network card in use
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return None


def make_server(port, local_only=False):
    host = "127.0.0.1" if local_only else "0.0.0.0"
    return ThreadingHTTPServer((host, port), Handler)


def serve(port=config.DEFAULT_PORT, open_browser=True, local_only=False, quiet=False, demo_note=False):
    db.init_db()
    Handler.quiet = quiet
    try:
        server = make_server(port, local_only)
    except OSError:
        print(f"Port {port} is already in use. Try:  python run.py --port {port + 1}")
        sys.exit(1)
    url = f"http://127.0.0.1:{port}"
    print(f"\n  {config.APP_NAME} is running")
    print(f"  On this computer:   {url}")
    ip = None if local_only else lan_ip()
    if ip:
        print(f"  On a phone/tablet:  http://{ip}:{port}   (same Wi-Fi; allow Python through the firewall if Windows asks)")
    if demo_note:
        print("  Demo sign-in:       demo@jesse.farm / demo1234   (more accounts in README.md)")
    print(f"  Database:           {config.DB_PATH}")
    print("  Stop with Ctrl+C\n")
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()

'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.config
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.config'] = r'''"""Settings that you may want to change. Everything else reads from here."""
import os

APP_NAME = "JESSE FARM MANAGEMENT SYSTEM"
APP_SHORT = "JESSE FMS"
VERSION = "2.0"

# The project folder (the one that contains run.py)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Database file. Can be overridden with the JESSE_DB environment variable (the tests do this).
DB_PATH = os.environ.get("JESSE_DB", os.path.join(BASE_DIR, "jesse_farm.db"))
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

SESSION_DAYS = 14
PASSWORD_ITERATIONS = 200_000
DEFAULT_PORT = 8000
LANGUAGE = "en"
'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.countries
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.countries'] = r'''"""
Country configuration for Zambia and Rwanda.

Everything that differs between the two countries lives in this one file, so adding a
third country later means adding one more entry to COUNTRIES (see the thesis, Chapter 4).

Sources (opened while building the system, November 2026):
- Zambia districts: Wikipedia "Districts of Zambia" (2026-03 snapshot) and "Lusaka Province".
  Sources disagree on Chirundu (Southern vs Lusaka Province); this list follows Wikipedia
  (Southern). CONFIRM with the Ministry of Local Government if it matters for your study.
- Rwanda districts: statoids.com "Districts of Rwanda" (codes from MINALOC); 5 provinces,
  30 districts, 416 sectors per gov.rw.
- Currency minor units: ISO 4217 (ZMW = 2 decimals, RWF = 0 decimals).
- Zambia notifiable diseases: Animal Health (Notifiable Diseases) Regulations, SI No. 81 of 2019,
  made under the Animal Health Act No. 27 of 2010.
- Gestation lengths: MSD/Merck Veterinary Manual table "Approximate Gestation Periods";
  cattle 283 days per NMSU Guide B-130 (citing the Merck Veterinary Manual).
"""

ZAMBIA_PROVINCES = {
    "Central": ["Chibombo", "Chisamba", "Chitambo", "Kabwe", "Kapiri Mposhi", "Luano", "Mkushi", "Mumbwa",
                "Ngabwe", "Serenje", "Shibuyunji"],
    "Copperbelt": ["Chililabombwe", "Chingola", "Kalulushi", "Kitwe", "Luanshya", "Lufwanyama", "Masaiti",
                   "Mpongwe", "Mufulira", "Ndola"],
    "Eastern": ["Chadiza", "Chama", "Chasefu", "Chipangali", "Chipata", "Kasenengwa", "Katete", "Lumezi",
                "Lundazi", "Lusangazi", "Mambwe", "Nyimba", "Petauke", "Sinda", "Vubwi"],
    "Luapula": ["Chembe", "Chiengi", "Chifunabuli", "Chipili", "Kawambwa", "Lunga", "Mansa", "Milenge",
                "Mwansabombwe", "Mwense", "Nchelenge", "Samfya"],
    "Lusaka": ["Chilanga", "Chongwe", "Kafue", "Luangwa", "Lusaka", "Rufunsa"],
    "Muchinga": ["Chinsali", "Isoka", "Kanchibiya", "Lavushimanda", "Mafinga", "Mpika", "Nakonde", "Shiwang'andu"],
    "Northern": ["Chilubi", "Kaputa", "Kasama", "Lunte", "Lupososhi", "Luwingu", "Mbala", "Mporokoso", "Mpulungu",
                 "Mungwi", "Nsama", "Senga"],
    "North-Western": ["Chavuma", "Ikelenge", "Kabompo", "Kasempa", "Kalumbila", "Manyinga", "Mufumbwe",
                      "Mushindamo", "Mwinilunga", "Solwezi", "Zambezi"],
    "Southern": ["Chikankata", "Chirundu", "Choma", "Gwembe", "Itezhi-Tezhi", "Kalomo", "Kazungula", "Livingstone",
                 "Mazabuka", "Monze", "Namwala", "Pemba", "Siavonga", "Sinazongwe", "Zimba"],
    "Western": ["Kalabo", "Kaoma", "Limulunga", "Luampa", "Lukulu", "Mitete", "Mongu", "Mulobezi", "Mwandi",
                "Nalolo", "Nkeyema", "Senanga", "Sesheke", "Shang'ombo", "Sikongo", "Sioma"],
}

RWANDA_PROVINCES = {
    "Kigali City": ["Gasabo", "Kicukiro", "Nyarugenge"],
    "Eastern": ["Bugesera", "Gatsibo", "Kayonza", "Kirehe", "Ngoma", "Nyagatare", "Rwamagana"],
    "Northern": ["Burera", "Gakenke", "Gicumbi", "Musanze", "Rulindo"],
    "Southern": ["Gisagara", "Huye", "Kamonyi", "Muhanga", "Nyamagabe", "Nyanza", "Nyaruguru", "Ruhango"],
    "Western": ["Karongi", "Ngororero", "Nyabihu", "Nyamasheke", "Rubavu", "Rusizi", "Rutsiro"],
}

# Animal Health (Notifiable Diseases) Regulations, SI No. 81 of 2019 (Zambia) - the full schedule.
ZAMBIA_NOTIFIABLE = [
    "African swine fever", "American foulbrood", "Anthrax", "Bluetongue", "Bovine anaplasmosis",
    "Bovine babesiosis", "Bovine spongiform encephalopathy", "Bovine tuberculosis", "Bovine virus diarrhoea",
    "Brucellosis (Brucella abortus)", "Brucellosis (Brucella melitensis)", "Brucellosis (Brucella suis)",
    "Contagious bovine pleuropneumonia (CBPP)", "Contagious caprine pleuropneumonia", "Contagious equine metritis",
    "Dourine", "Duck virus hepatitis", "Enzootic abortion", "Epizootic ulcerative syndrome",
    "Equine infectious anaemia", "Equine viral arteritis", "European foulbrood", "Foot and mouth disease",
    "Glanders", "Haemorrhagic septicaemia", "Heartwater", "Highly pathogenic avian influenza",
    "African horse sickness", "Equine herpesvirus 1", "Peste des petits ruminants",
    "Infectious bovine rhinotracheitis", "Infectious bursal disease (Gumboro)", "Varroosis (honey bees)",
    "Johne's disease", "Koi herpesvirus disease", "Lumpy skin disease", "Malignant catarrhal fever",
    "Nairobi sheep disease", "Newcastle disease", "Porcine cysticercosis", "Q fever", "Rabies",
    "Rift Valley fever", "Scrapie", "Sheep pox and goat pox", "Spring viraemia of carp",
    "Theileriosis / East Coast fever", "Tilapia lake virus", "Transmissible spongiform encephalopathy",
    "Trypanosomiasis (tsetse-transmitted)", "Viral haemorrhagic septicaemia",
]

# Suggestions only (a starting list for the disease field). NOT an official Rwandan list:
# the 2026 law leaves the disease list to ministerial orders that were still being drafted.
COMMON_DISEASES = [
    "Foot and mouth disease", "Theileriosis / East Coast fever", "Lumpy skin disease", "Anthrax",
    "Brucellosis", "Contagious bovine pleuropneumonia (CBPP)", "African swine fever", "Newcastle disease",
    "Rabies", "Rift Valley fever", "Peste des petits ruminants", "Mastitis", "Heartwater", "Trypanosomiasis",
    "Internal parasites (worms)", "Ticks", "Pneumonia", "Diarrhoea",
]

COUNTRIES = {
    "ZM": {
        "code": "ZM",
        "name": "Zambia",
        "currency": "ZMW",
        "currency_name": "Zambian Kwacha",
        "decimals": 2,
        "provinces": ZAMBIA_PROVINCES,
        "area_label": "Town / ward / village",
        "area_hint": "e.g. Mazabuka town or the village name",
        "date_format": "%d/%m/%Y",  # Assumption: day/month/year is the common written order; confirm locally.
        "notifiable": ZAMBIA_NOTIFIABLE,
        "notifiable_note": ("Notifiable in Zambia (Animal Health (Notifiable Diseases) Regulations, SI 81 of 2019). "
                            "Report it to the nearest veterinary officer."),
        "id_label": "Brand / identification mark",
        "id_hint": "Registered mark under the Animal Identification and Traceability Act No. 2 of 2024",
        "movement_label": "Stock movement permit no.",
        "extra_acquisition": [],
        "rules": [
            ("Animal Health Act No. 27 of 2010",
             "Names the Director of Veterinary Services as the veterinary authority; covers disease control, "
             "movement of animals, cleansing (dipping) and tsetse control.",
             "https://leap.unep.org/en/countries/zm/national-legislation/animal-health-act-2010-no-27-2010"),
            ("Animal Health (Notifiable Diseases) Regulations, SI 81 of 2019",
             "Lists 51 notifiable diseases, including FMD, East Coast fever, CBPP, ASF, lumpy skin disease and "
             "Newcastle disease.",
             "https://faolex.fao.org/docs/pdf/zam228980.pdf"),
            ("Animal Identification and Traceability Act No. 2 of 2024",
             "Creates a national animal identification and traceability system and registration of "
             "identification marks and premises.",
             "https://leap.unep.org/en/countries/zm/national-legislation/animal-identification-and-traceability-act-2024-act-no-2-2024"),
            ("Animal Health (Veterinary Services Fees) Regulations, SI 22 of 2018",
             "Sets fees for veterinary services and stock movement permits (inter-district and inter-provincial).",
             "https://leap.unep.org/en/countries/zm/national-legislation/animal-health-veterinary-services-fees-regulations-2018-si-no-22"),
        ],
    },
    "RW": {
        "code": "RW",
        "name": "Rwanda",
        "currency": "RWF",
        "currency_name": "Rwandan Franc",
        "decimals": 0,
        "provinces": RWANDA_PROVINCES,
        "area_label": "Sector (umurenge)",
        "area_hint": "e.g. Gishali; add the cell after a comma if you like",
        "date_format": "%d/%m/%Y",  # Assumption: day/month/year; confirm locally.
        "notifiable": [],
        "notifiable_note": ("Rwanda's 2026 law on animal husbandry requires surveillance and reporting of infectious "
                            "diseases; the detailed list is set by ministerial order. Confirm with your sector "
                            "veterinary officer or RAB."),
        "id_label": "Ear tag / national animal ID",
        "id_hint": "Number on the national cattle ear tag, if the animal has one",
        "movement_label": "Movement and transport certificate no.",
        "extra_acquisition": [("girinka", "Girinka programme")],
        "rules": [
            ("Law governing animal husbandry and fisheries (Official Gazette, 11 September 2026)",
             "Requires a certificate for moving and transporting animals (Article 53) and provides for registering "
             "farmers as small, medium or large scale; details follow in ministerial orders.",
             "https://allafrica.com/stories/202610190018.html"),
            ("Same law: veterinary medicines and One Health (Article 4)",
             "Tightens control of animal treatment and veterinary medicines; requires farmers and vets to apply "
             "the One Health principle.",
             "https://allafrica.com/stories/202610200123.html"),
            ("Girinka (One Cow per Poor Family), since 2006",
             "A family receiving a Girinka cow passes on its first female calf to another family.",
             "https://www.minagri.gov.rw/updates/news-details/how-a-single-jersey-cow-turned-round-life-for-a-rural-rwandan-community"),
            ("National cattle identification and registration (RAB)",
             "RAB is rolling out ear-tag identification of cattle for traceability.",
             "https://www.icar.org/Documents/Verona-2026/Presentations/TS03_02__Shumbusho.pdf"),
        ],
    },
}

COUNTRY_CHOICES = [(c["code"], c["name"]) for c in COUNTRIES.values()]

# Average gestation in days (MSD/Merck Veterinary Manual; cattle per NMSU B-130).
# Poultry: 21 days incubation is an ASSUMPTION (not verified in this study) - confirm.
GESTATION_DAYS = {"cattle": 283, "goat": 150, "sheep": 150, "pig": 114, "rabbit": 31, "poultry": 21}


def country(code):
    return COUNTRIES.get(code) or COUNTRIES["ZM"]


def district_options(code):
    """(value, label, group) tuples for a district <select>, grouped by province."""
    out = []
    for province, districts in country(code)["provinces"].items():
        for d in districts:
            out.append((f"{province}|{d}", d, province))
    return out


def valid_location(code, province, district):
    return district in country(code)["provinces"].get(province, [])


def is_notifiable(code, disease):
    if not disease:
        return False
    d = disease.strip().lower()
    return any(d == n.lower() or (len(d) > 5 and d in n.lower()) for n in country(code)["notifiable"])
'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.db
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.db'] = r'''"""
Database: connection, schema, migrations, backup and restore.

How versions work
-----------------
SQLite stores a number called user_version inside the database file.
  version 0/1 = the original single-file livestock_app.py database
  version 2   = JESSE FARM MANAGEMENT SYSTEM (multi-farm, Zambia/Rwanda, finance, breeding, feeding, sales)

A brand-new database is created with the version 1 tables and then upgraded by exactly the same
migration that upgrades an old livestock_app.py database. That way the migration is exercised every
time the system is installed, and old data can never take a different path from new data.

All SQL in the system uses "?" placeholders, never string formatting of user values, which
prevents SQL injection. Table and column names that are put into SQL are always fixed in code.
"""
import datetime as dt
import os
import shutil
import sqlite3

from . import config

SCHEMA_VERSION = 2

# --------------------------------------------------------------------------- version 1 (original app)
SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS farms (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    address TEXT DEFAULT '',
    city TEXT DEFAULT '',
    country TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    farm_id INTEGER REFERENCES farms(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    first_name TEXT NOT NULL,
    last_name TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    role TEXT NOT NULL DEFAULT 'owner',
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    csrf TEXT NOT NULL,
    flash TEXT DEFAULT '',
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS livestock (
    id INTEGER PRIMARY KEY,
    farm_id INTEGER NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    tag_number TEXT UNIQUE,
    name TEXT DEFAULT '',
    animal_type TEXT NOT NULL,
    breed TEXT DEFAULT '',
    gender TEXT NOT NULL,
    date_of_birth TEXT,
    acquisition_date TEXT NOT NULL,
    acquisition_method TEXT NOT NULL DEFAULT 'born',
    status TEXT NOT NULL DEFAULT 'active',
    weight_kg REAL,
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS health_records (
    id INTEGER PRIMARY KEY,
    livestock_id INTEGER NOT NULL REFERENCES livestock(id) ON DELETE CASCADE,
    record_type TEXT NOT NULL,
    title TEXT NOT NULL,
    date TEXT NOT NULL,
    diagnosis TEXT DEFAULT '',
    treatment TEXT DEFAULT '',
    vet_name TEXT DEFAULT '',
    cost REAL NOT NULL DEFAULT 0,
    next_due_date TEXT,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY,
    farm_id INTEGER NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    UNIQUE (farm_id, name)
);
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    farm_id INTEGER NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    unit TEXT NOT NULL DEFAULT 'kg',
    quantity REAL NOT NULL DEFAULT 0,
    reorder_level REAL NOT NULL DEFAULT 0,
    unit_price REAL NOT NULL DEFAULT 0,
    expiry_date TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    change REAL NOT NULL,
    reason TEXT DEFAULT '',
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY,
    farm_id INTEGER NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    priority TEXT NOT NULL DEFAULT 'medium',
    status TEXT NOT NULL DEFAULT 'pending',
    due_date TEXT,
    assigned_to INTEGER REFERENCES users(id) ON DELETE SET NULL,
    livestock_id INTEGER REFERENCES livestock(id) ON DELETE SET NULL,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    completed_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

# --------------------------------------------------------------------------- version 1 -> 2
MIGRATION_1_TO_2 = """
-- Farms: country, location, size and ownership
ALTER TABLE farms ADD COLUMN country_code TEXT NOT NULL DEFAULT 'ZM';
ALTER TABLE farms ADD COLUMN province TEXT DEFAULT '';
ALTER TABLE farms ADD COLUMN district TEXT DEFAULT '';
ALTER TABLE farms ADD COLUMN local_area TEXT DEFAULT '';
ALTER TABLE farms ADD COLUMN size_ha REAL;
ALTER TABLE farms ADD COLUMN ownership TEXT DEFAULT 'individual';
ALTER TABLE farms ADD COLUMN owner_name TEXT DEFAULT '';
ALTER TABLE farms ADD COLUMN registration_no TEXT DEFAULT '';
ALTER TABLE farms ADD COLUMN farm_scale TEXT DEFAULT 'small';
UPDATE farms SET country_code = 'RW' WHERE lower(trim(country)) IN ('rwanda', 'rw');

-- Users can belong to several farms, with a role on each
ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0;
CREATE TABLE memberships (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    farm_id INTEGER NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'owner',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, farm_id)
);
INSERT INTO memberships (user_id, farm_id, role)
    SELECT id, farm_id, role FROM users WHERE farm_id IS NOT NULL;
UPDATE users SET is_admin = 1 WHERE id = (SELECT MIN(id) FROM users);
ALTER TABLE sessions ADD COLUMN farm_id INTEGER REFERENCES farms(id) ON DELETE SET NULL;

-- Livestock: identification, parents, purchase and exit details
ALTER TABLE livestock ADD COLUMN official_id TEXT DEFAULT '';
ALTER TABLE livestock ADD COLUMN colour TEXT DEFAULT '';
ALTER TABLE livestock ADD COLUMN dam_id INTEGER REFERENCES livestock(id) ON DELETE SET NULL;
ALTER TABLE livestock ADD COLUMN sire_id INTEGER REFERENCES livestock(id) ON DELETE SET NULL;
ALTER TABLE livestock ADD COLUMN purchase_price REAL;
ALTER TABLE livestock ADD COLUMN seller TEXT DEFAULT '';
ALTER TABLE livestock ADD COLUMN exit_date TEXT;
ALTER TABLE livestock ADD COLUMN exit_reason TEXT DEFAULT '';
ALTER TABLE livestock ADD COLUMN pass_on_due INTEGER NOT NULL DEFAULT 0;
UPDATE livestock SET status = 'dead' WHERE status = 'deceased';
CREATE INDEX IF NOT EXISTS idx_livestock_farm ON livestock(farm_id, status);

CREATE TABLE weights (
    id INTEGER PRIMARY KEY,
    livestock_id INTEGER NOT NULL REFERENCES livestock(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    weight_kg REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO weights (livestock_id, date, weight_kg)
    SELECT id, substr(created_at, 1, 10), weight_kg FROM livestock WHERE weight_kg IS NOT NULL;

-- Health: disease, notifiable flag, medicine withdrawal date
ALTER TABLE health_records ADD COLUMN disease TEXT DEFAULT '';
ALTER TABLE health_records ADD COLUMN notifiable INTEGER NOT NULL DEFAULT 0;
ALTER TABLE health_records ADD COLUMN withdrawal_until TEXT;
CREATE INDEX IF NOT EXISTS idx_health_due ON health_records(next_due_date);

-- Inventory: product kind (decides the expense category) and cost of each stock movement
ALTER TABLE products ADD COLUMN kind TEXT NOT NULL DEFAULT 'other';
UPDATE products SET kind = 'feed' WHERE category_id IN (SELECT id FROM categories WHERE lower(name) LIKE '%feed%');
UPDATE products SET kind = 'medicine' WHERE category_id IN (SELECT id FROM categories WHERE lower(name) LIKE '%medic%' OR lower(name) LIKE '%vaccin%' OR lower(name) LIKE '%drug%');
UPDATE products SET kind = 'equipment' WHERE category_id IN (SELECT id FROM categories WHERE lower(name) LIKE '%equip%');
ALTER TABLE stock_movements ADD COLUMN unit_cost REAL;
CREATE INDEX IF NOT EXISTS idx_tasks_farm ON tasks(farm_id, status, due_date);

-- Breeding and reproduction
CREATE TABLE breeding_events (
    id INTEGER PRIMARY KEY,
    farm_id INTEGER NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    female_id INTEGER NOT NULL REFERENCES livestock(id) ON DELETE CASCADE,
    male_id INTEGER REFERENCES livestock(id) ON DELETE SET NULL,
    method TEXT NOT NULL DEFAULT 'natural',
    sire_details TEXT DEFAULT '',
    mating_date TEXT NOT NULL,
    expected_date TEXT,
    status TEXT NOT NULL DEFAULT 'served',
    check_date TEXT,
    outcome_date TEXT,
    born_alive INTEGER NOT NULL DEFAULT 0,
    born_dead INTEGER NOT NULL DEFAULT 0,
    notes TEXT DEFAULT '',
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_breeding_farm ON breeding_events(farm_id, status);

-- Feeding
CREATE TABLE feeding_records (
    id INTEGER PRIMARY KEY,
    farm_id INTEGER NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
    feed_name TEXT NOT NULL,
    animal_type TEXT DEFAULT '',
    livestock_id INTEGER REFERENCES livestock(id) ON DELETE SET NULL,
    animal_count INTEGER NOT NULL DEFAULT 1,
    quantity REAL NOT NULL,
    unit TEXT NOT NULL DEFAULT 'kg',
    cost REAL NOT NULL DEFAULT 0,
    notes TEXT DEFAULT '',
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_feeding_farm ON feeding_records(farm_id, date);

-- Livestock sales and receipts
CREATE TABLE sales (
    id INTEGER PRIMARY KEY,
    farm_id INTEGER NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    receipt_no TEXT NOT NULL UNIQUE,
    date TEXT NOT NULL,
    buyer_name TEXT NOT NULL,
    buyer_phone TEXT DEFAULT '',
    buyer_address TEXT DEFAULT '',
    payment_method TEXT NOT NULL DEFAULT 'cash',
    permit_no TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    total REAL NOT NULL DEFAULT 0,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE sale_items (
    id INTEGER PRIMARY KEY,
    sale_id INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
    livestock_id INTEGER REFERENCES livestock(id) ON DELETE SET NULL,
    description TEXT NOT NULL,
    price REAL NOT NULL
);
CREATE INDEX idx_sales_farm ON sales(farm_id, date);

-- Finance: one ledger. Other modules add linked rows (source_type/source_id) automatically.
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY,
    farm_id INTEGER NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('income', 'expense')),
    category TEXT NOT NULL,
    amount REAL NOT NULL CHECK (amount >= 0),
    description TEXT DEFAULT '',
    party TEXT DEFAULT '',
    source_type TEXT DEFAULT '',
    source_id INTEGER,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_tx_farm ON transactions(farm_id, date);
CREATE INDEX idx_tx_source ON transactions(source_type, source_id);

-- Bring existing costs into the ledger so old farms get correct profit and loss figures
INSERT INTO transactions (farm_id, date, kind, category, amount, description, source_type, source_id)
    SELECT l.farm_id, h.date, 'expense', 'veterinary', h.cost, h.title, 'health', h.id
    FROM health_records h JOIN livestock l ON l.id = h.livestock_id WHERE h.cost > 0;
"""


def connect(path=None):
    conn = sqlite3.connect(path or config.DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def version(conn):
    return conn.execute("PRAGMA user_version").fetchone()[0]


def has_table(conn, name):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def init_db(path=None, log=print):
    """Create or upgrade the database. Safe to call every time the app starts."""
    path = path or config.DB_PATH
    existed = os.path.exists(path) and os.path.getsize(path) > 0
    conn = connect(path)
    try:
        v = version(conn)
        if v >= SCHEMA_VERSION:
            return v
        if existed and has_table(conn, "farms"):
            # An existing older database: keep a copy before changing anything
            backup = backup_db(path, label=f"before-upgrade-v{v}")
            log(f"  Upgrading database to version {SCHEMA_VERSION}. A copy was saved first: {backup}")
        conn.executescript(SCHEMA_V1)
        # Executes the migration inside one transaction: either everything is upgraded or nothing is
        conn.executescript("BEGIN;" + MIGRATION_1_TO_2 + f"PRAGMA user_version = {SCHEMA_VERSION};COMMIT;")
        conn.execute("PRAGMA journal_mode = WAL")
        return SCHEMA_VERSION
    except Exception:
        conn.rollback() if conn.in_transaction else None
        raise
    finally:
        conn.close()


# --------------------------------------------------------------------------- backup and restore
def backup_db(path=None, label="manual"):
    """Copy the live database safely (SQLite's online backup) into the backups folder."""
    path = path or config.DB_PATH
    os.makedirs(config.BACKUP_DIR, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    target = os.path.join(config.BACKUP_DIR, f"jesse-{stamp}-{label}.db")
    n = 1
    while os.path.exists(target):
        n += 1
        target = os.path.join(config.BACKUP_DIR, f"jesse-{stamp}-{label}-{n}.db")
    src = sqlite3.connect(path)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return target


def list_backups():
    if not os.path.isdir(config.BACKUP_DIR):
        return []
    files = [f for f in os.listdir(config.BACKUP_DIR) if f.endswith(".db")]
    return sorted(files, reverse=True)


def restore_db(backup_file, path=None):
    """Replace the live database with a backup. The current database is backed up first."""
    path = path or config.DB_PATH
    check = sqlite3.connect(backup_file)
    try:
        ok = check.execute("PRAGMA integrity_check").fetchone()[0]
        if ok != "ok":
            raise ValueError(f"Backup failed the integrity check: {ok}")
    finally:
        check.close()
    safety = backup_db(path, label="before-restore") if os.path.exists(path) else None
    for extra in ("-wal", "-shm"):
        if os.path.exists(path + extra):
            os.remove(path + extra)
    shutil.copyfile(backup_file, path)
    init_db(path, log=lambda *_: None)  # upgrade if the backup came from an older version
    return safety
'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.demo
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.demo'] = r'''"""
Demonstration data: one owner with a Zambian farm and a Rwandan farm, plus a manager, a worker, a vet
and an unrelated farmer (to show that farms cannot see each other's records).

All names, prices and events are FICTIONAL sample data for demonstrating and testing the system.
They are not survey results and must not be reported as findings.
"""
import datetime as dt

from . import db
from .countries import GESTATION_DAYS
from .security import hash_password

ACCOUNTS = [
    # email, password, first name, last name
    ("demo@jesse.farm", "demo1234", "Jesse", "Demo"),
    ("manager@jesse.farm", "manager1234", "Mary", "Banda"),
    ("worker@jesse.farm", "worker1234", "Joseph", "Phiri"),
    ("vet@jesse.farm", "vet12345", "Aline", "Uwase"),
    ("other@jesse.farm", "other1234", "Peter", "Mwale"),
]
TAG = {"cattle": "CAT", "goat": "GOA", "sheep": "SHP", "pig": "PIG", "poultry": "PLT", "rabbit": "RAB"}


def create_demo(path=None):
    conn = db.connect(path)
    if conn.execute("SELECT 1 FROM users WHERE email='demo@jesse.farm'").fetchone():
        conn.close()
        return False
    t = dt.date.today()

    def d(days):
        return (t + dt.timedelta(days=days)).isoformat()

    cur = conn.cursor()
    users = {}
    first = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
    for i, (email, pw, fn, ln) in enumerate(ACCOUNTS):
        cur.execute("INSERT INTO users (email, first_name, last_name, role, password_hash, is_admin) VALUES (?,?,?,?,?,?)",
                    (email, fn, ln, "owner", hash_password(pw), 1 if (i == 0 and first) else 0))
        users[email] = cur.lastrowid

    def farm(name, code, country, province, district, area, size, scale, members):
        cur.execute("""INSERT INTO farms (name, country_code, country, province, district, local_area, size_ha, farm_scale,
                       ownership, owner_name, phone) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (name, code, country, province, district, area, size, scale, "family", "Jesse Demo",
                     "+260 97 000 0000" if code == "ZM" else "+250 78 000 0000"))
        fid = cur.lastrowid
        for email, role in members:
            cur.execute("INSERT INTO memberships (user_id, farm_id, role) VALUES (?,?,?)", (users[email], fid, role))
        return fid

    zm = farm("Kafue Flats Mixed Farm", "ZM", "Zambia", "Southern", "Mazabuka", "Nakambala", 42.5, "medium",
              [("demo@jesse.farm", "owner"), ("manager@jesse.farm", "manager"), ("worker@jesse.farm", "worker")])
    rw = farm("Nyagatare Hill Farm", "RW", "Rwanda", "Eastern", "Nyagatare", "Karangazi", 6.0, "small",
              [("demo@jesse.farm", "owner"), ("worker@jesse.farm", "worker"), ("vet@jesse.farm", "vet")])
    other = farm("Chipata Goat Project", "ZM", "Zambia", "Eastern", "Chipata", "Kapata", 3.0, "small",
                 [("other@jesse.farm", "owner")])

    def tx(fid, date, kind, cat, amount, desc, party="", stype="", sid=None):
        cur.execute("""INSERT INTO transactions (farm_id, date, kind, category, amount, description, party, source_type, source_id, created_by)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""", (fid, date, kind, cat, amount, desc, party, stype, sid, users["demo@jesse.farm"]))

    def animal(fid, code, kind, name, breed, sex, dob, acq, how="born", price=None, weight=None, dam=None, sire=None, girinka=False):
        cur.execute("""INSERT INTO livestock (farm_id, name, animal_type, breed, gender, date_of_birth, acquisition_date,
                       acquisition_method, purchase_price, weight_kg, dam_id, sire_id, pass_on_due) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (fid, name, kind, breed, sex, dob, acq, how, price, weight, dam, sire, 1 if girinka else 0))
        aid = cur.lastrowid
        cur.execute("UPDATE livestock SET tag_number=? WHERE id=?", (f"{code}-{TAG[kind]}-{(dob or acq).replace('-', '')}-{aid:04d}", aid))
        if weight:
            cur.execute("INSERT INTO weights (livestock_id, date, weight_kg) VALUES (?,?,?)", (aid, d(-90), round(weight * 0.92, 1)))
            cur.execute("INSERT INTO weights (livestock_id, date, weight_kg) VALUES (?,?,?)", (aid, d(-5), weight))
        if price:
            tx(fid, acq, "expense", "animal_purchase", price, f"Bought {kind} {name}".strip(), "Local market", "animal_purchase", aid)
        return aid

    def health(fid, aid, kind, title, date, cost=0, disease="", due=None, notifiable=0, vet="", diagnosis="", treatment=""):
        cur.execute("""INSERT INTO health_records (livestock_id, record_type, title, date, cost, disease, next_due_date, notifiable,
                       vet_name, diagnosis, treatment, created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (aid, kind, title, date, cost, disease, due, notifiable, vet, diagnosis, treatment, users["demo@jesse.farm"]))
        hid = cur.lastrowid
        if cost:
            tx(fid, date, "expense", "veterinary", cost, title, vet, "health", hid)
        return hid

    def product(fid, name, kind, unit, qty, reorder, price, expiry=None):
        cur.execute("""INSERT INTO products (farm_id, name, kind, unit, quantity, reorder_level, unit_price, expiry_date)
                       VALUES (?,?,?,?,?,?,?,?)""", (fid, name, kind, unit, qty, reorder, price, expiry))
        pid = cur.lastrowid
        cur.execute("INSERT INTO stock_movements (product_id, change, reason, user_id, unit_cost, created_at) VALUES (?,?,?,?,?,?)",
                    (pid, qty, "Opening stock", users["demo@jesse.farm"], price, d(-75) + " 08:00:00"))
        return pid

    def feeding(fid, pid, name, unit, price, days, qty, kind):
        for i in range(days, 0, -3):
            cur.execute("""INSERT INTO feeding_records (farm_id, date, product_id, feed_name, animal_type, animal_count, quantity,
                           unit, cost, created_by) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (fid, d(-i), pid, name, kind, 5, qty, unit, round(qty * price, 2), users["worker@jesse.farm"]))

    def breeding(fid, female, male, kind, mating, status, outcome=None, alive=0, dead=0, method="natural", sire=""):
        exp = (dt.date.fromisoformat(mating) + dt.timedelta(days=GESTATION_DAYS[kind])).isoformat()
        cur.execute("""INSERT INTO breeding_events (farm_id, female_id, male_id, method, sire_details, mating_date, expected_date, status,
                       outcome_date, born_alive, born_dead, created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (fid, female, male, method, sire, mating, exp, status, outcome, alive, dead, users["demo@jesse.farm"]))

    def sale(fid, code, seq, date, buyer, phone, items, permit=""):
        total = sum(p for _, p in items)
        receipt = f"{code}-{fid:03d}-{date[:4]}-{seq:04d}"
        cur.execute("""INSERT INTO sales (farm_id, receipt_no, date, buyer_name, buyer_phone, payment_method, permit_no, total, created_by)
                       VALUES (?,?,?,?,?,?,?,?,?)""", (fid, receipt, date, buyer, phone, "mobile_money", permit, total, users["demo@jesse.farm"]))
        sid = cur.lastrowid
        for aid, price in items:
            row = cur.execute("SELECT name, tag_number, animal_type FROM livestock WHERE id=?", (aid,)).fetchone()
            cur.execute("INSERT INTO sale_items (sale_id, livestock_id, description, price) VALUES (?,?,?,?)",
                        (sid, aid, f"{row[2].title()} {row[0] or row[1]}", price))
            cur.execute("UPDATE livestock SET status='sold', exit_date=?, exit_reason=? WHERE id=?", (date, f"Sold to {buyer} (receipt {receipt})", aid))
        tx(fid, date, "income", "livestock_sale", total, f"Livestock sale, receipt {receipt}", buyer, "sale", sid)

    # ---------------- Zambia farm (money in ZMW) ----------------
    bull = animal(zm, "ZM", "cattle", "Mazabuka", "Boran", "male", d(-1600), d(-700), "purchased", 18000, 610)
    cows = [animal(zm, "ZM", "cattle", n, b, "female", d(-dob), d(-dob), "born", None, w)
            for n, b, dob, w in [("Namwala", "Angoni", 2100, 420), ("Choma", "Tonga", 1700, 395), ("Kalomo", "Boran x Angoni", 1500, 430),
                                 ("Monze", "Tonga", 1250, 380)]]
    heifer = animal(zm, "ZM", "cattle", "Mwandi", "Angoni", "female", d(-420), d(-420), "born", None, 240, cows[0], bull)
    steers = [animal(zm, "ZM", "cattle", n, "Angoni", "male", d(-dob), d(-dob), "born", None, w, cows[1], bull)
              for n, dob, w in [("", 700, 310), ("", 650, 295), ("", 600, 280)]]
    goats = [animal(zm, "ZM", "goat", "", "Boer", s, d(-dob), d(-200), "purchased", 1500, w) for s, dob, w in
             [("female", 700, 42), ("female", 650, 40), ("male", 800, 55), ("female", 500, 36)]]
    sow = animal(zm, "ZM", "pig", "Big Mama", "Large White", "female", d(-500), d(-300), "purchased", 2500, 160)
    boar = animal(zm, "ZM", "pig", "", "Large White", "male", d(-600), d(-300), "purchased", 2800, 190)
    animal(zm, "ZM", "poultry", "Layer flock A", "Hy-Line (flock)", "female", d(-160), d(-140), "purchased", 9000, None)
    dead_calf = animal(zm, "ZM", "cattle", "", "Tonga", "male", d(-120), d(-120), "born", None, 60, cows[3], bull)
    cur.execute("UPDATE livestock SET status='dead', exit_date=?, exit_reason=? WHERE id=?", (d(-40), "Theileriosis / East Coast fever", dead_calf))
    health(zm, dead_calf, "treatment", "ECF treatment", d(-45), 650, "Theileriosis / East Coast fever", None, 1, "Dr. Mwiinga",
           "High fever, swollen lymph nodes", "Buparvaquone injection")
    for c in cows + [bull, heifer] + steers:
        health(zm, c, "vaccination", "Lumpy skin disease vaccine", d(-170), 45, "", d(195))
        health(zm, c, "dipping", "Weekly dipping", d(-3), 0, "", d(4))
    health(zm, cows[2], "vet_visit", "Lameness check", d(-12), 300, "", d(9), 0, "Dr. Mwiinga", "Foot rot", "Footbath and antibiotics")
    for g in goats:
        health(zm, g, "deworming", "Deworming", d(-80), 25, "Internal parasites (worms)", d(10))
    health(zm, sow, "vaccination", "Erysipelas vaccine", d(-60), 60, "", d(120))
    breeding(zm, cows[0], bull, "cattle", d(-420 - 284), "delivered", d(-420), 1, 0)  # mother of Mwandi
    breeding(zm, cows[1], bull, "cattle", d(-150), "pregnant")
    breeding(zm, cows[2], None, "cattle", d(-240), "pregnant", method="ai", sire="AI straw BOR-221")
    breeding(zm, cows[3], bull, "cattle", d(-30), "served")
    breeding(zm, sow, boar, "pig", d(-105), "pregnant")
    breeding(zm, goats[0], goats[2], "goat", d(-170), "delivered", d(-20), 2, 0)
    animal(zm, "ZM", "goat", "", "Boer", "female", d(-20), d(-20), "born", None, 4, goats[0], goats[2])
    animal(zm, "ZM", "goat", "", "Boer", "male", d(-20), d(-20), "born", None, 4.3, goats[0], goats[2])
    breeding(zm, goats[1], goats[2], "goat", d(-60), "not_pregnant")
    meal = product(zm, "Dairy meal", "feed", "bags", 30, 10, 420)
    hay = product(zm, "Hay bales", "feed", "bales", 60, 25, 35)
    product(zm, "Layer mash", "feed", "bags", 6, 8, 480)
    product(zm, "ECF vaccine (Muguga cocktail)", "medicine", "doses", 8, 5, 120, d(200))
    product(zm, "Oxytetracycline 20%", "medicine", "bottles", 1, 2, 210, d(-10))
    product(zm, "Spray pump", "equipment", "pcs", 2, 1, 650)
    feeding(zm, meal, "Dairy meal", "bags", 420, 60, 0.5, "cattle")
    feeding(zm, hay, "Hay bales", "bales", 35, 60, 4, "cattle")
    cur.execute("UPDATE products SET quantity = quantity - 10 WHERE id=?", (meal,))
    cur.execute("UPDATE products SET quantity = quantity - 40 WHERE id=?", (hay,))
    cur.execute("INSERT INTO stock_movements (product_id, change, reason, user_id) VALUES (?,?,?,?)", (meal, -10, "Feeding records", users["worker@jesse.farm"]))
    cur.execute("INSERT INTO stock_movements (product_id, change, reason, user_id) VALUES (?,?,?,?)", (hay, -40, "Feeding records", users["worker@jesse.farm"]))
    sale(zm, "ZM", 1, d(-95), "Choma Livestock Traders", "+260 96 111 2222", [(steers[0], 11500)], "SMP/MZB/0193")
    sale(zm, "ZM", 2, d(-25), "Mrs. Hamoonga", "+260 97 333 4444", [(goats[3], 2200)])
    for m in range(5, -1, -1):
        day = (t.replace(day=1) - dt.timedelta(days=30 * m)).replace(day=5).isoformat()
        tx(zm, day, "income", "milk", 6200 + 300 * (m % 3), "Milk sold to co-operative", "Magoye Dairy Co-op")
        tx(zm, day, "income", "eggs", 2400 + 150 * (m % 2), "Egg sales", "Local shops")
        tx(zm, day, "expense", "labour", 3600, "Herdsman and general worker wages")
        if m % 2 == 0:
            tx(zm, day, "expense", "transport", 850, "Transport of milk and feed")
        tx(zm, day, "expense", "feed", 1800, "Maize bran and concentrates bought")
    tx(zm, d(-60), "expense", "fees", 300, "Stock movement permit and levies")
    cur.execute("""INSERT INTO tasks (farm_id, title, priority, status, due_date, assigned_to, created_by) VALUES
                   (?,?,?,?,?,?,?),(?,?,?,?,?,?,?),(?,?,?,?,?,?,?)""",
                (zm, "Dip all cattle", "high", "pending", d(4), users["worker@jesse.farm"], users["demo@jesse.farm"],
                 zm, "Repair kraal fence", "medium", "pending", d(-2), users["worker@jesse.farm"], users["demo@jesse.farm"],
                 zm, "Book vet for pregnancy diagnosis", "medium", "pending", d(6), users["manager@jesse.farm"], users["demo@jesse.farm"]))

    # ---------------- Rwanda farm (money in RWF) ----------------
    rcows = [animal(rw, "RW", "cattle", n, b, "female", d(-dob), d(-acq), how, price, w, girinka=g)
             for n, b, dob, acq, how, price, w, g in [
                 ("Gikundiro", "Friesian x Ankole", 1500, 800, "purchased", 650000, 410, False),
                 ("Inyambo", "Ankole (Inyambo)", 2000, 2000, "born", None, 380, False),
                 ("Ishimwe", "Jersey", 1000, 300, "girinka", None, 330, True)]]
    animal(rw, "RW", "cattle", "Rugwiro", "Ankole", "male", d(-900), d(-300), "purchased", 480000, 450)
    rgoats = [animal(rw, "RW", "goat", "", "Local x Boer", s, d(-dob), d(-dob), "born", None, w) for s, dob, w in
              [("female", 600, 30), ("female", 550, 29), ("male", 700, 38)]]
    rabbits = [animal(rw, "RW", "rabbit", "", "New Zealand White", s, d(-dob), d(-90), "purchased", 8000, 3.5) for s, dob in
               [("female", 300), ("female", 280), ("male", 320)]]
    for c in rcows:
        health(rw, c, "vaccination", "Foot and mouth disease vaccine", d(-150), 3000, "", d(30), 0, "Sector vet")
    health(rw, rcows[0], "treatment", "Mastitis treatment", d(-18), 12000, "Mastitis", d(-4), 0, "Dr. Uwase",
           "Hard, swollen quarter", "Intramammary antibiotic, 3 days")
    breeding(rw, rcows[0], None, "cattle", d(-200), "pregnant", method="ai", sire="RAB AI straw FRI-0442")
    breeding(rw, rcows[2], None, "cattle", d(-276), "pregnant", method="ai", sire="RAB AI straw JER-1180")
    breeding(rw, rgoats[0], rgoats[2], "goat", d(-140), "pregnant")
    breeding(rw, rabbits[0], rabbits[2], "rabbit", d(-50), "delivered", d(-19), 6, 1)
    for sex in ("female", "female", "female", "male", "male", "male"):
        animal(rw, "RW", "rabbit", "", "New Zealand White", sex, d(-19), d(-19), "born", None, None, rabbits[0], rabbits[2])
    breeding(rw, rabbits[1], rabbits[2], "rabbit", d(-20), "served")
    napier = product(rw, "Napier grass (cut)", "feed", "kg", 400, 150, 30)
    product(rw, "Dairy concentrate", "feed", "kg", 60, 100, 450)
    product(rw, "Acaricide", "medicine", "litres", 2, 1, 15000, d(300))
    feeding(rw, napier, "Napier grass (cut)", "kg", 30, 45, 40, "cattle")
    for m in range(5, -1, -1):
        day = (t.replace(day=1) - dt.timedelta(days=30 * m)).replace(day=8).isoformat()
        tx(rw, day, "income", "milk", 180000 + 15000 * (m % 3), "Milk delivered to collection centre", "Nyagatare MCC")
        tx(rw, day, "expense", "labour", 60000, "Herdsman wages")
        tx(rw, day, "expense", "feed", 45000, "Concentrates and mineral salt")
    sale(rw, "RW", 1, d(-60), "Kigali Meat Ltd", "+250 78 555 6666", [(rgoats[1], 70000)], "MC-NYG-2026-118")
    cur.execute("""INSERT INTO tasks (farm_id, title, priority, status, due_date, assigned_to, created_by) VALUES (?,?,?,?,?,?,?)""",
                (rw, "Spray cattle with acaricide", "high", "pending", d(2), users["worker@jesse.farm"], users["demo@jesse.farm"]))

    # ---------------- unrelated farm (for the data-separation demonstration) ----------------
    for s in ("female", "female", "male"):
        animal(other, "ZM", "goat", "", "Local", s, d(-500), d(-500), "born", None, 30)
    tx(other, d(-10), "income", "other_income", 900, "Private income of another farmer")

    conn.commit()
    conn.close()
    return True

'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.i18n
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.i18n'] = r'''"""
Translations. English is the only language today.

To add a language (for example Kinyarwanda "rw" or Bemba "bem"):
  1. Copy the "en" dictionary below to a new key, e.g. STRINGS["rw"] = {...}
  2. Translate the values (never the keys).
  3. Set LANGUAGE = "rw" in config.py.
Any key missing from a language falls back to English, so a partial translation still works.
"""
from . import config

STRINGS = {
    "en": {
        "dashboard": "Dashboard",
        "animals": "Livestock",
        "breeding": "Breeding",
        "health": "Animal health",
        "feeding": "Feeding",
        "inventory": "Inventory",
        "sales": "Livestock sales",
        "finance": "Finance",
        "tasks": "Tasks",
        "reports": "Reports",
        "farms": "My farms",
        "settings": "Settings",
        "sign_out": "Sign out",
        "sign_in": "Sign in",
        "save": "Save",
        "add": "Add",
        "edit": "Edit",
        "delete": "Delete",
        "search": "Search",
        "income": "Income",
        "expense": "Expense",
        "profit": "Profit",
        "loss": "Loss",
    }
}


def t(key):
    lang = STRINGS.get(config.LANGUAGE, STRINGS["en"])
    return lang.get(key) or STRINGS["en"].get(key) or key
'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.security
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.security'] = r'''"""Passwords, roles and permissions."""
import hashlib
import hmac
import re
import secrets

from . import config

ROLES = [("owner", "Farm owner"), ("manager", "Farm manager"), ("worker", "Farm worker"), ("vet", "Veterinarian")]

# What each role may do on a farm. Everyone who belongs to a farm can VIEW its records
# (except money, which needs "finance").
PERMISSIONS = {
    "owner": {"animals", "health", "breeding", "feeding", "inventory", "tasks", "finance", "delete",
              "manage_farm", "export"},
    "manager": {"animals", "health", "breeding", "feeding", "inventory", "tasks", "finance", "delete", "export"},
    "worker": {"animals", "feeding", "inventory", "tasks"},
    "vet": {"health", "breeding", "tasks"},
}

PERMISSION_LABELS = {
    "animals": "Add and edit animals",
    "health": "Record health and treatments",
    "breeding": "Record breeding and births",
    "feeding": "Record feeding",
    "inventory": "Manage stock",
    "tasks": "Manage tasks",
    "finance": "See and record money (sales, income, expenses)",
    "delete": "Delete records",
    "manage_farm": "Edit farm details and team",
    "export": "Export data",
}


def can(role, permission):
    return permission in PERMISSIONS.get(role, set())


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), config.PASSWORD_ITERATIONS).hex()
    return f"pbkdf2_sha256${config.PASSWORD_ITERATIONS}${salt}${digest}"


def check_password(password, stored):
    try:
        _, iterations, salt, digest = stored.split("$")
        test = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations)).hex()
        return hmac.compare_digest(test, digest)
    except (ValueError, AttributeError):
        return False


def password_problem(password):
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if password.isdigit():
        return "Password can't be only numbers."
    return ""


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.ui
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.ui'] = r'''"""
Page layout, form helpers, formatting and charts.

Every piece of text that a user typed is passed through e() before it is put into HTML.
That escaping is what stops cross-site scripting (XSS).
"""
import datetime as dt
import html
import urllib.parse

from . import config
from .countries import country
from .i18n import t


# --------------------------------------------------------------------------- formatting
def e(value):
    return html.escape("" if value is None else str(value), quote=True)


def today():
    return dt.date.today()


def parse_date(text):
    try:
        return dt.date.fromisoformat(str(text)[:10])
    except (TypeError, ValueError):
        return None


def fmt_date(value, code="ZM"):
    d = parse_date(value) if value else None
    return d.strftime(country(code)["date_format"]) if d else "—"


def fmt_num(value, digits=2):
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "—"
    text = f"{n:,.{digits}f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def money(value, code="ZM", show_code=True):
    """ZMW 1,250.50 / RWF 125,000 - decimals follow ISO 4217 for each currency."""
    c = country(code)
    try:
        n = float(value or 0)
    except (TypeError, ValueError):
        n = 0.0
    text = f"{abs(n):,.{c['decimals']}f}"
    sign = "−" if n < 0 else ""
    return f"{sign}{c['currency']} {text}" if show_code else f"{sign}{text}"


def age_text(dob, until=None):
    born = parse_date(dob) if dob else None
    if not born:
        return "Age unknown"
    end = parse_date(until) if until else today()
    months = (end.year - born.year) * 12 + end.month - born.month - (1 if end.day < born.day else 0)
    months = max(months, 0)
    if months < 1:
        return f"{max((end - born).days, 0)} days"
    if months < 12:
        return f"{months} mo"
    years, rest = divmod(months, 12)
    return f"{years} yr {rest} mo" if rest else f"{years} yr"


def label(choices, value):
    return dict(choices).get(value, value or "")


# --------------------------------------------------------------------------- forms
class Form:
    """Reads and checks submitted values; collects one error message per field."""

    def __init__(self, data):
        self.data = data
        self.errors = {}

    def text(self, name, required=False, label_="This field", max_len=500):
        value = (self.data.get(name) or "").strip()
        if required and not value:
            self.errors[name] = f"{label_} is required."
        elif len(value) > max_len:
            self.errors[name] = f"{label_} is too long (max {max_len} characters)."
        return value

    def choice(self, name, choices, default=None):
        value = self.data.get(name) or default
        if value not in dict(choices):
            self.errors[name] = "Choose one of the options."
        return value

    def date(self, name, required=False, label_="Date", not_future=False):
        value = (self.data.get(name) or "").strip()
        if not value:
            if required:
                self.errors[name] = f"{label_} is required."
            return None
        d = parse_date(value)
        if not d or len(value) != 10:
            self.errors[name] = f"{label_} must be a real date."
            return None
        if not_future and d > today():
            self.errors[name] = f"{label_} can't be in the future."
        return value

    def number(self, name, required=False, minimum=0, label_="Value", default=None, maximum=None):
        raw = (self.data.get(name) or "").strip().replace(",", "")
        if not raw:
            if required:
                self.errors[name] = f"{label_} is required."
            return default
        try:
            n = float(raw)
        except ValueError:
            self.errors[name] = f"{label_} must be a number."
            return default
        if n != n or n in (float("inf"), float("-inf")):
            self.errors[name] = f"{label_} must be a number."
            return default
        if minimum is not None and n < minimum:
            self.errors[name] = f"{label_} must be {fmt_num(minimum)} or more."
        if maximum is not None and n > maximum:
            self.errors[name] = f"{label_} must be {fmt_num(maximum)} or less."
        return n

    def integer(self, name, required=False, minimum=0, label_="Value", default=0):
        n = self.number(name, required, minimum, label_, default)
        if n is not None and n != int(n):
            self.errors[name] = f"{label_} must be a whole number."
        return int(n) if n is not None else None

    def id(self, name):
        raw = (self.data.get(name) or "").strip()
        return int(raw) if raw.isdigit() else None

    @property
    def ok(self):
        return not self.errors


def _attrs(attrs):
    out = []
    for k, v in attrs.items():
        if v is None or v is False:
            continue
        name = k.rstrip("_").replace("_", "-")
        out.append(name if v is True else f'{name}="{e(v)}"')
    return " ".join(out)


def _wrap(name, label_, inner, err, hint):
    return (
        f'<div class="field{" bad" if err else ""}"><label for="{name}">{e(label_)}</label>{inner}'
        + (f'<div class="err">{e(err)}</div>' if err else (f'<div class="hint">{e(hint)}</div>' if hint else ""))
        + "</div>"
    )


def field(name, label_, value="", errors=None, type_="text", hint="", **attrs):
    err = (errors or {}).get(name, "")
    val = "" if value is None else value
    if isinstance(val, float):
        val = fmt_num(val, 4).replace(",", "")
    inner = f'<input id="{name}" name="{name}" type="{type_}" value="{e(val)}" {_attrs(attrs)}>'
    return _wrap(name, label_, inner, err, hint)


def textarea(name, label_, value="", errors=None, hint=""):
    err = (errors or {}).get(name, "")
    return _wrap(name, label_, f'<textarea id="{name}" name="{name}">{e(value)}</textarea>', err, hint)


def select(name, label_, options, value="", errors=None, blank=None, hint="", groups=False):
    """options = [(value, text)] or, with groups=True, [(value, text, group)]"""
    err = (errors or {}).get(name, "")
    cur = "" if value is None else str(value)
    opts = f'<option value="">{e(blank)}</option>' if blank is not None else ""
    current_group = None
    for opt in options:
        v, text = opt[0], opt[1]
        if groups and opt[2] != current_group:
            if current_group is not None:
                opts += "</optgroup>"
            current_group = opt[2]
            opts += f'<optgroup label="{e(current_group)}">'
        sel = " selected" if str(v) == cur else ""
        opts += f'<option value="{e(v)}"{sel}>{e(text)}</option>'
    if groups and current_group is not None:
        opts += "</optgroup>"
    return _wrap(name, label_, f'<select id="{name}" name="{name}">{opts}</select>', err, hint)


def datalist(list_id, values):
    return f'<datalist id="{list_id}">' + "".join(f'<option value="{e(v)}">' for v in values) + "</datalist>"


def chips(base, param, options, current, extra=None):
    out = '<div class="chips">'
    for value, text in options:
        params = {k: v for k, v in (extra or {}).items() if v}
        if value:
            params[param] = value
        else:
            params.pop(param, None)
        href = base + ("?" + urllib.parse.urlencode(params) if params else "")
        on = (current or "") == (value or "")
        out += f'<a class="chip{" on" if on else ""}" href="{e(href)}">{e(text)}</a>'
    return out + "</div>"


def badge(text, color=""):
    return f'<span class="badge{" b-" + color if color else ""}">{e(text)}</span>'


def post_button(req, action, text, cls="btn danger", confirm=None, hidden=None):
    onsubmit = f' onsubmit="return confirm(\'{e(confirm)}\')"' if confirm else ""
    extra = "".join(f'<input type="hidden" name="{e(k)}" value="{e(v)}">' for k, v in (hidden or {}).items())
    return (f'<form class="inline" method="post" action="{e(action)}"{onsubmit}>{req.csrf_input()}{extra}'
            f'<button class="{cls}" type="submit">{e(text)}</button></form>')


def dl(rows):
    return "<dl>" + "".join(f"<div><dt>{e(k)}</dt><dd>{v}</dd></div>" for k, v in rows) + "</dl>"


def empty(title, sub=""):
    return f'<div class="empty"><b>{e(title)}</b><div class="muted">{e(sub)}</div></div>'


def table(headers, rows, numeric=()):
    """headers: list of str; rows: list of lists of already-escaped HTML; numeric: column indexes to right-align."""
    if not rows:
        return ""
    head = "".join(f'<th class="{"num" if i in numeric else ""}">{e(h)}</th>' for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join(f'<td class="{"num" if i in numeric else ""}" data-label="{e(headers[i])}">{c}</td>'
                         for i, c in enumerate(r)) + "</tr>"
        for r in rows
    )
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def card(inner, title=None, actions=""):
    head = f'<div class="card-head"><h3>{e(title)}</h3>{actions}</div>' if title or actions else ""
    return f'<section class="card">{head}{inner}</section>'


def stat(value, text, href=None, tone=""):
    tag = "a" if href else "div"
    href_attr = f' href="{e(href)}"' if href else ""
    return f'<{tag} class="stat {tone}"{href_attr}><div class="n">{value}</div><div class="muted">{e(text)}</div></{tag}>'


# --------------------------------------------------------------------------- charts (SVG, no libraries)
PALETTE = ["#2e7d32", "#1565c0", "#ef6c00", "#6a1b9a", "#00838f", "#c62828", "#5d4037"]


def bar_chart(series, fmt=lambda v: fmt_num(v, 0), color="#2e7d32", height=180, unit=""):
    """series = [(label, value)]. Hover a bar to see its exact value."""
    if not series or not any(v for _, v in series):
        return '<p class="muted">No data for this period.</p>'
    peak = max(v for _, v in series) or 1
    n = len(series)
    w = 640
    bw = w / n
    bars = []
    for i, (lab, v) in enumerate(series):
        h = (v / peak) * (height - 40) if v > 0 else 0
        x = i * bw + bw * 0.2
        y = height - 22 - h
        bars.append(
            f'<g><rect x="{x:.1f}" y="{y:.1f}" width="{bw * 0.6:.1f}" height="{max(h, 1):.1f}" rx="3" fill="{color}">'
            f'<title>{e(lab)}: {e(fmt(v))}{e(unit)}</title></rect>'
            + (f'<text x="{x + bw * 0.3:.1f}" y="{y - 4:.1f}" text-anchor="middle" class="cv">{e(fmt(v))}</text>' if v else "")
            + f'<text x="{x + bw * 0.3:.1f}" y="{height - 6}" text-anchor="middle" class="cl">{e(lab)}</text></g>'
        )
    return f'<svg class="chart" viewBox="0 0 {w} {height}" role="img">{"".join(bars)}</svg>'


def pair_chart(series, labels=("Income", "Expenses"), colors=("#2e7d32", "#c62828"), fmt=lambda v: fmt_num(v, 0), height=200):
    """Two bars per period, e.g. income and expenses per month: series = [(label, a, b)]."""
    if not series or not any(a or b for _, a, b in series):
        return '<p class="muted">No data for this period.</p>'
    peak = max(max(a, b) for _, a, b in series) or 1
    w, n = 640, len(series)
    bw = w / n
    parts = []
    for i, (lab, a, b) in enumerate(series):
        for j, v in enumerate((a, b)):
            h = v / peak * (height - 44)
            x = i * bw + bw * 0.12 + j * bw * 0.38
            y = height - 22 - h
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw * 0.36:.1f}" height="{max(h, 1):.1f}" rx="2" '
                         f'fill="{colors[j]}"><title>{e(lab)} {e(labels[j])}: {e(fmt(v))}</title></rect>')
        parts.append(f'<text x="{i * bw + bw * 0.5:.1f}" y="{height - 6}" text-anchor="middle" class="cl">{e(lab)}</text>')
    legend = "".join(f'<span class="key"><i style="background:{c}"></i>{e(t_)}</span>' for t_, c in zip(labels, colors))
    return f'<div class="legend">{legend}</div><svg class="chart" viewBox="0 0 {w} {height}" role="img">{"".join(parts)}</svg>'


def hbars(rows, fmt=lambda v: fmt_num(v, 0)):
    """rows = [(label, value)] as horizontal bars, largest first."""
    if not rows:
        return '<p class="muted">No data yet.</p>'
    peak = max(v for _, v in rows) or 1
    return "".join(
        f'<div class="hrow"><span>{e(lab)}</span><b>{e(fmt(v))}</b></div>'
        f'<div class="hbar" title="{e(lab)}: {e(fmt(v))}"><div style="width:{max(v / peak * 100, 1):.0f}%"></div></div>'
        for lab, v in rows
    )


def months_back(n, end=None):
    first = (end or today()).replace(day=1)
    out = []
    for _ in range(n):
        out.append(first.strftime("%Y-%m"))
        first = (first - dt.timedelta(days=1)).replace(day=1)
    return list(reversed(out))


def month_label(ym):
    return dt.date.fromisoformat(ym + "-01").strftime("%b %y")


# --------------------------------------------------------------------------- page layout
CSS = """
:root{--g:#1f6f3a;--gd:#154d28;--gl:#e7f3ea;--bg:#f3f5f4;--t:#17201a;--m:#56625a;--b:#d6ddd8;--r:#c62828;--rl:#fdecec;
--y:#8a5a00;--yl:#fff4d6;--bl:#1565c0;--bll:#e6f0fb;--side:#14261b;--sidet:#cfe3d5}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--t);font-size:15.5px;line-height:1.5}
a{color:var(--g)}h1{font-size:24px;margin:0 0 4px}h2{font-size:18px;margin:26px 0 10px}h3{font-size:16px;margin:0}
.shell{display:flex;min-height:100vh;background:linear-gradient(to right,var(--side) 248px,var(--bg) 248px)}
aside{width:248px;background:var(--side);color:var(--sidet);flex:none;position:sticky;top:0;height:100vh;overflow-y:auto;display:flex;flex-direction:column}
aside .brand{padding:18px 18px 10px;font-weight:800;color:#fff;font-size:15px;letter-spacing:.3px;line-height:1.25}
aside .brand small{display:block;font-weight:500;color:#9fc3aa;font-size:12px;letter-spacing:0}
aside nav a{display:flex;gap:10px;align-items:center;padding:9px 18px;color:var(--sidet);text-decoration:none;font-size:14.5px;border-left:3px solid transparent}
aside nav a:hover{background:#1c3426;color:#fff}aside nav a.on{background:#1f3d2b;color:#fff;border-left-color:#7bd88f;font-weight:600}
aside nav .ico{width:20px;text-align:center}aside .sect{padding:14px 18px 4px;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#7f9c88}
aside .foot{margin-top:auto;padding:14px 18px;font-size:12.5px;color:#9fb8a7}
.main{flex:1;min-width:0}
.top{background:#fff;border-bottom:1px solid var(--b);padding:10px 24px;display:flex;align-items:center;gap:14px;position:sticky;top:0;z-index:5}
.top .farm{flex:1;min-width:0}.top .farm b{display:block;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.top .farm span{font-size:12.5px;color:var(--m)}
.top select{width:auto;max-width:230px;padding:7px 10px;font-size:14px}
.menu-btn{display:none;font-size:24px;background:none;border:0;cursor:pointer;padding:0 4px}
#menu{display:none}
.content{max-width:1180px;margin:0 auto;padding:22px 24px 60px}
.pagehead{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;flex-wrap:wrap;margin-bottom:16px}
.pagehead p{margin:0;color:var(--m)}
.card{background:#fff;border:1px solid #e1e7e3;border-radius:12px;padding:16px 18px;margin-bottom:16px}
.card-head{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap}
.grid{display:grid;gap:16px}.g2{grid-template-columns:repeat(2,minmax(0,1fr))}.g3{grid-template-columns:repeat(3,minmax(0,1fr))}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:16px}
.stat{background:#fff;border:1px solid #e1e7e3;border-radius:12px;padding:14px 16px;text-decoration:none;color:inherit;display:block}
a.stat:hover{border-color:var(--g)}.stat .n{font-size:26px;font-weight:800;line-height:1.2}
.stat.warn .n{color:var(--y)}.stat.bad .n{color:var(--r)}.stat.good .n{color:var(--g)}
.muted{color:var(--m);font-size:13.5px}.big{font-size:28px;font-weight:800}
.badge{display:inline-block;padding:2px 9px;border-radius:10px;font-size:12px;font-weight:700;background:#eceeec;color:var(--m);white-space:nowrap}
.b-green{background:var(--gl);color:var(--gd)}.b-red{background:var(--rl);color:var(--r)}.b-yellow{background:var(--yl);color:var(--y)}.b-blue{background:var(--bll);color:var(--bl)}
.btn{display:inline-block;border:1.5px solid var(--g);background:var(--g);color:#fff;border-radius:9px;padding:9px 16px;font-size:15px;font-weight:600;text-decoration:none;cursor:pointer;font-family:inherit;line-height:1.3}
.btn:hover{background:var(--gd)}.btn.sec{background:#fff;color:var(--g)}.btn.sec:hover{background:var(--gl)}
.btn.danger{background:#fff;color:var(--r);border-color:var(--r)}.btn.small{padding:5px 11px;font-size:13.5px}
.btn.block{display:block;width:100%;text-align:center}.actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
form.inline{display:inline}
label{display:block;font-weight:600;font-size:13.5px;margin:0 0 5px}.field{margin-bottom:14px}
input,select,textarea{width:100%;padding:10px 12px;border:1px solid var(--b);border-radius:9px;font-size:15.5px;font-family:inherit;background:#fff;color:var(--t)}
textarea{min-height:84px}input:focus,select:focus,textarea:focus{outline:2px solid var(--g);border-color:var(--g)}
.err{color:var(--r);font-size:13.5px;margin-top:4px}.hint{color:var(--m);font-size:12.5px;margin-top:4px}
.field.bad input,.field.bad select,.field.bad textarea{border-color:var(--r)}
.fgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 16px}.fgrid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:0 16px}
.flash{background:var(--gl);color:var(--gd);border-radius:9px;padding:10px 14px;margin-bottom:14px;font-weight:600}.flash.bad{background:var(--rl);color:var(--r)}
.note{background:var(--yl);color:#5c3d00;border-radius:9px;padding:10px 14px;margin-bottom:14px;font-size:14px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
.chip{padding:6px 13px;border:1px solid var(--b);border-radius:20px;background:#fff;color:var(--t);text-decoration:none;font-size:13.5px}.chip.on{background:var(--g);border-color:var(--g);color:#fff;font-weight:600}
.filters{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end;margin-bottom:14px}.filters .field{margin:0;min-width:150px;flex:1}
.filters input,.filters select{padding:8px 10px}
dl{margin:0}dl div{display:flex;justify-content:space-between;gap:12px;padding:8px 0;border-bottom:1px solid #edf0ee}
dt{color:var(--m)}dd{margin:0;font-weight:500;text-align:right}
.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:14.5px}
th{text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:var(--m);padding:9px 10px;border-bottom:2px solid #e1e7e3;white-space:nowrap}
td{padding:10px;border-bottom:1px solid #eef1ef;vertical-align:top}tr:hover td{background:#fafcfb}
.num{text-align:right;white-space:nowrap}
.empty{text-align:center;padding:34px 10px;color:var(--m)}
.chart{width:100%;height:auto;display:block}.chart .cv{font-size:11px;fill:#17201a}.chart .cl{font-size:10.5px;fill:#56625a}
.legend{display:flex;gap:14px;font-size:13px;color:var(--m)}.legend .key i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px}
.hrow{display:flex;justify-content:space-between;font-size:14px}.hbar{height:8px;background:#e6eae7;border-radius:4px;margin:3px 0 10px}.hbar div{height:8px;background:var(--g);border-radius:4px}
.plus{color:var(--g);font-weight:700}.minus{color:var(--r);font-weight:700}
.auth{max-width:440px;margin:48px auto;padding:0 16px}.auth .logo{text-align:center;font-weight:800;color:var(--g);font-size:20px;line-height:1.25;margin-bottom:6px}
.check{background:none;border:0;font-size:22px;cursor:pointer;padding:0 4px;line-height:1}
.done{text-decoration:line-through;color:var(--m)}
.receipt{max-width:640px;margin:0 auto;background:#fff;border:1px solid #ccc;padding:28px}
@media (max-width:900px){
 .shell{background:var(--bg)}
 aside{position:fixed;left:-260px;z-index:20;transition:left .2s}#menu:checked~aside{left:0;box-shadow:0 0 0 100vmax rgba(0,0,0,.35)}
 .menu-btn{display:block}.content{padding:16px 14px 60px}.top{padding:10px 14px}
 .g2,.g3,.fgrid,.fgrid3{grid-template-columns:1fr}
 table.stack thead{display:none}
}
@media (max-width:640px){
 .table-wrap table thead{display:none}.table-wrap tr{display:block;border-bottom:1px solid #e1e7e3;padding:6px 0}
 .table-wrap td{display:flex;justify-content:space-between;gap:12px;border:0;padding:4px 6px;text-align:right}
 .table-wrap td::before{content:attr(data-label);color:var(--m);font-size:12.5px;text-align:left}
 .top select{max-width:140px}
}
@media print{aside,.top,.noprint,.btn,form{display:none!important}.content{padding:0}.card{break-inside:avoid;border-color:#bbb}body{background:#fff}}
"""

NAV = [
    ("main", None),
    ("dashboard", "/", "▦"),
    ("animals", "/animals", "🐄"),
    ("breeding", "/breeding", "♀"),
    ("health", "/health", "✚"),
    ("feeding", "/feeding", "🌾"),
    ("inventory", "/inventory", "📦"),
    ("tasks", "/tasks", "✓"),
    ("money", None),
    ("sales", "/sales", "🧾"),
    ("finance", "/finance", "💰"),
    ("insight", None),
    ("reports", "/reports", "📊"),
    ("farms", "/farms", "🏡"),
    ("settings", "/settings", "⚙"),
]
SECTION_TITLES = {"main": "Farm work", "money": "Money", "insight": "Insight & admin"}


def layout(req, title, body, active="", subtitle="", actions=""):
    flash = req.pop_flash()
    flash_html = ""
    if flash:
        kind, _, text = flash.partition(":")
        flash_html = f'<div class="flash{" bad" if kind == "bad" else ""}">{e(text)}</div>'
    links = []
    for item in NAV:
        if item[1] is None:
            if item[0] == "money" and not req.can("finance"):
                continue
            links.append(f'<div class="sect">{e(SECTION_TITLES[item[0]])}</div>')
            continue
        key, href, icon = item
        if key in ("sales", "finance") and not req.can("finance"):
            continue
        on = " on" if key == active else ""
        links.append(f'<a class="{on.strip()}" href="{href}"><span class="ico">{icon}</span>{e(t(key))}</a>')
    farm = req.farm
    c = country(farm["country_code"]) if farm else None
    switcher = ""
    farms = req.my_farms() if req.user else []
    if len(farms) > 1:
        opts = "".join(
            f'<option value="{f["id"]}"{" selected" if farm and f["id"] == farm["id"] else ""}>'
            f'{e(f["name"])} ({e(f["country_code"])})</option>' for f in farms)
        switcher = (f'<form method="post" action="/farms/switch" class="noprint">{req.csrf_input()}'
                    f'<select name="farm_id" onchange="this.form.submit()" aria-label="Switch farm">{opts}</select>'
                    f'<noscript><button class="btn small">Go</button></noscript></form>')
    farm_info = (f'<div class="farm"><b>{e(farm["name"])}</b><span>{e(c["name"])} · {e(farm["district"] or "location not set")}'
                 f' · {e(c["currency"])} · you are {e(farm["role"])}</span></div>') if farm else '<div class="farm"><b>No farm yet</b></div>'
    head = (f'<div class="pagehead"><div><h1>{e(title)}</h1>{f"<p>{e(subtitle)}</p>" if subtitle else ""}</div>'
            f'<div class="actions noprint">{actions}</div></div>')
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{e(title)} · {config.APP_SHORT}</title><style>{CSS}</style></head><body>"
        f'<div class="shell"><input type="checkbox" id="menu"><aside><div class="brand">JESSE FARM<br>MANAGEMENT SYSTEM'
        f'<small>Zambia · Rwanda</small></div><nav>{"".join(links)}</nav>'
        f'<div class="foot">{e(req.user["first_name"])} {e(req.user["last_name"])}<br>'
        f'{post_button(req, "/logout", t("sign_out"), "btn small sec")}</div></aside>'
        f'<div class="main"><div class="top"><label for="menu" class="menu-btn" aria-label="Menu">☰</label>{farm_info}{switcher}</div>'
        f'<div class="content">{flash_html}{head}{body}</div></div></div></body></html>'
    )


def bare_page(title, body, req=None):
    """Pages without the sidebar: sign in, register, errors before sign-in, printable receipts."""
    flash = req.pop_flash() if req and req.session else ""
    flash_html = ""
    if flash:
        kind, _, text = flash.partition(":")
        flash_html = f'<div class="flash{" bad" if kind == "bad" else ""}">{e(text)}</div>'
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{e(title)} · {config.APP_SHORT}</title><style>{CSS}</style></head><body>{flash_html}{body}</body></html>")


def error_page(req, title, message):
    body = f"<p>{e(message)}</p><p><a class='btn' href='/'>Go to the dashboard</a></p>"
    if req and req.user:
        try:
            return layout(req, title, body)
        except Exception:
            pass
    return bare_page(title, f'<div class="auth"><div class="card"><h1>{e(title)}</h1>{body}</div></div>')
'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.views  (package)
# --------------------------------------------------------------------------------------------------------------
PACKAGES.add('jesse_farm.views')
MODULES['jesse_farm.views'] = r'''"""Pages of the system, one module per area (farms, animals, health, ...)."""
'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.views.animals
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.views.animals'] = r'''"""Livestock register: animals, identification, weights, births/deaths/exits and individual history."""
from ..countries import country
from ..ui import (Form, age_text, badge, card, chips, dl, e, empty, field, fmt_date, fmt_num, label, layout, money,
                  post_button, select, table, textarea, today)
from ..web import Redirect, route
from .common import (ANIMAL_STATUS, ANIMAL_TYPES, GENDERS, HEALTH_TYPES, STATUS_COLOR, TAG_PREFIX, acquisition_choices,
                     animal_name, animal_options, get_animal, link_transaction, unlink_transaction)

EXIT_REASONS = [("dead", "Died"), ("slaughtered", "Slaughtered for home use"), ("given_away", "Given away")]


def make_tag(code, animal_type, day, new_id):
    """Unique animal number: COUNTRY-SPECIES-YYYYMMDD-ID, e.g. ZM-CAT-20230501-0007."""
    return f"{code}-{TAG_PREFIX.get(animal_type, 'OTH')}-{day.replace('-', '')}-{new_id:04d}"


@route("/animals")
def animals_list(req):
    q = req.query.get("q", "").strip()
    status = req.query.get("status", "active")
    kind = req.query.get("type", "")
    gender = req.query.get("gender", "")
    sql, params = "SELECT * FROM livestock WHERE farm_id=?", [req.fid]
    if status in dict(ANIMAL_STATUS):
        sql += " AND status=?"
        params.append(status)
    elif status == "exited":
        sql += " AND status!='active'"
    if kind in dict(ANIMAL_TYPES):
        sql += " AND animal_type=?"
        params.append(kind)
    if gender in dict(GENDERS):
        sql += " AND gender=?"
        params.append(gender)
    if q:
        sql += " AND (name LIKE ? OR tag_number LIKE ? OR breed LIKE ? OR official_id LIKE ?)"
        params += [f"%{q}%"] * 4
    rows = req.all(sql + " ORDER BY created_at DESC, id DESC LIMIT 1000", params)
    keep = {"q": q, "status": status, "type": kind, "gender": gender}
    body = f"""<form class="filters noprint" method="get">
        <div class="field"><label for="q">Search</label><input id="q" name="q" value="{e(q)}" placeholder="Name, number, breed or ID"></div>
        <input type="hidden" name="status" value="{e(status)}"><input type="hidden" name="type" value="{e(kind)}">
        <input type="hidden" name="gender" value="{e(gender)}"><button class="btn">Search</button></form>"""
    body += chips("/animals", "status", [("active", "Active"), ("exited", "Sold / died / exited"), ("all", "All")], status, keep)
    body += chips("/animals", "type", [("", "All species")] + ANIMAL_TYPES, kind, keep)
    trs = [[f'<a href="/animals/{a["id"]}"><b>{e(a["name"] or a["tag_number"])}</b></a><div class="muted">{e(a["tag_number"])}</div>',
            e(label(ANIMAL_TYPES, a["animal_type"])), e(a["breed"] or "—"), e(label(GENDERS, a["gender"])),
            age_text(a["date_of_birth"], a["exit_date"]), f'{fmt_num(a["weight_kg"], 1)} kg' if a["weight_kg"] else "—",
            badge(label(ANIMAL_STATUS, a["status"]), STATUS_COLOR.get(a["status"], ""))] for a in rows]
    body += card(f'<p class="muted">{len(rows)} animal(s)</p>' + (table(["Animal", "Species", "Breed", "Sex", "Age", "Weight", "Status"], trs)
                 or empty("No animals match", "Register an animal with the button above.")))
    actions = '<a class="btn" href="/animals/new">+ Register animal</a>'
    if req.can("export"):
        actions += ' <a class="btn sec" href="/export/animals.csv">Export CSV</a>'
    return layout(req, "Livestock", body, "animals", actions=actions)


def animal_form(req, animal=None):
    code = req.country
    c = country(code)
    acq = acquisition_choices(code)
    if req.method == "GET":
        data = dict(animal) if animal else {"acquisition_date": today().isoformat(), "animal_type": "cattle",
                                            "gender": "female", "acquisition_method": "born"}
    else:
        data = req.form
    f = Form(req.form)
    if req.method == "POST":
        v = {
            "name": f.text("name", False, "Name", 100),
            "animal_type": f.choice("animal_type", ANIMAL_TYPES),
            "breed": f.text("breed", False, "Breed", 100),
            "gender": f.choice("gender", GENDERS),
            "date_of_birth": f.date("date_of_birth", False, "Date of birth", not_future=True),
            "colour": f.text("colour", False, "Colour / markings", 100),
            "official_id": f.text("official_id", False, c["id_label"], 60),
            "acquisition_method": f.choice("acquisition_method", acq),
            "acquisition_date": f.date("acquisition_date", True, "Date acquired", not_future=True),
            "purchase_price": f.number("purchase_price", False, 0, "Purchase price"),
            "seller": f.text("seller", False, "Seller", 150),
            "dam_id": f.id("dam_id"),
            "sire_id": f.id("sire_id"),
            "notes": f.text("notes", False, "Notes", 2000),
        }
        weight = f.number("weight_kg", False, 0, "Weight", maximum=5000)
        dob, acq_date = v["date_of_birth"], v["acquisition_date"]
        if dob and acq_date and acq_date < dob:
            f.errors["acquisition_date"] = "The date acquired is before the date of birth."
        for k in ("dam_id", "sire_id"):
            if v[k] and not req.one("SELECT 1 FROM livestock WHERE id=? AND farm_id=?", (v[k], req.fid)):
                v[k] = None
            if v[k] and animal and v[k] == animal["id"]:
                f.errors[k] = "An animal can't be its own parent."
        if v["acquisition_method"] != "purchased":
            v["purchase_price"] = None  # only purchases cost money
        if f.ok:
            v["pass_on_due"] = 1 if v["acquisition_method"] == "girinka" else (animal["pass_on_due"] if animal else 0)
            cols = list(v)
            with req.conn:
                if animal:
                    req.conn.execute(f"UPDATE livestock SET {', '.join(k + '=?' for k in cols)} WHERE id=? AND farm_id=?",
                                     [v[k] for k in cols] + [animal["id"], req.fid])
                    aid = animal["id"]
                else:
                    aid = req.conn.execute(f"INSERT INTO livestock (farm_id, {', '.join(cols)}) VALUES (?{', ?' * len(cols)})",
                                           [req.fid] + [v[k] for k in cols]).lastrowid
                    tag = make_tag(code, v["animal_type"], dob or acq_date, aid)
                    req.conn.execute("UPDATE livestock SET tag_number=? WHERE id=?", (tag, aid))
                if weight:
                    req.conn.execute("INSERT INTO weights (livestock_id, date, weight_kg) VALUES (?,?,?)", (aid, today().isoformat(), weight))
                    req.conn.execute("UPDATE livestock SET weight_kg=? WHERE id=?", (weight, aid))
                link_transaction(req, "animal_purchase", aid, "expense", "animal_purchase", v["purchase_price"] or 0,
                                 acq_date, f"Bought {label(ANIMAL_TYPES, v['animal_type']).lower()} {v['name']}".strip(), v["seller"])
            req.flash("Animal saved." if animal else "Animal registered.")
            raise Redirect(f"/animals/{aid}")
    er = f.errors
    keep = animal["id"] if animal else None
    mothers = [o for o in animal_options(req, True, "female") if o[0] != keep]
    fathers = [o for o in animal_options(req, True, "male") if o[0] != keep]
    title = "Edit animal" if animal else "Register animal"
    form = f"""<form method="post">{req.csrf_input()}
      {'' if animal else '<p class="muted">An animal number such as ' + e(make_tag(code, "cattle", today().isoformat(), 7)) + ' is created when you save.</p>'}
      <div class="fgrid3">{select("animal_type", "Species", ANIMAL_TYPES, data.get("animal_type"), er)}
      {field("breed", "Breed", data.get("breed"), er, placeholder="e.g. Angoni, Ankole, Boer")}
      {select("gender", "Sex", GENDERS, data.get("gender"), er)}
      {field("name", "Name (optional)", data.get("name"), er)}
      {field("date_of_birth", "Date of birth", data.get("date_of_birth"), er, type_="date", hint="Leave empty if unknown", max=today().isoformat())}
      {field("colour", "Colour / markings", data.get("colour"), er)}
      {field("official_id", c["id_label"], data.get("official_id"), er, hint=c["id_hint"])}
      {'' if animal else field("weight_kg", "Weight now (kg)", "", er, type_="number", step="0.1", min="0")}
      </div><h3>How the animal came to the farm</h3><br><div class="fgrid3">
      {select("acquisition_method", "Acquired by", acq, data.get("acquisition_method"), er)}
      {field("acquisition_date", "Date acquired / born", data.get("acquisition_date"), er, type_="date", required=True, max=today().isoformat())}
      {field("purchase_price", f"Purchase price ({c['currency']})", data.get("purchase_price"), er, type_="number", step="any", min="0", hint="Only for purchases; recorded as an expense")}
      {field("seller", "Seller / giver", data.get("seller"), er)}
      {select("dam_id", "Mother (dam)", mothers, data.get("dam_id"), er, blank="— unknown / not on farm —", groups=True)}
      {select("sire_id", "Father (sire)", fathers, data.get("sire_id"), er, blank="— unknown / not on farm —", groups=True)}
      </div>{textarea("notes", "Notes", data.get("notes"), er)}
      <button class="btn block">{'Save changes' if animal else 'Register animal'}</button></form>"""
    return layout(req, title, card(form), "animals")


@route("/animals/new", ("GET", "POST"))
def animal_new(req):
    req.require("animals")
    return animal_form(req)


@route(r"/animals/(\d+)/edit", ("GET", "POST"))
def animal_edit(req, animal_id):
    req.require("animals")
    return animal_form(req, get_animal(req, animal_id))


@route(r"/animals/(\d+)/weight", ("POST",))
def animal_weight(req, animal_id):
    req.require("animals")
    a = get_animal(req, animal_id)
    f = Form(req.form)
    w = f.number("weight_kg", True, 0.01, "Weight", maximum=5000)
    d = f.date("date", True, not_future=True)
    if not f.ok:
        req.flash(next(iter(f.errors.values())), bad=True)
    else:
        with req.conn:
            req.conn.execute("INSERT INTO weights (livestock_id, date, weight_kg) VALUES (?,?,?)", (a["id"], d, w))
            latest = req.conn.execute("SELECT weight_kg FROM weights WHERE livestock_id=? ORDER BY date DESC, id DESC LIMIT 1", (a["id"],)).fetchone()
            req.conn.execute("UPDATE livestock SET weight_kg=? WHERE id=?", (latest["weight_kg"], a["id"]))
        req.flash("Weight recorded.")
    raise Redirect(f"/animals/{a['id']}")


@route(r"/animals/(\d+)/exit", ("POST",))
def animal_exit(req, animal_id):
    """Record a death, slaughter or giving away. Sales are recorded in the Sales module."""
    req.require("animals")
    a = get_animal(req, animal_id)
    f = Form(req.form)
    reason = f.choice("exit_status", EXIT_REASONS)
    d = f.date("exit_date", True, not_future=True)
    note = f.text("exit_reason", False, "Cause / note", 300)
    if a["status"] != "active":
        f.errors["exit_status"] = "This animal is already recorded as not active."
    if d and a["date_of_birth"] and d < a["date_of_birth"]:
        f.errors["exit_date"] = "Date is before the animal's birth."
    if not f.ok:
        req.flash(next(iter(f.errors.values())), bad=True)
    else:
        req.run("UPDATE livestock SET status=?, exit_date=?, exit_reason=? WHERE id=?", (reason, d, note, a["id"]))
        req.flash(f"{animal_name(a)} recorded as {label(EXIT_REASONS, reason).lower()}.")
    raise Redirect(f"/animals/{a['id']}")


@route(r"/animals/(\d+)/reactivate", ("POST",))
def animal_reactivate(req, animal_id):
    req.require("delete")
    a = get_animal(req, animal_id)
    if a["status"] == "sold":
        req.flash("This animal was sold. Delete the sale to undo it.", bad=True)
    else:
        req.run("UPDATE livestock SET status='active', exit_date=NULL, exit_reason='' WHERE id=?", (a["id"],))
        req.flash("Animal is active again.")
    raise Redirect(f"/animals/{a['id']}")


@route(r"/animals/(\d+)/passed-on", ("POST",))
def animal_passed_on(req, animal_id):
    req.require("animals")
    a = get_animal(req, animal_id)
    req.run("UPDATE livestock SET pass_on_due=0 WHERE id=?", (a["id"],))
    req.flash("Girinka pass-on marked as done.")
    raise Redirect(f"/animals/{a['id']}")


@route(r"/animals/(\d+)/delete", ("POST",))
def animal_delete(req, animal_id):
    req.require("delete")
    a = get_animal(req, animal_id)
    if req.one("SELECT 1 FROM sale_items WHERE livestock_id=?", (a["id"],)):
        req.flash("This animal is on a sales receipt. Delete the sale first.", bad=True)
        raise Redirect(f"/animals/{a['id']}")
    with req.conn:
        unlink_transaction(req, "animal_purchase", a["id"])
        for h in req.conn.execute("SELECT id FROM health_records WHERE livestock_id=?", (a["id"],)).fetchall():
            unlink_transaction(req, "health", h["id"])
        req.conn.execute("DELETE FROM livestock WHERE id=?", (a["id"],))
    req.flash(f"{animal_name(a)} deleted.")
    raise Redirect("/animals")


@route(r"/animals/(\d+)")
def animal_detail(req, animal_id):
    a = get_animal(req, animal_id)
    code = req.country
    c = country(code)
    dam = req.one("SELECT * FROM livestock WHERE id=?", (a["dam_id"],)) if a["dam_id"] else None
    sire = req.one("SELECT * FROM livestock WHERE id=?", (a["sire_id"],)) if a["sire_id"] else None
    health = req.all("SELECT * FROM health_records WHERE livestock_id=? ORDER BY date DESC, id DESC", (a["id"],))
    weights = req.all("SELECT * FROM weights WHERE livestock_id=? ORDER BY date DESC, id DESC LIMIT 20", (a["id"],))
    offspring = req.all("SELECT * FROM livestock WHERE dam_id=? OR sire_id=? ORDER BY date_of_birth DESC", (a["id"], a["id"]))
    breeding = req.all("""SELECT b.*, m.name mname, m.tag_number mtag FROM breeding_events b LEFT JOIN livestock m ON m.id=b.male_id
                          WHERE b.female_id=? OR b.male_id=? ORDER BY b.mating_date DESC""", (a["id"], a["id"]))
    sale = req.one("""SELECT s.*, i.price FROM sale_items i JOIN sales s ON s.id=i.sale_id WHERE i.livestock_id=?""", (a["id"],))

    status = badge(label(ANIMAL_STATUS, a["status"]), STATUS_COLOR.get(a["status"], ""))
    info = [("Animal number", e(a["tag_number"])), ("Species", e(label(ANIMAL_TYPES, a["animal_type"]))),
            ("Breed", e(a["breed"] or "—")), ("Sex", e(label(GENDERS, a["gender"]))),
            ("Date of birth", fmt_date(a["date_of_birth"], code)), ("Age", age_text(a["date_of_birth"], a["exit_date"])),
            ("Colour / markings", e(a["colour"] or "—")), (c["id_label"], e(a["official_id"] or "—")),
            ("Latest weight", f"{fmt_num(a['weight_kg'], 1)} kg" if a["weight_kg"] else "—"),
            ("Acquired", f"{fmt_date(a['acquisition_date'], code)} · {e(label(acquisition_choices(code), a['acquisition_method']))}"),
            ("Mother", f'<a href="/animals/{dam["id"]}">{e(animal_name(dam))}</a>' if dam else "—"),
            ("Father", f'<a href="/animals/{sire["id"]}">{e(animal_name(sire))}</a>' if sire else "—")]
    if a["purchase_price"] and req.can("finance"):
        info.append(("Purchase price", money(a["purchase_price"], code) + (f" from {e(a['seller'])}" if a["seller"] else "")))
    if a["status"] != "active":
        info.append(("Left the herd", f"{fmt_date(a['exit_date'], code)} · {e(label(ANIMAL_STATUS, a['status']))}"
                     + (f" — {e(a['exit_reason'])}" if a["exit_reason"] else "")))
    if sale:
        info.append(("Sale", f'<a href="/sales/{sale["id"]}">Receipt {e(sale["receipt_no"])}</a> to {e(sale["buyer_name"])}'
                     + (f" · {money(sale['price'], code)}" if req.can("finance") else "")))
    body = ""
    if a["pass_on_due"]:
        done_btn = post_button(req, f"/animals/{a['id']}/passed-on", "Mark as passed on", "btn small sec") if req.can("animals") else ""
        body += f'<div class="note">Girinka animal: its first female calf should be passed on to another family. {done_btn}</div>'

    body += card(f'<div class="row">{status}</div>' + dl(info) + (f'<p class="muted">{e(a["notes"])}</p>' if a["notes"] else ""), "Profile")

    hrows = [[fmt_date(h["date"], code), f'<a href="/health/{h["id"]}/edit">{e(h["title"])}</a>' +
              (f' {badge("notifiable", "red")}' if h["notifiable"] else ""), e(label(HEALTH_TYPES, h["record_type"])),
              e(h["disease"] or h["diagnosis"] or "—"), fmt_date(h["next_due_date"], code) if h["next_due_date"] else "—"]
             + ([money(h["cost"], code)] if req.can("finance") else []) for h in health]
    hhead = ["Date", "Record", "Type", "Disease / diagnosis", "Next due"] + (["Cost"] if req.can("finance") else [])
    hact = f'<a class="btn small sec" href="/health/new?animal={a["id"]}">+ Health record</a>' if req.can("health") and a["status"] == "active" else ""
    body += card(table(hhead, hrows, numeric=(5,)) or empty("No health records yet"), "Medical history", hact)

    left = ""
    wrows = [[fmt_date(w["date"], code), f'{fmt_num(w["weight_kg"], 1)} kg'] for w in weights]
    wform = ""
    if req.can("animals") and a["status"] == "active":
        wform = f"""<form method="post" action="/animals/{a['id']}/weight" class="filters">{req.csrf_input()}
            {field("weight_kg", "Weight (kg)", "", type_="number", step="0.1", min="0.01", required=True)}
            {field("date", "Date", today().isoformat(), type_="date", required=True, max=today().isoformat())}
            <button class="btn">Add</button></form>"""
    left += card(wform + (table(["Date", "Weight"], wrows, numeric=(1,)) or empty("No weights recorded")), "Weight history")
    brows = [[f'<a href="/breeding/{b["id"]}">{fmt_date(b["mating_date"], code)}</a>', e(b["method"].upper() if b["method"] == "ai" else "Natural"),
              e(b["status"].replace("_", " ").capitalize()), fmt_date(b["expected_date"], code), str(b["born_alive"] or "—")] for b in breeding]
    bact = f'<a class="btn small sec" href="/breeding/new?female={a["id"]}">+ Breeding</a>' if req.can("breeding") and a["gender"] == "female" and a["status"] == "active" else ""
    orows = [[f'<a href="/animals/{o["id"]}">{e(animal_name(o))}</a>', fmt_date(o["date_of_birth"], code),
              e(label(GENDERS, o["gender"])), badge(label(ANIMAL_STATUS, o["status"]), STATUS_COLOR.get(o["status"], ""))] for o in offspring]
    right = card(table(["Mated", "Method", "Result", "Expected", "Born alive"], brows) or empty("No breeding records"), "Breeding", bact)
    right += card(table(["Offspring", "Born", "Sex", "Status"], orows) or empty("No offspring recorded"), "Offspring")
    body += f'<div class="grid g2"><div>{left}</div><div>{right}</div></div>'

    if a["status"] == "active" and req.can("animals"):
        exit_form = f"""<form method="post" action="/animals/{a['id']}/exit">{req.csrf_input()}<div class="fgrid3">
            {select("exit_status", "What happened", EXIT_REASONS, "dead")}
            {field("exit_date", "Date", today().isoformat(), type_="date", required=True, max=today().isoformat())}
            {field("exit_reason", "Cause / note", "", placeholder="e.g. East Coast fever, lightning, slaughtered for wedding")}</div>
            <button class="btn danger" onclick="return confirm('Record that this animal has left the herd?')">Record</button>
            {'<a class="btn sec" href="/sales/new?animal=' + str(a["id"]) + '">Sell this animal instead</a>' if req.can("finance") else ''}</form>"""
        body += card(exit_form, "Record death, slaughter or giving away")
    actions = ""
    if req.can("animals"):
        actions += f'<a class="btn" href="/animals/{a["id"]}/edit">Edit</a>'
    if req.can("delete"):
        if a["status"] not in ("active", "sold"):
            actions += " " + post_button(req, f"/animals/{a['id']}/reactivate", "Undo exit", "btn sec")
        actions += " " + post_button(req, f"/animals/{a['id']}/delete", "Delete", confirm="Delete this animal and its health records?")
    return layout(req, animal_name(a), body, "animals", subtitle=f"{label(ANIMAL_TYPES, a['animal_type'])} · {a['breed'] or 'breed not set'}", actions=actions)
'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.views.auth
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.views.auth'] = r'''"""Sign in, create account, sign out."""
from ..security import EMAIL_RE, check_password, hash_password, password_problem
from ..ui import Form, bare_page, e, field
from ..web import Redirect, route


def auth_page(title, inner, below=""):
    return bare_page(title, f"""<div class="auth"><div class="logo">JESSE FARM<br>MANAGEMENT SYSTEM</div>
        <p class="muted" style="text-align:center;margin-top:0">Livestock records, health, breeding and money for farms in
        Zambia and Rwanda</p><div class="card">{inner}</div>{below}</div>""")


@route("/login", ("GET", "POST"), public=True)
def login(req):
    if req.user:
        raise Redirect("/")
    error, email = "", ""
    if req.method == "POST":
        email = req.form.get("email", "").strip().lower()
        user = req.one("SELECT * FROM users WHERE email=?", (email,))
        if user and check_password(req.form.get("password", ""), user["password_hash"]):
            req.login(user["id"])
            raise Redirect("/")
        error = "Incorrect email or password."
    inner = f"""<h1 style="font-size:20px">Sign in</h1><form method="post">
        {f'<div class="flash bad">{e(error)}</div>' if error else ''}
        {field("email", "Email", email, type_="email", required=True, autocomplete="email", autofocus=True)}
        {field("password", "Password", "", type_="password", required=True, autocomplete="current-password")}
        <button class="btn block">Sign in</button></form>"""
    return auth_page("Sign in", inner, '<p style="text-align:center">New here? <a href="/register">Create an account</a></p>')


@route("/register", ("GET", "POST"), public=True)
def register(req):
    if req.user:
        raise Redirect("/")
    f = Form(req.form)
    if req.method == "POST":
        first = f.text("first_name", True, "First name", 150)
        last = f.text("last_name", False, "Last name", 150)
        email = f.text("email", True, "Email", 254).lower()
        phone = f.text("phone", False, "Phone", 30)
        password = req.form.get("password", "")
        if email and not EMAIL_RE.match(email):
            f.errors["email"] = "Enter a valid email address."
        elif email and req.one("SELECT 1 FROM users WHERE email=?", (email,)):
            f.errors["email"] = "An account with this email already exists."
        if password_problem(password):
            f.errors["password"] = password_problem(password)
        elif password != req.form.get("confirm", ""):
            f.errors["confirm"] = "Passwords don't match."
        if f.ok:
            first_user = req.one("SELECT COUNT(*) c FROM users")["c"] == 0
            uid = req.run("INSERT INTO users (email, first_name, last_name, phone, role, password_hash, is_admin) "
                          "VALUES (?,?,?,?,?,?,?)",
                          (email, first, last, phone, "owner", hash_password(password), 1 if first_user else 0))
            req.login(uid)
            raise Redirect("/farms/new?welcome=1")
    d, er = req.form, f.errors
    inner = f"""<h1 style="font-size:20px">Create your account</h1>
      <p class="muted">Next you will register your farm in Zambia or Rwanda.</p><form method="post">
      <div class="fgrid">{field("first_name", "First name", d.get("first_name"), er, required=True)}
      {field("last_name", "Last name", d.get("last_name"), er)}</div>
      {field("email", "Email", d.get("email"), er, type_="email", required=True)}
      {field("phone", "Phone (optional)", d.get("phone"), er, type_="tel", placeholder="+260… or +250…")}
      {field("password", "Password", "", er, type_="password", required=True, hint="At least 8 characters, not only numbers")}
      {field("confirm", "Confirm password", "", er, type_="password", required=True)}
      <button class="btn block">Create account</button></form>"""
    return auth_page("Create account", inner, '<p style="text-align:center">Already registered? <a href="/login">Sign in</a></p>')


@route("/logout", ("POST",), needs_farm=False)
def logout(req):
    req.logout()
    raise Redirect("/login")

'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.views.breeding
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.views.breeding'] = r'''"""Breeding and reproduction: matings, pregnancy checks, expected dates, births and offspring."""
import datetime as dt

from ..countries import GESTATION_DAYS
from ..ui import (Form, badge, card, chips, dl, e, empty, field, fmt_date, label, layout, parse_date,
                  post_button, select, stat, table, textarea, today)
from ..web import NotFound, Redirect, route
from .common import ANIMAL_TYPES, animal_name, animal_options, get_animal
from .animals import make_tag

METHODS = [("natural", "Natural mating"), ("ai", "Artificial insemination (AI)")]
STATUSES = [("served", "Mated, not yet checked"), ("pregnant", "Pregnancy confirmed"), ("not_pregnant", "Not pregnant"),
            ("delivered", "Gave birth"), ("aborted", "Lost the pregnancy")]
STATUS_COLOR = {"served": "", "pregnant": "blue", "not_pregnant": "yellow", "delivered": "green", "aborted": "red"}
OPEN = ("served", "pregnant")


def expected_date(animal_type, mating_date):
    days = GESTATION_DAYS.get(animal_type)
    d = parse_date(mating_date)
    return (d + dt.timedelta(days=days)).isoformat() if days and d else None


def get_event(req, event_id):
    b = req.one("SELECT * FROM breeding_events WHERE id=? AND farm_id=?", (event_id, req.fid))
    if not b:
        raise NotFound()
    return b


def performance(req, start=None, end=None, animal_type=None, fids=None):
    """Reproductive performance figures used by the breeding page and the reports."""
    fids = fids or [req.fid]
    where, params = f"b.farm_id IN ({','.join('?' * len(fids))})", list(fids)
    if start:
        where += " AND b.mating_date >= ?"
        params.append(start)
    if end:
        where += " AND b.mating_date <= ?"
        params.append(end)
    if animal_type:
        where += " AND l.animal_type = ?"
        params.append(animal_type)
    rows = req.all(f"SELECT b.*, l.animal_type FROM breeding_events b JOIN livestock l ON l.id=b.female_id WHERE {where}", params)
    known = [r for r in rows if r["status"] in ("pregnant", "not_pregnant", "delivered", "aborted")]
    conceived = [r for r in known if r["status"] in ("pregnant", "delivered", "aborted")]
    delivered = [r for r in rows if r["status"] == "delivered"]
    alive = sum(r["born_alive"] for r in delivered)
    dead = sum(r["born_dead"] for r in delivered)
    gest = [(parse_date(r["outcome_date"]) - parse_date(r["mating_date"])).days for r in delivered
            if r["outcome_date"] and r["mating_date"]]
    # Interval between births of the same mother (calving / kidding interval)
    births_by_mother = {}
    for r in sorted(delivered, key=lambda r: r["outcome_date"] or ""):
        births_by_mother.setdefault(r["female_id"], []).append(parse_date(r["outcome_date"]))
    intervals = [(b - a).days for ds in births_by_mother.values() for a, b in zip(ds, ds[1:]) if a and b]
    return {
        "services": len(rows), "known": len(known), "conceived": len(conceived), "delivered": len(delivered),
        "conception_rate": (len(conceived) / len(known) * 100) if known else None,
        "born_alive": alive, "born_dead": dead,
        "survival": (alive / (alive + dead) * 100) if alive + dead else None,
        "litter": (alive / len(delivered)) if delivered else None,
        "gestation": (sum(gest) / len(gest)) if gest else None,
        "interval": (sum(intervals) / len(intervals)) if intervals else None,
    }


def pct(v):
    return f"{v:.0f}%" if v is not None else "—"


@route("/breeding")
def breeding_list(req):
    code = req.country
    show = req.query.get("show", "open")
    sql = """SELECT b.*, f.name fname, f.tag_number ftag, f.animal_type, m.name mname, m.tag_number mtag
             FROM breeding_events b JOIN livestock f ON f.id=b.female_id LEFT JOIN livestock m ON m.id=b.male_id
             WHERE b.farm_id=?"""
    if show == "open":
        sql += " AND b.status IN ('served','pregnant') ORDER BY b.expected_date"
    elif show == "done":
        sql += " AND b.status NOT IN ('served','pregnant') ORDER BY b.mating_date DESC"
    else:
        show = "all"
        sql += " ORDER BY b.mating_date DESC"
    rows = req.all(sql, (req.fid,))
    p = performance(req)
    t = today()
    body = '<div class="stats">'
    body += stat(sum(1 for r in rows if r["status"] in OPEN) if show != "done" else "—", "Open pregnancies / services")
    body += stat(pct(p["conception_rate"]), "Conception rate (checked services)")
    body += stat(p["born_alive"], "Young born alive (all time)")
    body += stat(f'{p["interval"]:.0f} days' if p["interval"] else "—", "Average interval between births")
    body += "</div>"
    body += chips("/breeding", "show", [("open", "Open (mated / pregnant)"), ("done", "Finished"), ("all", "All")], show)
    trs = []
    for r in rows:
        due = ""
        if r["status"] in OPEN and r["expected_date"]:
            days = (parse_date(r["expected_date"]) - t).days
            due = badge(f"{days} days" if days >= 0 else f"{-days} days overdue", "red" if days < 0 else ("yellow" if days <= 14 else "blue"))
        sire = f"{r['mname'] or r['mtag']}" if r["male_id"] else (r["sire_details"] or "—")
        trs.append([f'<a href="/breeding/{r["id"]}"><b>{e(r["fname"] or r["ftag"])}</b></a><div class="muted">{e(label(ANIMAL_TYPES, r["animal_type"]))}</div>',
                    e(sire), e(label(METHODS, r["method"])), fmt_date(r["mating_date"], code),
                    fmt_date(r["expected_date"], code), badge(label(STATUSES, r["status"]), STATUS_COLOR[r["status"]]), due])
    body += card(table(["Female", "Sire", "Method", "Mated", "Expected birth", "Status", "Due in"], trs)
                 or empty("No breeding records", "Record a mating or insemination with the button above."))
    body += '<p class="muted">Expected birth dates use average gestation lengths (cattle 283, goats and sheep 150, pigs 114, rabbits 31 days; source: MSD Veterinary Manual). Real dates vary by a few days.</p>'
    actions = '<a class="btn" href="/breeding/new">+ Record mating</a>' if req.can("breeding") else ""
    return layout(req, "Breeding & reproduction", body, "breeding", actions=actions)


def event_form(req, ev=None):
    code = req.country
    if req.method == "GET":
        data = dict(ev) if ev else {"mating_date": today().isoformat(), "method": "natural", "status": "served",
                                    "female_id": req.query.get("female", "")}
    else:
        data = req.form
    f = Form(req.form)
    if req.method == "POST":
        female_id, male_id = f.id("female_id"), f.id("male_id")
        female = req.one("SELECT * FROM livestock WHERE id=? AND farm_id=? AND gender='female'", (female_id, req.fid)) if female_id else None
        male = req.one("SELECT * FROM livestock WHERE id=? AND farm_id=? AND gender='male'", (male_id, req.fid)) if male_id else None
        if not female:
            f.errors["female_id"] = "Choose the female."
        if male_id and not male:
            f.errors["male_id"] = "Choose a male from this farm, or leave empty."
        if female and male and female["animal_type"] != male["animal_type"]:
            f.errors["male_id"] = "The male must be the same species as the female."
        v = {
            "female_id": female_id, "male_id": male_id if male else None,
            "method": f.choice("method", METHODS),
            "sire_details": f.text("sire_details", False, "Sire details", 200),
            "mating_date": f.date("mating_date", True, "Mating date", not_future=True),
            "status": f.choice("status", STATUSES[:3]) if not ev or ev["status"] in ("served", "pregnant", "not_pregnant") else ev["status"],
            "check_date": f.date("check_date", False, "Pregnancy check date", not_future=True),
            "notes": f.text("notes", False, "Notes", 2000),
        }
        manual_expected = f.date("expected_date", False, "Expected date")
        if v["check_date"] and v["mating_date"] and v["check_date"] < v["mating_date"]:
            f.errors["check_date"] = "The check can't be before the mating."
        if female and female["date_of_birth"] and v["mating_date"] and v["mating_date"] < female["date_of_birth"]:
            f.errors["mating_date"] = "Mating date is before the female was born."
        if f.ok:
            v["expected_date"] = expected_date(female["animal_type"], v["mating_date"]) or manual_expected
            cols = list(v)
            if ev:
                req.run(f"UPDATE breeding_events SET {', '.join(c + '=?' for c in cols)} WHERE id=? AND farm_id=?",
                        [v[c] for c in cols] + [ev["id"], req.fid])
                eid = ev["id"]
            else:
                eid = req.run(f"INSERT INTO breeding_events (farm_id, created_by, {', '.join(cols)}) VALUES (?, ?{', ?' * len(cols)})",
                              [req.fid, req.user["id"]] + [v[c] for c in cols])
            req.flash("Breeding record saved." + (f" Expected birth: {fmt_date(v['expected_date'], code)}." if v["expected_date"] else ""))
            raise Redirect(f"/breeding/{eid}")
    er = f.errors
    keep_f = ev["female_id"] if ev else None
    keep_m = ev["male_id"] if ev else None
    status_choices = STATUSES[:3] if not ev or ev["status"] in ("served", "pregnant", "not_pregnant") else [(ev["status"], label(STATUSES, ev["status"]))]
    form = f"""<form method="post">{req.csrf_input()}<div class="fgrid">
      {select("female_id", "Female", animal_options(req, True, "female", keep_f), data.get("female_id"), er, blank="— choose —", groups=True)}
      {select("male_id", "Male on this farm (optional)", animal_options(req, True, "male", keep_m), data.get("male_id"), er, blank="— none / outside bull or AI —", groups=True)}
      {select("method", "Method", METHODS, data.get("method"), er)}
      {field("sire_details", "Sire details", data.get("sire_details"), er, hint="Outside bull name or AI straw code")}
      {field("mating_date", "Mating / insemination date", data.get("mating_date"), er, type_="date", required=True, max=today().isoformat())}
      {select("status", "Pregnancy status", status_choices, data.get("status"), er)}
      {field("check_date", "Pregnancy check date", data.get("check_date"), er, type_="date", max=today().isoformat())}
      {field("expected_date", "Expected birth (only for species without a standard)", data.get("expected_date"), er, type_="date",
             hint="Calculated automatically for cattle, goats, sheep, pigs, rabbits and poultry")}
      </div>{textarea("notes", "Notes", data.get("notes"), er)}
      <button class="btn block">Save</button></form>"""
    return layout(req, "Edit breeding record" if ev else "Record mating", card(form), "breeding")


@route("/breeding/new", ("GET", "POST"))
def breeding_new(req):
    req.require("breeding")
    return event_form(req)


@route(r"/breeding/(\d+)/edit", ("GET", "POST"))
def breeding_edit(req, event_id):
    req.require("breeding")
    return event_form(req, get_event(req, event_id))


@route(r"/breeding/(\d+)/outcome", ("POST",))
def breeding_outcome(req, event_id):
    """Record the end of a pregnancy. A birth creates the offspring in the livestock register."""
    req.require("breeding")
    ev = get_event(req, event_id)
    code = req.country
    mother = get_animal(req, ev["female_id"])
    f = Form(req.form)
    result = f.choice("result", [("delivered", ""), ("aborted", ""), ("not_pregnant", "")])
    d = f.date("outcome_date", True, "Date", not_future=True)
    males = f.integer("males", False, 0, "Male young", 0) or 0
    females = f.integer("females", False, 0, "Female young", 0) or 0
    dead = f.integer("born_dead", False, 0, "Born dead", 0) or 0
    if ev["status"] not in OPEN:
        f.errors["result"] = "The outcome of this pregnancy is already recorded."
    if d and d < ev["mating_date"]:
        f.errors["outcome_date"] = "Date is before the mating."
    if result == "delivered" and males + females + dead == 0:
        f.errors["males"] = "Enter how many young were born."
    if males + females + dead > 30:
        f.errors["males"] = "That is more young than is possible in one birth."
    if not f.ok:
        req.flash(next(iter(f.errors.values())), bad=True)
        raise Redirect(f"/breeding/{ev['id']}")
    created = []
    with req.conn:
        if result == "delivered":
            for sex, n in (("male", males), ("female", females)):
                for _ in range(n):
                    aid = req.conn.execute(
                        """INSERT INTO livestock (farm_id, animal_type, breed, gender, date_of_birth, acquisition_date,
                           acquisition_method, dam_id, sire_id, notes) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (req.fid, mother["animal_type"], mother["breed"], sex, d, d, "born", mother["id"], ev["male_id"],
                         f"Born from breeding record #{ev['id']}")).lastrowid
                    req.conn.execute("UPDATE livestock SET tag_number=? WHERE id=?", (make_tag(code, mother["animal_type"], d, aid), aid))
                    created.append(aid)
        req.conn.execute("""UPDATE breeding_events SET status=?, outcome_date=?, born_alive=?, born_dead=? WHERE id=?""",
                         (result, d, (males + females) if result == "delivered" else 0, dead if result == "delivered" else 0, ev["id"]))
    msg = {"delivered": f"Birth recorded: {len(created)} young added to the register.", "aborted": "Pregnancy loss recorded.",
           "not_pregnant": "Recorded as not pregnant."}[result]
    if result == "delivered" and females and mother["pass_on_due"]:
        msg += " Girinka: this mother's first female calf is due to be passed on to another family."
    req.flash(msg)
    raise Redirect(f"/breeding/{ev['id']}")


@route(r"/breeding/(\d+)/delete", ("POST",))
def breeding_delete(req, event_id):
    req.require("delete")
    ev = get_event(req, event_id)
    req.run("DELETE FROM breeding_events WHERE id=?", (ev["id"],))
    req.flash("Breeding record deleted. Any offspring already registered stay in the livestock register.")
    raise Redirect("/breeding")


@route(r"/breeding/(\d+)")
def breeding_detail(req, event_id):
    ev = get_event(req, event_id)
    code = req.country
    mother = get_animal(req, ev["female_id"])
    male = req.one("SELECT * FROM livestock WHERE id=?", (ev["male_id"],)) if ev["male_id"] else None
    young = req.all("SELECT * FROM livestock WHERE dam_id=? AND date_of_birth=? ORDER BY id", (mother["id"], ev["outcome_date"])) if ev["outcome_date"] else []
    info = [("Female", f'<a href="/animals/{mother["id"]}">{e(animal_name(mother))}</a>'),
            ("Sire", f'<a href="/animals/{male["id"]}">{e(animal_name(male))}</a>' if male else e(ev["sire_details"] or "—")),
            ("Method", e(label(METHODS, ev["method"]))), ("Mating date", fmt_date(ev["mating_date"], code)),
            ("Pregnancy check", fmt_date(ev["check_date"], code)), ("Expected birth", fmt_date(ev["expected_date"], code)),
            ("Status", badge(label(STATUSES, ev["status"]), STATUS_COLOR[ev["status"]]))]
    if ev["outcome_date"]:
        info.append(("Outcome date", fmt_date(ev["outcome_date"], code)))
        gest = (parse_date(ev["outcome_date"]) - parse_date(ev["mating_date"])).days
        info.append(("Days from mating", str(gest)))
    if ev["status"] == "delivered":
        info.append(("Born alive / dead", f"{ev['born_alive']} / {ev['born_dead']}"))
    body = card(dl(info) + (f'<p class="muted">{e(ev["notes"])}</p>' if ev["notes"] else ""), "Breeding record")
    if young:
        body += card(table(["Young", "Sex"], [[f'<a href="/animals/{y["id"]}">{e(animal_name(y))}</a>', e(y["gender"])] for y in young]), "Offspring from this birth")
    if ev["status"] in OPEN and req.can("breeding"):
        body += card(f"""<form method="post" action="/breeding/{ev['id']}/outcome">{req.csrf_input()}<div class="fgrid3">
            {select("result", "Result", [("delivered", "Gave birth"), ("aborted", "Lost the pregnancy"), ("not_pregnant", "Was not pregnant")], "delivered")}
            {field("outcome_date", "Date", today().isoformat(), type_="date", required=True, max=today().isoformat())}
            {field("born_dead", "Born dead", "0", type_="number", min="0", step="1")}
            {field("males", "Males born alive", "0", type_="number", min="0", step="1")}
            {field("females", "Females born alive", "0", type_="number", min="0", step="1")}</div>
            <p class="muted">Each young born alive is added to the livestock register with its mother and father linked.</p>
            <button class="btn">Save outcome</button></form>""", "Record the outcome")
    actions = ""
    if req.can("breeding"):
        actions += f'<a class="btn sec" href="/breeding/{ev["id"]}/edit">Edit</a>'
    if req.can("delete"):
        actions += " " + post_button(req, f"/breeding/{ev['id']}/delete", "Delete", confirm="Delete this breeding record?")
    return layout(req, f"Breeding: {animal_name(mother)}", body, "breeding", actions=actions)

'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.views.common
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.views.common'] = r'''"""Choices and helpers shared by several modules."""
from ..countries import country
from ..web import NotFound

ANIMAL_TYPES = [("cattle", "Cattle"), ("goat", "Goat"), ("sheep", "Sheep"), ("pig", "Pig"),
                ("poultry", "Poultry"), ("rabbit", "Rabbit"), ("other", "Other")]
GENDERS = [("female", "Female"), ("male", "Male")]
ANIMAL_STATUS = [("active", "Active"), ("sold", "Sold"), ("dead", "Died"), ("slaughtered", "Slaughtered"),
                 ("given_away", "Given away")]
STATUS_COLOR = {"active": "green", "sold": "blue", "dead": "red", "slaughtered": "", "given_away": "yellow"}
BASE_ACQUISITION = [("born", "Born on farm"), ("purchased", "Purchased"), ("gift", "Gift"), ("inherited", "Inherited")]
TAG_PREFIX = {"cattle": "CAT", "goat": "GOA", "sheep": "SHP", "pig": "PIG", "poultry": "PLT", "rabbit": "RAB", "other": "OTH"}

HEALTH_TYPES = [("vaccination", "Vaccination"), ("treatment", "Treatment"), ("vet_visit", "Veterinary visit"),
                ("checkup", "Check-up"), ("deworming", "Deworming"), ("dipping", "Dipping / spraying"),
                ("other", "Other")]

INCOME_CATEGORIES = [("livestock_sale", "Livestock sales"), ("milk", "Milk sales"), ("eggs", "Egg sales"),
                     ("manure", "Manure / by-products"), ("services", "Services (e.g. bull hire)"),
                     ("other_income", "Other income")]
EXPENSE_CATEGORIES = [("animal_purchase", "Animal purchases"), ("feed", "Feed"), ("veterinary", "Veterinary"),
                      ("labour", "Labour"), ("transport", "Transport"), ("supplies", "Supplies & equipment"),
                      ("utilities", "Water & electricity"), ("fees", "Permits, fees & levies"),
                      ("other_expense", "Other expenses")]
ALL_CATEGORIES = INCOME_CATEGORIES + EXPENSE_CATEGORIES

PRODUCT_KINDS = [("feed", "Feed"), ("medicine", "Medicine / vaccine"), ("equipment", "Equipment"), ("other", "Other")]
KIND_TO_EXPENSE = {"feed": "feed", "medicine": "veterinary", "equipment": "supplies", "other": "supplies"}

PRIORITIES = [("high", "High"), ("medium", "Medium"), ("low", "Low")]
PRIORITY_COLOR = {"high": "red", "medium": "yellow", "low": ""}
TASK_STATUS = [("pending", "Pending"), ("in_progress", "In progress"), ("completed", "Completed")]


def acquisition_choices(code):
    return BASE_ACQUISITION + country(code)["extra_acquisition"]


def get_animal(req, animal_id):
    a = req.one("SELECT * FROM livestock WHERE id=? AND farm_id=?", (animal_id, req.fid))
    if not a:
        raise NotFound()
    return a


def animal_name(a):
    if not a:
        return "—"
    return f"{a['name']} ({a['tag_number']})" if a["name"] else (a["tag_number"] or f"#{a['id']}")


def animal_options(req, only_active=True, gender=None, keep_id=None):
    sql = "SELECT id, name, tag_number, animal_type, status FROM livestock WHERE farm_id=?"
    params = [req.fid]
    if only_active:
        sql += " AND (status='active' OR id=?)"
        params.append(keep_id or 0)
    if gender:
        sql += " AND gender=?"
        params.append(gender)
    rows = req.all(sql + " ORDER BY animal_type, name, tag_number", params)
    return [(r["id"], animal_name(r) + ("" if r["status"] == "active" else f" — {r['status']}"),
             dict(ANIMAL_TYPES).get(r["animal_type"], r["animal_type"])) for r in rows]


def link_transaction(req, source_type, source_id, kind, category, amount, date, description, party=""):
    """Keep exactly one ledger row for a record that costs or earns money (health cost, sale, purchase...)."""
    req.conn.execute("DELETE FROM transactions WHERE farm_id=? AND source_type=? AND source_id=?",
                     (req.fid, source_type, source_id))
    if amount and amount > 0:
        req.conn.execute(
            """INSERT INTO transactions (farm_id, date, kind, category, amount, description, party,
               source_type, source_id, created_by) VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (req.fid, date, kind, category, amount, description, party, source_type, source_id, req.user["id"]),
        )


def unlink_transaction(req, source_type, source_id):
    req.conn.execute("DELETE FROM transactions WHERE farm_id=? AND source_type=? AND source_id=?",
                     (req.fid, source_type, source_id))


def safe_back(req, default):
    import urllib.parse
    back = urllib.parse.urlsplit(req.handler.headers.get("Referer") or "")
    same_site = not back.netloc or back.netloc == req.handler.headers.get("Host")
    if back.path.startswith("/") and same_site:
        return back.path + ("?" + back.query if back.query else "")
    return default
'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.views.dashboard
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.views.dashboard'] = r'''"""Dashboard: the farm at a glance."""
import datetime as dt

from ..countries import country
from ..ui import (bar_chart, badge, card, e, empty, fmt_date, hbars, label, layout, money, month_label, months_back,
                  pair_chart, stat, table, today)
from ..web import route
from .common import ANIMAL_TYPES, HEALTH_TYPES, PRIORITIES, PRIORITY_COLOR, animal_name


@route("/")
def dashboard(req):
    fid, code, t = req.fid, req.country, today()
    ti, soon = t.isoformat(), (t + dt.timedelta(days=14)).isoformat()
    month_start = t.replace(day=1).isoformat()

    active = req.one("SELECT COUNT(*) c FROM livestock WHERE farm_id=? AND status='active'", (fid,))["c"]
    by_type = req.all("""SELECT animal_type k, COUNT(*) c FROM livestock WHERE farm_id=? AND status='active'
                         GROUP BY k ORDER BY c DESC""", (fid,))
    health_due = req.all("""SELECT h.*, l.name, l.tag_number, l.id lid FROM health_records h JOIN livestock l ON l.id=h.livestock_id
                            WHERE l.farm_id=? AND l.status='active' AND h.next_due_date BETWEEN ? AND ?
                            ORDER BY h.next_due_date LIMIT 8""", (fid, ti, soon))
    overdue_health = req.one("""SELECT COUNT(*) c FROM health_records h JOIN livestock l ON l.id=h.livestock_id
                                WHERE l.farm_id=? AND l.status='active' AND h.next_due_date < ? AND h.next_due_date >= ?""",
                             (fid, ti, (t - dt.timedelta(days=60)).isoformat()))["c"]
    births_due = req.all("""SELECT b.*, l.name, l.tag_number FROM breeding_events b JOIN livestock l ON l.id=b.female_id
                            WHERE b.farm_id=? AND b.status IN ('served','pregnant') AND b.expected_date <= ?
                            ORDER BY b.expected_date LIMIT 6""", (fid, (t + dt.timedelta(days=30)).isoformat()))
    tasks = req.all("""SELECT * FROM tasks WHERE farm_id=? AND status!='completed' AND due_date <= ?
                       ORDER BY due_date LIMIT 6""", (fid, (t + dt.timedelta(days=7)).isoformat()))
    low = req.all("SELECT * FROM products WHERE farm_id=? AND quantity <= reorder_level ORDER BY name LIMIT 6", (fid,))
    notifiable = req.all("""SELECT h.*, l.name, l.tag_number FROM health_records h JOIN livestock l ON l.id=h.livestock_id
                            WHERE l.farm_id=? AND h.notifiable=1 AND h.date >= ? ORDER BY h.date DESC LIMIT 3""",
                         (fid, (t - dt.timedelta(days=30)).isoformat()))
    pass_on = req.all("SELECT * FROM livestock WHERE farm_id=? AND pass_on_due=1 AND status='active'", (fid,))

    body = ""
    if not req.farm["district"]:
        body += '<div class="note">This farm has no district yet. <a href="/farms/edit">Add its location</a> so reports and records are complete.</div>'
    for n in notifiable:
        body += (f'<div class="flash bad">Notifiable disease recorded: {e(n["disease"])} in {e(animal_name(n))} on '
                 f'{fmt_date(n["date"], code)}. {e(country(code)["notifiable_note"])}</div>')
    if overdue_health:
        body += f'<div class="note">{overdue_health} vaccination(s) or treatment(s) are past their due date. <a href="/health?show=overdue">See them</a></div>'
    for a in pass_on:
        body += (f'<div class="note">Girinka: {e(animal_name(a))} came through the Girinka programme. Remember to pass on '
                 f'its first female calf. <a href="/animals/{a["id"]}">Open animal</a></div>')

    stats = stat(active, "Active animals", "/animals")
    stats += stat(len(health_due), "Health care due (14 days)", "/health", "warn" if health_due else "")
    stats += stat(len(births_due), "Births expected (30 days)", "/breeding", "warn" if births_due else "")
    stats += stat(len(low), "Products low in stock", "/inventory?low=1", "bad" if low else "")
    if req.can("finance"):
        inc = req.one("SELECT COALESCE(SUM(amount),0) s FROM transactions WHERE farm_id=? AND kind='income' AND date>=?", (fid, month_start))["s"]
        exp = req.one("SELECT COALESCE(SUM(amount),0) s FROM transactions WHERE farm_id=? AND kind='expense' AND date>=?", (fid, month_start))["s"]
        stats += stat(money(inc - exp, code), "Profit this month", "/finance", "good" if inc >= exp else "bad")
    body += f'<div class="stats">{stats}</div>'

    left = card(hbars([(label(ANIMAL_TYPES, r["k"]), r["c"]) for r in by_type]) or empty("No animals yet"),
                "Herd by species", '<a class="btn small sec" href="/animals/new">+ Animal</a>')
    if req.can("finance"):
        months = months_back(6)
        rows = req.all("""SELECT substr(date,1,7) m, kind, SUM(amount) s FROM transactions WHERE farm_id=? AND date >= ?
                          GROUP BY m, kind""", (fid, months[0] + "-01"))
        series = {m: [0, 0] for m in months}
        for r in rows:
            if r["m"] in series:
                series[r["m"]][0 if r["kind"] == "income" else 1] = r["s"]
        right = card(pair_chart([(month_label(m), a, b) for m, (a, b) in series.items()],
                                fmt=lambda v: money(v, code, False)), f"Income and expenses, last 6 months ({country(code)['currency']})")
    else:
        months = months_back(6)
        rows = dict((r["m"], r["c"]) for r in req.all(
            """SELECT substr(b.outcome_date,1,7) m, SUM(b.born_alive) c FROM breeding_events b
               WHERE b.farm_id=? AND b.status='delivered' AND b.outcome_date >= ? GROUP BY m""", (fid, months[0] + "-01")))
        right = card(bar_chart([(month_label(m), rows.get(m, 0) or 0) for m in months]), "Births, last 6 months")
    body += f'<div class="grid g2">{left}{right}</div>'

    hd = [[f'<a href="/animals/{h["lid"]}">{e(animal_name(h))}</a>', e(h["title"]), e(label(HEALTH_TYPES, h["record_type"])),
           badge(fmt_date(h["next_due_date"], code), "yellow")] for h in health_due]
    bd = [[f'<a href="/breeding/{b["id"]}">{e(animal_name(b))}</a>', fmt_date(b["mating_date"], code),
           badge(fmt_date(b["expected_date"], code), "blue")] for b in births_due]
    tk = [[f'<a href="/tasks/{x["id"]}/edit">{e(x["title"])}</a>', fmt_date(x["due_date"], code),
           badge("Overdue", "red") if x["due_date"] and x["due_date"] < ti else badge(label(PRIORITIES, x["priority"]), PRIORITY_COLOR[x["priority"]])]
          for x in tasks]
    lw = [[f'<a href="/inventory/{p["id"]}">{e(p["name"])}</a>', f'{e(p["quantity"] if p["quantity"] % 1 else int(p["quantity"]))} {e(p["unit"])}']
          for p in low]
    body += '<div class="grid g2">'
    body += card(table(["Animal", "Treatment", "Type", "Due"], hd) or empty("Nothing due in the next 14 days"), "Upcoming vaccinations & treatments")
    body += card(table(["Mother", "Mated", "Expected"], bd) or empty("No births expected in the next 30 days"), "Expected births")
    body += card(table(["Task", "Due", ""], tk) or empty("No tasks due this week"), "Tasks this week")
    body += card(table(["Product", "Left"], lw) or empty("All stock above warning levels"), "Running low")
    body += "</div>"
    actions = ('<a class="btn sec" href="/health/new">+ Health record</a> <a class="btn sec" href="/feeding/new">+ Feeding</a> '
               '<a class="btn" href="/reports">Reports</a>')
    return layout(req, "Dashboard", body, "dashboard", subtitle=f"Hello {req.user['first_name']} — {fmt_date(t, code)}", actions=actions)
'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.views.exports
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.views.exports'] = r'''"""CSV exports (open in Excel, LibreOffice or Google Sheets)."""
import csv
import io

from ..countries import country
from ..security import can
from ..ui import today
from ..web import NotFound, Forbidden, Response, route
from .reports import report_data, scope_from_query

EXPORTS = {
    # name: (permission needed besides "export", SQL, headers)
    "animals": (None, """SELECT tag_number, name, animal_type, breed, gender, date_of_birth, colour, official_id, acquisition_method,
                         acquisition_date, purchase_price, seller, status, exit_date, exit_reason, weight_kg, notes
                         FROM livestock WHERE farm_id=? ORDER BY id"""),
    "health": (None, """SELECT h.date, l.tag_number, l.name, h.record_type, h.title, h.disease, h.notifiable, h.diagnosis, h.treatment,
                        h.vet_name, h.cost, h.next_due_date, h.withdrawal_until FROM health_records h JOIN livestock l ON l.id=h.livestock_id
                        WHERE l.farm_id=? ORDER BY h.date"""),
    "breeding": (None, """SELECT f.tag_number female, m.tag_number male, b.method, b.sire_details, b.mating_date, b.expected_date, b.status,
                          b.check_date, b.outcome_date, b.born_alive, b.born_dead, b.notes FROM breeding_events b
                          JOIN livestock f ON f.id=b.female_id LEFT JOIN livestock m ON m.id=b.male_id WHERE b.farm_id=? ORDER BY b.mating_date"""),
    "feeding": (None, """SELECT date, feed_name, quantity, unit, animal_type, animal_count, cost, notes FROM feeding_records
                         WHERE farm_id=? ORDER BY date"""),
    "inventory": (None, """SELECT name, kind, unit, quantity, reorder_level, unit_price, expiry_date, description FROM products
                           WHERE farm_id=? ORDER BY name"""),
    "tasks": (None, "SELECT title, priority, status, due_date, completed_at, description FROM tasks WHERE farm_id=? ORDER BY due_date"),
    "sales": ("finance", """SELECT s.receipt_no, s.date, s.buyer_name, s.buyer_phone, s.payment_method, s.permit_no, i.description, i.price
                           FROM sales s JOIN sale_items i ON i.sale_id=s.id WHERE s.farm_id=? ORDER BY s.date"""),
    "transactions": ("finance", """SELECT date, kind, category, amount, description, party, source_type FROM transactions
                                  WHERE farm_id=? ORDER BY date"""),
}


def safe(value):
    """Stop spreadsheet formula injection: a cell starting with = + - @ is shown as text."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@"):
        return "'" + value
    return value


def to_csv(headers, rows):
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(headers)
    for r in rows:
        w.writerow([safe(v) for v in r])
    return "﻿" + out.getvalue()  # the BOM makes Excel read accented letters correctly


@route(r"/export/([a-z]+)\.csv")
def export(req, name):
    req.require("export")
    stamp = today().isoformat()
    if name == "report":
        farms, fids, code, _ = scope_from_query(req)
        if not all(can(f["role"], "export") for f in farms):
            raise Forbidden()
        start = req.query.get("from") or today().replace(month=1, day=1).isoformat()
        end = req.query.get("to") or stamp
        d = report_data(req, fids, start, end, req.query.get("type", ""))
        cur = country(code)["currency"]
        rows = [("Scope", "; ".join(f["name"] for f in farms)), ("Country", country(code)["name"]), ("From", start), ("To", end),
                ("Active animals", d["total_active"]), ("Born", d["births"]), ("Died", d["deaths"]),
                ("Breeding services", d["breeding"]["services"]), ("Young born alive", d["breeding"]["born_alive"])]
        if all(can(f["role"], "finance") for f in farms):
            rows += [(f"Income ({cur})", d["income"]), (f"Expenses ({cur})", d["expense"]), (f"Profit ({cur})", d["income"] - d["expense"]),
                     (f"Livestock sales ({cur})", d["sales_total"]), (f"Feed cost ({cur})", d["feed_cost"])]
            rows += [(f"{r['kind']}: {r['category']} ({cur})", r["s"]) for r in d["fin_cats"]]
        rows += [(f"Active {r['k']}", r["c"]) for r in d["population"]]
        return Response(to_csv(["Measure", "Value"], rows), "text/csv; charset=utf-8", f"jesse-report-{stamp}.csv")
    if name not in EXPORTS:
        raise NotFound()
    perm, sql = EXPORTS[name]
    if perm:
        req.require(perm)
    cur = req.conn.execute(sql, (req.fid,))
    headers = [c[0] for c in cur.description]
    body = to_csv(headers, cur.fetchall())
    return Response(body, "text/csv; charset=utf-8", f"jesse-{name}-{req.country}-{stamp}.csv")
'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.views.farms
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.views.farms'] = r'''"""Farms: register farms in Zambia or Rwanda, switch between them, edit, manage the team."""
from ..countries import COUNTRIES, country, district_options, valid_location
from ..security import EMAIL_RE, ROLES, PERMISSION_LABELS, PERMISSIONS, hash_password, password_problem
from ..ui import Form, bare_page, badge, card, e, field, layout, post_button, select, table
from ..web import NotFound, Redirect, route

OWNERSHIP = [("individual", "Individual"), ("family", "Family"), ("cooperative", "Cooperative / group"),
             ("company", "Company"), ("government", "Government / institution"), ("other", "Other")]
SCALE = [("small", "Small-scale"), ("medium", "Medium-scale"), ("large", "Large-scale")]


def farm_form_html(req, code, data, errors, editing=False):
    c = country(code)
    loc = f"{data.get('province', '')}|{data.get('district', '')}" if data.get("district") else data.get("location", "")
    return f"""<form method="post">{req.csrf_input()}<input type="hidden" name="country_code" value="{e(code)}">
      <div class="note">Country: <b>{e(c['name'])}</b> · money is recorded in <b>{e(c['currency'])}</b>
      ({e(c['currency_name'])}){'' if editing else ' · <a href="/farms/new">change country</a>'}</div>
      <div class="fgrid">
      {field("name", "Farm name", data.get("name"), errors, required=True, placeholder="e.g. Kafue Valley Farm")}
      {select("location", "District (grouped by province)", district_options(code), loc, errors, blank="— choose district —", groups=True)}
      {field("local_area", c["area_label"], data.get("local_area"), errors, hint=c["area_hint"])}
      {field("address", "Address / directions", data.get("address"), errors)}
      {field("size_ha", "Farm size (hectares)", data.get("size_ha"), errors, type_="number", step="0.01", min="0")}
      {select("farm_scale", "Scale", SCALE, data.get("farm_scale") or "small", errors,
              hint="Rwanda's 2026 law classifies farmers by scale; the criteria come by ministerial order." if code == "RW" else "")}
      {select("ownership", "Ownership", OWNERSHIP, data.get("ownership") or "individual", errors)}
      {field("owner_name", "Registered owner name", data.get("owner_name"), errors)}
      {field("registration_no", "Registration / premises number (optional)", data.get("registration_no"), errors)}
      {field("phone", "Farm phone", data.get("phone"), errors, type_="tel")}
      {field("email", "Farm email", data.get("email"), errors, type_="email")}
      </div><button class="btn block">{'Save farm details' if editing else 'Register farm'}</button></form>"""


def read_farm_form(req, code):
    f = Form(req.form)
    values = {
        "name": f.text("name", True, "Farm name", 150),
        "local_area": f.text("local_area", False, "Area", 150),
        "address": f.text("address", False, "Address", 300),
        "size_ha": f.number("size_ha", False, 0, "Farm size", maximum=10_000_000),
        "farm_scale": f.choice("farm_scale", SCALE, "small"),
        "ownership": f.choice("ownership", OWNERSHIP, "individual"),
        "owner_name": f.text("owner_name", False, "Owner name", 150),
        "registration_no": f.text("registration_no", False, "Registration number", 60),
        "phone": f.text("phone", False, "Phone", 30),
        "email": f.text("email", False, "Email", 254),
    }
    province, _, district = (req.form.get("location") or "").partition("|")
    if not valid_location(code, province, district):
        f.errors["location"] = "Choose the district where the farm is."
    values["province"], values["district"] = province, district
    if values["email"] and not EMAIL_RE.match(values["email"]):
        f.errors["email"] = "Enter a valid email address."
    return f, values


@route("/farms/new", ("GET", "POST"), needs_farm=False)
def farm_new(req):
    code = req.form.get("country_code") or req.query.get("country")
    if code not in COUNTRIES:
        cards = "".join(
            f"""<a class="stat" href="/farms/new?country={c['code']}" style="padding:22px">
                <div class="n">{e(c['name'])}</div><div class="muted">Money in {e(c['currency'])} · {len(c['provinces'])}
                provinces, {sum(len(v) for v in c['provinces'].values())} districts</div></a>"""
            for c in COUNTRIES.values())
        welcome = req.query.get("welcome")
        intro = ("<p>Welcome! Start by registering your farm. Choose the country it is in — this sets the currency, "
                 "the district list and the country-specific rules.</p>") if welcome else "<p>Which country is the farm in?</p>"
        body = f'{intro}<div class="stats">{cards}</div>'
        if req.farm:
            return layout(req, "Register a farm", body, "farms")
        return bare_page("Register a farm", f'<div class="auth" style="max-width:640px"><div class="card"><h1>Register your farm</h1>{body}</div>'
                         f'{post_button(req, "/logout", "Sign out", "btn sec small")}</div>', req)
    data, errors = req.form, {}
    if req.method == "POST":
        f, values = read_farm_form(req, code)
        errors = f.errors
        if f.ok:
            with req.conn:
                fid = req.conn.execute(
                    """INSERT INTO farms (name, country_code, country, province, district, local_area, address, size_ha,
                       farm_scale, ownership, owner_name, registration_no, phone, email)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (values["name"], code, country(code)["name"], values["province"], values["district"],
                     values["local_area"], values["address"], values["size_ha"], values["farm_scale"],
                     values["ownership"], values["owner_name"] or f"{req.user['first_name']} {req.user['last_name']}".strip(),
                     values["registration_no"], values["phone"], values["email"])).lastrowid
                req.conn.execute("INSERT INTO memberships (user_id, farm_id, role) VALUES (?,?,'owner')", (req.user["id"], fid))
            req.switch_farm(fid)
            req.flash(f"{values['name']} registered in {country(code)['name']}. Records and money for this farm are kept separate.")
            raise Redirect("/")
    form = farm_form_html(req, code, data, errors)
    if req.farm:
        return layout(req, "Register a farm", card(form), "farms")
    return bare_page("Register a farm", f'<div class="auth" style="max-width:720px"><div class="card"><h1>Register your farm</h1>{form}</div></div>', req)


@route("/farms/switch", ("POST",), needs_farm=False)
def farm_switch(req):
    fid = req.form.get("farm_id", "")
    if not fid.isdigit() or not req.switch_farm(int(fid)):
        raise NotFound()
    req.flash(f"Now working on {req.farm['name']}.")
    raise Redirect("/")


@route("/farms")
def farms_list(req):
    rows = []
    for f in req.my_farms():
        c = country(f["country_code"])
        n = req.one("SELECT COUNT(*) c FROM livestock WHERE farm_id=? AND status='active'", (f["id"],))["c"]
        current = badge("current", "green") if f["id"] == req.fid else post_button(req, "/farms/switch", "Open", "btn small sec", hidden={"farm_id": f["id"]})
        rows.append([f"<b>{e(f['name'])}</b>", e(c["name"]), e(f"{f['district']}, {f['province']}" if f["district"] else "not set"),
                     e(c["currency"]), str(n), e(dict(ROLES).get(f["role"], f["role"])), current])
    body = card(table(["Farm", "Country", "District", "Currency", "Active animals", "Your role", ""], rows, numeric=(4,)))
    body += '<p class="muted">Each farm keeps its own animals, records and money. A Zambian farm reports in ZMW and a ' \
            'Rwandan farm in RWF; the system never converts between them.</p>'
    c = country(req.country)
    rules = "".join(f'<li><a href="{e(url)}" target="_blank" rel="noopener">{e(name)}</a> — {e(text)}</li>' for name, text, url in c["rules"])
    body += card(f"<ul>{rules}</ul><p class='muted'>Summaries for orientation only, not legal advice. Check the current "
                 f"rules with your veterinary office.</p>", f"Rules that apply to farms in {c['name']}")
    actions = '<a class="btn" href="/farms/new">+ Register another farm</a>'
    if req.can("manage_farm"):
        actions += ' <a class="btn sec" href="/farms/edit">Edit this farm</a> <a class="btn sec" href="/farms/team">Team</a>'
    return layout(req, "My farms", body, "farms", actions=actions)


@route("/farms/edit", ("GET", "POST"))
def farm_edit(req):
    req.require("manage_farm")
    code = req.country
    data, errors = dict(req.farm), {}
    if req.method == "POST":
        data = req.form
        f, values = read_farm_form(req, code)
        errors = f.errors
        if f.ok:
            cols = list(values)
            req.run(f"UPDATE farms SET {', '.join(c + '=?' for c in cols)} WHERE id=?", [values[c] for c in cols] + [req.fid])
            req.flash("Farm details saved.")
            raise Redirect("/farms")
    body = card(farm_form_html(req, code, data, errors, editing=True))
    body += card("<p>Deleting a farm removes all its animals, records and money permanently. Make a backup first "
                 "(Settings → Backup).</p>" + post_button(req, "/farms/delete", "Delete this farm",
                 confirm="Delete this farm and ALL its records permanently?"), "Danger zone")
    return layout(req, "Edit farm", body, "farms")


@route("/farms/delete", ("POST",))
def farm_delete(req):
    req.require("manage_farm")
    name = req.farm["name"]
    req.run("DELETE FROM farms WHERE id=?", (req.fid,))  # cascades to every record of the farm
    req.run("UPDATE sessions SET farm_id=NULL WHERE token=?", (req.session["token"],))
    req.flash(f"{name} deleted.")
    raise Redirect("/farms/new")


@route("/farms/team", ("GET", "POST"))
def farm_team(req):
    req.require("manage_farm")
    f = Form(req.form)
    if req.method == "POST":
        email = f.text("email", True, "Email", 254).lower()
        role = f.choice("role", ROLES[1:])
        existing = req.one("SELECT * FROM users WHERE email=?", (email,)) if email else None
        if existing:
            if req.one("SELECT 1 FROM memberships WHERE user_id=? AND farm_id=?", (existing["id"], req.fid)):
                f.errors["email"] = "This person is already on the farm."
            elif f.ok:
                req.run("INSERT INTO memberships (user_id, farm_id, role) VALUES (?,?,?)", (existing["id"], req.fid, role))
                req.flash(f"{existing['first_name']} added as {dict(ROLES)[role]}. They will see this farm in their farm list.")
                raise Redirect("/farms/team")
        else:
            first = f.text("first_name", True, "First name", 150)
            last = f.text("last_name", False, "Last name", 150)
            password = req.form.get("password", "")
            if email and not EMAIL_RE.match(email):
                f.errors["email"] = "Enter a valid email address."
            if password_problem(password):
                f.errors["password"] = password_problem(password) + " (needed to create their account)"
            if f.ok:
                with req.conn:
                    uid = req.conn.execute("INSERT INTO users (email, first_name, last_name, role, password_hash) VALUES (?,?,?,?,?)",
                                           (email, first, last, role, hash_password(password))).lastrowid
                    req.conn.execute("INSERT INTO memberships (user_id, farm_id, role) VALUES (?,?,?)", (uid, req.fid, role))
                req.flash(f"Account created for {first}. They sign in with {email} and the password you set.")
                raise Redirect("/farms/team")
    members = req.all("""SELECT u.*, m.role farm_role, m.id mid FROM users u JOIN memberships m ON m.user_id=u.id
                         WHERE m.farm_id=? ORDER BY m.role='owner' DESC, u.first_name""", (req.fid,))
    rows = []
    for m in members:
        action = "" if m["id"] == req.user["id"] else post_button(
            req, f"/farms/team/{m['mid']}/remove", "Remove", "btn small danger", confirm=f"Remove {m['first_name']} from this farm?")
        rows.append([f"{e(m['first_name'])} {e(m['last_name'])}", e(m["email"]), e(dict(ROLES).get(m["farm_role"])), action])
    body = card(table(["Name", "Email", "Role on this farm", ""], rows))
    d, er = req.form, f.errors
    body += card(f"""<form method="post">{req.csrf_input()}<div class="fgrid">
        {field("email", "Email", d.get("email"), er, type_="email", required=True, hint="If they already have an account, only email and role are needed")}
        {select("role", "Role", ROLES[1:], d.get("role", "worker"), er)}
        {field("first_name", "First name (new accounts)", d.get("first_name"), er)}
        {field("last_name", "Last name (new accounts)", d.get("last_name"), er)}
        {field("password", "Temporary password (new accounts)", "", er, type_="password")}</div>
        <button class="btn">Add to farm</button></form>""", "Add a person")
    perm_rows = [[e(label_)] + [("✔" if p in PERMISSIONS[r] else "—") for r, _ in ROLES] for p, label_ in PERMISSION_LABELS.items()]
    body += card(table(["Permission"] + [n for _, n in ROLES], perm_rows) +
                 "<p class='muted'>Everyone on a farm can view its animal, health, breeding, feeding, stock and task records.</p>",
                 "What each role can do")
    return layout(req, "Farm team", body, "farms")


@route(r"/farms/team/(\d+)/remove", ("POST",))
def farm_team_remove(req, mid):
    req.require("manage_farm")
    m = req.one("SELECT * FROM memberships WHERE id=? AND farm_id=? AND user_id!=?", (mid, req.fid, req.user["id"]))
    if not m:
        raise NotFound()
    req.run("DELETE FROM memberships WHERE id=?", (m["id"],))
    req.flash("Removed from this farm. Their account still exists for other farms.")
    raise Redirect("/farms/team")

'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.views.feeding
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.views.feeding'] = r'''"""Feeding and nutrition: daily feeding, feed consumption and feeding cost."""
import datetime as dt

from ..countries import country
from ..ui import (Form, card, e, empty, field, fmt_date, fmt_num, hbars, label, layout, money, post_button, select,
                  stat, table, textarea, today)
from ..web import NotFound, Redirect, route
from .common import ANIMAL_TYPES, animal_name, animal_options


def get_feeding(req, rid):
    r = req.one("SELECT * FROM feeding_records WHERE id=? AND farm_id=?", (rid, req.fid))
    if not r:
        raise NotFound()
    return r


@route("/feeding")
def feeding_list(req):
    code = req.country
    t = today()
    start = req.query.get("from") or (t - dt.timedelta(days=30)).isoformat()
    end = req.query.get("to") or t.isoformat()
    species = req.query.get("type", "")
    sql = """SELECT r.*, l.name lname, l.tag_number ltag FROM feeding_records r LEFT JOIN livestock l ON l.id=r.livestock_id
             WHERE r.farm_id=? AND r.date BETWEEN ? AND ?"""
    params = [req.fid, start, end]
    if species in dict(ANIMAL_TYPES):
        sql += " AND (r.animal_type=? OR l.animal_type=?)"
        params += [species, species]
    rows = req.all(sql + " ORDER BY r.date DESC, r.id DESC", params)
    fin = req.can("finance")
    total_cost = sum(r["cost"] for r in rows)
    by_feed = {}
    for r in rows:
        key = f"{r['feed_name']} ({r['unit']})"
        by_feed[key] = by_feed.get(key, 0) + r["quantity"]
    days = max((dt.date.fromisoformat(end) - dt.date.fromisoformat(start)).days + 1, 1)
    body = f"""<form class="filters noprint" method="get">
        {field("from", "From", start, type_="date")}{field("to", "To", end, type_="date")}
        {select("type", "Species", ANIMAL_TYPES, species, blank="All species")}<button class="btn">Show</button></form>"""
    body += '<div class="stats">' + stat(len(rows), "Feedings recorded")
    if fin:
        body += stat(money(total_cost, code), "Feed cost in period") + stat(money(total_cost / days, code), "Average feed cost per day")
    body += "</div>"
    trs = [[fmt_date(r["date"], code), e(r["feed_name"]), f'{fmt_num(r["quantity"])} {e(r["unit"])}',
            e(animal_name({"name": r["lname"], "tag_number": r["ltag"], "id": r["livestock_id"]}) if r["livestock_id"]
              else f"{label(ANIMAL_TYPES, r['animal_type']) or 'All animals'} × {r['animal_count']}")]
           + ([money(r["cost"], code)] if fin else [])
           + [post_button(req, f"/feeding/{r['id']}/delete", "Delete", "btn small danger", confirm="Delete this feeding? Stock is put back.") if req.can("delete") else ""]
           for r in rows]
    body += '<div class="grid g2">' + card(hbars(sorted(by_feed.items(), key=lambda x: -x[1])), "Feed used in this period")
    body += card("<p class='muted'>Record each feeding (or one record per day per group). If the feed comes from "
                 "your stock, the stock goes down automatically and the cost is worked out from the product price.</p>",
                 "How feeding records work") + "</div>"
    body += card(table(["Date", "Feed", "Quantity", "Fed to"] + (["Cost"] if fin else []) + [""], trs, numeric=(2, 4) if fin else (2,))
                 or empty("No feeding recorded in this period"), "Feeding records")
    actions = '<a class="btn" href="/feeding/new">+ Record feeding</a>' if req.can("feeding") else ""
    if req.can("export"):
        actions += ' <a class="btn sec" href="/export/feeding.csv">Export CSV</a>'
    return layout(req, "Feeding & nutrition", body, "feeding", actions=actions)


@route("/feeding/new", ("GET", "POST"))
def feeding_new(req):
    req.require("feeding")
    code = req.country
    feeds = req.all("SELECT * FROM products WHERE farm_id=? AND kind='feed' ORDER BY name", (req.fid,))
    data = {"date": today().isoformat(), "animal_count": "1", "unit": "kg"} if req.method == "GET" else req.form
    f = Form(req.form)
    if req.method == "POST":
        pid = f.id("product_id")
        product = req.one("SELECT * FROM products WHERE id=? AND farm_id=?", (pid, req.fid)) if pid else None
        v = {
            "date": f.date("date", True, not_future=True),
            "feed_name": product["name"] if product else f.text("feed_name", True, "Feed name", 150),
            "quantity": f.number("quantity", True, 0.0001, "Quantity"),
            "unit": product["unit"] if product else (f.text("unit", True, "Unit", 20) or "kg"),
            "animal_type": "",
            "livestock_id": None,
            "animal_count": f.integer("animal_count", False, 1, "Number of animals", 1) or 1,
            "notes": f.text("notes", False, "Notes", 500),
        }
        target = req.form.get("target", "")
        if target.startswith("type:") and target[5:] in dict(ANIMAL_TYPES):
            v["animal_type"] = target[5:]
        elif target.startswith("animal:") and target[7:].isdigit():
            a = req.one("SELECT * FROM livestock WHERE id=? AND farm_id=?", (int(target[7:]), req.fid))
            if a:
                v["livestock_id"], v["animal_type"], v["animal_count"] = a["id"], a["animal_type"], 1
        elif target != "all":
            f.errors["target"] = "Choose which animals were fed."
        if product and v["quantity"] and v["quantity"] > product["quantity"] + 1e-6:
            f.errors["quantity"] = f"Only {fmt_num(product['quantity'])} {product['unit']} of {product['name']} in stock."
        manual_cost = f.number("cost", False, 0, "Cost", 0) or 0
        if f.ok:
            v["cost"] = round(v["quantity"] * product["unit_price"], 2) if product else manual_cost
            v["product_id"] = product["id"] if product else None
            cols = list(v)
            with req.conn:
                rid = req.conn.execute(f"INSERT INTO feeding_records (farm_id, created_by, {', '.join(cols)}) VALUES (?, ?{', ?' * len(cols)})",
                                       [req.fid, req.user["id"]] + [v[c] for c in cols]).lastrowid
                if product:
                    cur = req.conn.execute("UPDATE products SET quantity = quantity - ? WHERE id=? AND quantity - ? >= -0.000001",
                                           (v["quantity"], product["id"], v["quantity"]))
                    if cur.rowcount == 0:
                        raise ValueError("Stock changed while saving")  # rolls back the whole feeding record
                    req.conn.execute("INSERT INTO stock_movements (product_id, change, reason, user_id) VALUES (?,?,?,?)",
                                     (product["id"], -v["quantity"], f"Feeding record #{rid}", req.user["id"]))
            req.flash("Feeding recorded." + (" Stock updated." if product else ""))
            raise Redirect("/feeding")
    er = f.errors
    targets = [("all", "All animals", "Groups")] + [(f"type:{k}", f"All {n.lower()}", "Groups") for k, n in ANIMAL_TYPES]
    targets += [(f"animal:{o[0]}", o[1], f"One animal — {o[2]}") for o in animal_options(req)]
    feed_opts = [(p["id"], f"{p['name']} — {fmt_num(p['quantity'])} {p['unit']} in stock") for p in feeds]
    form = f"""<form method="post">{req.csrf_input()}<div class="fgrid">
      {field("date", "Date", data.get("date"), er, type_="date", required=True, max=today().isoformat())}
      {select("target", "Fed to", targets, data.get("target", "all"), er, groups=True)}
      {select("product_id", "Feed from stock", feed_opts, data.get("product_id"), er, blank="— not from stock (type the name below) —",
              hint="Feed products are added under Inventory with kind 'Feed'")}
      {field("feed_name", "Feed name (if not from stock)", data.get("feed_name"), er, placeholder="e.g. Napier grass, maize bran")}
      {field("quantity", "Quantity given", data.get("quantity"), er, type_="number", step="any", min="0.0001", required=True)}
      {field("unit", "Unit (if not from stock)", data.get("unit"), er)}
      {field("animal_count", "Number of animals fed", data.get("animal_count"), er, type_="number", min="1", step="1")}
      {field("cost", f"Cost ({country(code)['currency']}) — only if not from stock", data.get("cost"), er, type_="number", step="any", min="0")}
      </div>{textarea("notes", "Notes", data.get("notes"), er)}<button class="btn block">Save feeding</button></form>"""
    return layout(req, "Record feeding", card(form), "feeding")


@route(r"/feeding/(\d+)/delete", ("POST",))
def feeding_delete(req, rid):
    req.require("delete")
    r = get_feeding(req, rid)
    with req.conn:
        if r["product_id"] and req.conn.execute("SELECT 1 FROM products WHERE id=? AND farm_id=?", (r["product_id"], req.fid)).fetchone():
            req.conn.execute("UPDATE products SET quantity = quantity + ? WHERE id=?", (r["quantity"], r["product_id"]))
            req.conn.execute("INSERT INTO stock_movements (product_id, change, reason, user_id) VALUES (?,?,?,?)",
                             (r["product_id"], r["quantity"], f"Feeding record #{r['id']} deleted", req.user["id"]))
        req.conn.execute("DELETE FROM feeding_records WHERE id=?", (r["id"],))
    req.flash("Feeding record deleted and stock put back.")
    raise Redirect("/feeding")
'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.views.finance
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.views.finance'] = r'''"""
Finance: income, expenses, profit and loss.

All money for a farm is in that farm's currency (ZMW for Zambia, RWF for Rwanda). The system never
converts between currencies and never adds a Zambian farm's money to a Rwandan farm's money.

Sales, animal purchases, veterinary costs and stock purchases are posted to the ledger automatically
(source_type/source_id); those rows are changed from the record they came from, not here.
"""
from ..countries import country
from ..ui import (Form, card, chips, e, empty, field, fmt_date, label, layout, money, month_label, months_back,
                  pair_chart, post_button, select, stat, table, today)
from ..web import NotFound, Redirect, route
from .common import ALL_CATEGORIES, EXPENSE_CATEGORIES, INCOME_CATEGORIES

SOURCE_LINKS = {"sale": ("Livestock sale", "/sales/{}"), "animal_purchase": ("Animal purchase", "/animals/{}"),
                "health": ("Health record", "/health/{}/edit"), "stock": ("Stock purchase", None)}


def period_from_query(req):
    t = today()
    p = req.query.get("period", "year")
    if p == "month":
        return p, t.replace(day=1).isoformat(), t.isoformat()
    if p == "custom":
        start = req.query.get("from") or t.replace(month=1, day=1).isoformat()
        end = req.query.get("to") or t.isoformat()
        return p, start, end
    if p == "all":
        return p, "0000-01-01", "9999-12-31"
    return "year", t.replace(month=1, day=1).isoformat(), t.isoformat()


def totals(req, fid, start, end):
    rows = req.all("""SELECT kind, category, SUM(amount) s, COUNT(*) n FROM transactions
                      WHERE farm_id=? AND date BETWEEN ? AND ? GROUP BY kind, category ORDER BY s DESC""", (fid, start, end))
    inc = sum(r["s"] for r in rows if r["kind"] == "income")
    exp = sum(r["s"] for r in rows if r["kind"] == "expense")
    return rows, inc, exp


@route("/finance")
def finance_home(req):
    req.require("finance")
    code = req.country
    period, start, end = period_from_query(req)
    kind = req.query.get("kind", "")
    rows, inc, exp = totals(req, req.fid, start, end)
    body = chips("/finance", "period", [("month", "This month"), ("year", "This year"), ("all", "All time"), ("custom", "Custom dates")], period)
    if period == "custom":
        body += f"""<form class="filters noprint" method="get"><input type="hidden" name="period" value="custom">
            {field("from", "From", start, type_="date")}{field("to", "To", end, type_="date")}<button class="btn">Show</button></form>"""
    profit = inc - exp
    body += '<div class="stats">' + stat(money(inc, code), "Income", tone="good") + stat(money(exp, code), "Expenses", tone="bad")
    body += stat(money(profit, code), "Profit" if profit >= 0 else "Loss", tone="good" if profit >= 0 else "bad")
    margin = f"{profit / inc * 100:.0f}%" if inc else "—"
    body += stat(margin, "Profit margin") + "</div>"
    inc_rows = [[e(label(ALL_CATEGORIES, r["category"])), str(r["n"]), money(r["s"], code)] for r in rows if r["kind"] == "income"]
    exp_rows = [[e(label(ALL_CATEGORIES, r["category"])), str(r["n"]), money(r["s"], code)] for r in rows if r["kind"] == "expense"]
    body += '<div class="grid g2">' + card(table(["Income from", "Entries", "Amount"], inc_rows, numeric=(1, 2)) or empty("No income in this period"), "Income by category")
    body += card(table(["Spent on", "Entries", "Amount"], exp_rows, numeric=(1, 2)) or empty("No expenses in this period"), "Expenses by category") + "</div>"
    months = months_back(12)
    mrows = req.all("""SELECT substr(date,1,7) m, kind, SUM(amount) s FROM transactions WHERE farm_id=? AND date >= ?
                       GROUP BY m, kind""", (req.fid, months[0] + "-01"))
    series = {m: [0, 0] for m in months}
    for r in mrows:
        if r["m"] in series:
            series[r["m"]][0 if r["kind"] == "income" else 1] = r["s"]
    body += card(pair_chart([(month_label(m), a, b) for m, (a, b) in series.items()], fmt=lambda v: money(v, code, False)),
                 f"Income and expenses by month, last 12 months ({country(code)['currency']})")
    sql = "SELECT * FROM transactions WHERE farm_id=? AND date BETWEEN ? AND ?"
    params = [req.fid, start, end]
    if kind in ("income", "expense"):
        sql += " AND kind=?"
        params.append(kind)
    tx = req.all(sql + " ORDER BY date DESC, id DESC LIMIT 300", params)
    trs = []
    for r in tx:
        src = ""
        if r["source_type"] in SOURCE_LINKS:
            name, url = SOURCE_LINKS[r["source_type"]]
            src = f'<a href="{url.format(r["source_id"])}">{name}</a>' if url else name
        elif req.can("finance"):
            src = f'<a href="/finance/{r["id"]}/edit">Edit</a>'
        amount = f'<span class="{"plus" if r["kind"] == "income" else "minus"}">{"+" if r["kind"] == "income" else "−"}{money(r["amount"], code)}</span>'
        trs.append([fmt_date(r["date"], code), e(label(ALL_CATEGORIES, r["category"])), e(r["description"]), e(r["party"] or ""), amount, src])
    body += chips("/finance", "kind", [("", "All entries"), ("income", "Income"), ("expense", "Expenses")], kind,
                  {"period": period, "from": req.query.get("from", ""), "to": req.query.get("to", "")})
    body += card(table(["Date", "Category", "Description", "Paid by / to", "Amount", "Source"], trs, numeric=(4,))
                 or empty("No entries", "Record income such as milk sales, or expenses such as labour and transport."), "Ledger")
    body += f'<p class="muted">All amounts in {e(country(code)["currency_name"])} ({e(country(code)["currency"])}). Entries marked with a source were added automatically from sales, purchases, health records and stock purchases.</p>'
    actions = ('<a class="btn" href="/finance/new?kind=income">+ Income</a> <a class="btn" href="/finance/new?kind=expense">+ Expense</a> '
               '<a class="btn sec" href="/finance/pnl">Profit & loss</a>')
    if req.can("export"):
        actions += ' <a class="btn sec" href="/export/transactions.csv">Export CSV</a>'
    return layout(req, "Finance", body, "finance", actions=actions)


def tx_form(req, tx=None):
    code = req.country
    kind = (tx["kind"] if tx else req.query.get("kind") or req.form.get("kind") or "expense")
    if kind not in ("income", "expense"):
        kind = "expense"
    cats = INCOME_CATEGORIES if kind == "income" else EXPENSE_CATEGORIES
    data = (dict(tx) if tx else {"date": today().isoformat(), "category": cats[0][0]}) if req.method == "GET" else req.form
    f = Form(req.form)
    if req.method == "POST":
        v = {
            "kind": kind,
            "date": f.date("date", True, not_future=True),
            "category": f.choice("category", cats),
            "amount": f.number("amount", True, 0.01, "Amount"),
            "description": f.text("description", True, "Description", 300),
            "party": f.text("party", False, "Paid by / to", 150),
        }
        if f.ok:
            v["amount"] = round(v["amount"], country(code)["decimals"])
            cols = list(v)
            if tx:
                req.run(f"UPDATE transactions SET {', '.join(c + '=?' for c in cols)} WHERE id=? AND farm_id=?",
                        [v[c] for c in cols] + [tx["id"], req.fid])
            else:
                req.run(f"INSERT INTO transactions (farm_id, created_by, {', '.join(cols)}) VALUES (?, ?{', ?' * len(cols)})",
                        [req.fid, req.user["id"]] + [v[c] for c in cols])
            req.flash("Saved.")
            raise Redirect("/finance")
    er = f.errors
    c = country(code)
    form = f"""<form method="post">{req.csrf_input()}<input type="hidden" name="kind" value="{kind}"><div class="fgrid">
      {field("date", "Date", data.get("date"), er, type_="date", required=True, max=today().isoformat())}
      {select("category", "Category", cats, data.get("category"), er)}
      {field("amount", f"Amount ({c['currency']})", data.get("amount"), er, type_="number", step="any", min="0.01", required=True,
             hint="Rwandan francs have no decimals" if c["decimals"] == 0 else "")}
      {field("party", "Paid by" if kind == "income" else "Paid to", data.get("party"), er)}</div>
      {field("description", "Description", data.get("description"), er, required=True,
             placeholder="e.g. Milk sold to dairy co-operative, March" if kind == "income" else "e.g. Herdsman wages, March")}
      <button class="btn block">Save</button></form>"""
    body = card(form)
    if tx and req.can("delete"):
        body += post_button(req, f"/finance/{tx['id']}/delete", "Delete entry", confirm="Delete this entry?")
    title = ("Edit " if tx else "Record ") + ("income" if kind == "income" else "expense")
    return layout(req, title, body, "finance")


@route("/finance/new", ("GET", "POST"))
def tx_new(req):
    req.require("finance")
    return tx_form(req)


def get_manual_tx(req, tid):
    tx = req.one("SELECT * FROM transactions WHERE id=? AND farm_id=?", (tid, req.fid))
    if not tx:
        raise NotFound()
    if tx["source_type"]:
        req.flash("This entry was created from another record. Change or delete that record instead.", bad=True)
        raise Redirect("/finance")
    return tx


@route(r"/finance/(\d+)/edit", ("GET", "POST"))
def tx_edit(req, tid):
    req.require("finance")
    return tx_form(req, get_manual_tx(req, tid))


@route(r"/finance/(\d+)/delete", ("POST",))
def tx_delete(req, tid):
    req.require("finance")
    req.require("delete")
    tx = get_manual_tx(req, tid)
    req.run("DELETE FROM transactions WHERE id=?", (tx["id"],))
    req.flash("Entry deleted.")
    raise Redirect("/finance")


def pnl_table(req, fid, code, year):
    """Monthly profit and loss table for one farm and year."""
    months = [f"{year}-{m:02d}" for m in range(1, 13)]
    rows = req.all("""SELECT substr(date,1,7) m, kind, category, SUM(amount) s FROM transactions
                      WHERE farm_id=? AND substr(date,1,4)=? GROUP BY m, kind, category""", (fid, str(year)))
    grid = {}
    for r in rows:
        grid.setdefault((r["kind"], r["category"]), {})[r["m"]] = r["s"]

    def line(name, values, strong=False):
        cells = [money(v, code, False) if v else "–" for v in values] + [money(sum(values), code, False)]
        return [f"<b>{e(name)}</b>" if strong else e(name)] + [f"<b>{c}</b>" if strong else c for c in cells]

    out, inc_tot, exp_tot = [], [0] * 12, [0] * 12
    for kind, cats, tot in (("income", INCOME_CATEGORIES, inc_tot), ("expense", EXPENSE_CATEGORIES, exp_tot)):
        for key, name in cats:
            vals = [grid.get((kind, key), {}).get(m, 0) for m in months]
            if any(vals):
                out.append(line(name, vals))
                for i, v in enumerate(vals):
                    tot[i] += v
        out.append(line("Total income" if kind == "income" else "Total expenses", tot, True))
    out.append(line("Profit / loss", [a - b for a, b in zip(inc_tot, exp_tot)], True))
    head = ["Line"] + [month_label(m) for m in months] + ["Year"]
    return table(head, out, numeric=tuple(range(1, 14))), sum(inc_tot), sum(exp_tot)


@route("/finance/pnl")
def pnl(req):
    req.require("finance")
    code = req.country
    year = req.query.get("year", str(today().year))
    year = int(year) if year.isdigit() and 1990 <= int(year) <= 2100 else today().year
    years = sorted({int(r["y"]) for r in req.all("SELECT DISTINCT substr(date,1,4) y FROM transactions WHERE farm_id=?", (req.fid,))} | {today().year})
    tbl, inc, exp = pnl_table(req, req.fid, code, year)
    body = chips("/finance/pnl", "year", [(str(y), str(y)) for y in reversed(years)], str(year))
    body += '<div class="stats">' + stat(money(inc, code), f"Income {year}", tone="good") + stat(money(exp, code), f"Expenses {year}", tone="bad")
    body += stat(money(inc - exp, code), f"Profit {year}" if inc >= exp else f"Loss {year}", tone="good" if inc >= exp else "bad") + "</div>"
    body += card(tbl, f"Profit and loss {year} — {req.farm['name']} ({country(code)['currency']})")
    body += "<p class='muted'>Cash basis: income and costs are counted on the date money was received or paid. Use Print to save as PDF.</p>"
    return layout(req, "Profit & loss", body, "finance", actions='<button class="btn sec" onclick="window.print()">Print</button>')
'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.views.health
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.views.health'] = r'''"""Animal health: vaccinations, treatments, vet visits, diseases, reminders and costs."""

from ..countries import COMMON_DISEASES, country, is_notifiable
from ..ui import (Form, badge, card, chips, datalist, e, empty, field, fmt_date, label, layout, money, post_button,
                  select, table, textarea, today)
from ..web import NotFound, Redirect, route
from .common import ANIMAL_TYPES, HEALTH_TYPES, animal_name, animal_options, link_transaction, unlink_transaction


def get_record(req, record_id):
    r = req.one("""SELECT h.* FROM health_records h JOIN livestock l ON l.id=h.livestock_id
                   WHERE h.id=? AND l.farm_id=?""", (record_id, req.fid))
    if not r:
        raise NotFound()
    return r


@route("/health")
def health_list(req):
    code = req.country
    show = req.query.get("show", "upcoming")
    kind = req.query.get("type", "")
    t = today().isoformat()
    base = """SELECT h.*, l.name, l.tag_number, l.animal_type, l.id lid FROM health_records h
              JOIN livestock l ON l.id=h.livestock_id WHERE l.farm_id=?"""
    params = [req.fid]
    if kind in dict(HEALTH_TYPES):
        base += " AND h.record_type=?"
        params.append(kind)
    if show == "upcoming":
        rows = req.all(base + " AND l.status='active' AND h.next_due_date >= ? ORDER BY h.next_due_date", params + [t])
    elif show == "overdue":
        rows = req.all(base + " AND l.status='active' AND h.next_due_date < ? ORDER BY h.next_due_date DESC", params + [t])
    elif show == "notifiable":
        rows = req.all(base + " AND h.notifiable=1 ORDER BY h.date DESC", params)
    else:
        show = "all"
        rows = req.all(base + " ORDER BY h.date DESC, h.id DESC LIMIT 500", params)
    body = chips("/health", "show", [("upcoming", "Upcoming"), ("overdue", "Past due"), ("all", "All records"),
                                     ("notifiable", "Notifiable diseases")], show, {"type": kind})
    body += chips("/health", "type", [("", "All types")] + HEALTH_TYPES, kind, {"show": show})
    if show == "overdue":
        body += '<div class="note">These follow-ups are past their due date. Record the new treatment, or edit the old record to clear its next due date.</div>'
    fin = req.can("finance")
    trs = []
    for h in rows:
        due = ""
        if h["next_due_date"]:
            due = badge(fmt_date(h["next_due_date"], code), "red" if h["next_due_date"] < t else "yellow")
        trs.append([fmt_date(h["date"], code), f'<a href="/animals/{h["lid"]}">{e(animal_name(h))}</a>',
                    f'<a href="/health/{h["id"]}/edit">{e(h["title"])}</a>' + (f' {badge("notifiable", "red")}' if h["notifiable"] else ""),
                    e(label(HEALTH_TYPES, h["record_type"])), e(h["disease"] or "—"), due or "—"]
                   + ([money(h["cost"], code)] if fin else []))
    body += card(table(["Date", "Animal", "Record", "Type", "Disease", "Next due"] + (["Cost"] if fin else []), trs, numeric=(6,))
                 or empty("Nothing here", "Record vaccinations and treatments. Add a next due date to get reminders on the dashboard."))
    actions = '<a class="btn" href="/health/new">+ Health record</a>' if req.can("health") else ""
    if req.can("export"):
        actions += ' <a class="btn sec" href="/export/health.csv">Export CSV</a>'
    return layout(req, "Animal health", body, "health", actions=actions)


def health_form(req, record=None):
    code = req.country
    c = country(code)
    if req.method == "GET":
        data = dict(record) if record else {"date": today().isoformat(), "record_type": "vaccination",
                                            "livestock_id": req.query.get("animal", ""), "scope": "one"}
    else:
        data = req.form
    f = Form(req.form)
    if req.method == "POST":
        scope = req.form.get("scope", "one") if not record else "one"
        values = {
            "record_type": f.choice("record_type", HEALTH_TYPES),
            "title": f.text("title", True, "Title", 150),
            "disease": f.text("disease", False, "Disease", 150),
            "date": f.date("date", True, not_future=True),
            "next_due_date": f.date("next_due_date", False, "Next due date"),
            "withdrawal_until": f.date("withdrawal_until", False, "Withdrawal date"),
            "diagnosis": f.text("diagnosis", False, "Diagnosis", 2000),
            "treatment": f.text("treatment", False, "Treatment", 2000),
            "vet_name": f.text("vet_name", False, "Vet name", 100),
            "cost": f.number("cost", False, 0, "Cost", 0) or 0,
        }
        if values["next_due_date"] and values["date"] and values["next_due_date"] <= values["date"]:
            f.errors["next_due_date"] = "The next due date must be after the record date."
        if values["withdrawal_until"] and values["date"] and values["withdrawal_until"] < values["date"]:
            f.errors["withdrawal_until"] = "Withdrawal must end on or after the treatment date."
        if scope == "species":
            species = f.choice("species", ANIMAL_TYPES)
            targets = [r["id"] for r in req.all("SELECT id FROM livestock WHERE farm_id=? AND status='active' AND animal_type=?",
                                                (req.fid, species))] if species else []
            if not targets and "species" not in f.errors:
                f.errors["species"] = "There are no active animals of that species."
        else:
            aid = f.id("livestock_id")
            ok = aid and req.one("SELECT 1 FROM livestock WHERE id=? AND farm_id=?", (aid, req.fid))
            if not ok:
                f.errors["livestock_id"] = "Choose an animal."
            targets = [aid] if ok else []
        if f.ok:
            values["notifiable"] = 1 if is_notifiable(code, values["disease"]) else 0
            cols = list(values)
            with req.conn:
                ids = []
                for aid in targets:
                    if record:
                        req.conn.execute(f"UPDATE health_records SET livestock_id=?, {', '.join(k + '=?' for k in cols)} WHERE id=?",
                                         [aid] + [values[k] for k in cols] + [record["id"]])
                        rid = record["id"]
                    else:
                        rid = req.conn.execute(
                            f"INSERT INTO health_records (livestock_id, created_by, {', '.join(cols)}) VALUES (?, ?{', ?' * len(cols)})",
                            [aid, req.user["id"]] + [values[k] for k in cols]).lastrowid
                    ids.append(rid)
                    link_transaction(req, "health", rid, "expense", "veterinary", values["cost"], values["date"],
                                     f"{label(HEALTH_TYPES, values['record_type'])}: {values['title']}", values["vet_name"])
            msg = f"Health record saved for {len(ids)} animal(s)."
            if values["notifiable"]:
                msg += " " + c["notifiable_note"]
                req.flash(msg, bad=True)
            else:
                req.flash(msg)
            raise Redirect(f"/animals/{targets[0]}" if len(targets) == 1 else "/health?show=all")
    er = f.errors
    keep = record["livestock_id"] if record else None
    diseases = sorted(set(COMMON_DISEASES + c["notifiable"]))
    scope_html = "" if record else f"""{select("scope", "Apply to", [("one", "One animal"), ("species", "All active animals of a species (e.g. herd vaccination)")], data.get("scope", "one"), er)}
        {select("species", "Species (when applying to all)", ANIMAL_TYPES, data.get("species", "cattle"), er)}"""
    fin_field = field("cost", f"Cost per animal ({c['currency']})", data.get("cost") or "", er, type_="number", step="any", min="0",
                      hint="Recorded as a veterinary expense")
    form = f"""<form method="post">{req.csrf_input()}<div class="fgrid">
      {scope_html}
      {select("livestock_id", "Animal", animal_options(req, True, keep_id=keep), data.get("livestock_id"), er, blank="— choose —", groups=True)}
      {select("record_type", "Type", HEALTH_TYPES, data.get("record_type"), er)}
      {field("title", "Title", data.get("title"), er, required=True, placeholder="e.g. ECF immunisation, FMD vaccine, deworming")}
      {field("disease", "Disease (if any)", data.get("disease"), er, list="diseases",
             hint="Start typing; diseases notifiable in Zambia are flagged automatically" if code == "ZM" else "Start typing to pick from the list")}
      {field("date", "Date", data.get("date"), er, type_="date", required=True, max=today().isoformat())}
      {field("next_due_date", "Next dose / follow-up due", data.get("next_due_date"), er, type_="date", hint="Shows as a reminder on the dashboard")}
      {field("withdrawal_until", "Milk / meat withdrawal until", data.get("withdrawal_until"), er, type_="date", hint="From the medicine label")}
      {field("vet_name", "Vet / para-vet", data.get("vet_name"), er)}
      {fin_field}</div>
      {textarea("diagnosis", "Diagnosis / signs", data.get("diagnosis"), er)}
      {textarea("treatment", "Treatment / medicine and dose", data.get("treatment"), er)}
      {datalist("diseases", diseases)}
      <button class="btn block">{'Save changes' if record else 'Save record'}</button></form>"""
    body = card(form)
    if record:
        body += post_button(req, f"/health/{record['id']}/delete", "Delete record", confirm="Delete this health record?") if req.can("delete") else ""
    return layout(req, "Edit health record" if record else "New health record", body, "health")


@route("/health/new", ("GET", "POST"))
def health_new(req):
    req.require("health")
    return health_form(req)


@route(r"/health/(\d+)/edit", ("GET", "POST"))
def health_edit(req, record_id):
    r = get_record(req, record_id)
    if not req.can("health"):
        # Read-only view for roles that may not edit health records
        a = req.one("SELECT * FROM livestock WHERE id=?", (r["livestock_id"],))
        code = req.country
        rows = [("Animal", e(animal_name(a))), ("Type", e(label(HEALTH_TYPES, r["record_type"]))),
                ("Date", fmt_date(r["date"], code)), ("Disease", e(r["disease"] or "—")),
                ("Diagnosis", e(r["diagnosis"] or "—")), ("Treatment", e(r["treatment"] or "—")),
                ("Next due", fmt_date(r["next_due_date"], code)), ("Withdrawal until", fmt_date(r["withdrawal_until"], code))]
        from ..ui import dl
        return layout(req, r["title"], card(dl(rows)), "health")
    return health_form(req, r)


@route(r"/health/(\d+)/delete", ("POST",))
def health_delete(req, record_id):
    req.require("delete")
    r = get_record(req, record_id)
    with req.conn:
        unlink_transaction(req, "health", r["id"])
        req.conn.execute("DELETE FROM health_records WHERE id=?", (r["id"],))
    req.flash("Health record deleted.")
    raise Redirect(f"/animals/{r['livestock_id']}")

'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.views.inventory
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.views.inventory'] = r'''"""Inventory: feed, medicines and equipment, with a full history of every stock change."""
from ..countries import country
from ..ui import (Form, badge, card, chips, datalist, dl, e, empty, field, fmt_date, fmt_num, label, layout, money,
                  post_button, select, table, textarea, today)
from ..web import NotFound, Redirect, route
from .common import KIND_TO_EXPENSE, PRODUCT_KINDS, link_transaction, unlink_transaction

UNITS = ["kg", "bags", "bales", "litres", "doses", "bottles", "pcs", "tonnes"]


def get_product(req, product_id):
    p = req.one("""SELECT p.*, c.name category_name FROM products p LEFT JOIN categories c ON c.id=p.category_id
                   WHERE p.id=? AND p.farm_id=?""", (product_id, req.fid))
    if not p:
        raise NotFound()
    return p


@route("/inventory")
def inventory_list(req):
    code = req.country
    q = req.query.get("q", "").strip()
    kind = req.query.get("kind", "")
    low = req.query.get("low", "")
    sql = """SELECT p.*, c.name category_name FROM products p LEFT JOIN categories c ON c.id=p.category_id WHERE p.farm_id=?"""
    params = [req.fid]
    if q:
        sql += " AND (p.name LIKE ? OR p.description LIKE ?)"
        params += [f"%{q}%"] * 2
    if kind in dict(PRODUCT_KINDS):
        sql += " AND p.kind=?"
        params.append(kind)
    if low:
        sql += " AND p.quantity <= p.reorder_level"
    rows = req.all(sql + " ORDER BY p.kind, p.name", params)
    t = today().isoformat()
    fin = req.can("finance")
    value = sum(r["quantity"] * r["unit_price"] for r in rows)
    keep = {"q": q, "kind": kind, "low": low}
    body = f"""<form class="filters noprint" method="get"><div class="field"><label for="q">Search</label>
        <input id="q" name="q" value="{e(q)}" placeholder="Product name"></div><input type="hidden" name="kind" value="{e(kind)}">
        <input type="hidden" name="low" value="{e(low)}"><button class="btn">Search</button></form>"""
    body += chips("/inventory", "kind", [("", "All kinds")] + PRODUCT_KINDS, kind, keep)
    body += chips("/inventory", "low", [("", "All items"), ("1", "Low stock only")], low, keep)
    trs = []
    for p in rows:
        tags = []
        if p["quantity"] <= p["reorder_level"]:
            tags.append(badge("Low", "red"))
        if p["expiry_date"] and p["expiry_date"] < t:
            tags.append(badge("Expired", "yellow"))
        trs.append([f'<a href="/inventory/{p["id"]}"><b>{e(p["name"])}</b></a>', e(label(PRODUCT_KINDS, p["kind"])),
                    f'{fmt_num(p["quantity"])} {e(p["unit"])}', f'{fmt_num(p["reorder_level"])} {e(p["unit"])}',
                    fmt_date(p["expiry_date"], code)] + ([money(p["quantity"] * p["unit_price"], code)] if fin else []) + [" ".join(tags)])
    head = ["Product", "Kind", "In stock", "Warn below", "Expires"] + (["Value"] if fin else []) + [""]
    summary = f'<p class="muted">{len(rows)} product(s)' + (f" · stock value {money(value, code)}" if fin else "") + "</p>"
    body += card(summary + (table(head, trs, numeric=(2, 3, 5) if fin else (2, 3)) or empty("No products", "Add feed, medicines and equipment.")))
    actions = '<a class="btn" href="/inventory/new">+ Add product</a>' if req.can("inventory") else ""
    return layout(req, "Inventory", body, "inventory", actions=actions)


def product_form(req, product=None):
    code = req.country
    cats = req.all("SELECT * FROM categories WHERE farm_id=? ORDER BY name", (req.fid,))
    data = (dict(product) if product else {"unit": "kg", "kind": "feed"}) if req.method == "GET" else req.form
    f = Form(req.form)
    if req.method == "POST":
        new_cat = f.text("new_category", False, "Category", 100)
        cat_id = f.id("category_id")
        if cat_id and not any(c["id"] == cat_id for c in cats):
            cat_id = None
        v = {
            "name": f.text("name", True, "Name", 150),
            "kind": f.choice("kind", PRODUCT_KINDS),
            "unit": f.text("unit", True, "Unit", 20),
            "reorder_level": f.number("reorder_level", False, 0, "Warning level", 0) or 0,
            "unit_price": f.number("unit_price", False, 0, "Unit price", 0) or 0,
            "expiry_date": f.date("expiry_date", False, "Expiry date"),
            "description": f.text("description", False, "Description", 2000),
        }
        qty = 0 if product else (f.number("quantity", False, 0, "Opening quantity", 0) or 0)
        if f.ok:
            with req.conn:
                if new_cat:
                    ex = req.conn.execute("SELECT id FROM categories WHERE farm_id=? AND name=? COLLATE NOCASE", (req.fid, new_cat)).fetchone()
                    cat_id = ex["id"] if ex else req.conn.execute("INSERT INTO categories (farm_id, name) VALUES (?,?)", (req.fid, new_cat)).lastrowid
                v["category_id"] = cat_id
                cols = list(v)
                if product:
                    req.conn.execute(f"UPDATE products SET {', '.join(c + '=?' for c in cols)} WHERE id=? AND farm_id=?",
                                     [v[c] for c in cols] + [product["id"], req.fid])
                    pid = product["id"]
                else:
                    pid = req.conn.execute(f"INSERT INTO products (farm_id, quantity, {', '.join(cols)}) VALUES (?, ?{', ?' * len(cols)})",
                                           [req.fid, qty] + [v[c] for c in cols]).lastrowid
                    if qty:
                        req.conn.execute("INSERT INTO stock_movements (product_id, change, reason, user_id, unit_cost) VALUES (?,?,?,?,?)",
                                         (pid, qty, "Opening stock", req.user["id"], v["unit_price"]))
            req.flash("Product saved.")
            raise Redirect(f"/inventory/{pid}")
    er = f.errors
    qty_html = "" if product else field("quantity", "Opening quantity (already on the farm)", data.get("quantity"), er, type_="number", step="any", min="0",
                                        hint="Not recorded as an expense. Record new purchases with 'Add stock'.")
    form = f"""<form method="post">{req.csrf_input()}<div class="fgrid">
      {field("name", "Product name", data.get("name"), er, required=True, placeholder="e.g. Dairy meal, Hay, ECF vaccine")}
      {select("kind", "Kind", PRODUCT_KINDS, data.get("kind"), er, hint="Feed products can be used in feeding records")}
      {select("category_id", "Category", [(c["id"], c["name"]) for c in cats], data.get("category_id"), er, blank="— none —")}
      {field("new_category", "…or new category", data.get("new_category"), er)}
      {field("unit", "Unit", data.get("unit"), er, required=True, list="units")}
      {qty_html}
      {field("reorder_level", "Warn me when stock falls below", data.get("reorder_level"), er, type_="number", step="any", min="0")}
      {field("unit_price", f"Usual price per unit ({country(code)['currency']})", data.get("unit_price"), er, type_="number", step="any", min="0",
             hint="Used to value stock and to cost feeding")}
      {field("expiry_date", "Expiry date", data.get("expiry_date"), er, type_="date")}</div>
      {textarea("description", "Description", data.get("description"), er)}{datalist("units", UNITS)}
      <button class="btn block">{'Save changes' if product else 'Add product'}</button></form>"""
    return layout(req, "Edit product" if product else "Add product", card(form), "inventory")


@route("/inventory/new", ("GET", "POST"))
def product_new(req):
    req.require("inventory")
    return product_form(req)


@route(r"/inventory/(\d+)/edit", ("GET", "POST"))
def product_edit(req, product_id):
    req.require("inventory")
    return product_form(req, get_product(req, product_id))


@route(r"/inventory/(\d+)/adjust", ("POST",))
def product_adjust(req, product_id):
    req.require("inventory")
    p = get_product(req, product_id)
    f = Form(req.form)
    amount = f.number("amount", True, 0.0001, "Amount")
    reason = f.text("reason", False, "Note", 150)
    direction = req.form.get("direction")
    cost = f.number("total_cost", False, 0, "Total cost", 0) or 0
    if direction not in ("use", "add", "loss"):
        f.errors["direction"] = "Choose what happened."
    if not f.ok:
        req.flash(next(iter(f.errors.values())), bad=True)
        raise Redirect(f"/inventory/{p['id']}")
    change = amount if direction == "add" else -amount
    with req.conn:
        # One UPDATE with a check, so stock can never go below zero even if two people use it at once
        cur = req.conn.execute("UPDATE products SET quantity = quantity + ? WHERE id=? AND quantity + ? >= -0.000001",
                               (change, p["id"], change))
        if cur.rowcount == 0:
            req.conn.rollback()
            req.flash(f"Only {fmt_num(p['quantity'])} {p['unit']} in stock.", bad=True)
            raise Redirect(f"/inventory/{p['id']}")
        unit_cost = (cost / amount) if (direction == "add" and cost) else None
        default_reason = {"add": "Bought / received", "use": "Used", "loss": "Lost / spoiled / expired"}[direction]
        mid = req.conn.execute("INSERT INTO stock_movements (product_id, change, reason, user_id, unit_cost) VALUES (?,?,?,?,?)",
                               (p["id"], change, reason or default_reason, req.user["id"], unit_cost)).lastrowid
        if direction == "add" and cost and req.can("finance"):
            link_transaction(req, "stock", mid, "expense", KIND_TO_EXPENSE.get(p["kind"], "supplies"), cost,
                             today().isoformat(), f"Bought {fmt_num(amount)} {p['unit']} {p['name']}", reason)
            req.conn.execute("UPDATE products SET unit_price=? WHERE id=?", (unit_cost, p["id"]))
    req.flash({"add": "Stock added.", "use": "Usage recorded.", "loss": "Loss recorded."}[direction])
    raise Redirect(f"/inventory/{p['id']}")


@route(r"/inventory/(\d+)/delete", ("POST",))
def product_delete(req, product_id):
    req.require("delete")
    p = get_product(req, product_id)
    with req.conn:
        for m in req.conn.execute("SELECT id FROM stock_movements WHERE product_id=?", (p["id"],)).fetchall():
            unlink_transaction(req, "stock", m["id"])
        req.conn.execute("DELETE FROM products WHERE id=?", (p["id"],))
    req.flash(f"{p['name']} deleted. Its purchase costs were removed from the accounts.")
    raise Redirect("/inventory")


@route(r"/inventory/(\d+)")
def product_detail(req, product_id):
    p = get_product(req, product_id)
    code = req.country
    fin = req.can("finance")
    moves = req.all("""SELECT m.*, u.first_name FROM stock_movements m LEFT JOIN users u ON u.id=m.user_id
                       WHERE m.product_id=? ORDER BY m.id DESC LIMIT 100""", (p["id"],))
    is_low = p["quantity"] <= p["reorder_level"]
    body = f"""<div class="stats"><div class="stat {'bad' if is_low else ''}"><div class="n">{fmt_num(p['quantity'])} {e(p['unit'])}</div>
        <div class="muted">In stock{' — below warning level' if is_low else ''}</div></div>
        {'<div class="stat"><div class="n">' + money(p['quantity'] * p['unit_price'], code) + '</div><div class="muted">Stock value</div></div>' if fin else ''}</div>"""
    if req.can("inventory"):
        body += card(f"""<form method="post" action="/inventory/{p['id']}/adjust">{req.csrf_input()}<div class="fgrid">
            {select("direction", "What happened", [("use", "Used (−)"), ("add", "Bought / received (+)"), ("loss", "Lost, spoiled or expired (−)")], "use")}
            {field("amount", f"Amount ({p['unit']})", "", type_="number", step="any", min="0.0001", required=True)}
            {field("total_cost", f"Total paid ({country(code)['currency']}) — purchases only", "", type_="number", step="any", min="0",
                   hint="Recorded as an expense") if fin else ''}
            {field("reason", "Note", "", placeholder="e.g. supplier name, or what it was used for")}</div>
            <button class="btn">Update stock</button>
            <span class="muted">Feed given to animals is best recorded under <a href="/feeding/new">Feeding</a>, which also reduces stock.</span></form>""",
                     "Update stock")
    info = [("Kind", e(label(PRODUCT_KINDS, p["kind"]))), ("Category", e(p["category_name"] or "—")),
            ("Warn when below", f"{fmt_num(p['reorder_level'])} {e(p['unit'])}"), ("Expiry date", fmt_date(p["expiry_date"], code))]
    if fin:
        info.insert(2, ("Price per unit", money(p["unit_price"], code)))
    body += card(dl(info) + (f'<p class="muted">{e(p["description"])}</p>' if p["description"] else ""), "Details")
    trs = [[fmt_date(m["created_at"], code), e(m["reason"]), e(m["first_name"] or ""),
            f'<span class="{"plus" if m["change"] > 0 else "minus"}">{"+" if m["change"] > 0 else ""}{fmt_num(m["change"])}</span>']
           + ([money(m["unit_cost"] * abs(m["change"]), code) if m["unit_cost"] and m["change"] > 0 else "—"] if fin else [])
           for m in moves]
    body += card(table(["Date", "What", "By", "Change"] + (["Cost"] if fin else []), trs, numeric=(3, 4)) or empty("No stock changes yet"), "Stock history")
    actions = f'<a class="btn sec" href="/inventory/{p["id"]}/edit">Edit</a>' if req.can("inventory") else ""
    if req.can("delete"):
        actions += " " + post_button(req, f"/inventory/{p['id']}/delete", "Delete", confirm="Delete this product and its history?")
    return layout(req, p["name"], body, "inventory", actions=actions)
'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.views.reports
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.views.reports'] = r'''"""
Reports and analytics, filtered by date, farm, species and country.

Scope is either the current farm or "all my farms in one country". Farms in different countries
are never combined, because their money is in different currencies.
"""
import datetime as dt
import urllib.parse

from ..countries import COUNTRIES, country
from ..security import can
from ..ui import (card, e, empty, fmt_date, fmt_num, hbars, label, layout, money, month_label,
                  months_back, pair_chart, select, stat, table, today, field)
from ..web import route
from .breeding import pct, performance
from .common import ALL_CATEGORIES, ANIMAL_STATUS, ANIMAL_TYPES, HEALTH_TYPES, animal_name


def months_between(start, end):
    s, en = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    n = (en.year - s.year) * 12 + en.month - s.month + 1
    return months_back(max(1, min(n, 36)), en)


def scope_from_query(req):
    """Returns (farms, fids, code, scope_value)."""
    scope = req.query.get("scope", "farm")
    farms = req.my_farms()
    if scope.startswith("country:") and scope[8:] in COUNTRIES:
        chosen = [f for f in farms if f["country_code"] == scope[8:]]
        if chosen:
            return chosen, [f["id"] for f in chosen], scope[8:], scope
    return [req.farm], [req.fid], req.country, "farm"


def report_data(req, fids, start, end, species):
    """All numbers for the reports page; also used by the CSV export and the tests."""
    ph = ",".join("?" * len(fids))
    sp_sql, sp = ("", []) if not species else (" AND l.animal_type=?", [species])
    one = lambda sql, p=(): req.one(sql, p)  # noqa: E731
    d = {}
    d["population"] = req.all(f"""SELECT l.animal_type k, COUNT(*) c FROM livestock l WHERE l.farm_id IN ({ph}) AND l.status='active'{sp_sql}
                                  GROUP BY k ORDER BY c DESC""", fids + sp)
    d["status"] = req.all(f"SELECT l.status k, COUNT(*) c FROM livestock l WHERE l.farm_id IN ({ph}){sp_sql} GROUP BY k ORDER BY c DESC", fids + sp)
    d["total_active"] = sum(r["c"] for r in d["population"])
    # Herd movements per month
    months = months_between(start, end)
    mv = {m: {"born": 0, "bought": 0, "sold": 0, "died": 0, "other_exit": 0} for m in months}
    for r in req.all(f"""SELECT substr(l.acquisition_date,1,7) m, l.acquisition_method a, COUNT(*) c FROM livestock l
                         WHERE l.farm_id IN ({ph}) AND l.acquisition_date BETWEEN ? AND ?{sp_sql} GROUP BY m, a""", fids + [start, end] + sp):
        if r["m"] in mv:
            mv[r["m"]]["born" if r["a"] == "born" else "bought"] += r["c"]
    for r in req.all(f"""SELECT substr(l.exit_date,1,7) m, l.status s, COUNT(*) c FROM livestock l
                         WHERE l.farm_id IN ({ph}) AND l.exit_date BETWEEN ? AND ?{sp_sql} GROUP BY m, s""", fids + [start, end] + sp):
        if r["m"] in mv:
            key = {"sold": "sold", "dead": "died"}.get(r["s"], "other_exit")
            mv[r["m"]][key] += r["c"]
    d["movements"] = mv
    d["births"] = sum(v["born"] for v in mv.values())
    d["deaths"] = sum(v["died"] for v in mv.values())
    d["death_causes"] = req.all(f"""SELECT COALESCE(NULLIF(l.exit_reason,''),'Not recorded') k, COUNT(*) c FROM livestock l
                                    WHERE l.farm_id IN ({ph}) AND l.status='dead' AND l.exit_date BETWEEN ? AND ?{sp_sql}
                                    GROUP BY k ORDER BY c DESC LIMIT 8""", fids + [start, end] + sp)
    # Health
    hbase = f"FROM health_records h JOIN livestock l ON l.id=h.livestock_id WHERE l.farm_id IN ({ph}) AND h.date BETWEEN ? AND ?{sp_sql}"
    hp = fids + [start, end] + sp
    d["health_types"] = req.all(f"SELECT h.record_type k, COUNT(*) c {hbase} GROUP BY k ORDER BY c DESC", hp)
    d["diseases"] = req.all(f"SELECT h.disease k, COUNT(*) c, MAX(h.notifiable) n {hbase} AND h.disease!='' GROUP BY k ORDER BY c DESC LIMIT 10", hp)
    d["notifiable"] = one(f"SELECT COUNT(*) c {hbase} AND h.notifiable=1", hp)["c"]
    d["health_cost"] = one(f"SELECT COALESCE(SUM(h.cost),0) s {hbase}", hp)["s"]
    t = today()
    d["schedule"] = req.all(f"""SELECT h.*, l.name, l.tag_number, l.id lid FROM health_records h JOIN livestock l ON l.id=h.livestock_id
                                WHERE l.farm_id IN ({ph}) AND l.status='active' AND h.next_due_date BETWEEN ? AND ?{sp_sql}
                                ORDER BY h.next_due_date LIMIT 40""", fids + [t.isoformat(), (t + dt.timedelta(days=60)).isoformat()] + sp)
    # Breeding
    d["breeding"] = performance(req, start, end, species or None, fids)
    # Feeding
    fsp_sql, fsp = ("", []) if not species else (" AND r.animal_type=?", [species])
    d["feed_by_name"] = req.all(f"""SELECT r.feed_name || ' (' || r.unit || ')' k, SUM(r.quantity) q, SUM(r.cost) s FROM feeding_records r
                                    WHERE r.farm_id IN ({ph}) AND r.date BETWEEN ? AND ?{fsp_sql} GROUP BY k ORDER BY s DESC, q DESC""",
                                 fids + [start, end] + fsp)
    d["feed_by_species"] = req.all(f"""SELECT COALESCE(NULLIF(r.animal_type,''),'all') k, SUM(r.cost) s, SUM(r.quantity) q FROM feeding_records r
                                       WHERE r.farm_id IN ({ph}) AND r.date BETWEEN ? AND ?{fsp_sql} GROUP BY k ORDER BY s DESC""",
                                    fids + [start, end] + fsp)
    d["feed_cost"] = sum(r["s"] or 0 for r in d["feed_by_name"])
    # Inventory (current)
    d["inventory"] = one(f"SELECT COUNT(*) n, SUM(quantity <= reorder_level) low, COALESCE(SUM(quantity*unit_price),0) v FROM products WHERE farm_id IN ({ph})", fids)
    d["low_stock"] = req.all(f"SELECT * FROM products WHERE farm_id IN ({ph}) AND quantity <= reorder_level ORDER BY name", fids)
    # Sales (by species through the animals sold)
    d["sales"] = req.all(f"""SELECT l.animal_type k, COUNT(*) c, SUM(i.price) s FROM sale_items i JOIN sales s ON s.id=i.sale_id
                             JOIN livestock l ON l.id=i.livestock_id WHERE s.farm_id IN ({ph}) AND s.date BETWEEN ? AND ?{sp_sql}
                             GROUP BY k ORDER BY s DESC""", fids + [start, end] + sp)
    d["sales_heads"] = sum(r["c"] for r in d["sales"])
    d["sales_total"] = sum(r["s"] for r in d["sales"])
    # Finance (never filtered by species: costs such as labour are not per species)
    d["fin_cats"] = req.all(f"""SELECT kind, category, SUM(amount) s FROM transactions WHERE farm_id IN ({ph}) AND date BETWEEN ? AND ?
                                GROUP BY kind, category ORDER BY s DESC""", fids + [start, end])
    d["income"] = sum(r["s"] for r in d["fin_cats"] if r["kind"] == "income")
    d["expense"] = sum(r["s"] for r in d["fin_cats"] if r["kind"] == "expense")
    fm = {m: [0, 0] for m in months}
    for r in req.all(f"""SELECT substr(date,1,7) m, kind, SUM(amount) s FROM transactions WHERE farm_id IN ({ph}) AND date BETWEEN ? AND ?
                         GROUP BY m, kind""", fids + [start, end]):
        if r["m"] in fm:
            fm[r["m"]][0 if r["kind"] == "income" else 1] = r["s"]
    d["fin_months"] = fm
    d["per_farm"] = req.all(f"""SELECT f.id, f.name, SUM(CASE WHEN t.kind='income' THEN t.amount ELSE 0 END) inc,
                                SUM(CASE WHEN t.kind='expense' THEN t.amount ELSE 0 END) exp FROM farms f
                                LEFT JOIN transactions t ON t.farm_id=f.id AND t.date BETWEEN ? AND ?
                                WHERE f.id IN ({ph}) GROUP BY f.id ORDER BY f.name""", [start, end] + fids)
    return d


@route("/reports")
def reports(req):
    t = today()
    start = req.query.get("from") or t.replace(month=1, day=1).isoformat()
    end = req.query.get("to") or t.isoformat()
    try:
        if dt.date.fromisoformat(start) > dt.date.fromisoformat(end):
            start, end = end, start
    except ValueError:
        start, end = t.replace(month=1, day=1).isoformat(), t.isoformat()
    species = req.query.get("type", "")
    species = species if species in dict(ANIMAL_TYPES) else ""
    farms, fids, code, scope = scope_from_query(req)
    fin = all(can(f["role"], "finance") for f in farms)
    d = report_data(req, fids, start, end, species)
    cur = country(code)["currency"]

    scope_opts = [("farm", f"This farm: {req.farm['name']}")]
    for c in COUNTRIES.values():
        mine = [f for f in req.my_farms() if f["country_code"] == c["code"]]
        if len(mine) > 1 or (mine and mine[0]["id"] != req.fid):
            scope_opts.append((f"country:{c['code']}", f"All my farms in {c['name']} ({len(mine)})"))
    filters = f"""<form class="filters noprint card" method="get">
        {select("scope", "Farm / country", scope_opts, scope)}
        {field("from", "From", start, type_="date")}{field("to", "To", end, type_="date")}
        {select("type", "Species", ANIMAL_TYPES, species, blank="All species")}<button class="btn">Apply</button></form>"""
    names = ", ".join(f["name"] for f in farms)
    body = filters + (f'<p class="muted">Report for <b>{e(names)}</b> ({e(country(code)["name"])}), '
                      f'{fmt_date(start, code)} to {fmt_date(end, code)}{", " + e(label(ANIMAL_TYPES, species)) + " only" if species else ""}. '
                      f'Money in {e(cur)}.</p>')
    sections = [("pop", "Population"), ("health", "Health"), ("breed", "Breeding"), ("feed", "Feeding"), ("stock", "Inventory")]
    if fin:
        sections += [("sales", "Sales"), ("money", "Income & profit")]
    body += '<div class="chips noprint">' + "".join(f'<a class="chip" href="#{k}">{n}</a>' for k, n in sections) + "</div>"

    # Population
    stats = stat(d["total_active"], "Active animals") + stat(d["births"], "Born in period", tone="good")
    stats += stat(d["deaths"], "Died in period", tone="bad" if d["deaths"] else "")
    mortality = d["deaths"] / (d["total_active"] + d["deaths"]) * 100 if (d["total_active"] + d["deaths"]) else None
    stats += stat(pct(mortality), "Deaths as share of herd")
    body += f'<h2 id="pop">Livestock population</h2><div class="stats">{stats}</div>'
    mv = d["movements"]
    mv_rows = [[month_label(m), str(v["born"]), str(v["bought"]), str(v["sold"]), str(v["died"]), str(v["other_exit"])] for m, v in mv.items()]
    body += '<div class="grid g2">' + card(hbars([(label(ANIMAL_TYPES, r["k"]), r["c"]) for r in d["population"]]), "Active animals by species")
    body += card(hbars([(label(ANIMAL_STATUS, r["k"]), r["c"]) for r in d["status"]]), "All animals by status") + "</div>"
    body += card(pair_chart([(month_label(m), v["born"], v["died"]) for m, v in mv.items()], labels=("Born", "Died")), "Births and deaths by month")
    body += card(table(["Month", "Born", "Bought / received", "Sold", "Died", "Slaughtered / given"], mv_rows, numeric=(1, 2, 3, 4, 5)), "Herd movements")
    if d["death_causes"]:
        body += card(hbars([(r["k"], r["c"]) for r in d["death_causes"]]), "Recorded causes of death")

    # Health
    hstats = stat(sum(r["c"] for r in d["health_types"]), "Health records in period")
    hstats += stat(d["notifiable"], "Notifiable disease records", tone="bad" if d["notifiable"] else "")
    if fin:
        hstats += stat(money(d["health_cost"], code), "Treatment costs")
    body += f'<h2 id="health">Animal health</h2><div class="stats">{hstats}</div><div class="grid g2">'
    body += card(hbars([(label(HEALTH_TYPES, r["k"]), r["c"]) for r in d["health_types"]]), "Records by type")
    body += card(hbars([(r["k"] + (" ⚠" if r["n"] else ""), r["c"]) for r in d["diseases"]]) +
                 ("<p class='muted'>⚠ = notifiable in Zambia (SI 81 of 2019)</p>" if code == "ZM" and any(r["n"] for r in d["diseases"]) else ""),
                 "Most recorded diseases") + "</div>"
    sched = [[fmt_date(h["next_due_date"], code), f'<a href="/animals/{h["lid"]}">{e(animal_name(h))}</a>', e(h["title"])] for h in d["schedule"]]
    body += card(table(["Due", "Animal", "Vaccination / treatment"], sched) or empty("Nothing scheduled in the next 60 days"), "Vaccination and treatment schedule, next 60 days")

    # Breeding
    b = d["breeding"]
    bstats = stat(b["services"], "Matings / inseminations") + stat(pct(b["conception_rate"]), "Conception rate")
    bstats += stat(b["born_alive"], "Young born alive") + stat(pct(b["survival"]), "Born alive (share)")
    bstats += stat(f"{b['litter']:.1f}" if b["litter"] else "—", "Young per birth")
    bstats += stat(f"{b['interval']:.0f} d" if b["interval"] else "—", "Interval between births")
    body += f'<h2 id="breed">Breeding performance</h2><div class="stats">{bstats}</div>'
    body += '<p class="muted">Conception rate = services that resulted in pregnancy ÷ services whose result is known. Matings in the selected period.</p>'

    # Feeding
    fstats = stat(len(d["feed_by_name"]), "Feeds used")
    if fin:
        fstats += stat(money(d["feed_cost"], code), "Feed cost in period")
        if d["total_active"]:
            fstats += stat(money(d["feed_cost"] / d["total_active"], code), "Feed cost per active animal")
    body += f'<h2 id="feed">Feed consumption</h2><div class="stats">{fstats}</div><div class="grid g2">'
    body += card(hbars([(r["k"], r["q"]) for r in d["feed_by_name"]], fmt=lambda v: fmt_num(v, 1)), "Quantity of each feed")
    if fin:
        body += card(hbars([("All animals" if r["k"] == "all" else label(ANIMAL_TYPES, r["k"]), r["s"] or 0) for r in d["feed_by_species"]],
                           fmt=lambda v: money(v, code)), "Feed cost by species")
    body += "</div>"

    # Inventory
    inv = d["inventory"]
    istats = stat(inv["n"], "Products") + stat(inv["low"] or 0, "Low in stock", tone="bad" if inv["low"] else "")
    if fin:
        istats += stat(money(inv["v"], code), "Stock value now")
    body += f'<h2 id="stock">Inventory</h2><div class="stats">{istats}</div>'
    low = [[e(p["name"]), f'{fmt_num(p["quantity"])} {e(p["unit"])}', f'{fmt_num(p["reorder_level"])} {e(p["unit"])}'] for p in d["low_stock"]]
    body += card(table(["Product", "In stock", "Warning level"], low) or empty("Nothing is low in stock"), "Low stock")

    if fin:
        sstats = stat(d["sales_heads"], "Animals sold") + stat(money(d["sales_total"], code), "Sales revenue")
        sstats += stat(money(d["sales_total"] / d["sales_heads"], code) if d["sales_heads"] else "—", "Average price per animal")
        body += f'<h2 id="sales">Livestock sales</h2><div class="stats">{sstats}</div>'
        srows = [[e(label(ANIMAL_TYPES, r["k"])), str(r["c"]), money(r["s"], code), money(r["s"] / r["c"], code)] for r in d["sales"]]
        body += card(table(["Species", "Sold", "Revenue", "Average"], srows, numeric=(1, 2, 3)) or empty("No sales in this period"), "Sales by species")
        profit = d["income"] - d["expense"]
        mstats = stat(money(d["income"], code), "Income", tone="good") + stat(money(d["expense"], code), "Expenses", tone="bad")
        mstats += stat(money(profit, code), "Profit" if profit >= 0 else "Loss", tone="good" if profit >= 0 else "bad")
        mstats += stat(f"{profit / d['income'] * 100:.0f}%" if d["income"] else "—", "Profit margin")
        body += f'<h2 id="money">Income, expenses and profitability</h2><div class="stats">{mstats}</div>'
        if species:
            body += '<p class="muted">Money figures cover the whole farm; the species filter does not apply to them.</p>'
        body += card(pair_chart([(month_label(m), a, x) for m, (a, x) in d["fin_months"].items()], fmt=lambda v: money(v, code, False)),
                     f"Income and expenses by month ({cur})")
        cats = [[e("Income" if r["kind"] == "income" else "Expense"), e(label(ALL_CATEGORIES, r["category"])), money(r["s"], code)] for r in d["fin_cats"]]
        body += '<div class="grid g2">' + card(table(["Type", "Category", "Amount"], cats, numeric=(2,)) or empty("No money recorded"), "By category")
        pf = [[e(r["name"]), money(r["inc"] or 0, code), money(r["exp"] or 0, code), money((r["inc"] or 0) - (r["exp"] or 0), code)] for r in d["per_farm"]]
        body += card(table(["Farm", "Income", "Expenses", "Profit"], pf, numeric=(1, 2, 3)), "Profitability by farm") + "</div>"
    else:
        body += '<p class="muted">Money sections are hidden because your role does not include finance on every farm in this report.</p>'
    qs = urllib.parse.urlencode({"scope": scope, "from": start, "to": end, "type": species})
    actions = '<button class="btn sec" onclick="window.print()">Print / PDF</button>'
    if all(can(f["role"], "export") for f in farms):
        actions += f' <a class="btn sec" href="/export/report.csv?{e(qs)}">Download report (CSV)</a>'
    return layout(req, "Reports", body, "reports", actions=actions)

'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.views.sales
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.views.sales'] = r'''"""Livestock sales: buyers, prices, receipts and sales history."""

from .. import config
from ..countries import country
from ..ui import (Form, bare_page, card, e, empty, field, fmt_date, layout, money, post_button, select, stat, table,
                  textarea, today)
from ..web import NotFound, Redirect, route
from .common import ANIMAL_TYPES, animal_name, link_transaction, unlink_transaction
from ..ui import label

PAYMENT = [("cash", "Cash"), ("mobile_money", "Mobile money"), ("bank", "Bank transfer"), ("cheque", "Cheque"),
           ("credit", "On credit (to be paid)")]


def get_sale(req, sid):
    s = req.one("SELECT * FROM sales WHERE id=? AND farm_id=?", (sid, req.fid))
    if not s:
        raise NotFound()
    return s


@route("/sales")
def sales_list(req):
    req.require("finance")
    code = req.country
    t = today()
    start = req.query.get("from") or t.replace(month=1, day=1).isoformat()
    end = req.query.get("to") or t.isoformat()
    rows = req.all("""SELECT s.*, (SELECT COUNT(*) FROM sale_items i WHERE i.sale_id=s.id) n FROM sales s
                      WHERE s.farm_id=? AND s.date BETWEEN ? AND ? ORDER BY s.date DESC, s.id DESC""", (req.fid, start, end))
    total = sum(r["total"] for r in rows)
    heads = sum(r["n"] for r in rows)
    body = f"""<form class="filters noprint" method="get">{field("from", "From", start, type_="date")}{field("to", "To", end, type_="date")}
        <button class="btn">Show</button></form>"""
    body += '<div class="stats">' + stat(len(rows), "Sales") + stat(heads, "Animals sold") + stat(money(total, code), "Revenue from livestock sales")
    body += stat(money(total / heads, code) if heads else "—", "Average price per animal") + "</div>"
    trs = [[f'<a href="/sales/{r["id"]}"><b>{e(r["receipt_no"])}</b></a>', fmt_date(r["date"], code), e(r["buyer_name"]),
            e(r["buyer_phone"] or "—"), str(r["n"]), e(label(PAYMENT, r["payment_method"])), money(r["total"], code)] for r in rows]
    body += card(table(["Receipt", "Date", "Buyer", "Phone", "Animals", "Payment", "Total"], trs, numeric=(4, 6))
                 or empty("No sales in this period"))
    actions = '<a class="btn" href="/sales/new">+ Record sale</a>'
    if req.can("export"):
        actions += ' <a class="btn sec" href="/export/sales.csv">Export CSV</a>'
    return layout(req, "Livestock sales", body, "sales", actions=actions)


@route("/sales/new", ("GET", "POST"))
def sale_new(req):
    req.require("finance")
    code = req.country
    c = country(code)
    animals = req.all("SELECT * FROM livestock WHERE farm_id=? AND status='active' ORDER BY animal_type, name, tag_number", (req.fid,))
    pre = req.query.get("animal", "")
    data = {"date": today().isoformat(), "payment_method": "cash"} if req.method == "GET" else req.form
    f = Form(req.form)
    chosen = []
    if req.method == "POST":
        v = {
            "date": f.date("date", True, not_future=True),
            "buyer_name": f.text("buyer_name", True, "Buyer name", 150),
            "buyer_phone": f.text("buyer_phone", False, "Buyer phone", 30),
            "buyer_address": f.text("buyer_address", False, "Buyer address", 300),
            "payment_method": f.choice("payment_method", PAYMENT),
            "permit_no": f.text("permit_no", False, c["movement_label"], 60),
            "notes": f.text("notes", False, "Notes", 1000),
        }
        ids = {int(x) for x in req.form_lists.get("animal", []) if x.isdigit()}
        valid = {a["id"]: a for a in animals}
        for aid in sorted(ids):
            if aid not in valid:
                continue
            price = f.number(f"price_{aid}", True, 0.01, f"Price for {animal_name(valid[aid])}")
            if v["date"] and valid[aid]["acquisition_date"] and v["date"] < valid[aid]["acquisition_date"]:
                f.errors[f"price_{aid}"] = f"{animal_name(valid[aid])} was acquired after this sale date."
            chosen.append((valid[aid], price))
        if not chosen:
            f.errors["animal"] = "Tick at least one animal and enter its price."
        if f.ok:
            total = round(sum(p for _, p in chosen), c["decimals"])
            with req.conn:
                seq = req.conn.execute("SELECT COUNT(*) c FROM sales WHERE farm_id=?", (req.fid,)).fetchone()["c"] + 1
                receipt = f"{code}-{req.fid:03d}-{v['date'][:4]}-{seq:04d}"
                while req.conn.execute("SELECT 1 FROM sales WHERE receipt_no=?", (receipt,)).fetchone():
                    seq += 1
                    receipt = f"{code}-{req.fid:03d}-{v['date'][:4]}-{seq:04d}"
                cols = list(v)
                sid = req.conn.execute(
                    f"INSERT INTO sales (farm_id, receipt_no, total, created_by, {', '.join(cols)}) VALUES (?,?,?,?{', ?' * len(cols)})",
                    [req.fid, receipt, total, req.user["id"]] + [v[k] for k in cols]).lastrowid
                for a, price in chosen:
                    desc = f"{label(ANIMAL_TYPES, a['animal_type'])} {animal_name(a)}" + (f", {a['breed']}" if a["breed"] else "")
                    req.conn.execute("INSERT INTO sale_items (sale_id, livestock_id, description, price) VALUES (?,?,?,?)",
                                     (sid, a["id"], desc, price))
                    req.conn.execute("UPDATE livestock SET status='sold', exit_date=?, exit_reason=? WHERE id=?",
                                     (v["date"], f"Sold to {v['buyer_name']} (receipt {receipt})", a["id"]))
                link_transaction(req, "sale", sid, "income", "livestock_sale", total, v["date"],
                                 f"Livestock sale, receipt {receipt}", v["buyer_name"])
            req.flash(f"Sale recorded. Receipt {receipt}.")
            raise Redirect(f"/sales/{sid}")
    er = f.errors
    ticked = {int(x) for x in req.form_lists.get("animal", []) if x.isdigit()} if req.method == "POST" else ({int(pre)} if pre.isdigit() else set())
    rows = []
    for a in animals:
        pk = f"price_{a['id']}"
        err = er.get(pk, "")
        rows.append([f'<input type="checkbox" name="animal" value="{a["id"]}" style="width:auto"{" checked" if a["id"] in ticked else ""} aria-label="Sell {e(animal_name(a))}">',
                     f'<b>{e(animal_name(a))}</b><div class="muted">{e(label(ANIMAL_TYPES, a["animal_type"]))} · {e(a["breed"] or "")}'
                     f'{" · " + str(a["weight_kg"]) + " kg" if a["weight_kg"] else ""}</div>',
                     f'<input name="price_{a["id"]}" type="number" step="any" min="0" value="{e(data.get(pk, ""))}" '
                     f'placeholder="{c["currency"]}" style="max-width:160px">' + (f'<div class="err">{e(err)}</div>' if err else "")])
    pick = table(["Sell", "Animal", f"Price ({c['currency']})"], rows) or empty("No active animals to sell")
    form = f"""<form method="post">{req.csrf_input()}
      {'<div class="flash bad">' + e(er["animal"]) + '</div>' if er.get("animal") else ''}
      <h3>1. Animals sold</h3>{pick}<br><h3>2. Buyer and payment</h3><br><div class="fgrid">
      {field("date", "Sale date", data.get("date"), er, type_="date", required=True, max=today().isoformat())}
      {field("buyer_name", "Buyer name", data.get("buyer_name"), er, required=True)}
      {field("buyer_phone", "Buyer phone", data.get("buyer_phone"), er, type_="tel")}
      {field("buyer_address", "Buyer address / ID number", data.get("buyer_address"), er)}
      {select("payment_method", "Payment", PAYMENT, data.get("payment_method"), er)}
      {field("permit_no", c["movement_label"], data.get("permit_no"), er, hint="If the animals are moved off the farm")}
      </div>{textarea("notes", "Notes", data.get("notes"), er)}<button class="btn block">Record sale and make receipt</button></form>"""
    return layout(req, "Record a livestock sale", card(form), "sales")


def receipt_html(req, s, items):
    code = req.country
    c = country(code)
    farm = req.farm
    lines = "".join(f"<tr><td>{e(i['description'])}</td><td class='num'>{money(i['price'], code)}</td></tr>" for i in items)
    return f"""<div class="receipt"><div style="display:flex;justify-content:space-between;gap:12px">
      <div><b style="font-size:18px">{e(farm['name'])}</b><div class="muted">{e(farm['district'])}{', ' + e(farm['province']) if farm['province'] else ''},
      {e(c['name'])}<br>{e(farm['phone'] or '')} {e(farm['email'] or '')}</div></div>
      <div style="text-align:right"><b style="font-size:18px">SALES RECEIPT</b><div>No. {e(s['receipt_no'])}</div><div>Date: {fmt_date(s['date'], code)}</div></div></div>
      <hr><p><b>Sold to:</b> {e(s['buyer_name'])}{' · ' + e(s['buyer_phone']) if s['buyer_phone'] else ''}
      {'<br>' + e(s['buyer_address']) if s['buyer_address'] else ''}</p>
      <table><thead><tr><th>Item</th><th class="num">Amount</th></tr></thead><tbody>{lines}
      <tr><td><b>Total</b></td><td class="num"><b>{money(s['total'], code)}</b></td></tr></tbody></table>
      <p>Payment: {e(label(PAYMENT, s['payment_method']))}{'<br>' + e(c['movement_label']) + ': ' + e(s['permit_no']) if s['permit_no'] else ''}</p>
      {'<p class="muted">' + e(s['notes']) + '</p>' if s['notes'] else ''}
      <br><div style="display:flex;justify-content:space-between;gap:20px"><div>Seller signature: ____________________</div>
      <div>Buyer signature: ____________________</div></div>
      <p class="muted" style="margin-top:24px">Produced by {e(config.APP_NAME)}. Amounts in {e(c['currency_name'])} ({e(c['currency'])}).</p></div>"""


@route(r"/sales/(\d+)")
def sale_detail(req, sid):
    req.require("finance")
    s = get_sale(req, sid)
    items = req.all("SELECT * FROM sale_items WHERE sale_id=?", (s["id"],))
    actions = f'<a class="btn" href="/sales/{s["id"]}/receipt" target="_blank">Print receipt</a>'
    if req.can("delete"):
        actions += " " + post_button(req, f"/sales/{s['id']}/delete", "Delete sale",
                                     confirm="Delete this sale? The animals become active again and the income is removed.")
    links = "".join(f'<li><a href="/animals/{i["livestock_id"]}">{e(i["description"])}</a></li>' for i in items if i["livestock_id"])
    body = receipt_html(req, s, items) + (card(f"<ul>{links}</ul>", "Animals on this receipt") if links else "")
    return layout(req, f"Sale {s['receipt_no']}", body, "sales", actions=actions)


@route(r"/sales/(\d+)/receipt")
def sale_receipt(req, sid):
    req.require("finance")
    s = get_sale(req, sid)
    items = req.all("SELECT * FROM sale_items WHERE sale_id=?", (s["id"],))
    return bare_page(f"Receipt {s['receipt_no']}", f'<div style="padding:20px">{receipt_html(req, s, items)}'
                     '<p class="noprint" style="text-align:center"><button class="btn" onclick="window.print()">Print / save as PDF</button></p></div>')


@route(r"/sales/(\d+)/delete", ("POST",))
def sale_delete(req, sid):
    req.require("finance")
    req.require("delete")
    s = get_sale(req, sid)
    with req.conn:
        for i in req.conn.execute("SELECT livestock_id FROM sale_items WHERE sale_id=?", (s["id"],)).fetchall():
            if i["livestock_id"]:
                req.conn.execute("UPDATE livestock SET status='active', exit_date=NULL, exit_reason='' WHERE id=? AND status='sold'",
                                 (i["livestock_id"],))
        unlink_transaction(req, "sale", s["id"])
        req.conn.execute("DELETE FROM sales WHERE id=?", (s["id"],))
    req.flash(f"Sale {s['receipt_no']} deleted; the animals are active again.")
    raise Redirect("/sales")

'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.views.settings
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.views.settings'] = r'''"""Settings: profile, password, account, and database backup (system administrator)."""
import os

from .. import config, db
from ..security import check_password, hash_password, password_problem
from ..ui import Form, card, e, field, layout, post_button, table
from ..web import Forbidden, NotFound, Redirect, Response, route


@route("/settings", ("GET", "POST"))
def settings(req):
    u = req.user
    f = Form(req.form)
    if req.method == "POST":
        first = f.text("first_name", True, "First name", 150)
        last = f.text("last_name", False, "Last name", 150)
        phone = f.text("phone", False, "Phone", 30)
        if f.ok:
            req.run("UPDATE users SET first_name=?, last_name=?, phone=? WHERE id=?", (first, last, phone, u["id"]))
            req.flash("Profile saved.")
            raise Redirect("/settings")
    d = dict(u) if req.method == "GET" else req.form
    er = f.errors
    body = '<div class="grid g2">'
    body += card(f"""<form method="post">{req.csrf_input()}{field("email", "Email", u["email"], disabled=True, hint="Your sign-in name")}
        {field("first_name", "First name", d.get("first_name"), er, required=True)}{field("last_name", "Last name", d.get("last_name"), er)}
        {field("phone", "Phone", d.get("phone"), er, type_="tel")}<button class="btn">Save profile</button></form>""", "My profile")
    body += card(f"""<form method="post" action="/settings/password">{req.csrf_input()}
        {field("current", "Current password", "", type_="password", required=True, autocomplete="current-password")}
        {field("new", "New password", "", type_="password", required=True, autocomplete="new-password", hint="At least 8 characters, not only numbers")}
        {field("confirm", "Confirm new password", "", type_="password", required=True, autocomplete="new-password")}
        <button class="btn">Change password</button></form>""", "Password") + "</div>"
    if u["is_admin"]:
        backups = db.list_backups()[:15]
        rows = [[e(b), f'{os.path.getsize(os.path.join(config.BACKUP_DIR, b)) / 1024:.0f} KB',
                 f'<a href="/settings/backups/{e(b)}">Download</a>'] for b in backups]
        body += card(f"""<p>A backup is a complete copy of the database (all farms). Keep copies on a USB stick or another computer.</p>
            {post_button(req, "/settings/backup", "Make a backup now", "btn")}
            <p class="muted">To restore, stop the system and run <code>python run.py --restore backups\\FILE.db</code>.
            The current database is backed up automatically before it is replaced.</p>
            {table(["Backup file", "Size", ""], rows)}""", "Backup and recovery (administrator)")
    body += card(f"""<p class="muted">Language: English. The interface text is kept in <code>jesse_farm/i18n.py</code>, so other languages
        such as Kinyarwanda or Bemba can be added later.</p>
        {post_button(req, "/settings/delete-account", "Delete my account", "btn danger",
                     confirm="Delete your account? Farms where you are the only member are deleted with all their records.")}""",
                 "Account")
    return layout(req, "Settings", body, "settings")


@route("/settings/password", ("POST",), needs_farm=False)
def settings_password(req):
    f = Form(req.form)
    if not check_password(req.form.get("current", ""), req.user["password_hash"]):
        f.errors["current"] = "Current password is incorrect."
    new = req.form.get("new", "")
    if password_problem(new):
        f.errors["new"] = password_problem(new)
    elif new != req.form.get("confirm", ""):
        f.errors["confirm"] = "New passwords don't match."
    if not f.ok:
        req.flash(" ".join(f.errors.values()), bad=True)
        raise Redirect("/settings")
    req.run("UPDATE users SET password_hash=? WHERE id=?", (hash_password(new), req.user["id"]))
    req.run("DELETE FROM sessions WHERE user_id=? AND token!=?", (req.user["id"], req.session["token"]))
    req.flash("Password changed. Other devices were signed out.")
    raise Redirect("/settings")


@route("/settings/backup", ("POST",), needs_farm=False)
def settings_backup(req):
    if not req.user["is_admin"]:
        raise Forbidden("Only the system administrator can make backups.")
    path = db.backup_db(label="manual")
    req.flash(f"Backup saved: {os.path.basename(path)}")
    raise Redirect("/settings")


@route(r"/settings/backups/(jesse-[\w\-]+\.db)", needs_farm=False)
def settings_backup_download(req, name):
    if not req.user["is_admin"]:
        raise Forbidden("Only the system administrator can download backups.")
    path = os.path.join(config.BACKUP_DIR, name)
    if not os.path.isfile(path):
        raise NotFound()
    with open(path, "rb") as fh:
        return Response(fh.read(), "application/octet-stream", name)


@route("/settings/delete-account", ("POST",), needs_farm=False)
def delete_account(req):
    uid = req.user["id"]
    with req.conn:
        for m in req.conn.execute("SELECT farm_id, role FROM memberships WHERE user_id=?", (uid,)).fetchall():
            others = req.conn.execute("SELECT user_id, role FROM memberships WHERE farm_id=? AND user_id!=? ORDER BY role='manager' DESC, id",
                                      (m["farm_id"], uid)).fetchall()
            if not others:
                req.conn.execute("DELETE FROM farms WHERE id=?", (m["farm_id"],))
            elif m["role"] == "owner" and not any(o["role"] == "owner" for o in others):
                # Hand the farm to the next person so it is never left without an owner
                req.conn.execute("UPDATE memberships SET role='owner' WHERE farm_id=? AND user_id=?", (m["farm_id"], others[0]["user_id"]))
        req.conn.execute("DELETE FROM sessions WHERE user_id=?", (uid,))
        req.conn.execute("DELETE FROM users WHERE id=?", (uid,))
    req.new_cookie = "sid=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
    raise Redirect("/login")
'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.views.tasks
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.views.tasks'] = r'''"""Farm tasks: plan work, assign it to people and tick it off."""
import datetime as dt

from ..ui import (Form, badge, card, chips, e, empty, field, fmt_date, label, layout, post_button, select, table,
                  textarea, today)
from ..web import NotFound, Redirect, route
from .common import PRIORITIES, PRIORITY_COLOR, TASK_STATUS, animal_name, animal_options, safe_back


def get_task(req, tid):
    t = req.one("SELECT * FROM tasks WHERE id=? AND farm_id=?", (tid, req.fid))
    if not t:
        raise NotFound()
    return t


def members(req):
    return req.all("""SELECT u.id, u.first_name, u.last_name FROM users u JOIN memberships m ON m.user_id=u.id
                      WHERE m.farm_id=? ORDER BY u.first_name""", (req.fid,))


@route("/tasks")
def tasks_list(req):
    code = req.country
    show = req.query.get("show", "open")
    t = today().isoformat()
    sql = """SELECT t.*, u.first_name assignee, l.name lname, l.tag_number ltag FROM tasks t
             LEFT JOIN users u ON u.id=t.assigned_to LEFT JOIN livestock l ON l.id=t.livestock_id WHERE t.farm_id=?"""
    params = [req.fid]
    if show == "overdue":
        sql += " AND t.status!='completed' AND t.due_date < ?"
        params.append(t)
    elif show == "mine":
        sql += " AND t.status!='completed' AND t.assigned_to=?"
        params.append(req.user["id"])
    elif show == "completed":
        sql += " AND t.status='completed'"
    else:
        show = "open"
        sql += " AND t.status!='completed'"
    order = (" ORDER BY t.completed_at DESC LIMIT 200" if show == "completed" else
             " ORDER BY (t.due_date IS NULL), t.due_date, CASE t.priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END")
    rows = req.all(sql + order, params)
    body = chips("/tasks", "show", [("open", "Open"), ("overdue", "Overdue"), ("mine", "Assigned to me"), ("completed", "Completed")], show)
    trs = []
    for x in rows:
        done = x["status"] == "completed"
        late = not done and x["due_date"] and x["due_date"] < t
        tick = post_button(req, f"/tasks/{x['id']}/toggle", "✅" if done else "⬜", "check") if req.can("tasks") else ("✅" if done else "⬜")
        tags = badge(label(PRIORITIES, x["priority"]), PRIORITY_COLOR[x["priority"]])
        if late:
            tags += " " + badge("Overdue", "red")
        if x["status"] == "in_progress":
            tags += " " + badge("In progress", "blue")
        animal = animal_name({"name": x["lname"], "tag_number": x["ltag"], "id": x["livestock_id"]}) if x["livestock_id"] else ""
        trs.append([tick, f'<a href="/tasks/{x["id"]}/edit" class="{"done" if done else ""}"><b>{e(x["title"])}</b></a>',
                    fmt_date(x["due_date"], code), e(x["assignee"] or "—"), e(animal or "—"), tags])
    body += card(table(["", "Task", "Due", "Assigned to", "Animal", ""], trs) or empty("No tasks here", "Plan feeding, dipping, vet visits and repairs."))
    actions = '<a class="btn" href="/tasks/new">+ New task</a>' if req.can("tasks") else ""
    return layout(req, "Tasks", body, "tasks", actions=actions)


def task_form(req, task=None):
    people = members(req)
    if req.method == "GET":
        data = dict(task) if task else {"priority": "medium", "status": "pending", "due_date": today().isoformat(),
                                        "livestock_id": req.query.get("animal", "")}
    else:
        data = req.form
    f = Form(req.form)
    if req.method == "POST":
        assigned, animal = f.id("assigned_to"), f.id("livestock_id")
        if assigned and not any(m["id"] == assigned for m in people):
            assigned = None
        if animal and not req.one("SELECT 1 FROM livestock WHERE id=? AND farm_id=?", (animal, req.fid)):
            animal = None
        v = {"title": f.text("title", True, "Task", 200), "description": f.text("description", False, "Details", 2000),
             "priority": f.choice("priority", PRIORITIES), "status": f.choice("status", TASK_STATUS, "pending"),
             "due_date": f.date("due_date", False, "Due date"), "assigned_to": assigned, "livestock_id": animal}
        if f.ok:
            was_done = task and task["status"] == "completed"
            v["completed_at"] = ((task["completed_at"] if was_done else dt.datetime.now().isoformat(timespec="seconds"))
                                 if v["status"] == "completed" else None)
            cols = list(v)
            if task:
                req.run(f"UPDATE tasks SET {', '.join(c + '=?' for c in cols)} WHERE id=? AND farm_id=?", [v[c] for c in cols] + [task["id"], req.fid])
            else:
                req.run(f"INSERT INTO tasks (farm_id, created_by, {', '.join(cols)}) VALUES (?, ?{', ?' * len(cols)})",
                        [req.fid, req.user["id"]] + [v[c] for c in cols])
            req.flash("Task saved.")
            raise Redirect("/tasks")
    er = f.errors
    form = f"""<form method="post">{req.csrf_input()}
      {field("title", "Task", data.get("title"), er, required=True, placeholder="e.g. Dip cattle, repair kraal fence")}
      {textarea("description", "Details", data.get("description"), er)}<div class="fgrid">
      {select("priority", "Priority", PRIORITIES, data.get("priority"), er)}
      {field("due_date", "Due date", data.get("due_date"), er, type_="date")}
      {select("status", "Status", TASK_STATUS, data.get("status"), er)}
      {select("assigned_to", "Assign to", [(m["id"], f"{m['first_name']} {m['last_name'] or ''}".strip()) for m in people], data.get("assigned_to"), er, blank="— nobody —")}
      {select("livestock_id", "Related animal", animal_options(req, keep_id=task["livestock_id"] if task else None), data.get("livestock_id"), er, blank="— none —", groups=True)}
      </div><button class="btn block">Save task</button></form>"""
    body = card(form)
    if task and req.can("delete"):
        body += post_button(req, f"/tasks/{task['id']}/delete", "Delete task", confirm="Delete this task?")
    return layout(req, "Edit task" if task else "New task", body, "tasks")


@route("/tasks/new", ("GET", "POST"))
def task_new(req):
    req.require("tasks")
    return task_form(req)


@route(r"/tasks/(\d+)/edit", ("GET", "POST"))
def task_edit(req, tid):
    req.require("tasks")
    return task_form(req, get_task(req, tid))


@route(r"/tasks/(\d+)/toggle", ("POST",))
def task_toggle(req, tid):
    req.require("tasks")
    t = get_task(req, tid)
    if t["status"] == "completed":
        req.run("UPDATE tasks SET status='pending', completed_at=NULL WHERE id=?", (t["id"],))
    else:
        req.run("UPDATE tasks SET status='completed', completed_at=? WHERE id=?", (dt.datetime.now().isoformat(timespec="seconds"), t["id"]))
        req.flash(f"“{t['title']}” done.")
    raise Redirect(safe_back(req, "/tasks"))


@route(r"/tasks/(\d+)/delete", ("POST",))
def task_delete(req, tid):
    req.require("delete")
    t = get_task(req, tid)
    req.run("DELETE FROM tasks WHERE id=?", (t["id"],))
    req.flash("Task deleted.")
    raise Redirect("/tasks")
'''

# --------------------------------------------------------------------------------------------------------------
# MODULE: jesse_farm.web
# --------------------------------------------------------------------------------------------------------------
MODULES['jesse_farm.web'] = r'''"""
A small web framework built on Python's standard library (http.server).

Why not Flask or Django? This system must install on a Windows PC with nothing but Python,
often with slow or no internet. Everything here is standard library, so there is nothing to
download, and every line can be read and explained in the thesis defence.

The flow of one request:
  browser -> Handler.dispatch -> Request (reads cookie, session, user, current farm)
          -> the route function in views/*.py -> HTML string or Response -> browser
"""
import datetime as dt
import hmac
import re
import secrets
import sys
import traceback
import urllib.parse
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler

from . import config, db
from .security import can


class Redirect(Exception):
    def __init__(self, location):
        self.location = location


class NotFound(Exception):
    pass


class Forbidden(Exception):
    def __init__(self, message="You don't have permission to do that."):
        self.message = message


class Response:
    """Anything that is not a normal HTML page: CSV downloads, files."""

    def __init__(self, body, content_type="text/html; charset=utf-8", filename=None, status=200):
        self.body = body if isinstance(body, bytes) else body.encode("utf-8")
        self.content_type = content_type
        self.filename = filename
        self.status = status


ROUTES = []


def route(pattern, methods=("GET",), public=False, needs_farm=True):
    """Register a page. public = no sign-in needed. needs_farm = a current farm must be selected."""

    def deco(fn):
        ROUTES.append((re.compile("^" + pattern + "$"), methods, fn, public, needs_farm))
        return fn

    return deco


class Request:
    def __init__(self, handler, method):
        self.handler = handler
        self.method = method
        parsed = urllib.parse.urlsplit(handler.path)
        self.path = parsed.path.rstrip("/") or "/"
        self.query = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
        self.raw_query = parsed.query
        self.form = {}
        self.form_lists = {}
        self.conn = db.connect()
        self.session = self.user = self.farm = self.role = None
        self.new_cookie = None
        self._load_session()

    # ---------------------------------------------------------------- session
    def read_form(self):
        length = int(self.handler.headers.get("Content-Length") or 0)
        if length > 2_000_000:
            raise ValueError("Form too large")
        raw = self.handler.rfile.read(length).decode("utf-8", "replace") if length else ""
        parsed = urllib.parse.parse_qs(raw, keep_blank_values=True)
        self.form = {k: v[0] for k, v in parsed.items()}
        self.form_lists = parsed

    def _load_session(self):
        cookie = SimpleCookie(self.handler.headers.get("Cookie", ""))
        token = cookie["sid"].value if "sid" in cookie else None
        if not token:
            return
        row = self.one("SELECT * FROM sessions WHERE token=? AND expires_at > ?", (token, dt.datetime.now().isoformat()))
        if not row:
            return
        self.session = row
        self.user = self.one("SELECT * FROM users WHERE id=?", (row["user_id"],))
        if self.user and row["farm_id"]:
            self._set_farm(row["farm_id"])
        if self.user and not self.farm:
            # No farm chosen yet (or it was removed): pick the user's first farm, if any
            first = self.one("SELECT farm_id FROM memberships WHERE user_id=? ORDER BY id LIMIT 1", (self.user["id"],))
            if first:
                self.switch_farm(first["farm_id"])

    def _set_farm(self, farm_id):
        m = self.one(
            "SELECT f.*, m.role FROM farms f JOIN memberships m ON m.farm_id=f.id WHERE f.id=? AND m.user_id=?",
            (farm_id, self.user["id"]),
        )
        if m:
            self.farm, self.role = m, m["role"]
        return bool(m)

    def switch_farm(self, farm_id):
        """Make another of the user's farms the current one. Returns False if they're not a member."""
        if not self._set_farm(farm_id):
            return False
        self.run("UPDATE sessions SET farm_id=? WHERE token=?", (farm_id, self.session["token"]))
        return True

    def login(self, user_id):
        token = secrets.token_urlsafe(32)
        expires = (dt.datetime.now() + dt.timedelta(days=config.SESSION_DAYS)).isoformat()
        first = self.one("SELECT farm_id FROM memberships WHERE user_id=? ORDER BY id LIMIT 1", (user_id,))
        self.run(
            "INSERT INTO sessions (token, user_id, csrf, expires_at, farm_id) VALUES (?,?,?,?,?)",
            (token, user_id, secrets.token_urlsafe(24), expires, first["farm_id"] if first else None),
        )
        self.run("DELETE FROM sessions WHERE expires_at < ?", (dt.datetime.now().isoformat(),))
        self.new_cookie = f"sid={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={config.SESSION_DAYS * 86400}"

    def logout(self):
        if self.session:
            self.run("DELETE FROM sessions WHERE token=?", (self.session["token"],))
        self.new_cookie = "sid=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
        self.session = self.user = self.farm = None

    def flash(self, text, bad=False):
        if self.session:
            self.run("UPDATE sessions SET flash=? WHERE token=?", (("bad:" if bad else "ok:") + text, self.session["token"]))

    def pop_flash(self):
        if not self.session:
            return ""
        row = self.one("SELECT flash FROM sessions WHERE token=?", (self.session["token"],))
        if row and row["flash"]:
            self.run("UPDATE sessions SET flash='' WHERE token=?", (self.session["token"],))
            return row["flash"]
        return ""

    def csrf_input(self):
        return f'<input type="hidden" name="csrf" value="{self.session["csrf"]}">' if self.session else ""

    # ---------------------------------------------------------------- permissions
    def can(self, permission):
        return bool(self.role) and can(self.role, permission)

    def require(self, permission):
        if not self.can(permission):
            raise Forbidden()

    @property
    def fid(self):
        return self.farm["id"]

    @property
    def country(self):
        return self.farm["country_code"]

    def my_farms(self):
        return self.all(
            """SELECT f.*, m.role FROM farms f JOIN memberships m ON m.farm_id=f.id
               WHERE m.user_id=? ORDER BY f.country_code, f.name""",
            (self.user["id"],),
        )

    # ---------------------------------------------------------------- database shortcuts
    def one(self, sql, params=()):
        return self.conn.execute(sql, params).fetchone()

    def all(self, sql, params=()):
        return self.conn.execute(sql, params).fetchall()

    def run(self, sql, params=()):
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return cur.lastrowid


class Handler(BaseHTTPRequestHandler):
    server_version = "JesseFMS/" + config.VERSION
    quiet = False

    def do_GET(self):
        self.dispatch("GET")

    def do_POST(self):
        self.dispatch("POST")

    def log_message(self, fmt, *args):
        if not self.quiet:
            sys.stderr.write("  %s %s\n" % (self.command, self.path))

    def send(self, status, body=b"", location=None, cookie=None, content_type="text/html; charset=utf-8", filename=None):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Cache-Control", "no-store")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        if location:
            self.send_header("Location", location)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(data)

    def dispatch(self, method):
        try:
            self._dispatch(method)
        except (BrokenPipeError, ConnectionResetError):
            pass  # the browser closed the connection before the reply was sent; nothing to do

    def _dispatch(self, method):
        from .ui import error_page  # imported here to avoid a circular import

        req = None
        try:
            req = Request(self, method)
            for pattern, methods, fn, public, needs_farm in ROUTES:
                m = pattern.match(req.path)
                if not m:
                    continue
                if method not in methods:
                    return self.send(405, error_page(req, "Not allowed", "That action isn't allowed here."))
                if method == "POST":
                    req.read_form()
                if not public:
                    if not req.user:
                        raise Redirect("/login")
                    if method == "POST" and not hmac.compare_digest(req.form.get("csrf", ""), req.session["csrf"]):
                        return self.send(403, error_page(req, "Form expired", "Go back, reload the page and try again."))
                    if needs_farm and not req.farm:
                        raise Redirect("/farms/new")
                result = fn(req, *m.groups())
                if isinstance(result, Response):
                    return self.send(result.status, result.body, cookie=req.new_cookie,
                                     content_type=result.content_type, filename=result.filename)
                return self.send(200, result, cookie=req.new_cookie)
            raise NotFound()
        except Redirect as r:
            self.send(303, b"", location=r.location, cookie=req.new_cookie if req else None)
        except NotFound:
            self.send(404, error_page(req, "Not found", "That page or record doesn't exist, or it belongs to another farm."))
        except Forbidden as f:
            self.send(403, error_page(req, "Not allowed", f.message))
        except Exception:
            traceback.print_exc()
            self.send(500, error_page(req, "Something went wrong",
                                      "The error was printed in the terminal window. Your data has not been changed."))
        finally:
            if req:
                req.conn.close()
'''


# ============================================================================ PART 2: LOADER
# Serves the modules above to Python's import system. __file__ is set as if the package sat next to this file,
# so the database and backups are stored beside jesse_farm_management_system.py.
_HERE = os.path.dirname(os.path.abspath(__file__))


class _OneFileImporter(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in MODULES:
            return importlib.util.spec_from_loader(fullname, self, is_package=fullname in PACKAGES)
        return None

    def create_module(self, spec):
        return None  # default module creation

    def exec_module(self, module):
        name = module.__name__
        parts = name.split(".")
        fake = os.path.join(_HERE, *parts) + (os.sep + "__init__.py" if name in PACKAGES else ".py")
        module.__file__ = fake
        if name in PACKAGES:
            module.__path__ = [os.path.dirname(fake)]
        code = compile(MODULES[name], fake, "exec")
        exec(code, module.__dict__)


sys.meta_path.insert(0, _OneFileImporter())


# ============================================================================ PART 3: ENTRY POINT (original run.py)
"""
JESSE FARM MANAGEMENT SYSTEM - start here.

    python run.py                 start the system and open it in your browser
    python run.py --demo          also load demonstration farms and accounts
    python run.py --port 8080     use another port
    python run.py --local-only    only this computer can connect (no phones)
    python run.py --backup        make a backup copy of the database and exit
    python run.py --restore FILE  replace the database with a backup and exit
    python run.py --reset-password EMAIL
                                  set a new password for a user who forgot theirs
    python run.py --import-old livestock.db
                                  bring in data from the earlier livestock_app.py

Needs only Python 3.11 or newer (tested on 3.11 and 3.13). Nothing to install.
"""
import argparse
import os
import shutil
import sys

from jesse_farm import config, db


def main():
    p = argparse.ArgumentParser(description=config.APP_NAME)
    p.add_argument("--port", type=int, default=config.DEFAULT_PORT)
    p.add_argument("--demo", action="store_true", help="load demonstration farms and accounts")
    p.add_argument("--no-browser", action="store_true", help="don't open the browser")
    p.add_argument("--local-only", action="store_true", help="only this computer can connect")
    p.add_argument("--quiet", action="store_true", help="don't print each request")
    p.add_argument("--backup", action="store_true", help="back up the database and exit")
    p.add_argument("--restore", metavar="FILE", help="restore the database from a backup file and exit")
    p.add_argument("--reset-password", metavar="EMAIL", help="set a new password for a user")
    p.add_argument("--import-old", metavar="FILE", help="import a livestock.db from the earlier livestock_app.py")
    a = p.parse_args()

    if sys.version_info < (3, 11):
        sys.exit("Python 3.11 or newer is needed. Download it from https://www.python.org/downloads/")

    if a.import_old:
        if os.path.exists(config.DB_PATH) and os.path.getsize(config.DB_PATH) > 0:
            sys.exit(f"{config.DB_PATH} already exists. Move it away first so nothing is overwritten.")
        shutil.copyfile(a.import_old, config.DB_PATH)
        db.init_db()
        print("Imported and upgraded. Each old farm was set to Zambia (or Rwanda if its country said so).")
        print("Sign in and open My farms -> Edit this farm to set its district.")
        return
    if a.reset_password:
        import getpass
        from jesse_farm.security import hash_password, password_problem
        db.init_db()
        conn = db.connect()
        user = conn.execute("SELECT id FROM users WHERE email=?", (a.reset_password.strip().lower(),)).fetchone()
        if not user:
            sys.exit("No account with that email.")
        new = getpass.getpass("New password (typing is hidden): ")
        if password_problem(new):
            sys.exit(password_problem(new))
        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(new), user["id"]))
        conn.execute("DELETE FROM sessions WHERE user_id=?", (user["id"],))
        conn.commit()
        print("Password changed.")
        return
    if a.restore:
        safety = db.restore_db(a.restore)
        print(f"Restored from {a.restore}." + (f" The previous database was saved as {safety}." if safety else ""))
        return
    db.init_db()
    if a.backup:
        print("Backup saved:", db.backup_db(label="manual"))
        return
    if a.demo:
        from jesse_farm.demo import create_demo
        if create_demo():
            print("  Demonstration data loaded.")

    from jesse_farm.app import serve
    serve(a.port, not a.no_browser, a.local_only, a.quiet, demo_note=a.demo)


if __name__ == "__main__":
    main()
