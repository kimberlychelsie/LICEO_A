import re
from difflib import SequenceMatcher


def normalize_identity_name(name):
    return re.sub(r"\s+", " ", str(name or "").strip().lower())


def normalize_identity_dob(dob):
    if not dob:
        return ""
    return str(dob).split(" ")[0].strip()


def normalize_identity_lrn(lrn):
    lrn = str(lrn or "").strip()
    return lrn if re.fullmatch(r"\d{12}", lrn) else ""


def normalize_identity_email(email):
    return str(email or "").strip().lower()


def student_name_from_row(row):
    if row.get("student_name"):
        return str(row.get("student_name") or "").strip()
    return " ".join(filter(None, [
        row.get("student_first_name"),
        row.get("student_middle_name"),
        row.get("student_last_name")
    ])).strip()


def _identity_similarity(left, right):
    return round(SequenceMatcher(None, left, right).ratio() * 100)


def evaluate_student_identity_match(new_name, new_dob, new_lrn, existing, new_email=None):
    """
    Email alone is never identity. With blank LRN, exact name + DOB + student
    email is a confirmed duplicate; name + DOB with different email is review.
    Returns ok/block/review for a single existing enrollment row.
    """
    name = normalize_identity_name(new_name)
    dob = normalize_identity_dob(new_dob)
    lrn = normalize_identity_lrn(new_lrn)
    existing_name = normalize_identity_name(student_name_from_row(existing))
    existing_dob = normalize_identity_dob(existing.get("dob"))
    existing_lrn = normalize_identity_lrn(existing.get("lrn"))
    email = normalize_identity_email(new_email)
    existing_email = normalize_identity_email(existing.get("email"))
    status = str(existing.get("status") or "").strip().lower()
    has_student_account = bool(existing.get("has_student_account"))
    if status in ("rejected", "cancelled") and not has_student_account:
        return {"action": "ok", "confidence": 0, "reasons": []}

    name_similarity = _identity_similarity(name, existing_name) if name and existing_name else 0
    same_name = bool(name and existing_name and name == existing_name)
    same_dob = bool(dob and existing_dob and dob == existing_dob)
    same_email = bool(email and existing_email and email == existing_email)

    if lrn and existing_lrn and lrn == existing_lrn:
        return {
            "action": "block",
            "confidence": 100,
            "reasons": ["LRN matches an existing student record"]
        }

    if same_name and same_dob:
        if same_email:
            return {
                "action": "block",
                "confidence": 95,
                "reasons": ["Student name, birthday, and email match an existing record"]
            }
        return {
            "action": "review",
            "confidence": 85,
            "reasons": ["Student name and birthday match an existing record"]
        }

    if same_dob and name_similarity >= 92:
        return {
            "action": "review",
            "confidence": 70,
            "reasons": ["Student details are very similar to an existing record"]
        }

    return {"action": "ok", "confidence": name_similarity if same_dob else 0, "reasons": []}
