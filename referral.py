def parse_referral_payload(raw_payload):
    if not raw_payload:
        return None
    payload = raw_payload.strip()
    if not payload.startswith("ref_"):
        return None
    value = payload[4:]
    if not value.isdigit():
        return None
    referral_id = int(value)
    return referral_id if referral_id > 0 else None


def build_referral_code(user_id):
    return f"ref_{user_id}"
