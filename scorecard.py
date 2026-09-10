"""Score creators across platforms, side by side, in one schema.

Usage:
    python scorecard.py youtube:@mkbhd
    python scorecard.py youtube:@mkbhd twitch:pokimane
    python scorecard.py @mkbhd                    # youtube is assumed

Credentials come from the environment, or from a .env file beside this script.
See .env.example for what is needed.
"""

import os
import sys

import metrics
import twitch
import youtube

PLATFORMS = ("youtube", "twitch")


def load_env():
    """Read a .env file beside this script into the environment, without a dependency."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                os.environ.setdefault(name.strip(), value.strip().strip("\"'"))
    except FileNotFoundError:
        pass


def need(name, what):
    value = os.environ.get(name, "").strip()
    if not value:
        sys.exit(f"No {what}. Copy .env.example to .env and fill in {name}.")
    return value


def parse(argument):
    """Turn "twitch:pokimane" into ("twitch", "pokimane"). YouTube is the default."""
    if ":" in argument:
        platform, handle = argument.split(":", 1)
        platform = platform.lower()
        if platform not in PLATFORMS:
            sys.exit(f"Unknown platform '{platform}'. Use one of: {', '.join(PLATFORMS)}.")
        return platform, handle
    return "youtube", argument


def fetch(platform, handle):
    if platform == "youtube":
        return youtube.fetch(handle, need("YOUTUBE_API_KEY", "YouTube API key"))
    return twitch.fetch(handle,
                        need("TWITCH_CLIENT_ID", "Twitch client ID"),
                        need("TWITCH_CLIENT_SECRET", "Twitch client secret"))


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python scorecard.py youtube:@mkbhd [twitch:pokimane]")

    load_env()

    cards, problems = [], []
    for argument in sys.argv[1:]:
        platform, handle = parse(argument)
        try:
            cards.append(fetch(platform, handle))
        except RuntimeError as err:
            # One creator failing must not lose the others.
            problems.append(f"{argument}: {err}")

    if cards:
        metrics.show(cards)
    for problem in problems:
        print(problem, file=sys.stderr)
    if not cards:
        sys.exit(1)


if __name__ == "__main__":
    main()
