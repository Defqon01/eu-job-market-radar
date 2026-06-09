"""
Job-board collector.

Currently implements Arbetsförmedlingen (Swedish Public Employment Service)
via the official JobTech open API — a public, no-auth JSON endpoint for live
job ads. This is the polite, sanctioned alternative to scraping a job board.

The file is named generically (`jobboard_collector`) so additional EU-level
job boards can be added here later as separate functions, each returning a
list of Items, all gathered by `collect()`.

JobTech API docs: https://jobtechdev.se/  (search endpoint returns JSON)
"""

from __future__ import annotations

import json
from urllib.parse import urlencode

import config
from radar.models import Item
from radar.utils.http import get
from radar.utils.logging import get_logger

logger = get_logger(__name__)


def _ad_to_item(ad: dict) -> Item | None:
    """Convert one JobTech ad dict into an Item, or None if unusable."""
    title = (ad.get("headline") or "").strip()
    url = (ad.get("webpage_url") or "").strip()
    if not title or not url:
        return None

    employer = ((ad.get("employer") or {}).get("name") or "").strip() or None
    address = ad.get("workplace_address") or {}
    municipality = (address.get("municipality") or "").strip()
    occupation = ((ad.get("occupation") or {}).get("label") or "").strip()
    field = ((ad.get("occupation_field") or {}).get("label") or "").strip() or None

    # A short human-readable summary from the structured fields.
    summary_bits = [b for b in (occupation, municipality) if b]
    summary = " — ".join(summary_bits) if summary_bits else None

    return Item(
        source_type="job_board",
        source_name="Arbetsförmedlingen",
        title=title,
        url=url,
        published_at=(ad.get("publication_date") or None),
        country="Sweden",                 # this API is Sweden-only
        company=employer,
        sector=field,
        signal_type="job_posting",        # these are real vacancies
        summary=summary,
        raw_text=summary,
    )


def collect_arbetsformedlingen() -> list[Item]:
    """Query the JobTech API for each configured search term."""
    items: list[Item] = []
    for query in config.ARBETSFORMEDLINGEN_QUERIES:
        params = {
            "q": query,
            "limit": config.ARBETSFORMEDLINGEN_LIMIT_PER_QUERY,
            "sort": "pubdate-desc",       # newest ads first
        }
        url = f"{config.ARBETSFORMEDLINGEN_API}?{urlencode(params)}"
        resp = get(url)
        if resp is None:
            continue
        try:
            data = resp.json()
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Arbetsförmedlingen returned non-JSON for '%s': %s", query, exc)
            continue

        hits = data.get("hits") or []
        logger.info("Arbetsförmedlingen '%s': %d ad(s)", query, len(hits))
        for ad in hits:
            item = _ad_to_item(ad)
            if item:
                items.append(item)

    return items


def collect() -> list[Item]:
    """Collect from all job boards implemented in this module."""
    items = collect_arbetsformedlingen()
    # TODO: add more EU-level job boards here as they become available.
    logger.info("Job-board collector produced %d items", len(items))
    return items
