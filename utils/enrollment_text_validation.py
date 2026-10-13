import re

_REPEAT_SAME_PUNCT = re.compile(r"""([.,;:!?/\-_'\"@#$%^&*+=<>\[\]{}\\|`~])\1""")
_REPEAT_PUNCT_PAIR = re.compile(r"([.,/\-]{1,2})\1+")
_ALNUM = re.compile(r"[A-Za-z0-9ñÑ]")
_PUNCT = re.compile(r"[^A-Za-z0-9ñÑ\s]")

SPAM_SPECIALS_MESSAGE = (
    "Special-character spam is not allowed "
    "(for example .,.,., or -,-,- or sadas-fsasd-asdas)."
)
_REMARKS_ALLOWED = re.compile(r"^[A-Za-z0-9ñÑ\s.,-]+$")
REMARKS_SPECIALS_MESSAGE = (
    "Remarks cannot contain special characters like = & % $ # ! * ( )."
)


def enrollment_remarks_error(val):
    if not val:
        return None
    spam_err = enrollment_field_spam_error(val)
    if spam_err:
        return spam_err
    text = str(val).strip()
    if not _REMARKS_ALLOWED.match(text) or "  " in text or "--" in text or ".." in text or ",," in text:
        return REMARKS_SPECIALS_MESSAGE
    return None


def enrollment_field_spam_error(val):
    """Return an error message if a text value looks like punctuation/hyphen spam."""
    if not val:
        return None
    text = str(val).strip()
    if not text:
        return None

    compact = re.sub(r"\s+", "", text)
    if _REPEAT_SAME_PUNCT.search(text):
        return SPAM_SPECIALS_MESSAGE
    if _REPEAT_PUNCT_PAIR.search(compact):
        return SPAM_SPECIALS_MESSAGE

    punct = len(_PUNCT.findall(text))
    alnum = len(_ALNUM.findall(text))
    if punct and alnum == 0:
        return SPAM_SPECIALS_MESSAGE
    if punct >= 3 and punct >= alnum:
        return SPAM_SPECIALS_MESSAGE

    hyphen_parts = [part for part in text.split("-") if part != ""]
    if len(hyphen_parts) >= 3 and " " not in text:
        return SPAM_SPECIALS_MESSAGE

    return None
