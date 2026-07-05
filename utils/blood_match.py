# Blood Type Compatibility Rules
# Key = Receiver blood type, Value = list of compatible donor types

COMPATIBILITY = {
    "A+":  ["A+", "A-", "O+", "O-"],
    "A-":  ["A-", "O-"],
    "B+":  ["B+", "B-", "O+", "O-"],
    "B-":  ["B-", "O-"],
    "AB+": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],  # Universal receiver
    "AB-": ["A-", "B-", "AB-", "O-"],
    "O+":  ["O+", "O-"],
    "O-":  ["O-"],  # Universal donor
}

def get_compatible_donors(receiver_blood_type):
    """Returns a list of blood types that can donate to the given receiver type."""
    return COMPATIBILITY.get(receiver_blood_type, [])

def find_matching_donors(receiver_blood_type, donors_list):
    """
    Given a receiver's blood type and a list of donor records,
    returns only donors with compatible blood types.
    Each donor record is a tuple where index 9 is Bloodtype.
    """
    compatible_types = get_compatible_donors(receiver_blood_type)
    matches = []
    for donor in donors_list:
        try:
            if donor[9] in compatible_types:
                matches.append(donor)
        except (IndexError, TypeError):
            continue
    return matches
