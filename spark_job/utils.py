import re
from urllib.parse import urlparse

try:
    from user_agents import parse as _ua_parse

    _HAS_UA_LIB = True
except ImportError:
    _HAS_UA_LIB = False


def extract_domain(url): 
    if not url:
        return None
    try:
        netloc = urlparse(url).netloc.lower()
        if not netloc:
            return None
        return netloc[4:] if netloc.startswith("www.") else netloc
    except Exception:
        return None


# Fallback when IP2Location failed
_DOMAIN_SUFFIX_TO_COUNTRY = {
    ".com": "United States",
    ".de": "Germany",
    ".fr": "France",
    ".it": "Italy",
    ".es": "Spain",
    ".uk": "United Kingdom",
    ".sg": "Singapore",
    ".cl": "Chile",
    ".mx": "Mexico",
    ".pl": "Poland",
    ".at": "Austria",
    ".ch": "Switzerland",
    ".vn": "Vietnam",
    ".jp": "Japan",
    ".kr": "South Korea",
    ".cn": "China",
    ".ae": "United Arab Emirates",
    ".sa": "Saudi Arabia",
    ".au": "Australia",
    ".ca": "Canada",
}


def map_country(domain):
    if not domain:
        return "Unknown"
    for suffix, country in _DOMAIN_SUFFIX_TO_COUNTRY.items():
        if domain.endswith(suffix):
            return country
    return "Unknown"


_BROWSER_PATTERNS = [
    ("Edge", r"Edg(e|A|iOS)?/"),
    ("Chrome", r"Chrome/"),
    ("Firefox", r"Firefox/"),
    ("Safari", r"Version/.*Safari/"),
    ("Opera", r"OPR/|Opera/"),
    ("Internet Explorer", r"MSIE |Trident/"),
]

_OS_PATTERNS = [
    ("iOS", r"iPhone|iPad|iPod"),
    ("Android", r"Android"),
    ("Windows", r"Windows NT"),
    ("Mac OS X", r"Mac OS X"),
    ("Linux", r"Linux"),
]


def parse_browser(user_agent):
    if not user_agent:
        return "Unknown"
    if _HAS_UA_LIB:
        try:
            family = _ua_parse(user_agent).browser.family
            if family:
                return family
        except Exception:
            pass
    for name, pat in _BROWSER_PATTERNS:
        if re.search(pat, user_agent):
            return name
    return "Other"


def parse_os(user_agent):
    if not user_agent:
        return "Unknown"
    if _HAS_UA_LIB:
        try:
            family = _ua_parse(user_agent).os.family
            if family:
                return family
        except Exception:
            pass
    for name, pat in _OS_PATTERNS:
        if re.search(pat, user_agent):
            return name
    return "Other"
