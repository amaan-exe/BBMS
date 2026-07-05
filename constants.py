import datetime as dt

def get_format_date():
    """Returns current date formatted as dd/mm/yy."""
    return f"{dt.datetime.now():%d/%m/%y}"

# Keep backward compatibility
FORMAT_DATE = get_format_date()

BLOOD_GROUP_MAPPING = {
    "A+": "Aplus",
    "B+": "Bplus",
    "O+": "Oplus",
    "AB+": "ABplus",
    "A-": "Aneg",
    "B-": "Bneg",
    "O-": "Oneg",
    "AB-": "ABneg"
}

# Blood shelf life in days (Red Blood Cells)
BLOOD_EXPIRY_DAYS = 42

# Reserve inventory thresholds in mL.
RESERVE_INVENTORY = {
    "O+": 14000,
    "B+": 12250,
    "A+": 10500,
    "AB+": 5250,
    "O-": 2800,
    "B-": 2100,
    "A-": 1750,
    "AB-": 1050,
}

# Backward-compatible generic low-stock threshold.
LOW_INVENTORY_THRESHOLD = min(RESERVE_INVENTORY.values())

# User roles for RBAC
USER_ROLES = {
    "admin": "Admin",
    "staff": "Staff"
}
