import hashlib
import re
import unicodedata

_CYRILLIC = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "yo",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "kh",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "shch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
)


def build_campaign_alias(name: str, idempotency_key: str) -> str:
    """Build a URL-safe, per-request alias accepted by Keitaro."""
    transliterated = name.casefold().translate(_CYRILLIC)
    ascii_name = (
        unicodedata.normalize("NFKD", transliterated)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")
    prefix = slug[:48].rstrip("-") or "campaign"
    suffix = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{suffix}"
