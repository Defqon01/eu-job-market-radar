"""
Report generator.

Produces a concise weekly markdown report from the items collected in the last
N days. Two paths:

1. LLM path (if LLM_PROVIDER is openai/anthropic and a key is present):
   we hand a compact summary of the items to the model and ask it to write the
   report in our required structure.

2. Deterministic fallback (default): we build the report purely from counts,
   keywords, and the newest items — no API key required. This always works.

Both paths return a markdown string. The caller is responsible for saving it.
"""

from __future__ import annotations

from collections import Counter
from datetime import date

import config
from radar.processing.keyword_extractor import top_keywords
from radar.utils.logging import get_logger

logger = get_logger(__name__)

# The section headers we always want, in order.
REPORT_SECTIONS = [
    "Executive summary",
    "Layoff and restructuring signals",
    "Hiring and job-market signals",
    "Emerging roles and skills",
    "Country spotlight",
    "Underrepresented angles",
    "What this means for HR / Talent / Workforce Planning",
    "Sources reviewed",
]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _today_str() -> str:
    return date.today().isoformat()


def _count_by(items: list[dict], key: str) -> Counter:
    counter: Counter = Counter()
    for item in items:
        value = item.get(key) or "unknown"
        counter[value] += 1
    return counter


def _items_with_signal(items: list[dict], signal_types: set[str]) -> list[dict]:
    return [i for i in items if i.get("signal_type") in signal_types]


def _format_item_line(item: dict) -> str:
    title = item.get("title") or "(untitled)"
    url = item.get("url") or ""
    bits = []
    if item.get("country"):
        bits.append(item["country"])
    if item.get("company"):
        bits.append(item["company"])
    suffix = f" _({', '.join(bits)})_" if bits else ""
    if url:
        return f"- [{title}]({url}){suffix}"
    return f"- {title}{suffix}"


# ---------------------------------------------------------------------------
# Deterministic fallback report
# ---------------------------------------------------------------------------
def generate_fallback_report(items: list[dict], days: int) -> str:
    """Build a markdown report using only counts and simple rules."""
    today = _today_str()

    # Drop unclassified items: they are kept in the database but add noise to
    # the report (Google News headlines often lack the keyword we match on).
    all_count = len(items)
    items = [i for i in items if i.get("signal_type") not in (None, "", "unknown")]
    omitted = all_count - len(items)
    total = len(items)

    by_signal = _count_by(items, "signal_type")
    by_country = _count_by(items, "country")
    keywords = top_keywords(items, limit=10)

    layoff_resto = _items_with_signal(items, {"layoff", "restructuring", "hiring_freeze"})
    hiring = _items_with_signal(items, {"job_posting"})
    skills = _items_with_signal(items, {"skills_shortage"})
    labour_news = _items_with_signal(items, {"labour_market_news"})

    lines: list[str] = []
    lines.append(f"# EU Job Market Radar — {today}")
    lines.append("")
    omitted_note = (
        f" {omitted} unclassified item(s) omitted." if omitted else ""
    )
    lines.append(
        f"_Automated weekly digest covering the last {days} days. "
        f"{total} classified item(s) shown.{omitted_note} "
        f"Generated without an LLM (deterministic mode)._"
    )
    lines.append("")

    # 1. Executive summary
    lines.append("## Executive summary")
    if total == 0:
        lines.append("No new items were collected this week.")
    else:
        signal_bits = ", ".join(
            f"{count} {name}" for name, count in by_signal.most_common()
        )
        top_country = by_country.most_common(1)
        country_note = (
            f" The most mentioned country was **{top_country[0][0]}** "
            f"({top_country[0][1]} mentions)."
            if top_country and top_country[0][0] != "unknown"
            else ""
        )
        lines.append(
            f"This week the radar reviewed **{total} items**. "
            f"Breakdown by signal: {signal_bits}.{country_note}"
        )
        lines.append("")
        lines.append(f"- Layoff / restructuring / freeze signals: **{len(layoff_resto)}**")
        lines.append(f"- Hiring / job-posting signals: **{len(hiring)}**")
        lines.append(f"- Skills-shortage signals: **{len(skills)}**")
        lines.append(f"- Broader labour-market news: **{len(labour_news)}**")
    lines.append("")

    # 2. Layoff and restructuring signals
    lines.append("## Layoff and restructuring signals")
    if layoff_resto:
        for item in layoff_resto[:15]:
            lines.append(_format_item_line(item))
    else:
        lines.append("_No layoff or restructuring signals detected this week._")
    lines.append("")

    # 3. Hiring and job-market signals
    lines.append("## Hiring and job-market signals")
    hiring_and_news = hiring + labour_news
    if hiring_and_news:
        for item in hiring_and_news[:15]:
            lines.append(_format_item_line(item))
    else:
        lines.append("_No clear hiring or job-market signals this week._")
    lines.append("")

    # 4. Emerging roles and skills
    lines.append("## Emerging roles and skills")
    if keywords:
        lines.append("Top keywords detected across collected items:")
        for kw, count in keywords:
            lines.append(f"- **{kw}** — {count} mention(s)")
    else:
        lines.append("_No notable keywords detected this week._")
    if skills:
        lines.append("")
        lines.append("Skills-shortage signals:")
        for item in skills[:10]:
            lines.append(_format_item_line(item))
    lines.append("")

    # 5. Country spotlight
    lines.append("## Country spotlight")
    named_countries = [(c, n) for c, n in by_country.most_common() if c != "unknown"]
    if named_countries:
        for country, count in named_countries[:10]:
            lines.append(f"- **{country}**: {count} item(s)")
    else:
        lines.append("_No country-specific signals detected this week._")
    lines.append("")

    # 6. Underrepresented angles
    lines.append("## Underrepresented angles")
    observations = _underrepresented_observations(by_signal, by_country)
    for obs in observations:
        lines.append(f"- {obs}")
    lines.append("")

    # 7. What this means for HR / Talent / Workforce Planning
    lines.append("## What this means for HR / Talent / Workforce Planning")
    for bullet in _hr_observations(layoff_resto, hiring, skills, by_country):
        lines.append(f"- {bullet}")
    lines.append("")

    # 8. Sources reviewed
    lines.append("## Sources reviewed")
    by_source = _count_by(items, "source_name")
    if by_source:
        for source, count in by_source.most_common():
            lines.append(f"- {source}: {count} item(s)")
    else:
        lines.append("_No sources produced items this week._")
    lines.append("")

    return "\n".join(lines)


def _underrepresented_observations(by_signal: Counter, by_country: Counter) -> list[str]:
    """Generate simple 'what's missing' bullets."""
    obs = []
    if by_signal.get("skills_shortage", 0) == 0:
        obs.append(
            "No skills-shortage coverage this week — consider adding more "
            "sector- or skills-focused feeds."
        )
    if by_signal.get("hiring_freeze", 0) == 0:
        obs.append("No hiring-freeze signals surfaced — they may be under-reported.")
    eastern = {"Poland"}
    if not any(by_country.get(c) for c in eastern):
        obs.append(
            "Central/Eastern Europe (e.g. Poland) is under-represented; "
            "the feeds skew toward Western/Nordic coverage."
        )
    if not obs:
        obs.append(
            "Coverage looks reasonably balanced this week across signal types "
            "and regions."
        )
    return obs


def _hr_observations(
    layoff_resto: list[dict],
    hiring: list[dict],
    skills: list[dict],
    by_country: Counter,
) -> list[str]:
    """Generate simple, practical HR/workforce-planning takeaways."""
    bullets = []
    if layoff_resto:
        bullets.append(
            f"{len(layoff_resto)} restructuring/layoff signal(s) suggest watching "
            "affected sectors for available talent and internal-mobility risk."
        )
    if skills:
        bullets.append(
            "Skills-shortage signals point to roles worth prioritising in "
            "workforce planning and reskilling budgets."
        )
    if hiring:
        bullets.append(
            "Active hiring signals indicate where competition for talent may be "
            "rising — useful for compensation benchmarking."
        )
    if not bullets:
        bullets.append(
            "A quiet week: a good moment to review pipelines and refresh "
            "workforce-planning assumptions rather than react to news."
        )
    return bullets


# ---------------------------------------------------------------------------
# LLM-based report
# ---------------------------------------------------------------------------
def _build_llm_prompt(items: list[dict], days: int) -> str:
    """Compose a compact prompt with the collected items for the LLM."""
    today = _today_str()
    # Send only classified items to the LLM — unclassified headlines are noise.
    items = [i for i in items if i.get("signal_type") not in (None, "", "unknown")]
    lines = [
        f"You are an analyst writing the 'EU Job Market Radar' weekly report for {today}.",
        f"Below are {len(items)} items collected over the last {days} days.",
        "",
        "Write a concise but insightful markdown report titled exactly:",
        f"# EU Job Market Radar — {today}",
        "",
        "Use these sections as level-2 headings, in this order:",
    ]
    for section in REPORT_SECTIONS:
        lines.append(f"- {section}")
    lines += [
        "",
        "Be concrete, cite item titles where useful, avoid hype, and keep it tight.",
        "Do not invent facts beyond the items provided.",
        "",
        "ITEMS (one per line: [signal_type | country | company] title — url):",
    ]
    for item in items[:120]:  # keep the prompt bounded
        meta = " | ".join(
            x for x in (
                item.get("signal_type") or "unknown",
                item.get("country") or "-",
                item.get("company") or "-",
            )
        )
        lines.append(f"[{meta}] {item.get('title')} — {item.get('url')}")
    return "\n".join(lines)


def _generate_with_openai(prompt: str) -> str | None:
    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai package not installed — falling back.")
        return None
    try:
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=config.get_llm_model(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        return resp.choices[0].message.content
    except Exception as exc:
        logger.warning("OpenAI request failed: %s — falling back.", exc)
        return None


def _generate_with_anthropic(prompt: str) -> str | None:
    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic package not installed — falling back.")
        return None
    try:
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model=config.get_llm_model(),
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        # Concatenate any text blocks in the response.
        return "".join(
            block.text for block in resp.content if getattr(block, "type", "") == "text"
        )
    except Exception as exc:
        logger.warning("Anthropic request failed: %s — falling back.", exc)
        return None


def generate_llm_report(items: list[dict], days: int) -> str | None:
    """Try to generate the report via the configured LLM. None on failure."""
    provider = config.LLM_PROVIDER
    prompt = _build_llm_prompt(items, days)

    if provider == "openai" and config.OPENAI_API_KEY:
        logger.info("Generating report via OpenAI (%s)", config.get_llm_model())
        return _generate_with_openai(prompt)
    if provider == "anthropic" and config.ANTHROPIC_API_KEY:
        logger.info("Generating report via Anthropic (%s)", config.get_llm_model())
        return _generate_with_anthropic(prompt)

    return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def generate_report(items: list[dict], days: int = 7) -> str:
    """
    Generate the weekly report markdown.

    Tries the LLM if configured; otherwise (or on any failure) uses the
    deterministic fallback so we always return something useful.
    """
    if config.LLM_PROVIDER in ("openai", "anthropic"):
        report = generate_llm_report(items, days)
        if report:
            return report
        logger.info("LLM unavailable/failed — using deterministic fallback report.")

    return generate_fallback_report(items, days)
