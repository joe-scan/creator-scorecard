"""The arithmetic, and the one schema that both platforms have to fit into.

This file is the interesting one. Every platform describes its creators differently,
so each fetcher converts its own answer into the shape below. Where a platform cannot
supply a field, it says so instead of guessing, and the reason travels with the card.
"""

import statistics
import textwrap


def card(platform, name, handle, url):
    """An empty scorecard. Every field a platform cannot fill stays None on purpose."""
    return {
        "platform": platform,
        "name": name,
        "handle": handle,
        "url": url,
        # The size of the audience. The unit is different on every platform, so the
        # unit travels with the number rather than being assumed equivalent.
        "audience": None,
        "audience_unit": "",
        # What one piece of content actually reaches.
        "reach": None,
        "reach_unit": "",
        "engagement_pct": None,
        "cadence_days": None,
        "spread_pct": None,
        "sample": 0,
        # Why any of the above is missing. Stated, never filled in with a guess.
        "gaps": [],
    }


def summarise(reaches, timestamps):
    """Turn a sample of content into the three numbers every platform can support.

    reaches:    views per video, or viewers per stream, or whatever the platform counts
    timestamps: unix seconds for each piece of content
    """
    if not reaches:
        return {"reach": None, "cadence_days": None, "spread_pct": None, "sample": 0}

    span_seconds = max(timestamps) - min(timestamps)
    gaps = len(timestamps) - 1

    return {
        # Median, not mean, so one breakout does not flatter the whole channel.
        "reach": int(statistics.median(reaches)),
        "cadence_days": (span_seconds / 86400) / gaps if gaps else None,
        # Coefficient of variation. Low means every upload lands about the same.
        # High means the median is carried by the occasional hit.
        "spread_pct": (statistics.stdev(reaches) / statistics.mean(reaches) * 100
                       if len(reaches) > 1 else 0.0),
        "sample": len(reaches),
    }


# ---- printing ----

ROWS = [
    ("audience", "Audience", "count", "audience_unit"),
    ("reach", "Median reach", "count", "reach_unit"),
    ("engagement_pct", "Engagement rate", "pct2", None),
    ("cadence_days", "Days between posts", "days", None),
    ("spread_pct", "Reach spread", "pct0", None),
]


def _fmt(value, kind, unit=""):
    """Format one cell. The unit rides along with the number, never assumed shared."""
    if value is None:
        return "not available"
    if kind == "count":
        text = f"{value:,}"
    elif kind == "pct2":
        text = f"{value:.2f}%"
    elif kind == "pct0":
        text = f"{value:.0f}%"
    else:
        text = f"{value:.1f}"
    return f"{text} {unit}".strip() if unit else text


def show(cards, col=26, gutter=22):
    """Print scorecards as columns, so the holes in the schema line up and are obvious.

    The row names are deliberately generic and the platform's own unit sits next to
    each number. "Subscribers" and "Followers" are not the same thing, so the table
    must not quietly present them as one.
    """
    def row(label, cells):
        print(label[:gutter - 1].ljust(gutter) + "".join(c.rjust(col - 2) + "  " for c in cells))

    rule = "-" * (gutter + col * len(cards))

    print()
    print("".ljust(gutter) + "".join(c["name"][:col - 2].ljust(col) for c in cards))
    print("".ljust(gutter) + "".join((c["platform"] + " " + c["handle"])[:col - 2].ljust(col)
                                     for c in cards))
    print(rule)

    for key, label, kind, unit_key in ROWS:
        row(label, [_fmt(c[key], kind, c.get(unit_key, "") if unit_key else "")
                    for c in cards])

    print(rule)
    row("Sample", [f"{c['sample']} items" for c in cards])

    gaps = [(c["platform"], g) for c in cards for g in c["gaps"]]
    if gaps:
        print("\nWhat is missing, and why:")
        for platform, gap in gaps:
            for i, line in enumerate(textwrap.wrap(f"{platform}. {gap}", 74)):
                print(("  " if i == 0 else "     ") + line)
    print()
