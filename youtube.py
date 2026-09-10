"""YouTube. Auth is an API key on the query string, which is the simple case.

Three calls, 3 quota units of the 10,000 a free key gets per day:
  channels      -> the channel, its subscriber count, its uploads playlist
  playlistItems -> the IDs of its recent uploads
  videos        -> statistics for those uploads, all in one batched call
"""

from datetime import datetime

import requests

import metrics

API = "https://www.googleapis.com/youtube/v3"
SAMPLE = 30


def _get(endpoint, key, **params):
    params["key"] = key
    r = requests.get(f"{API}/{endpoint}", params=params, timeout=15)
    if not r.ok:
        # 400 bad key or bad request, 403 quota spent or key restricted, 404 not found.
        reason = r.json().get("error", {}).get("message", r.text)
        if "referer" in reason.lower():
            # A key restricted to a website cannot be used from a command line, which
            # has no referrer to send. One key per use, each restricted to suit.
            reason += (" This key is restricted to a website, so it only works in a "
                       "browser page. Use a separate key for the command line, "
                       "restricted by IP address or left unrestricted.")
        raise RuntimeError(f"YouTube said {r.status_code}: {reason}")
    return r.json()


def _find_channel(handle, key):
    field = "id" if handle.startswith("UC") else "forHandle"
    data = _get("channels", key, part="snippet,statistics,contentDetails", **{field: handle})
    if not data.get("items"):
        raise RuntimeError(f"No YouTube channel found for {handle}.")
    return data["items"][0]


def _recent_videos(channel, key, limit=SAMPLE, pages=1):
    """Recent uploads. One page is 50 at most, so more than that means paging."""
    playlist = channel["contentDetails"]["relatedPlaylists"]["uploads"]
    video_ids, token = [], None

    for _ in range(pages):
        params = {"part": "contentDetails", "playlistId": playlist,
                  "maxResults": min(limit, 50)}
        if token:
            params["pageToken"] = token          # this is what paging actually is
        page = _get("playlistItems", key, **params)

        video_ids += [i["contentDetails"]["videoId"] for i in page.get("items", [])]
        token = page.get("nextPageToken")
        if not token or len(video_ids) >= limit:
            break

    video_ids = video_ids[:limit]
    if not video_ids:
        raise RuntimeError("That YouTube channel has no public uploads to measure.")

    # One call for up to 50 videos rather than 50 calls. This is batching, and it is
    # why the whole lookup costs 3 quota units instead of 32.
    return _get("videos", key, part="snippet,statistics", id=",".join(video_ids))["items"]


def fetch(handle, key, limit=SAMPLE):
    channel = _find_channel(handle, key)
    videos = _recent_videos(channel, key, limit=limit)

    views, engagements, stamps = [], [], []
    for v in videos:
        seen = int(v["statistics"].get("viewCount", 0))
        if not seen:
            continue                              # no views means no ratio to take
        views.append(seen)
        reactions = (int(v["statistics"].get("likeCount", 0))
                     + int(v["statistics"].get("commentCount", 0)))
        engagements.append(reactions / seen)
        published = v["snippet"]["publishedAt"].replace("Z", "+00:00")
        stamps.append(datetime.fromisoformat(published).timestamp())

    c = metrics.card("YouTube", channel["snippet"]["title"],
                     channel["snippet"].get("customUrl", channel["id"]),
                     "https://www.youtube.com/channel/" + channel["id"])

    subs = int(channel["statistics"].get("subscriberCount", 0))
    c["audience"] = subs or None
    c["audience_unit"] = "subs"
    c["reach_unit"] = "per video"
    c.update(metrics.summarise(views, stamps))

    if engagements:
        c["engagement_pct"] = sum(engagements) / len(engagements) * 100

    if channel["statistics"].get("hiddenSubscriberCount"):
        c["gaps"].append("Subscribers: this channel hides the count.")

    return c
