import sqlite3
import random
from datetime import datetime, timedelta
import database


def _reserve_seed_rows():
    today = datetime.now().strftime("%d/%m/%y")
    return [
        (today, "Reserve A Negative", "Male", "Reserve Stock", "9900000001", "Indian", "Aadhaar Card", "RSV-A-0001", "30-40", "A-", "5000"),
        (today, "Reserve B Negative", "Female", "Reserve Stock", "9900000002", "Indian", "Aadhaar Card", "RSV-B-0001", "30-40", "B-", "6000"),
        (today, "Reserve O Negative", "Male", "Reserve Stock", "9900000003", "Indian", "Aadhaar Card", "RSV-O-0001", "30-40", "O-", "8000"),
    ]

def seed_realistic_large_dataset():
    print("Connecting to database and initializing realistic seed script...")
    conn = database.connect_db()
    cursor = conn.cursor()
    # Ensure tables exist
    database.setup_tables()

    # print("Cleaning up previous 1ml/2ml seed data...")
    # cursor.execute("DELETE FROM blood_allocations")
    # cursor.execute("DELETE FROM donater WHERE Idnumber LIKE 'ID-D-%' OR Unitml IN ('1', '2') OR Mobile LIKE '827100%'")
    # cursor.execute("DELETE FROM receiver WHERE Idnumber LIKE 'ID-R-%' OR Unitml IN ('1', '2', '3') OR Mobile LIKE '700300%'")
    # cursor.execute("DELETE FROM login WHERE username LIKE '980000%' OR username LIKE '990000%' OR username LIKE '827100%' OR username LIKE '700300%'")

    first_names = [
        "Amaan", "Aarav", "Vihaan", "Vivaan", "Advik", "Kabir", "Arjun", "Rohan", "Rahul", "Amit",
        "Sunil", "Vikram", "Suresh", "Ramesh", "Rajesh", "Deepak", "Gaurav", "Manoj", "Vinay", "Rohit",
        "Alok", "Vijay", "Karan", "Ayush", "Aditya", "Yash", "Harsh", "Nikhil", "Ankit", "Abhishek",
        "Pranav", "Siddharth", "Akash", "Mohit", "Varun", "Shubham", "Akhil", "Tarun", "Nitin", "Pankaj",
        "Rakesh", "Ashish", "Sachin", "Anurag", "Lokesh", "Hemant", "Anoop", "Ravindra", "Mukesh", "Dinesh",

        "Ananya", "Diya", "Mira", "Neha", "Pooja", "Priya", "Sneha", "Kavita", "Gita", "Geeta",
        "Sara", "Riya", "Priyanka", "Anjali", "Sunita", "Divya", "Meera", "Anita", "Suman", "Jyoti",
        "Shreya", "Aditi", "Nandini", "Ishita", "Khushi", "Simran", "Muskan", "Tanvi", "Rashmi", "Swati",
        "Komal", "Ritu", "Pallavi", "Preeti", "Pinki", "Kritika", "Shruti", "Pallak", "Nikita", "Poonam",
        "Farah", "Ayesha", "Zoya", "Sana", "Fatima", "Nazia", "Hina", "Afreen", "Alina", "Mariam"
    ]
    
    
    last_names = [
        "Sharma", "Verma", "Gupta", "Malhotra", "Agarwal", "Mehta", "Jain", "Chopra", "Singh", "Patel",
        "Kumar", "Rao", "Nair", "Pillai", "Yadav", "Das", "Bose", "Sen", "Chowdhury", "Roy",
        "Khan", "Ali", "Shah", "Iyer", "Kulkarni", "Joshi", "Deshmukh", "Banerjee", "Chatterjee", "Mishra",
        "Tripathi", "Pandey", "Tiwari", "Dubey", "Shukla", "Srivastava", "Saxena", "Sinha", "Sahu", "Prasad",
        "Mahato", "Mahto", "Mondal", "Paul", "Dutta", "Ghosh", "Mukherjee", "Biswas", "Naik", "Reddy",
        "Naidu", "Shetty", "Gowda", "Bhat", "Hegde", "Chaudhary", "Thakur", "Chauhan", "Solanki", "Pawar",
        "Jadhav", "More", "Bhosale", "Kale", "Pathak", "Ansari", "Qureshi", "Shaikh", "Hussain", "Syed",
        "Farooqui", "Rehman", "Beg", "Lal", "Soni", "Nigam", "Rawat", "Negi", "Bisht", "Tomar"
    ]


    cities = [
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

    blood_types = ["A+", "B+", "O+", "AB+", "A-", "B-", "O-", "AB-"]
    blood_weights = [0.211, 0.311, 0.357, 0.085, 0.008, 0.011, 0.016, 0.003]
    
    age_groups = ["18-20", "21-30", "31-40", "41-50", "51-60", "61-70"]
    age_weights = [0.09, 0.27, 0.25, 0.19, 0.13, 0.07]

    print("Generating 1500 Realistic Donors (350ml / 450ml)...")
    donors = []
    logins = []

    base_date = datetime.now() - timedelta(days=365)
    
    for i in range(1600):
        mobile = str(8271000000 + i)
        
        idproof = random.choice(["Aadhaar Card", "Voter ID"])
        if idproof == "Aadhaar Card":
            idnumber = str(943100000000 + i)
        else:
            idnumber = f"XYZ{1000000 + i}"
            
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        name = f"{fname} {lname}" if fname != "Amaan" else "Amaan"
        gender = random.choice(["Male", "Female"])
        address = random.choice(cities) # Stored in Pincode column
        nationality = "Indian"
        
        age = random.choices(age_groups, weights=age_weights, k=1)[0]
        btype = random.choices(blood_types, weights=blood_weights, k=1)[0]
        
        # Standard blood donation bag volumes in ml
        units = str(random.choice([350, 450]))
        
        don_date = base_date + timedelta(days=random.randint(0, 365))
        date_str = don_date.strftime("%d/%m/%y")
        
        donors.append((date_str, name, gender, address, mobile, nationality, idproof, idnumber, age, btype, units))
        
        enc_pass = database.encrypt_password(mobile)
        enc_recode = database.encrypt_password(idnumber)
        logins.append((name, mobile, mobile, enc_recode, enc_pass, enc_pass, "Auto-generated portal account", "donor"))

    print("Generating 750 Realistic Receivers (350ml to 1350ml)...")
    receivers = []
    recv_base_date = datetime.now() - timedelta(days=180)
    
    for i in range(1350):
        mobile = str(7553000000 + i)
        
        idproof = random.choice(["Aadhaar Card", "Voter ID"])
        if idproof == "Aadhaar Card":
            idnumber = str(834650000000 + i)
        else:
            idnumber = f"LMN{5000000 + i}"
            
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        name = f"{fname} {lname}"
        gender = random.choice(["Male", "Female"])
        address = random.choice(cities)
        nationality = "Indian"
        
        age = random.choices(age_groups, weights=age_weights, k=1)[0]
        btype = random.choices(blood_types, weights=blood_weights, k=1)[0]
        
        # Realistic receiver volume requirements in ml (1 to 3 bags of 350ml/450ml)
        units = str(random.choice([150,250,350, 450, 700, 900, 1050, 1350]))
        
        req_date = recv_base_date + timedelta(days=random.randint(0, 180))
        date_str = req_date.strftime("%d/%m/%y")
        
        receivers.append((date_str, name, gender, address, mobile, nationality, idproof, idnumber, age, btype, units))
        
        enc_pass = database.encrypt_password(mobile)
        enc_recode = database.encrypt_password(idnumber)
        logins.append((name, mobile, mobile, enc_recode, enc_pass, enc_pass, "Auto-generated portal account", "receiver"))

    print("Inserting Realistic Donors into database...")
    cursor.executemany("""
        INSERT OR IGNORE INTO donater (date, Name, Gender, Pincode, Mobile, Nationality, Idproof, Idnumber, Age, Bloodtype, Unitml)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, donors)

    print("Inserting Realistic Receivers into database...")
    cursor.executemany("""
        INSERT OR IGNORE INTO receiver (date, Name, Gender, Pincode, Mobile, Nationality, Idproof, Idnumber, Age, Bloodtype, Unitml)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, receivers)

    print("Inserting portal login accounts...")
    cursor.executemany("""
        INSERT OR IGNORE INTO login (fullname, username, contact, recode, pass, conpass, reques, role)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, logins)

    reserve_rows = _reserve_seed_rows()
    print("Inserting manual reserve donor stock for A-, B-, and O-...")
    cursor.executemany("""
        INSERT OR IGNORE INTO donater (date, Name, Gender, Pincode, Mobile, Nationality, Idproof, Idnumber, Age, Bloodtype, Unitml)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, reserve_rows)

    print("Rebuilding blood allocations to accurately match donors and receivers in ml...")
    database._rebuild_receiver_allocations(cursor)

    print("Rebuilding inventory totals in ml...")
    database._rebuild_inventory_totals(cursor)

    conn.commit()
    conn.close()
    print("Successfully seeded 1500 realistic donors, 750 realistic receivers, created logins, and generated accurate ml allocation matches!")

if __name__ == "__main__":
    seed_realistic_large_dataset()
