"""Print a scorecard for one YouTube creator.

Usage:  python youtube_scorecard.py @mkbhd

Three API calls, 3 quota units out of the 10,000 a free key gets per day:
  1. channels     find the channel, its subscriber count, its uploads playlist
  2. playlistItems  the IDs of its most recent uploads
  3. videos       views, likes and comments for those uploads
"""

import os
import statistics
import sys
from datetime import datetime

import requests

API = "https://www.googleapis.com/youtube/v3"
SAMPLE = 30  # how many recent videos to judge the channel on


def load_key():
    """Read the API key from the environment, or from a .env file beside this script."""
    key = os.environ.get("YOUTUBE_API_KEY")
    if key:
        return key
    try:
        with open(os.path.join(os.path.dirname(__file__), ".env")) as f:
            for line in f:
                if line.strip().startswith("YOUTUBE_API_KEY="):
                    return line.strip().split("=", 1)[1].strip().strip("\"'")
    except FileNotFoundError:
        pass
    sys.exit("No API key. Copy .env.example to .env and put your key in it.")


def get(endpoint, key, **params):
    """One GET against the API. Raises with the API's own message if it refuses."""
    params["key"] = key
    r = requests.get(f"{API}/{endpoint}", params=params, timeout=15)
    if not r.ok:
        # 400 bad request, 401 bad key, 403 quota exceeded, 404 not found.
        reason = r.json().get("error", {}).get("message", r.text)
        sys.exit(f"API said {r.status_code}: {reason}")
    return r.json()


def find_channel(handle, key):
    """Look the channel up by @handle, or by channel ID if one was given instead."""
    field = "id" if handle.startswith("UC") else "forHandle"
    data = get("channels", key, part="snippet,statistics,contentDetails", **{field: handle})
    if not data.get("items"):
        sys.exit(f"No channel found for {handle}.")
    return data["items"][0]


def recent_videos(uploads_playlist, key, limit=SAMPLE):
    """The most recent uploads. One page of up to 50; more would need pageToken paging."""
    data = get("playlistItems", key, part="contentDetails",
               playlistId=uploads_playlist, maxResults=min(limit, 50))
    ids = [item["contentDetails"]["videoId"] for item in data.get("items", [])]
    if not ids:
        sys.exit("That channel has no public uploads to measure.")
    return get("videos", key, part="snippet,statistics", id=",".join(ids))["items"]


def score(videos):
    """The numbers a brand actually asks about, worked out from raw counts."""
    views, engagements, dates = [], [], []
    for v in videos:
        stats = v["statistics"]
        seen = int(stats.get("viewCount", 0))
        if seen == 0:
            continue  # a video with no views tells us nothing and breaks the division
        views.append(seen)
        reactions = int(stats.get("likeCount", 0)) + int(stats.get("commentCount", 0))
        engagements.append(reactions / seen)
        dates.append(datetime.fromisoformat(v["snippet"]["publishedAt"].replace("Z", "+00:00")))

    span_days = (max(dates) - min(dates)).days
    return {
        "videos_measured": len(views),
        "median_views": int(statistics.median(views)),
        "engagement_rate": statistics.mean(engagements) * 100,
        "days_between_uploads": span_days / (len(dates) - 1) if len(dates) > 1 else 0,
        # Coefficient of variation. Low means every video lands about the same.
        # High means the channel lives on the odd viral hit.
        "view_spread": (statistics.stdev(views) / statistics.mean(views) * 100
                        if len(views) > 1 else 0),
    }


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python youtube_scorecard.py @handle")

    key = load_key()
    channel = find_channel(sys.argv[1], key)
    videos = recent_videos(channel["contentDetails"]["relatedPlaylists"]["uploads"], key)
    s = score(videos)

    subs = int(channel["statistics"].get("subscriberCount", 0))
    print(f"\n{channel['snippet']['title']}")
    print("-" * len(channel["snippet"]["title"]))
    print(f"{'Subscribers':<24}{subs:>14,}")
    print(f"{'Median views per video':<24}{s['median_views']:>14,}")
    if subs:
        reach = f"{s['median_views'] / subs * 100:.1f}%"
    else:
        reach = "hidden"  # some channels hide their subscriber count
    print(f"{'Views as % of subs':<24}{reach:>14}")
    print(f"{'Engagement rate':<24}{s['engagement_rate']:>13.2f}%")
    print(f"{'Days between uploads':<24}{s['days_between_uploads']:>14.1f}")
    print(f"{'View spread':<24}{s['view_spread']:>13.0f}%")
    print(f"\nMeasured on the last {s['videos_measured']} videos.\n")


if __name__ == "__main__":
    main()
