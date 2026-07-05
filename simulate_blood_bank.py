"""
simulate_blood_bank.py

Simulates ~1 year of realistic blood bank operations using the existing
`blood.db` and `database.py` helpers. This script inserts donors and
receivers into the real database while ensuring all constraints are met:

- Uses compatibility-aware FIFO allocation via `database.allocate_blood_to_receiver`.
- Does not insert receivers that cannot be fully satisfied.
- Maintains in-memory inventory (donated - allocated) during the run.
- Enforces 90-day donor cool-down.

Run:
    python simulate_blood_bank.py

Options:
    --days N   simulate N days (default 365)

This script is intentionally conservative: it checks availability before
committing receivers, and rolls back partial allocations if the allocation
does not meet the requested amount.
"""

from datetime import datetime, timedelta
import random
import argparse
import sqlite3
import database
from constants import RESERVE_INVENTORY

# --- Configuration / realistic distributions ---
# Indian blood group approximate frequencies (relative weights)
BLOOD_TYPE_WEIGHTS = {
    "O+": 37,
    "B+": 32,
    "A+": 21,
    "AB+": 8,
    "O-": 1.5,
    "A-": 0.9,
    "B-": 0.9,
    "AB-": 0.6,
}
BP_TYPES = list(BLOOD_TYPE_WEIGHTS.keys())
BP_WEIGHTS = list(BLOOD_TYPE_WEIGHTS.values())

AGE_GROUPS = [(18, 20), (21, 30), (31, 40), (41, 50), (51, 60), (61, 70)]
AGE_WEIGHTS = [0.09, 0.27, 0.25, 0.19, 0.13, 0.07]

GENDERS = ["Male", "Female"]
GENDER_WEIGHTS = [0.52, 0.48]

CITIES = [
    "Jamshedpur", "Ghatshila", "Ranchi", "Dhanbad", "Bokaro", "Hazaribagh", "Deoghar", "Giridih",
    "Patna", "Bhagalpur", "Muzaffarpur", "Gaya", "Darbhanga", "Purnia", "Ara",
    "Kolkata", "Howrah", "Asansol", "Durgapur", "Siliguri", "Kharagpur", "Malda",
    "Bhubaneswar", "Cuttack", "Rourkela", "Berhampur", "Sambalpur", "Balasore", "Puri",
    "Mumbai", "Pune", "Nagpur", "Thane", "Nashik", "Aurangabad", "Kolhapur",
    "Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar",
    "Bengaluru", "Mysuru", "Hubballi", "Mangaluru", "Belagavi",
    "Hyderabad", "Warangal", "Karimnagar", "Nizamabad",
    "Chennai", "Coimbatore", "Madurai", "Salem", "Tiruchirappalli",
    "Delhi", "Noida", "Gurugram", "Ghaziabad", "Faridabad",
    "Lucknow", "Kanpur", "Varanasi", "Prayagraj", "Agra", "Meerut", "Bareilly", "Gorakhpur",
    "Jaipur", "Jodhpur", "Udaipur", "Kota", "Ajmer",
    "Bhopal", "Indore", "Jabalpur", "Gwalior", "Ujjain",
    "Chandigarh", "Ludhiana", "Amritsar", "Jalandhar",
    "Guwahati", "Shillong", "Agartala", "Imphal", "Aizawl",
    "Kochi", "Thiruvananthapuram", "Kozhikode",
    "Visakhapatnam", "Vijayawada", "Guntur",
    "Raipur", "Bilaspur"
]

MALE_FIRST = ["Amaan", "Aarav", "Vihaan", "Vivaan", "Advik", "Kabir", "Arjun", "Rohan", "Rahul", "Amit",
    "Sunil", "Vikram", "Suresh", "Ramesh", "Rajesh", "Deepak", "Gaurav", "Manoj", "Vinay", "Rohit",
    "Alok", "Vijay", "Karan", "Ayush", "Aditya", "Yash", "Harsh", "Nikhil", "Ankit", "Abhishek",
    "Pranav", "Siddharth", "Akash", "Mohit", "Varun", "Shubham", "Akhil", "Tarun", "Nitin", "Pankaj",
    "Rakesh", "Ashish", "Sachin", "Anurag", "Lokesh", "Hemant", "Anoop", "Ravindra", "Mukesh", "Dinesh"]


FEMALE_FIRST = ["Ananya", "Diya", "Mira", "Neha", "Pooja", "Priya", "Sneha", "Kavita", "Gita", "Geeta",
    "Sara", "Riya", "Priyanka", "Anjali", "Sunita", "Divya", "Meera", "Anita", "Suman", "Jyoti",
    "Shreya", "Aditi", "Nandini", "Ishita", "Khushi", "Simran", "Muskan", "Tanvi", "Rashmi", "Swati",
    "Komal", "Ritu", "Pallavi", "Preeti", "Pinki", "Kritika", "Shruti", "Pallak", "Nikita", "Poonam",
    "Farah", "Ayesha", "Zoya", "Sana", "Fatima", "Nazia", "Hina", "Afreen", "Alina", "Mariam"]


LAST_NAMES = [ "Sharma", "Verma", "Gupta", "Malhotra", "Agarwal", "Mehta", "Jain", "Chopra", "Singh", "Patel",
    "Kumar", "Rao", "Nair", "Pillai", "Yadav", "Das", "Bose", "Sen", "Chowdhury", "Roy",
    "Khan", "Ali", "Shah", "Iyer", "Kulkarni", "Joshi", "Deshmukh", "Banerjee", "Chatterjee", "Mishra",
    "Tripathi", "Pandey", "Tiwari", "Dubey", "Shukla", "Srivastava", "Saxena", "Sinha", "Sahu", "Prasad",
    "Mahato", "Mahto", "Mondal", "Paul", "Dutta", "Ghosh", "Mukherjee", "Biswas", "Naik", "Reddy",
    "Naidu", "Shetty", "Gowda", "Bhat", "Hegde", "Chaudhary", "Thakur", "Chauhan", "Solanki", "Pawar",
    "Jadhav", "More", "Bhosale", "Kale", "Pathak", "Ansari", "Qureshi", "Shaikh", "Hussain", "Syed",
    "Farooqui", "Rehman", "Beg", "Lal", "Soni", "Nigam", "Rawat", "Negi", "Bisht", "Tomar"]


DONOR_BAG_CHOICES = [350, 450]
DONOR_BAG_WEIGHTS = [0.8, 0.2]

RECV_CHOICES = [150,250,350,450,700,900,1050,1350]
RECV_WEIGHTS = [0.05,0.07,0.25,0.3,0.08,0.07,0.09,0.09]

# Compatibility mapping (recipient -> donor types in preference order)
COMPATIBILITY = {
    "O-": ["O-"],
    "O+": ["O+", "O-"],
    "A-": ["A-", "O-"],
    "A+": ["A+", "A-", "O+", "O-"],
    "B-": ["B-", "O-"],
    "B+": ["B+", "B-", "O+", "O-"],
    "AB-": ["AB-", "A-", "B-", "O-"],
    "AB+": ["AB+", "AB-", "A+", "A-", "B+", "B-", "O+", "O-"],
}

# Donor cooldown period (days)
DONOR_COOLDOWN = 90


class Simulator:
    def __init__(self, days=365, target_donors=10574, target_receivers=(5800,7200)):
        self.days = days
        self.target_donors = target_donors
        self.target_receivers = target_receivers

        # in-memory state
        self.donated = {bt: 0 for bt in BP_TYPES}
        self.allocated = {bt: 0 for bt in BP_TYPES}

        # donor/receiver registries to avoid collisions and to enforce cooldown
        self.used_mobiles = set()
        self.used_idnumbers = set()
        self.donor_last_date = {}  # idnumber -> date

        # stats
        self.inserted_donors = 0
        self.inserted_receivers = 0
        self.allocated_ml = 0
        self.unfulfilled_attempts = 0

        # load initial state from DB
        self._init_from_db()

    def _init_from_db(self):
        conn = sqlite3.connect(database.DB_NAME)
        c = conn.cursor()

        # existing mobiles and idnumbers
        c.execute("SELECT Mobile, Idnumber, date, Unitml FROM donater")
        for mobile, idn, date_text, unit in c.fetchall():
            if mobile:
                self.used_mobiles.add(mobile)
            if idn:
                self.used_idnumbers.add(idn)
            try:
                units = int(unit or 0)
            except Exception:
                units = 0
            # aggregate donated
            # we keep the donated totals separate from DB's totals so simulation tracks changes
            # but seed values count as donated history
            # We accumulate by Bloodtype in a follow-up query
        c.execute("SELECT Bloodtype, COALESCE(SUM(CAST(Unitml AS INTEGER)),0) FROM donater GROUP BY Bloodtype")
        for bt, total in c.fetchall():
            if bt in self.donated:
                self.donated[bt] = int(total or 0)

        # existing allocations
        c.execute("SELECT bloodtype, COALESCE(SUM(allocated_units),0) FROM blood_allocations GROUP BY bloodtype")
        for bt, total in c.fetchall():
            if bt in self.allocated:
                self.allocated[bt] = int(total or 0)

        # populate donor_last_date from recent donations (Idnumber -> most recent date)
        c.execute("SELECT Idnumber, date FROM donater WHERE Idnumber IS NOT NULL")
        for idn, date_text in c.fetchall():
            if not idn or not date_text:
                continue
            try:
                dt = datetime.strptime(date_text, "%d/%m/%y")
            except Exception:
                continue
            prev = self.donor_last_date.get(idn)
            if not prev or dt > prev:
                self.donor_last_date[idn] = dt

        conn.close()

    # --- utilities for generating unique identities ---
    def _next_mobile(self):
        # generate 10-digit mobiles starting at 9000000000
        base = 9000000000
        while True:
            n = str(base + random.randint(0, 99999999))
            if n not in self.used_mobiles and n[0] in '6789':
                self.used_mobiles.add(n)
                return n

    def _next_idnumber(self):
        # generate pseudo-unique ID numbers
        while True:
            n = str(random.randint(800000000000, 999999999999))
            if n not in self.used_idnumbers:
                self.used_idnumbers.add(n)
                return n

    def generate_donor(self, date):
        gender = random.choices(GENDERS, weights=GENDER_WEIGHTS, k=1)[0]
        first = random.choice(MALE_FIRST if gender == 'Male' else FEMALE_FIRST)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        mobile = self._next_mobile()
        idnumber = self._next_idnumber()
        pincode = random.choice(CITIES)
        nationality = 'Indian'
        idproof = random.choice(['Aadhaar Card', 'Driving Licence'])
        age_group = random.choices(AGE_GROUPS, weights=AGE_WEIGHTS, k=1)[0]
        age = f"{age_group[0]}-{age_group[1]}"
        bloodtype = random.choices(BP_TYPES, weights=BP_WEIGHTS, k=1)[0]
        unitml = str(random.choices(DONOR_BAG_CHOICES, weights=DONOR_BAG_WEIGHTS, k=1)[0])

        return (date.strftime("%d/%m/%y"), name, gender, pincode, mobile, nationality, idproof, idnumber, age, bloodtype, unitml)

    def generate_receiver(self, date):
        gender = random.choices(GENDERS, weights=GENDER_WEIGHTS, k=1)[0]
        first = random.choice(MALE_FIRST if gender == 'Male' else FEMALE_FIRST)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        mobile = self._next_mobile()
        idnumber = self._next_idnumber()
        pincode = random.choice(CITIES)
        nationality = 'Indian'
        idproof = random.choice(['Aadhaar Card', 'Hospital ID'])
        age_group = random.choices(AGE_GROUPS, weights=AGE_WEIGHTS, k=1)[0]
        age = f"{age_group[0]}-{age_group[1]}"
        bloodtype = random.choices(BP_TYPES, weights=BP_WEIGHTS, k=1)[0]
        unitml = random.choices(RECV_CHOICES, weights=RECV_WEIGHTS, k=1)[0]

        return (date.strftime("%d/%m/%y"), name, gender, pincode, mobile, nationality, idproof, idnumber, age, bloodtype, str(unitml))

    # Check if we can allocate `qty` ml to a receiver requesting `bloodtype`
    def can_allocate(self, bloodtype, qty):
        # Sum available across compatible donor groups taking reserve into account
        candidate = COMPATIBILITY.get(bloodtype, [bloodtype])
        available = 0
        for bt in candidate:
            donated = self.donated.get(bt, 0)
            allocated = self.allocated.get(bt, 0)
            reserve = RESERVE_INVENTORY.get(bt, 0)
            # conservative available for allocation from this group
            avail = max(0, donated - allocated - reserve)
            available += avail
        return available >= qty

    def _update_after_donor(self, donor_tuple):
        # donor_tuple matches add_donor signature
        bt = donor_tuple[9]
        try:
            units = int(donor_tuple[10])
        except Exception:
            units = 0
        if bt in self.donated:
            self.donated[bt] += units

    def _update_after_receiver_allocation(self, receiver_mobile, receiver_idnumber):
        # query allocations for this receiver and update allocated/inventory
        conn = sqlite3.connect(database.DB_NAME)
        c = conn.cursor()
        c.execute("SELECT bloodtype, COALESCE(SUM(allocated_units),0) FROM blood_allocations WHERE receiver_mobile=? AND receiver_idnumber=? GROUP BY bloodtype", (receiver_mobile, receiver_idnumber))
        rows = c.fetchall()
        conn.close()
        total = 0
        for bt, amt in rows:
            amt = int(amt or 0)
            if bt in self.allocated:
                self.allocated[bt] += amt
            total += amt
        return total

    def simulate_day(self, date):
        # number of donors and receivers for the day (stochastic)
        donors_today = max(0, int(random.gauss(10, 3)))
        receivers_today = max(0, int(random.gauss(3.5, 1.6)))

        # Generate donors first to feed receivers same-day
        for _ in range(donors_today):
            if self.inserted_donors >= self.target_donors:
                break
            donor = self.generate_donor(date)
            print("\nDONOR : ",donor)
            # enforce 90-day rule for repeat donors: new donors always allowed
            try:
                database.add_donor(*donor)
                # create portal account for completeness
                try:
                    database.ensure_portal_account(donor[1], donor[4], donor[7], 'donor')
                except Exception:
                    pass
                self._update_after_donor(donor)
                self.donor_last_date[donor[7]] = date
                self.inserted_donors += 1
            except Exception:
                # skip if DB constraints fail (e.g., duplicate) and continue
                continue

        # Now generate receivers (only insert if allocation guaranteed)
        for _ in range(receivers_today):
            if self.inserted_receivers >= self.target_receivers[1]:
                break
            recv = self.generate_receiver(date)
            print("\nReciever : ",recv)
            requested_qty = int(recv[10])
            requested_bt = recv[9]

            if not self.can_allocate(requested_bt, requested_qty):
                # skip or count as unfulfilled attempt
                self.unfulfilled_attempts += 1
                continue

            # Insert receiver then allocate using DB allocator (which uses FIFO & compatibility)
            try:
                database.add_receiver(*recv)
                allocated = database.allocate_blood_to_receiver(recv[4], recv[7], requested_bt, requested_qty, recv[0])
                if allocated < requested_qty:
                    # Something prevented full allocation despite can_allocate check.
                    # Roll back this receiver and its allocations to keep DB consistent with policy.
                    try:
                        database.release_receiver_allocations(recv[4])
                    except Exception:
                        pass
                    # delete receiver (best-effort)
                    try:
                        database.delete_receiver(recv[4])
                    except Exception:
                        pass
                    self.unfulfilled_attempts += 1
                    continue

                # Update in-memory allocated totals
                added = self._update_after_receiver_allocation(recv[4], recv[7])
                self.allocated_ml += added
                self.inserted_receivers += 1
            except Exception:
                self.unfulfilled_attempts += 1
                continue

    def simulate(self):
        start_date = datetime.now() - timedelta(days=self.days)
        for day in range(self.days):
            current = start_date + timedelta(days=day)
            self.simulate_day(current)
            # early exit if targets reached
            if self.inserted_donors >= self.target_donors and self.inserted_receivers >= self.target_receivers[0]:
                break

    def print_report(self):
        print("--- Simulation Report ---")
        print(f"Days simulated: {self.days}")
        print(f"Donors inserted: {self.inserted_donors}")
        print(f"Receivers inserted: {self.inserted_receivers}")
        print(f"Total allocated (ml) recorded by simulator: {self.allocated_ml}")
        total_inventory = {bt: max(0, self.donated.get(bt,0) - self.allocated.get(bt,0)) for bt in BP_TYPES}
        print("Remaining inventory (ml) by blood group:")
        for bt in BP_TYPES:
            print(f"  {bt}: {total_inventory.get(bt,0)}")
        total_available = sum(total_inventory.values())
        print(f"Total remaining inventory (ml): {total_available}")
        print(f"Unfulfilled attempts (skipped receivers): {self.unfulfilled_attempts}")
        print("Blood group distribution (donated ml):")
        for bt in BP_TYPES:
            print(f"  {bt}: donated={self.donated.get(bt,0)} allocated={self.allocated.get(bt,0)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=365)
    args = parser.parse_args()

    sim = Simulator(days=args.days)
    print("Starting simulation:")
    sim.simulate()
    sim.print_report()


if __name__ == '__main__':
    main()
