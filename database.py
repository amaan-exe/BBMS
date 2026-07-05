import sqlite3
import sys
import os
from datetime import datetime, timedelta

from constants import RESERVE_INVENTORY

# Add CrypTXT to path for custom encryption (resolved relative to this file)
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_CRYPTXT_PATH = os.path.join(_THIS_DIR, "..", "..", "..", "work", "bloodbank", "CrypTXT")
if not os.path.isdir(_CRYPTXT_PATH):
    # Fallback: try the absolute path
    _CRYPTXT_PATH = r"d:\work\bloodbank\CrypTXT"
sys.path.insert(0, os.path.normpath(_CRYPTXT_PATH))
from function import nibble_encrypt, nibble_decrypt

DB_NAME = "blood.db"
_ADMIN_USERNAME = "Admin"
_ADMIN_PASSWORD = "1234"
_ADMIN_CONTACT = "827101179"
_ADMIN_RECOVERY = "AdminRecovery"
_ADMIN_QUESTION = "what is your hobby?"

_BLOOD_TOTAL_COLUMNS = {
    "A+": "Aplus",
    "B+": "Bplus",
    "O+": "Oplus",
    "AB+": "ABplus",
    "A-": "Aneg",
    "B-": "Bneg",
    "O-": "Oneg",
    "AB-": "ABneg",
}


def generate_portal_password(mobile, record_id):
    """Uses the user's phone number as the portal password."""
    return mobile

def connect_db():
    # Use a reasonable timeout and enable WAL + relaxed sync for better concurrent write/read performance.
    conn = sqlite3.connect(DB_NAME, timeout=30)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
    except Exception:
        pass
    return conn

def setup_tables():
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE if not exists donater (
        date varchar(20),
        Name varchar(30),
        Gender char(15),
        Pincode varchar(20),
        Mobile varchar(10),
        Nationality varchar(50),
        Idproof varchar(20),
        Idnumber varchar(20) UNIQUE,
        Age varchar(20),
        Bloodtype varchar(20),
        Unitml varchar(20),
        PRIMARY KEY (Mobile));''')

    cursor.execute('''CREATE TABLE if not exists receiver (
        date varchar(20),
        Name varchar(30),
        Gender char(15),
        Pincode varchar(20),
        Mobile varchar(10),
        Nationality varchar(50),
        Idproof varchar(20),
        Idnumber varchar(20) UNIQUE,
        Age varchar(20),
        Bloodtype varchar(20),
        Unitml varchar(20),
        PRIMARY KEY (Mobile));''')

    cursor.execute('''CREATE TABLE if not exists total (
        Aplus INT,
        Bplus INT,
        Oplus INT,
        ABplus INT,
        Aneg INT,
        Bneg INT,
        Oneg INT,
        ABneg INT);''')

    cursor.execute('''CREATE TABLE if not exists blood_allocations (
        donor_mobile varchar(10),
        donor_idnumber varchar(20),
        receiver_mobile varchar(10),
        receiver_idnumber varchar(20),
        bloodtype varchar(20),
        allocated_units INT,
        donor_date varchar(20),
        receiver_date varchar(20)
    );''')

    _ensure_login_table(cursor)

    # Initialize total table if empty
    cursor.execute("SELECT * FROM total")
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO total VALUES (0,0,0,0,0,0,0,0)")

    _seed_admin_account(cursor)
    _rebuild_inventory_totals(cursor)

    # Create indexes to speed common lookup operations
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_donater_mobile ON donater(Mobile)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_donater_idnumber ON donater(Idnumber)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_donater_bloodtype ON donater(Bloodtype)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_receiver_mobile ON receiver(Mobile)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_receiver_idnumber ON receiver(Idnumber)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_receiver_bloodtype ON receiver(Bloodtype)")
    except Exception:
        pass

    # --- RBAC Migration: Add 'role' column if it doesn't exist ---
    try:
        cursor.execute("ALTER TABLE login ADD COLUMN role varchar(10) DEFAULT 'staff'")
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()
    conn.close()


def migrate_current_portal_users():
    """Public wrapper used by startup or manual recovery to refresh portal credentials."""
    refresh_current_portal_users()


def purge_demo_data():
    """Public cleanup helper to remove seeded demo donors, receivers, and allocations."""
    with connect_db() as conn:
        cursor = conn.cursor()
        _purge_demo_data(cursor)
        _rebuild_receiver_allocations(cursor)
        _rebuild_inventory_totals(cursor)
        conn.commit()


def _seed_demo_data(cursor):
    pass


def _purge_demo_data(cursor):
    pass



def _rebuild_inventory_totals(cursor):
    # Inventory should be derived from actual donated units minus allocated units
    # (i.e., what's physically available). This prevents negative inventory
    # and keeps the dashboard consistent with allocations.
    # Compute donated totals per blood type
    donated = {bt: 0 for bt in _BLOOD_TOTAL_COLUMNS.keys()}
    cursor.execute("SELECT Bloodtype, COALESCE(SUM(CAST(Unitml AS INTEGER)), 0) FROM donater GROUP BY Bloodtype")
    for blood_type, total_units in cursor.fetchall():
        if blood_type in donated:
            donated[blood_type] = int(total_units or 0)

    # Compute allocated totals per blood type from allocations table
    allocated = {bt: 0 for bt in _BLOOD_TOTAL_COLUMNS.keys()}
    cursor.execute("SELECT bloodtype, COALESCE(SUM(allocated_units), 0) FROM blood_allocations GROUP BY bloodtype")
    for blood_type, total_alloc in cursor.fetchall():
        if blood_type in allocated:
            allocated[blood_type] = int(total_alloc or 0)

    # Net available = donated - allocated (never negative)
    net_available = {bt: max(0, donated.get(bt, 0) - allocated.get(bt, 0)) for bt in donated}

    # Map to DB total columns order
    values = [
        net_available.get("A+", 0),
        net_available.get("B+", 0),
        net_available.get("O+", 0),
        net_available.get("AB+", 0),
        net_available.get("A-", 0),
        net_available.get("B-", 0),
        net_available.get("O-", 0),
        net_available.get("AB-", 0),
    ]

    cursor.execute("DELETE FROM total")
    cursor.execute("INSERT INTO total VALUES (?,?,?,?,?,?,?,?)", values)


def _seed_admin_account(cursor):
    encrypted_pw = encrypt_password(_ADMIN_PASSWORD)
    encrypted_recode = encrypt_password(_ADMIN_RECOVERY)
    cursor.execute(
        '''INSERT INTO login (fullname, username, contact, recode, pass, conpass, reques, role)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(username) DO UPDATE SET
               fullname=excluded.fullname,
               contact=excluded.contact,
               recode=excluded.recode,
               pass=excluded.pass,
               conpass=excluded.conpass,
               reques=excluded.reques,
               role=excluded.role''',
        (
            "Admin",
            _ADMIN_USERNAME,
            _ADMIN_CONTACT,
            encrypted_recode,
            encrypted_pw,
            encrypted_pw,
            _ADMIN_QUESTION,
            "admin",
        ),
    )


def _upsert_portal_account(cursor, fullname, mobile, record_id, role, question="portal account"):
    password = generate_portal_password(mobile, record_id)
    encrypted_pw = encrypt_password(password)
    encrypted_recode = encrypt_password(record_id)

    cursor.execute("SELECT role FROM login WHERE username=?", (mobile,))
    row = cursor.fetchone()
    effective_role = role
    if row and row[0] in {"donor", "receiver", "member"} and row[0] != role:
        effective_role = "member"
    elif row and row[0] in {"donor", "receiver", "member"}:
        effective_role = row[0]

    if row:
        cursor.execute(
            """UPDATE login
               SET fullname=?, contact=?, recode=?, pass=?, conpass=?, reques=?, role=?
               WHERE username=?""",
            (fullname, mobile, encrypted_recode, encrypted_pw, encrypted_pw, question, effective_role, mobile),
        )
    else:
        cursor.execute(
            """INSERT INTO login (fullname, username, contact, recode, pass, conpass, reques, role)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (fullname, mobile, mobile, encrypted_recode, encrypted_pw, encrypted_pw, question, effective_role),
        )

    return password, effective_role


def _upsert_portal_account_with_cursor(cursor, fullname, mobile, record_id, role, question="portal account"):
    password = generate_portal_password(mobile, record_id)
    encrypted_pw = encrypt_password(password)
    encrypted_recode = encrypt_password(record_id)

    cursor.execute("SELECT role FROM login WHERE username=?", (mobile,))
    row = cursor.fetchone()
    effective_role = role
    if row and row[0] in {"donor", "receiver", "member"} and row[0] != role:
        effective_role = "member"
    elif row and row[0] in {"donor", "receiver", "member"}:
        effective_role = row[0]

    if row:
        cursor.execute(
            """UPDATE login
               SET fullname=?, contact=?, recode=?, pass=?, conpass=?, reques=?, role=?
               WHERE username=?""",
            (fullname, mobile, encrypted_recode, encrypted_pw, encrypted_pw, question, effective_role, mobile),
        )
    else:
        cursor.execute(
            """INSERT INTO login (fullname, username, contact, recode, pass, conpass, reques, role)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (fullname, mobile, mobile, encrypted_recode, encrypted_pw, encrypted_pw, question, effective_role),
        )

    return password, effective_role


def _provision_existing_user_login(cursor, mobile):
    cursor.execute("SELECT Name, Idnumber FROM donater WHERE Mobile=?", (mobile,))
    donor_row = cursor.fetchone()
    cursor.execute("SELECT Name, Idnumber FROM receiver WHERE Mobile=?", (mobile,))
    receiver_row = cursor.fetchone()

    if not donor_row and not receiver_row:
        return None

    if donor_row and receiver_row:
        fullname = donor_row[0] or receiver_row[0] or mobile
        record_id = donor_row[1] or receiver_row[1] or mobile
        role = "member"
    elif donor_row:
        fullname = donor_row[0] or mobile
        record_id = donor_row[1] or mobile
        role = "donor"
    else:
        fullname = receiver_row[0] or mobile
        record_id = receiver_row[1] or mobile
        role = "receiver"

    return _upsert_portal_account(cursor, fullname, mobile, record_id, role, question="Auto-generated portal account")


def _backfill_existing_portal_accounts(cursor):
    cursor.execute("SELECT Mobile FROM donater UNION SELECT Mobile FROM receiver")
    mobiles = [row[0] for row in cursor.fetchall() if row and row[0]]
    for mobile in mobiles:
        _provision_existing_user_login(cursor, mobile)


def refresh_current_portal_users():
    """Force all current donor/receiver portal users to use the latest phone-password login."""
    with connect_db() as conn:
        cursor = conn.cursor()
        _backfill_existing_portal_accounts(cursor)
        _rebuild_receiver_allocations(cursor)
        conn.commit()


def ensure_portal_account(fullname, mobile, record_id, role, question="portal account"):
    """Creates or updates a donor/receiver portal account keyed by mobile number."""
    password = generate_portal_password(mobile, record_id)
    encrypted_pw = encrypt_password(password)
    encrypted_recode = encrypt_password(record_id)

    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM login WHERE username=?", (mobile,))
        row = cursor.fetchone()
        effective_role = role
        if row and row[0] in {"donor", "receiver", "member"} and row[0] != role:
            effective_role = "member"
        elif row and row[0] in {"donor", "receiver", "member"}:
            effective_role = row[0]

        if row:
            cursor.execute(
                """UPDATE login
                   SET fullname=?, contact=?, recode=?, pass=?, conpass=?, reques=?, role=?
                   WHERE username=?""",
                (fullname, mobile, encrypted_recode, encrypted_pw, encrypted_pw, question, effective_role, mobile),
            )
        else:
            cursor.execute(
                """INSERT INTO login (fullname, username, contact, recode, pass, conpass, reques, role)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (fullname, mobile, mobile, encrypted_recode, encrypted_pw, encrypted_pw, question, effective_role),
            )

    return password, effective_role


def delete_portal_account(mobile):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM login WHERE username=?", (mobile,))


def sync_portal_account(previous_mobile, fullname, mobile, record_id, role, question="portal account"):
    if previous_mobile and previous_mobile != mobile:
        delete_portal_account(previous_mobile)
    return ensure_portal_account(fullname, mobile, record_id, role, question)


def _parse_date_for_sorting(date_text):
    try:
        return datetime.strptime(date_text, "%d/%m/%y")
    except Exception:
        return datetime.min


def _fetch_allocated_by_donor(cursor, donor_mobile):
    cursor.execute(
        "SELECT donor_idnumber, COALESCE(SUM(allocated_units), 0) FROM blood_allocations WHERE donor_mobile=? GROUP BY donor_idnumber",
        (donor_mobile,),
    )
    return {row[0]: int(row[1] or 0) for row in cursor.fetchall()}


def _fetch_allocated_by_receiver(cursor, receiver_mobile):
    cursor.execute(
        "SELECT receiver_idnumber, COALESCE(SUM(allocated_units), 0) FROM blood_allocations WHERE receiver_mobile=? GROUP BY receiver_idnumber",
        (receiver_mobile,),
    )
    return {row[0]: int(row[1] or 0) for row in cursor.fetchall()}


def _fetch_allocation_details_for_donor(cursor, donor_mobile):
    cursor.execute(
        """
        SELECT a.donor_idnumber, a.receiver_mobile, COALESCE(r.Name, a.receiver_mobile), a.receiver_idnumber, a.receiver_date, a.allocated_units
        FROM blood_allocations a
        LEFT JOIN receiver r ON r.Mobile = a.receiver_mobile
        WHERE a.donor_mobile=?
        ORDER BY a.donor_idnumber, a.receiver_date
        """,
        (donor_mobile,),
    )

    allocation_map = {}
    for donor_idnumber, receiver_mobile, receiver_name, receiver_idnumber, receiver_date, allocated_units in cursor.fetchall():
        allocation_map.setdefault(donor_idnumber, []).append({
            "receiver_mobile": receiver_mobile,
            "receiver_name": receiver_name,
            "receiver_idnumber": receiver_idnumber,
            "receiver_date": receiver_date,
            "allocated_units": int(allocated_units or 0),
        })
    return allocation_map


def _fetch_allocation_details_for_receiver(cursor, receiver_mobile):
    cursor.execute(
        """
        SELECT a.receiver_idnumber, a.donor_mobile, COALESCE(d.Name, a.donor_mobile), a.donor_idnumber, a.donor_date, a.allocated_units
        FROM blood_allocations a
        LEFT JOIN donater d ON d.Mobile = a.donor_mobile
        WHERE a.receiver_mobile=?
        ORDER BY a.receiver_idnumber, a.donor_date
        """,
        (receiver_mobile,),
    )

    allocation_map = {}
    for receiver_idnumber, donor_mobile, donor_name, donor_idnumber, donor_date, allocated_units in cursor.fetchall():
        allocation_map.setdefault(receiver_idnumber, []).append({
            "donor_mobile": donor_mobile,
            "donor_name": donor_name,
            "donor_idnumber": donor_idnumber,
            "donor_date": donor_date,
            "allocated_units": int(allocated_units or 0),
        })
    return allocation_map


def _allocate_blood_to_receiver_with_cursor(cursor, receiver_mobile, receiver_idnumber, bloodtype, needed_units, receiver_date):
    # Allocate using FIFO across compatible donor blood types while respecting reserve.
    # Compatibility order (best match first)
    COMPATIBILITY = {
        "A+": ["A+", "A-", "O+", "O-"],
        "A-": ["A-", "O-"],
        "B+": ["B+", "B-", "O+", "O-"],
        "B-": ["B-", "O-"],
        "O+": ["O+", "O-"],
        "O-": ["O-"],
        "AB+": ["AB+", "AB-", "A+", "A-", "B+", "B-", "O+", "O-"],
        "AB-": ["AB-", "A-", "B-", "O-"],
    }

    needed = int(needed_units)
    if needed <= 0:
        return 0

    candidate_types = COMPATIBILITY.get(bloodtype, [bloodtype])

    # Load donor rows for all candidate types
    placeholders = ','.join(['?'] * len(candidate_types))
    cursor.execute(f"SELECT Mobile, Idnumber, date, Bloodtype, CAST(Unitml AS INTEGER) FROM donater WHERE Bloodtype IN ({placeholders})", tuple(candidate_types))
    donor_rows = cursor.fetchall()

    # Sort globally by donor date (oldest first)
    donor_rows.sort(key=lambda row: _parse_date_for_sorting(row[2]))

    # Track per-donor used units (by Idnumber) and per-bloodtype allocated totals so far
    cursor.execute("SELECT donor_idnumber, COALESCE(SUM(allocated_units),0) FROM blood_allocations GROUP BY donor_idnumber")
    existing_used = {row[0]: int(row[1] or 0) for row in cursor.fetchall()}

    cursor.execute("SELECT bloodtype, COALESCE(SUM(allocated_units),0) FROM blood_allocations GROUP BY bloodtype")
    allocated_by_group = {row[0]: int(row[1] or 0) for row in cursor.fetchall()}

    # Compute total donated per bloodtype to respect reserves
    cursor.execute("SELECT Bloodtype, COALESCE(SUM(CAST(Unitml AS INTEGER)),0) FROM donater GROUP BY Bloodtype")
    donated_by_group = {row[0]: int(row[1] or 0) for row in cursor.fetchall()}

    remaining_needed = needed
    allocated_total = 0

    for donor_mobile, donor_idnumber, donor_date, donor_bt, donated_units in donor_rows:
        if remaining_needed <= 0:
            break
        donated_units = int(donated_units or 0)
        already_used = existing_used.get(donor_idnumber, 0)
        available = max(0, donated_units - already_used)
        if available <= 0:
            continue

        # Enforce reserve at bloodtype level: do not reduce netAvailable below reserve.
        group_allocated = allocated_by_group.get(donor_bt, 0)
        group_donated = donated_by_group.get(donor_bt, 0)
        reserve_limit = RESERVE_INVENTORY.get(donor_bt, 0)

        # Maximum we can allocate from this donor without breaching reserve for the group
        max_alloc_group = max(0, group_donated - group_allocated - reserve_limit)
        if max_alloc_group <= 0:
            # nothing available from this blood group (reserve anchored)
            continue

        # But we also cannot allocate more than the donor's available
        allocatable = min(available, max_alloc_group)
        if allocatable <= 0:
            continue

        allocation = min(allocatable, remaining_needed)

        cursor.execute(
            """INSERT INTO blood_allocations
               (donor_mobile, donor_idnumber, receiver_mobile, receiver_idnumber, bloodtype, allocated_units, donor_date, receiver_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (donor_mobile, donor_idnumber, receiver_mobile, receiver_idnumber, donor_bt, allocation, donor_date, receiver_date),
        )

        # update trackers
        existing_used[donor_idnumber] = already_used + allocation
        allocated_by_group[donor_bt] = group_allocated + allocation
        remaining_needed -= allocation
        allocated_total += allocation

    return allocated_total


def _rebuild_receiver_allocations(cursor):
    # Recompute allocations from scratch while respecting reserves, FIFO and compatibility.
    cursor.execute("DELETE FROM blood_allocations")

    # Order receivers by request date (oldest first) to satisfy FIFO for requests
    cursor.execute("SELECT Mobile, Idnumber, date, Bloodtype, CAST(Unitml AS INTEGER) FROM receiver ORDER BY date, Mobile")
    receiver_rows = cursor.fetchall()

    for receiver_mobile, receiver_idnumber, receiver_date, bloodtype, needed_units in receiver_rows:
        try:
            _allocate_blood_to_receiver_with_cursor(cursor, receiver_mobile, receiver_idnumber, bloodtype, needed_units, receiver_date)
        except Exception:
            # On failure for a particular receiver, continue with others to avoid halting the rebuild.
            continue


def allocate_blood_to_receiver(receiver_mobile, receiver_idnumber, bloodtype, needed_units, receiver_date):
    """Allocates blood from oldest matching donor batches using FIFO logic."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT Mobile, Idnumber, date, CAST(Unitml AS INTEGER) FROM donater WHERE Bloodtype=?", (bloodtype,))
    donor_rows = cursor.fetchall()
    donor_rows.sort(key=lambda row: _parse_date_for_sorting(row[2]))

    used_map = _fetch_allocated_by_donor(cursor, None) if False else {}
    cursor.execute(
        "SELECT donor_idnumber, COALESCE(SUM(allocated_units), 0) FROM blood_allocations WHERE bloodtype=? GROUP BY donor_idnumber",
        (bloodtype,),
    )
    used_map = {row[0]: int(row[1] or 0) for row in cursor.fetchall()}

    remaining_needed = int(needed_units)
    allocated_total = 0

    for donor_mobile, donor_idnumber, donor_date, donated_units in donor_rows:
        if remaining_needed <= 0:
            break
        already_used = used_map.get(donor_idnumber, 0)
        available = max(0, int(donated_units) - already_used)
        if available <= 0:
            continue
        allocation = min(available, remaining_needed)
        cursor.execute(
            """INSERT INTO blood_allocations
               (donor_mobile, donor_idnumber, receiver_mobile, receiver_idnumber, bloodtype, allocated_units, donor_date, receiver_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (donor_mobile, donor_idnumber, receiver_mobile, receiver_idnumber, bloodtype, allocation, donor_date, receiver_date),
        )
        used_map[donor_idnumber] = already_used + allocation
        remaining_needed -= allocation
        allocated_total += allocation

    conn.commit()
    conn.close()
    return allocated_total


def release_receiver_allocations(receiver_mobile):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM blood_allocations WHERE receiver_mobile=?", (receiver_mobile,))


def get_donor_portal_summary(mobile):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT Name FROM donater WHERE Mobile=?", (mobile,))
    name_row = cursor.fetchone()
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(CAST(Unitml AS INTEGER)), 0) FROM donater WHERE Mobile=?", (mobile,))
    donation_count, donated_units = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) FROM donater WHERE Mobile=?", (mobile,))
    donation_count = cursor.fetchone()[0]
    cursor.execute("SELECT COALESCE(SUM(allocated_units), 0) FROM blood_allocations WHERE donor_mobile=?", (mobile,))
    used_units = int(cursor.fetchone()[0] or 0)
    conn.close()
    donated_units = int(donated_units or 0)
    remaining_units = max(0, donated_units - used_units)
    return {
        "name": name_row[0] if name_row else mobile,
        "donation_count": donation_count,
        "donated_units": donated_units,
        "used_units": used_units,
        "remaining_units": remaining_units,
    }


def get_receiver_portal_summary(mobile):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT Name FROM receiver WHERE Mobile=?", (mobile,))
    name_row = cursor.fetchone()
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(CAST(Unitml AS INTEGER)), 0) FROM receiver WHERE Mobile=?", (mobile,))
    request_count, requested_units = cursor.fetchone()
    cursor.execute("SELECT COALESCE(SUM(allocated_units), 0) FROM blood_allocations WHERE receiver_mobile=?", (mobile,))
    allocated_units = int(cursor.fetchone()[0] or 0)
    conn.close()
    requested_units = int(requested_units or 0)
    pending_units = max(0, requested_units - allocated_units)
    return {
        "name": name_row[0] if name_row else mobile,
        "request_count": request_count,
        "requested_units": requested_units,
        "allocated_units": allocated_units,
        "pending_units": pending_units,
    }


def get_donor_portal_records(mobile):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT date, Name, Idnumber, Bloodtype, CAST(Unitml AS INTEGER) FROM donater WHERE Mobile=?", (mobile,))
    donor_rows = cursor.fetchall()
    allocated_map = _fetch_allocated_by_donor(cursor, mobile)
    allocation_details = _fetch_allocation_details_for_donor(cursor, mobile)
    conn.close()

    records = []
    for date_text, name, idnumber, bloodtype, units in donor_rows:
        used = int(allocated_map.get(idnumber, 0))
        remaining = max(0, int(units) - used)
        usage_rows = allocation_details.get(idnumber, [])
        if usage_rows:
            latest_use = max(usage_rows, key=lambda item: _parse_date_for_sorting(item["receiver_date"]))
            used_by = latest_use["receiver_name"]
            used_on = latest_use["receiver_date"]
            usage_count = len(usage_rows)
        else:
            used_by = ""
            used_on = ""
            usage_count = 0
        if used == 0:
            status = "Unused"
        elif remaining == 0:
            status = "Fully Used"
        else:
            status = "Partially Used"
        records.append({
            "date": date_text,
            "name": name,
            "idnumber": idnumber,
            "blood_type": bloodtype,
            "donated_units": int(units),
            "used_units": used,
            "remaining_units": remaining,
            "used_by": used_by,
            "used_on": used_on,
            "usage_count": usage_count,
            "status": status,
        })
    records.sort(key=lambda item: _parse_date_for_sorting(item["date"]))
    return records


def get_receiver_portal_records(mobile):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT date, Name, Idnumber, Bloodtype, CAST(Unitml AS INTEGER) FROM receiver WHERE Mobile=?", (mobile,))
    receiver_rows = cursor.fetchall()
    allocated_map = _fetch_allocated_by_receiver(cursor, mobile)
    allocation_details = _fetch_allocation_details_for_receiver(cursor, mobile)
    conn.close()

    records = []
    for date_text, name, idnumber, bloodtype, units in receiver_rows:
        allocated = int(allocated_map.get(idnumber, 0))
        pending = max(0, int(units) - allocated)
        usage_rows = allocation_details.get(idnumber, [])
        if usage_rows:
            latest_use = max(usage_rows, key=lambda item: _parse_date_for_sorting(item["donor_date"]))
            received_from = latest_use["donor_name"]
            received_from_id = latest_use["donor_idnumber"]
            received_on = latest_use["donor_date"]
            allocation_count = len(usage_rows)
        else:
            received_from = ""
            received_from_id = ""
            received_on = ""
            allocation_count = 0
        if allocated == 0:
            status = "Pending"
        elif pending == 0:
            status = "Fulfilled"
        else:
            status = "Partially Fulfilled"
        records.append({
            "date": date_text,
            "name": name,
            "idnumber": idnumber,
            "blood_type": bloodtype,
            "requested_units": int(units),
            "allocated_units": allocated,
            "pending_units": pending,
            "received_from": received_from,
            "received_from_id": received_from_id,
            "received_on": received_on,
            "allocation_count": allocation_count,
            "status": status,
        })
    records.sort(key=lambda item: _parse_date_for_sorting(item["date"]))
    return records


def rebuild_allocations_and_totals():
    """Maintenance helper: recompute receiver allocations and inventory totals.

    This is intentionally explicit so UI callers can request a consistent
    recomputation after destructive edits (update/delete) where local
    incremental bookkeeping is error-prone.
    """
    with connect_db() as conn:
        cursor = conn.cursor()
        _rebuild_receiver_allocations(cursor)
        _rebuild_inventory_totals(cursor)
        conn.commit()


def _ensure_login_table(cursor):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='login'")
    exists = cursor.fetchone() is not None

    if not exists:
        cursor.execute('''CREATE TABLE login (
            fullname varchar(30),
            username varchar(30) UNIQUE,
            contact varchar(30),
            recode varchar(30),
            pass varchar(30),
            conpass varchar(30),
            reques varchar(200),
            role varchar(10) DEFAULT 'staff'
        )''')
        return

    cursor.execute("PRAGMA table_info(login)")
    columns = cursor.fetchall()
    column_names = {column[1] for column in columns}
    recode_is_pk = any(column[1] == "recode" and column[5] for column in columns)

    if not recode_is_pk and "role" in column_names:
        return

    cursor.execute("DROP TABLE IF EXISTS login_migration_tmp")
    cursor.execute("ALTER TABLE login RENAME TO login_migration_tmp")
    cursor.execute('''CREATE TABLE login (
        fullname varchar(30),
        username varchar(30) UNIQUE,
        contact varchar(30),
        recode varchar(30),
        pass varchar(30),
        conpass varchar(30),
        reques varchar(200),
        role varchar(10) DEFAULT 'staff'
    )''')

    role_expr = "role" if "role" in column_names else "'staff'"
    cursor.execute(f'''
        INSERT INTO login (fullname, username, contact, recode, pass, conpass, reques, role)
        SELECT fullname, username, contact, recode, pass, conpass, reques, {role_expr}
        FROM login_migration_tmp
    ''')
    cursor.execute("DROP TABLE login_migration_tmp")

# --- Password Encryption (CrypTXT) ---
def encrypt_password(password):
    """Encrypts a password using CrypTXT nibble encryption."""
    encrypted_chars = nibble_encrypt(password)
    return ''.join(encrypted_chars)

def decrypt_password(encrypted):
    """Decrypts a password using CrypTXT nibble decryption."""
    char_list = list(encrypted)
    return nibble_decrypt(char_list)

# --- User Auth Queries ---
def get_user_by_username(username):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM login WHERE username=?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row

def register_user(fullname, username, contact, recode, password, conpass, reques, role="staff"):
    encrypted_pw = encrypt_password(password)
    encrypted_recode = encrypt_password(recode)

    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO login (fullname,username,contact,recode,pass,conpass,reques,role) VALUES (?,?,?,?,?,?,?,?)", 
                       (fullname, username, contact, encrypted_recode, encrypted_pw, encrypted_pw, reques, role))

def login_user(username, password):
    conn = connect_db()
    cursor = conn.cursor()
    encrypted_pw = encrypt_password(password)
    # Try encrypted first, then plain text for backward compatibility
    cursor.execute("SELECT * FROM login WHERE username=? AND pass=?", (username, encrypted_pw))
    row = cursor.fetchone()
    if row is None:
        _provision_existing_user_login(cursor, username)
        conn.commit()
        cursor.execute("SELECT * FROM login WHERE username=? AND pass=?", (username, encrypted_pw))
        row = cursor.fetchone()
    if row is None:
        # Fallback: check plain text password (pre-encryption users)
        cursor.execute("SELECT * FROM login WHERE username=? AND pass=?", (username, password))
        row = cursor.fetchone()
        if row:
            # Migrate to encrypted password
            cursor.execute("UPDATE login SET pass=?, conpass=? WHERE username=?", (encrypted_pw, encrypted_pw, username))
            conn.commit()
    conn.close()
    return row

def get_user_role(username):
    """Returns the role of a user (admin/staff)."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM login WHERE username=?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "staff"

def verify_recovery(username, recode):
    conn = connect_db()
    cursor = conn.cursor()
    encrypted_recode = encrypt_password(recode)
    # Try encrypted first
    cursor.execute("SELECT * FROM login WHERE username=? AND recode=?", (username, encrypted_recode))
    row = cursor.fetchone()
    if row is None:
        # Fallback: check plain text (pre-encryption users)
        cursor.execute("SELECT * FROM login WHERE username=? AND recode=?", (username, recode))
        row = cursor.fetchone()
        if row:
            # Migrate to encrypted recode
            cursor.execute("UPDATE login SET recode=? WHERE username=?", (encrypted_recode, username))
            conn.commit()
    conn.close()
    return row

def update_password(username, recode, new_password):
    conn = connect_db()
    cursor = conn.cursor()
    encrypted_pw = encrypt_password(new_password)
    encrypted_recode = encrypt_password(recode)
    # Try with encrypted recode first, then plain text fallback
    cursor.execute("UPDATE login SET pass=?, conpass=? WHERE username=? AND recode=?", (encrypted_pw, encrypted_pw, username, encrypted_recode))
    if cursor.rowcount == 0:
        cursor.execute("UPDATE login SET pass=?, conpass=? WHERE username=? AND recode=?", (encrypted_pw, encrypted_pw, username, recode))
    conn.commit()
    conn.close()

# --- Inventory Queries ---
def get_blood_total():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM total")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_specific_blood_total(blood_group_column):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT {blood_group_column} FROM total")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0


def _get_specific_blood_total_with_cursor(cursor, blood_group_column):
    cursor.execute(f"SELECT {blood_group_column} FROM total")
    row = cursor.fetchone()
    return row[0] if row else 0

def update_blood_total(blood_group_column, new_amount):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE total SET {blood_group_column}=?", (new_amount,))
    conn.commit()
    conn.close()

def get_blood_inventory_dict():
    """Returns a dictionary of blood group -> total units for analytics."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT Aplus, Bplus, Oplus, ABplus, Aneg, Bneg, Oneg, ABneg FROM total")
    row = cursor.fetchone()
    conn.close()
    if row:
        labels = ["A+", "B+", "O+", "AB+", "A-", "B-", "O-", "AB-"]
        return dict(zip(labels, row))
    return {}

def get_low_inventory_alerts(threshold=None):
    """Returns a list of blood groups that are at or below the threshold.

    When threshold is None, the per-group reserve inventory is used.
    """
    inv = get_blood_inventory_dict()
    alerts = []
    for blood_type, amount in inv.items():
        reserve_limit = RESERVE_INVENTORY.get(blood_type, 0) if threshold is None else threshold
        if amount <= reserve_limit:
            alerts.append((blood_type, amount))
    return alerts


def can_consume_blood_reserve(blood_type, requested_units, role):
    """Checks whether stock consumption would dip into reserve for non-admin users."""
    column_name = _BLOOD_TOTAL_COLUMNS.get(blood_type)
    if not column_name:
        return False, 0, 0, 0

    current_units = get_specific_blood_total(column_name)
    requested_units = int(requested_units or 0)
    reserve_limit = RESERVE_INVENTORY.get(blood_type, 0)
    projected_units = current_units - requested_units

    if projected_units < 0:
        return False, current_units, projected_units, reserve_limit

    if projected_units < reserve_limit and role != "admin":
        return False, current_units, projected_units, reserve_limit

    return True, current_units, projected_units, reserve_limit

# --- Analytics Queries ---
def get_total_donors_count():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM donater")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_total_receivers_count():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM receiver")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_donations_by_blood_type():
    """Returns count of donations per blood type for bar chart."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT Bloodtype, COUNT(*) FROM donater GROUP BY Bloodtype")
    rows = cursor.fetchall()
    conn.close()
    return dict(rows) if rows else {}

def get_requests_by_blood_type():
    """Returns count of requests per blood type for bar chart."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT Bloodtype, COUNT(*) FROM receiver GROUP BY Bloodtype")
    rows = cursor.fetchall()
    conn.close()
    return dict(rows) if rows else {}

# --- Expiry Tracking ---
def get_expiring_donations(expiry_days=42):
    """Returns donations that are expiring within 7 days from now based on their donation date."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT date, Name, Bloodtype, Unitml, Mobile FROM donater")
    all_donations = cursor.fetchall()
    conn.close()
    
    expiring = []
    today = datetime.now()
    for row in all_donations:
        try:
            donation_date = datetime.strptime(row[0], "%d/%m/%y")
            expiry_date = donation_date + timedelta(days=expiry_days)
            days_left = (expiry_date - today).days
            if 0 <= days_left <= 7:
                expiring.append({
                    "name": row[1],
                    "blood_type": row[2],
                    "units": row[3],
                    "mobile": row[4],
                    "donation_date": row[0],
                    "expiry_date": expiry_date.strftime("%d/%m/%y"),
                    "days_left": days_left
                })
        except (ValueError, TypeError):
            continue  # Skip rows with invalid dates
    
    return expiring

# --- Donor Queries ---
def add_donor(date, name, gender, pincode, mobile, nationality, idproof, idnumber, age, bloodtype, unitml):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO donater (date,Name,Gender,Pincode,Mobile,Nationality,Idproof,Idnumber,Age,Bloodtype,Unitml) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                   (date, name, gender, pincode, mobile, nationality, idproof, idnumber, age, bloodtype, unitml))
    # Avoid expensive full rebuilds here — update totals/inventory at caller level
    # Caller (UI) already updates `total` via `update_blood_total`, and
    # receiver allocations are expensive to recompute on every insert.
    # If a full rebuild is required, call `database.refresh_current_portal_users()`
    # or `_rebuild_receiver_allocations` explicitly from maintenance tasks.
    conn.commit()
    conn.close()


def add_donor_with_portal_and_inventory(date, name, gender, pincode, mobile, nationality, idproof, idnumber, age, bloodtype, unitml):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO donater (date,Name,Gender,Pincode,Mobile,Nationality,Idproof,Idnumber,Age,Bloodtype,Unitml) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (date, name, gender, pincode, mobile, nationality, idproof, idnumber, age, bloodtype, unitml),
        )
        password, role = _upsert_portal_account_with_cursor(
            cursor,
            name,
            mobile,
            idnumber,
            "donor",
            question="Auto-generated donor portal account",
        )
        current_avl = _get_specific_blood_total_with_cursor(cursor, _BLOOD_TOTAL_COLUMNS[bloodtype])
        cursor.execute(f"UPDATE total SET {_BLOOD_TOTAL_COLUMNS[bloodtype]}=?", (current_avl + int(unitml),))
        conn.commit()
        return password, role

# Allowlist of valid columns for search queries (Bug 2 fix)
_VALID_DONOR_SEARCH_COLS = {"Mobile", "Idnumber", "Name", "Bloodtype"}
_VALID_RECEIVER_SEARCH_COLS = {"Mobile", "Idnumber", "Name", "Bloodtype"}

def update_donor(mobile, row_mobile, pincode, age, unitml, idnumber):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE donater SET Mobile=?, Pincode=?, Age=?, Unitml=? WHERE Mobile=?",
                   (mobile, pincode, age, unitml, row_mobile))
    conn.commit()
    conn.close()

def delete_donor(mobile):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM donater WHERE Mobile=?", (mobile,))
    conn.commit()
    conn.close()

def get_all_donors():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM donater")
    rows = cursor.fetchall()
    conn.close()
    return rows

def search_donor(search_by, search_text):
    if search_by not in _VALID_DONOR_SEARCH_COLS:
        return []
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM donater WHERE {search_by} LIKE ?", (search_text + "%",))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_donor_by_mobile(mobile):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT Idnumber FROM donater WHERE Mobile=?", (mobile,))
    row = cursor.fetchone()
    if row:
        cursor.execute("SELECT * FROM donater WHERE Idnumber=?", (row[0],))
        final_row = cursor.fetchall()
        conn.close()
        return final_row
    conn.close()
    return []

# --- Receiver Queries ---
def add_receiver(date, name, gender, pincode, mobile, nationality, idproof, idnumber, age, bloodtype, unitml):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO receiver (date,Name,Gender,Pincode,Mobile,Nationality,Idproof,Idnumber,Age,Bloodtype,Unitml) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                   (date, name, gender, pincode, mobile, nationality, idproof, idnumber, age, bloodtype, unitml))
    conn.commit()
    conn.close()


def add_receiver_with_portal_and_inventory(date, name, gender, pincode, mobile, nationality, idproof, idnumber, age, bloodtype, unitml):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO receiver (date,Name,Gender,Pincode,Mobile,Nationality,Idproof,Idnumber,Age,Bloodtype,Unitml) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (date, name, gender, pincode, mobile, nationality, idproof, idnumber, age, bloodtype, unitml),
        )
        allocated_units = _allocate_blood_to_receiver_with_cursor(cursor, mobile, idnumber, bloodtype, int(unitml), date)
        password, role = _upsert_portal_account_with_cursor(
            cursor,
            name,
            mobile,
            idnumber,
            "receiver",
            question="Auto-generated receiver portal account",
        )
        current_avl = _get_specific_blood_total_with_cursor(cursor, _BLOOD_TOTAL_COLUMNS[bloodtype])
        cursor.execute(f"UPDATE total SET {_BLOOD_TOTAL_COLUMNS[bloodtype]}=?", (max(0, current_avl - allocated_units),))
        conn.commit()
        return allocated_units, password, role

def update_receiver(mobile, row_mobile, pincode, age, unitml, idnumber):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE receiver SET Mobile=?, Pincode=?, Age=?, Unitml=? WHERE Mobile=?",
                   (mobile, pincode, age, unitml, row_mobile))
    conn.commit()
    conn.close()

def delete_receiver(mobile):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM receiver WHERE Mobile=?", (mobile,))
    conn.commit()
    conn.close()

def get_all_receivers():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM receiver")
    rows = cursor.fetchall()
    conn.close()
    return rows

def search_receiver(search_by, search_text):
    if search_by not in _VALID_RECEIVER_SEARCH_COLS:
        return []
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM receiver WHERE {search_by} LIKE ?", (search_text + "%",))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_receiver_by_mobile(mobile):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT Idnumber FROM receiver WHERE Mobile=?", (mobile,))
    row = cursor.fetchone()
    if row:
        cursor.execute("SELECT * FROM receiver WHERE Idnumber=?", (row[0],))
        final_row = cursor.fetchall()
        conn.close()
        return final_row
    conn.close()
    return []

