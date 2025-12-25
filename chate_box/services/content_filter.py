# services/content_filter.py
import re


def filter_message(text: str):
    """
    Manual filtering for emails, phone numbers, and social links.
    Special focus on Pakistani, Indian, and UAE phone numbers.
    Returns:
    - filtered_text
    - has_forbidden_content (bool)
    - blocked_content_type (comma-separated)
    """
    blocked_types = []
    filtered_text = text

    print(f"DEBUG - Input text: '{text}'")  # Debug line

    # Email pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    email_matches = re.findall(email_pattern, text)
    if email_matches:
        print(f"DEBUG - Found emails: {email_matches}")  # Debug line
        filtered_text = re.sub(email_pattern, '[EMAIL REMOVED]', filtered_text)
        blocked_types.append('email')

    # ===== COMPREHENSIVE PHONE NUMBER DETECTION =====

    # First, let's find ALL number sequences that could be phone numbers
    # This regex finds sequences of 8-15 digits, allowing spaces, dashes, dots
    all_number_sequences = re.findall(r'(?:\d[-\s.]?){8,15}\d', text)

    # Also find plain digit sequences
    plain_digits = re.findall(r'\b\d{8,15}\b', text)

    # Combine all found sequences
    all_candidates = all_number_sequences + plain_digits
    all_candidates = list(set(all_candidates))  # Remove duplicates

    print(f"DEBUG - Number candidates: {all_candidates}")  # Debug line

    phone_found = False

    # Check each candidate if it looks like a phone number
    for candidate in all_candidates:
        # Clean the candidate (remove non-digits)
        clean_candidate = re.sub(r'[^\d]', '', candidate)

        print(f"DEBUG - Checking candidate: {candidate} -> {clean_candidate}")  # Debug line

        # PAKISTANI NUMBER CHECKS
        is_pakistani = False

        # Check for Pakistani mobile (03XXXXXXXXX)
        if len(clean_candidate) == 11 and clean_candidate.startswith('03'):
            is_pakistani = True
            print(f"DEBUG - Pakistani mobile detected: {clean_candidate}")

        # Check for Pakistani mobile without leading 0 (3XXXXXXXXXX)
        elif len(clean_candidate) == 10 and clean_candidate.startswith('3'):
            is_pakistani = True
            print(f"DEBUG - Pakistani mobile (no leading 0): {clean_candidate}")

        # Check for Pakistani with country code (+92)
        elif len(clean_candidate) >= 11 and clean_candidate.startswith('92'):
            is_pakistani = True
            print(f"DEBUG - Pakistani with country code: {clean_candidate}")

        # Check if it contains common Pakistani mobile prefixes
        pakistani_prefixes = ['300', '301', '302', '303', '304', '305', '306', '307', '308', '309',
                              '310', '311', '312', '313', '314', '315', '316', '317', '318', '319',
                              '320', '321', '322', '323', '324', '325', '326', '327', '328', '329',
                              '330', '331', '332', '333', '334', '335', '336', '337', '338', '339',
                              '340', '341', '342', '343', '344', '345', '346', '347', '348', '349',
                              '350', '351', '352', '353', '354', '355', '356', '357', '358', '359']

        for prefix in pakistani_prefixes:
            if clean_candidate.startswith(prefix) and 10 <= len(clean_candidate) <= 12:
                is_pakistani = True
                print(f"DEBUG - Pakistani prefix {prefix} detected: {clean_candidate}")
                break

        # INDIAN NUMBER CHECKS
        is_indian = False

        # Check for Indian mobile (6-9 followed by 9 digits)
        if len(clean_candidate) == 10 and re.match(r'^[6-9]\d{9}$', clean_candidate):
            is_indian = True
            print(f"DEBUG - Indian mobile detected: {clean_candidate}")

        # Check for Indian with country code (91)
        elif len(clean_candidate) >= 11 and clean_candidate.startswith('91'):
            is_indian = True
            print(f"DEBUG - Indian with country code: {clean_candidate}")

        # UAE NUMBER CHECKS
        is_uae = False

        # Check for UAE mobile (5XXXXXXXX)
        if len(clean_candidate) == 9 and clean_candidate.startswith('5'):
            is_uae = True
            print(f"DEBUG - UAE mobile detected: {clean_candidate}")

        # Check for UAE with country code (971)
        elif len(clean_candidate) >= 11 and clean_candidate.startswith('971'):
            is_uae = True
            print(f"DEBUG - UAE with country code: {clean_candidate}")

        # Check for UAE landline (starting with 2-4)
        elif len(clean_candidate) == 8 and re.match(r'^[2-4]\d{7}$', clean_candidate):
            is_uae = True
            print(f"DEBUG - UAE landline detected: {clean_candidate}")

        # GENERAL INTERNATIONAL CHECKS
        is_international = False

        # If it's 10-15 digits and not already identified
        if 10 <= len(clean_candidate) <= 15 and not (is_pakistani or is_indian or is_uae):
            # Check if it looks like a phone number (not a random number sequence)
            # Phone numbers usually don't start with 0 (except for local numbers)
            # and are not all the same digit
            if len(set(clean_candidate)) > 1:  # Not all same digit
                is_international = True
                print(f"DEBUG - International phone suspected: {clean_candidate}")

        # If any phone type detected, replace it
        if is_pakistani or is_indian or is_uae or is_international:
            # Replace the exact pattern found in text (with original formatting)
            # We need to escape special regex characters
            escaped_candidate = re.escape(candidate)
            filtered_text = re.sub(escaped_candidate, '[PHONE REMOVED]', filtered_text)
            phone_found = True
            print(f"DEBUG - Replaced: {candidate} -> [PHONE REMOVED]")

    if phone_found and 'phone' not in blocked_types:
        blocked_types.append('phone')

    # ===== SOCIAL MEDIA LINKS =====
    social_patterns = [
        r'(https?://)?(www\.)?(facebook|fb)\.com/[^\s]+',
        r'(https?://)?(www\.)?twitter\.com/[^\s]+',
        r'(https?://)?(www\.)?instagram\.com/[^\s]+',
        r'(https?://)?(www\.)?linkedin\.com/[^\s]+',
        r'(https?://)?(www\.)?whatsapp\.com/[^\s]+',
        r'(https?://)?(www\.)?telegram\.me/[^\s]+',
        r'(https?://)?(www\.)?discord\.gg/[^\s]+',
        r'(https?://)?(www\.)?snapchat\.com/[^\s]+',
        r'(https?://)?(www\.)?tiktok\.com/@[^\s]+',
    ]

    social_found = False
    for pattern in social_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            filtered_text = re.sub(pattern, '[SOCIAL LINK REMOVED]', filtered_text, flags=re.IGNORECASE)
            social_found = True
            print(f"DEBUG - Social link detected: {matches}")

    if social_found and 'social_link' not in blocked_types:
        blocked_types.append('social_link')

    # Check if any forbidden content was found
    has_forbidden = len(blocked_types) > 0
    blocked_type_str = ", ".join(blocked_types) if blocked_types else ""

    print(f"DEBUG - Final filtered: '{filtered_text}'")  # Debug line
    print(f"DEBUG - Has forbidden: {has_forbidden}, Types: {blocked_type_str}")  # Debug line

    return filtered_text, has_forbidden, blocked_type_str


# Simple test function
def test_filter():
    test_cases = [
        "My number is 03003820801",
        "Call me at 0300-382-0801",
        "Contact: 0300 382 0801",
        "My email is test@example.com",
        "Indian: 9876543210",
        "UAE: 501234567",
        "Random long number 123456789012345",
    ]

    for test in test_cases:
        print("\n" + "=" * 50)
        print(f"Testing: {test}")
        result, has_forbidden, blocked_type = filter_message(test)
        print(f"Result: {result}")
        print(f"Forbidden: {has_forbidden}, Type: {blocked_type}")
