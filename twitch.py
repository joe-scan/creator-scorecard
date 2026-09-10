"""Twitch. Auth is a token you are issued, which is the harder and more common case.

YouTube takes a key on the URL and that is the whole story. Twitch makes you swap a
client ID and secret for a short-lived access token, then send that token as a Bearer
header on every call. When it expires you swap again. That exchange is the OAuth
client credentials grant.

The difference in one line: a key is a password you keep sending, a token is something
you are issued and that runs out.

Because the secret is required to get a token, none of this can live in a browser page.
That is why the web version of this project is YouTube only.
"""

import json
import os
import time
from datetime import datetime

import requests

import metrics

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
API = "https://api.twitch.tv/helix"
SAMPLE = 30
TOKEN_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".twitch_token.json")


# ---- the token ----

def _cached_token():
    """A token lasts weeks, so asking for a new one on every run is waste."""
    try:
        with open(TOKEN_CACHE) as f:
            saved = json.load(f)
        if saved.get("expires_at", 0) > time.time() + 60:   # a minute of headroom
            return saved["access_token"]
    except (OSError, ValueError, KeyError):
        pass
    return None


def get_token(client_id, client_secret):
    token = _cached_token()
    if token:
        return token

    r = requests.post(TOKEN_URL, params={
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",     # no user involved, just the app itself
    }, timeout=15)

    if not r.ok:
        raise RuntimeError(f"Twitch refused the token request, {r.status_code}: {r.text}")

    body = r.json()
    try:
        with open(TOKEN_CACHE, "w") as f:
            json.dump({"access_token": body["access_token"],
                       "expires_at": time.time() + body.get("expires_in", 0)}, f)
        os.chmod(TOKEN_CACHE, 0o600)
    except OSError:
        pass                                    # not being able to cache is not fatal

    return body["access_token"]


# ---- the calls ----

def _get(endpoint, client_id, token, **params):
    r = requests.get(f"{API}/{endpoint}", params=params, timeout=15, headers={
        "Client-Id": client_id,
        "Authorization": f"Bearer {token}",     # the token goes in a header, not the URL
    })
    if r.status_code == 401:
        raise RuntimeError("Twitch said 401. The token has expired or been revoked. "
                           "Delete .twitch_token.json and run again.")
    if not r.ok:
        raise RuntimeError(f"Twitch said {r.status_code}: {r.text[:200]}")
    return r.json()


def fetch(login, client_id, client_secret, limit=SAMPLE):
    token = get_token(client_id, client_secret)
    login = login.lstrip("@")

    users = _get("users", client_id, token, login=login)
    if not users.get("data"):
        raise RuntimeError(f"No Twitch channel found for {login}.")
    user = users["data"][0]

    # Past broadcasts. Twitch calls them archives, and only keeps them for a while.
    vods = _get("videos", client_id, token,
                user_id=user["id"], type="archive", first=min(limit, 100))

    views, stamps = [], []
    for v in vods.get("data", []):
        seen = int(v.get("view_count", 0))
        if not seen:
            continue
        views.append(seen)
        stamps.append(datetime.fromisoformat(v["published_at"].replace("Z", "+00:00")).timestamp())

    c = metrics.card("Twitch", user["display_name"], user["login"],
                     "https://twitch.tv/" + user["login"])
    c["audience_unit"] = "followers"
    c["reach_unit"] = "per stream"
    c.update(metrics.summarise(views, stamps))

    # The honest holes. Both are stated rather than guessed at, and both are the
    # reason a creator data company has a product to sell.
    c["gaps"].append("Followers: Twitch only gives a follower count to a token the "
                     "creator has personally authorised, so an app token cannot see it.")
    c["gaps"].append("Engagement rate: past broadcasts carry no public likes or "
                     "comments, so there is nothing to divide by views.")

    if not views:
        c["gaps"].append("Reach: no past broadcasts are public. Twitch deletes them "
                         "after a couple of weeks unless the creator saves them.")

    return c
