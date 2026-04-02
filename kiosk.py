"""PLM Guest Kiosk — sign-in, waiver, model release, interest capture."""

import sqlite3, csv, threading
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_file

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "kiosk.db"
CSV_PATH = APP_DIR / "guest_log.csv"
SERVICE_ACCOUNT = str(APP_DIR / "service-account.json")
SHEET_ID = "1laFiw_2cUfJAl3zxuR9D_jK8665TpDE0ohffH53P4QQ"

HEADERS = ["Timestamp", "Name", "Email", "Phone", "Guest Of",
           "Visit Reason", "Minor", "Guardian Name",
           "Guardian Contact", "Guest Waiver", "Workshop Waiver",
           "Model Release", "Interested in Membership", "Newsletter", "Calendar"]

app = Flask(__name__, static_folder=str(APP_DIR / "static"))


# --------------- database ---------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with get_db() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS guest_signins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            guest_of TEXT,
            visit_reason TEXT,
            is_minor INTEGER DEFAULT 0,
            guardian_name TEXT,
            guardian_contact TEXT,
            waiver_signed INTEGER DEFAULT 0,
            workshop_waiver_signed INTEGER DEFAULT 0,
            model_release_signed INTEGER DEFAULT 0,
            interested_in_membership INTEGER DEFAULT 0,
            join_newsletter INTEGER DEFAULT 0,
            join_calendar INTEGER DEFAULT 0,
            signed_in_at TEXT NOT NULL
        )""")


init_db()


# --------------- google sheets ---------------

_sheet = None

def get_sheet():
    global _sheet
    if _sheet is not None:
        return _sheet
    try:
        import gspread
        gc = gspread.service_account(filename=str(SERVICE_ACCOUNT))
        spreadsheet = gc.open_by_key(SHEET_ID)
        _sheet = spreadsheet.sheet1
        # write headers if sheet is empty
        if not _sheet.row_values(1):
            _sheet.append_row(HEADERS)
        return _sheet
    except Exception as e:
        print(f"[SHEETS] Failed to connect: {e}")
        return None


def _append_to_sheet(row_data):
    """Append a row to Google Sheet in background thread."""
    def _do():
        try:
            sheet = get_sheet()
            if sheet:
                sheet.append_row(row_data)
                print(f"[SHEETS] Wrote row for {row_data[1]}")
        except Exception as e:
            print(f"[SHEETS] Error: {e}")
            # reset connection on error
            global _sheet
            _sheet = None
    threading.Thread(target=_do, daemon=True).start()


def _row_from_record(r):
    return [
        r["signed_in_at"], r["name"], r["email"],
        r["phone"], r["guest_of"], r["visit_reason"],
        "Yes" if r["is_minor"] else "No",
        r["guardian_name"], r["guardian_contact"],
        "Yes" if r["waiver_signed"] else "No",
        "Yes" if r["workshop_waiver_signed"] else "No",
        "Yes" if r["model_release_signed"] else "No",
        "Yes" if r["interested_in_membership"] else "No",
        "Yes" if r["join_newsletter"] else "No",
        "Yes" if r["join_calendar"] else "No",
    ]


# --------------- routes ---------------

_refresh_flag = False

@app.get("/")
def index():
    return send_file(APP_DIR / "kiosk.html")

@app.get("/api/check-refresh")
def check_refresh():
    global _refresh_flag
    if _refresh_flag:
        _refresh_flag = False
        return jsonify({"refresh": True})
    return jsonify({"refresh": False})

@app.post("/api/trigger-refresh")
def trigger_refresh():
    global _refresh_flag
    _refresh_flag = True
    return jsonify({"ok": True})


@app.post("/api/signin")
def signin():
    d = request.json or {}
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # normalize text fields once
    name = d.get("name", "").strip()
    email = d.get("email", "").strip()
    phone = d.get("phone", "").strip()
    guest_of = d.get("guest_of", "").strip()
    visit_reason = d.get("visit_reason", "")
    is_minor = 1 if d.get("is_minor") else 0
    guardian_name = d.get("guardian_name", "").strip()
    guardian_contact = d.get("guardian_contact", "").strip()
    waiver = 1 if d.get("waiver_signed") else 0
    workshop_waiver = 1 if d.get("workshop_waiver_signed") else 0
    model_release = 1 if d.get("model_release_signed") else 0
    membership = 1 if d.get("interested_in_membership") else 0
    newsletter = 1 if d.get("join_newsletter") else 0
    calendar = 1 if d.get("join_calendar") else 0

    with get_db() as db:
        db.execute("""INSERT INTO guest_signins
            (name, email, phone, guest_of, visit_reason, is_minor,
             guardian_name, guardian_contact, waiver_signed,
             workshop_waiver_signed, model_release_signed,
             interested_in_membership, join_newsletter, join_calendar, signed_in_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (name, email, phone, guest_of, visit_reason, is_minor,
             guardian_name, guardian_contact, waiver, workshop_waiver,
             model_release, membership, newsletter, calendar, now))

        # re-fetch the inserted row to build the sheet/CSV data via _row_from_record
        row_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        record = db.execute(
            "SELECT * FROM guest_signins WHERE id = ?", (row_id,)
        ).fetchone()

    _export_csv()
    _append_to_sheet(_row_from_record(record))

    return jsonify({"ok": True})


@app.get("/api/guests")
def guests():
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM guest_signins ORDER BY signed_in_at DESC"
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.get("/export")
def export():
    """Download guest log as CSV."""
    _export_csv()
    if CSV_PATH.exists():
        return send_file(CSV_PATH, as_attachment=True,
                         download_name="plm_guest_log.csv")
    return "No data yet", 404


# --------------- helpers ---------------

def _export_csv():
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM guest_signins ORDER BY signed_in_at DESC"
        ).fetchall()
    if not rows:
        return
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADERS)
        for r in rows:
            w.writerow(_row_from_record(r))


if __name__ == "__main__":
    # pre-connect to sheet on startup
    threading.Thread(target=get_sheet, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False)
