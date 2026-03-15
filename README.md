# TikTok Public Metadata Collector

This starter project collects **publicly visible** TikTok metadata from user and hashtag pages, then writes results to CSV + SQLite.

Extraction backend order:
- `yt-dlp` (primary, more resilient)
- Playwright page parser (fallback)

## Important

- Follow TikTok Terms and local privacy/data laws.
- Use this only for legitimate research/analytics use cases.
- Site structure changes may break extraction over time.

## What it collects

- `video_id`
- `url`
- `author_username`
- `author_id`
- `description`
- `create_time_utc`
- `digg_count`, `comment_count`, `share_count`, `play_count`
- `source_target`
- `collected_at_utc`

## 1) Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
pip install -e .
```

## 2) Configure targets

Edit [config.yaml](config.yaml):

- `targets.users`: usernames without `@`
- `targets.users_file`: line-by-line username file (best for influencer lists)
- `targets.hashtags`: hashtags without `#`
- `limits.max_videos_per_target`: per target cap (`0` = all available)
- `filters.*`: creator-level influencer filters (views/likes/keyword exclusions)

Optional runtime env vars in [\.env.example](.env.example):

- `TIKTOK_PROXY`
- `TIKTOK_USER_AGENT`

Copy `.env.example` to `.env` if needed.

## 3) Run

```bash
tiktok-collect --config config.yaml
```

## Output

- CSV: `data/tiktok_videos.csv`
- SQLite: `data/tiktok_videos.db` (table: `tiktok_videos`)

## Notes

- This extractor reads page-embedded JSON (`__UNIVERSAL_DATA_FOR_REHYDRATION__` / `SIGI_STATE`).
- If schema changes, update parser logic in [src/tiktok_collector/collector.py](src/tiktok_collector/collector.py).

## Troubleshooting

- If you still get `Collected 0 records`, try:
	- setting a proxy in `.env` (`TIKTOK_PROXY=...`)
	- changing targets in [config.yaml](config.yaml) to active public accounts
	- increasing `run.delay_seconds` and `run.retries`
- On some systems, SSL trust chains can fail; the `yt-dlp` backend already runs with certificate checks disabled to reduce this issue.
