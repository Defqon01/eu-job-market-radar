"""
Central configuration for EU Job Market Radar.

Everything that you might want to tweak (data sources, keywords, country list,
LLM settings, email settings) lives here so beginners only have to look in one
place to customise the project.

Secrets (SMTP password, API keys) are read from environment variables, which
are loaded from a local ".env" file via python-dotenv.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load variables from a .env file in the project root (if present).
load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
DB_PATH = DATA_DIR / "radar.sqlite"

# Make sure the folders exist (cheap and safe to call on every run).
DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# HTTP / politeness settings
# ---------------------------------------------------------------------------
# A descriptive User-Agent is good manners: it tells site owners who is making
# requests and gives them a way to contact you.
USER_AGENT = (
    "eu-job-market-radar/1.0 (personal learning project; "
    "+https://github.com/your-username/eu-job-market-radar)"
)
# Seconds to wait between requests to the SAME host (simple rate limiting).
REQUEST_DELAY_SECONDS = 2.0
# Per-request network timeout in seconds.
REQUEST_TIMEOUT_SECONDS = 20
# Whether to check robots.txt before scraping HTML pages.
RESPECT_ROBOTS_TXT = True

# ---------------------------------------------------------------------------
# Google News RSS search queries
# ---------------------------------------------------------------------------
# Each query becomes a Google News RSS feed. Google News exposes search results
# as RSS, which is allowed and far friendlier than scraping HTML.
GOOGLE_NEWS_QUERIES = [
    "Europe layoffs",
    "EU layoffs",
    "Europe job cuts",
    "Europe redundancies",
    "Sweden layoffs",
    "Denmark layoffs",
    "Germany layoffs",
    "Netherlands layoffs",
    "France layoffs",
    "Italy layoffs",
    "Spain layoffs",
    "Europe hiring freeze",
    "Europe restructuring",
    "EU skills shortage",
    "AI jobs Europe",
    "AI governance jobs Europe",
    "workforce planning Europe",
    "HR analytics Europe",
    "talent management Europe",
]

# Google News RSS endpoint. {query} is URL-encoded by the collector.
# hl = language, gl = country, ceid = country:language edition.
GOOGLE_NEWS_RSS_TEMPLATE = (
    "https://news.google.com/rss/search?q={query}&hl=en&gl=US&ceid=US:en"
)

# ---------------------------------------------------------------------------
# Generic / direct RSS feeds (non-Google).
# Add any public RSS feed about labour markets, HR, or the economy here.
# ---------------------------------------------------------------------------
DIRECT_RSS_FEEDS = [
    # (source_name, url)
    # Example placeholders — uncomment / replace with feeds you trust:
    # ("Euractiv Economy", "https://www.euractiv.com/sections/economy-jobs/feed/"),
    # ("ECB Press", "https://www.ecb.europa.eu/rss/press.html"),
]

# ---------------------------------------------------------------------------
# Company newsrooms / press release feeds.
# Many large companies publish an RSS feed or a press page. Where a public RSS
# feed is known it is listed; otherwise the URL is left as None with a TODO so
# the collector simply skips it without crashing.
# ---------------------------------------------------------------------------
COMPANY_FEEDS = [
    # (company_name, rss_url_or_None)
    ("Ericsson", "https://www.ericsson.com/en/rss"),
    ("Spotify", "https://newsroom.spotify.com/feed/"),
    ("SAP", "https://news.sap.com/feed/"),
    ("Nokia", "https://www.nokia.com/rss.xml"),
    # TODO: confirm/replace the feeds below — left as None so they skip safely.
    ("IKEA", None),            # TODO: find a public Inter IKEA / IKEA newsroom RSS
    ("Volvo Group", None),     # TODO: Volvo Group media RSS
    ("Klarna", None),          # TODO: Klarna newsroom RSS
    ("Siemens", None),         # TODO: Siemens press RSS
    ("Maersk", None),          # TODO: Maersk press RSS
    ("Novo Nordisk", None),    # TODO: Novo Nordisk news RSS
]

# ---------------------------------------------------------------------------
# Eurofound European Restructuring Monitor (ERM)
# ---------------------------------------------------------------------------
EUROFOUND_ERM_URL = "https://www.eurofound.europa.eu/en/restructuring/erm"

# ---------------------------------------------------------------------------
# EURES (European job mobility portal)
# ---------------------------------------------------------------------------
EURES_URL = "https://eures.europa.eu/index_en"

# ---------------------------------------------------------------------------
# Classification keywords (lower-cased matching).
# Order matters: the classifier checks job_posting hints, then the categories
# below in this dictionary order.
# ---------------------------------------------------------------------------
SIGNAL_KEYWORDS = {
    "layoff": [
        "layoff", "layoffs", "lay off", "lay offs", "job cuts", "jobcuts",
        "redundancy", "redundancies", "dismissal", "dismissals",
        "workforce reduction", "cut jobs", "cutting jobs", "slash jobs",
        "axe jobs", "headcount reduction", "downsizing",
    ],
    "restructuring": [
        "restructuring", "restructure", "reorganization", "reorganisation",
        "reorganize", "reorganise", "transformation programme",
        "transformation program", "business transformation",
    ],
    "hiring_freeze": [
        "hiring freeze", "hiring freezes", "freeze hiring", "freezing hiring",
        "recruitment freeze", "pause hiring", "hiring pause",
    ],
    "skills_shortage": [
        "skills shortage", "skill shortage", "talent shortage",
        "labour shortage", "labor shortage", "skills gap", "skill gap",
        "talent gap",
    ],
    # labour_market_news is a catch-all for HR/analytics/AI-governance topics.
    "labour_market_news": [
        "ai governance", "ai jobs", "workforce planning", "hr analytics",
        "people analytics", "talent management", "labour market",
        "labor market", "employment report", "unemployment",
    ],
}

# Words that strongly suggest the item is an actual job posting (vacancy)
# rather than news about the labour market.
JOB_POSTING_HINTS = [
    "apply now", "we are hiring", "we're hiring", "job opening",
    "job vacancy", "vacancy", "open position", "open role", "join our team",
    "now hiring", "career opportunity",
]

# ---------------------------------------------------------------------------
# Country detection. Maps a canonical country label to keywords to search for.
# ---------------------------------------------------------------------------
COUNTRY_KEYWORDS = {
    "Sweden": ["sweden", "swedish", "stockholm"],
    "Denmark": ["denmark", "danish", "copenhagen"],
    "Norway": ["norway", "norwegian", "oslo"],
    "Finland": ["finland", "finnish", "helsinki"],
    "Germany": ["germany", "german", "berlin", "munich", "frankfurt"],
    "Netherlands": ["netherlands", "dutch", "amsterdam", "the hague"],
    "France": ["france", "french", "paris"],
    "Italy": ["italy", "italian", "rome", "milan"],
    "Spain": ["spain", "spanish", "madrid", "barcelona"],
    "Poland": ["poland", "polish", "warsaw"],
    "Ireland": ["ireland", "irish", "dublin"],
    "Belgium": ["belgium", "belgian", "brussels"],
    "Austria": ["austria", "austrian", "vienna"],
    "Switzerland": ["switzerland", "swiss", "zurich", "geneva"],
    # Broad fallbacks checked last.
    "EU": ["european union", "eu-wide", "eu "],
    "Europe": ["europe", "european"],
}

# Extra keywords surfaced in the "top keywords" section of the fallback report.
EXTRA_KEYWORDS_OF_INTEREST = [
    "ai", "artificial intelligence", "automation", "remote work",
    "return to office", "rto", "manufacturing", "tech", "banking",
    "automotive", "retail", "green jobs", "renewable", "semiconductor",
]

# ---------------------------------------------------------------------------
# LLM settings
# ---------------------------------------------------------------------------
LLM_PROVIDER = (os.getenv("LLM_PROVIDER") or "none").strip().lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
LLM_MODEL = (os.getenv("LLM_MODEL") or "").strip()

# Sensible default models per provider.
DEFAULT_LLM_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-6",
}


def get_llm_model() -> str:
    """Return the configured model, or a sensible default for the provider."""
    if LLM_MODEL:
        return LLM_MODEL
    return DEFAULT_LLM_MODELS.get(LLM_PROVIDER, "")


# ---------------------------------------------------------------------------
# Email settings
# ---------------------------------------------------------------------------
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587") or "587")
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
EMAIL_FROM = os.getenv("EMAIL_FROM", "").strip()
EMAIL_TO = os.getenv("EMAIL_TO", "").strip()


def email_is_configured() -> bool:
    """True only if every required SMTP/email field is present."""
    return all([SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO])
