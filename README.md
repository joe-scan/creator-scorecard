# creator-scorecard

A small command line tool that scores a YouTube creator the way a brand would look at them.
Give it a handle, it gives you the numbers back.

```
$ python youtube_scorecard.py @mkbhd

Marques Brownlee
----------------
Subscribers                 21,200,000
Median views per video       3,631,714
Views as % of subs               17.1%
Engagement rate                  3.10%
Days between uploads               4.1
View spread                        39%

Measured on the last 30 videos.
```

A handle or a channel ID both work: `@veritasium` and `UCXuqSBlHAE6Xw-yeJA0Tunw` are equally
valid arguments.

## What the numbers mean

| Number | How it is worked out | Why a brand cares |
| --- | --- | --- |
| Median views per video | The middle value of the last 30 videos, not the average, so one viral hit does not flatter the channel | What a sponsored video would realistically reach |
| Views as % of subs | Median views divided by subscriber count | Whether the audience still shows up, or the subscriber number is historical |
| Engagement rate | Likes plus comments, divided by views, averaged across the sample | Whether people react or just watch |
| Days between uploads | The span of the sample divided by the gaps in it | Whether the channel is active and predictable |
| View spread | Standard deviation of views as a percentage of the mean | Low means every video lands about the same. High means the channel lives on the odd breakout |

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env      # then paste your key into .env
python youtube_scorecard.py @mkbhd
```

Getting a key takes about ten minutes and costs nothing:

1. Open `console.cloud.google.com` and sign in.
2. Create a new project, any name.
3. APIs and Services, then Library. Search for YouTube Data API v3 and enable it.
4. Credentials, Create Credentials, API key. Copy it into `.env`.

`.env` is gitignored, so your key stays on your machine.

## Quota

A free key gets 10,000 units a day. One run of this costs 3 units: one call to find the
channel, one to list its recent uploads, one to fetch those videos' statistics. So roughly
3,000 runs a day before it stops.

If it does stop, the API returns HTTP 403 and the script prints the reason it gave.

## Limits worth knowing

- **One page of uploads.** The playlist call takes up to 50 videos in one request. Going deeper
  means following `pageToken` through more pages, which this does not do yet.
- **Public data only.** No audience demographics, no location, no age split. That needs either
  the creator's own permission or a paid data provider.
- **YouTube only.** A subscriber here is not the same unit as a follower on Instagram or TikTok,
  which is the interesting part of adding a second platform.
- **Instagram and TikTok are not free.** Both need app review and a business account, which is
  why companies pay for creator data rather than collecting it themselves.

## Comparing three channels

Run on the same day, on the last 30 uploads of each.

| | MKBHD | Veritasium | Linus Tech Tips |
| --- | --- | --- | --- |
| Subscribers | 21,200,000 | 21,200,000 | 16,900,000 |
| Median views | 3,631,714 | 3,113,885 | 1,165,410 |
| Views as % of subs | 17.1% | 14.7% | 6.9% |
| Engagement rate | 3.10% | 2.89% | 2.61% |
| Days between uploads | 4.1 | 3.9 | 1.2 |
| View spread | 39% | 79% | 68% |

Two channels with an identical subscriber count are not the same buy. MKBHD's views land in a
tight band, so a sponsored video has a predictable floor. Veritasium reaches a similar median
off a spread twice as wide, meaning the average is carried by breakout videos and any single
placement is a gamble. Linus Tech Tips posts nearly daily to a smaller share of its own
subscribers, which is a volume strategy rather than an event one.

The subscriber count, the number most often quoted in a media kit, is the least useful column
here.
