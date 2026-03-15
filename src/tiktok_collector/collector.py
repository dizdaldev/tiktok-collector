from __future__ import annotations

import json
import os
import re
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, Page, Playwright, sync_playwright
from yt_dlp import YoutubeDL

from .config import AppConfig
from .models import VideoRecord


class _QuietYDLLogger:
    def debug(self, msg: str) -> None:  # noqa: D401
        return

    def warning(self, msg: str) -> None:  # noqa: D401
        return

    def error(self, msg: str) -> None:  # noqa: D401
        return

_UNIVERSAL_DATA_RE = re.compile(
    r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
    re.DOTALL,
)
_SIGI_STATE_RE = re.compile(
    r'<script id="SIGI_STATE"[^>]*>(.*?)</script>',
    re.DOTALL,
)
_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
    re.DOTALL,
)



def _parse_epoch_to_iso(value: Any) -> str | None:
    try:
        epoch = int(value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()



def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None



def _extract_json_blob(html: str) -> dict[str, Any]:
    for pattern in (_UNIVERSAL_DATA_RE, _SIGI_STATE_RE, _NEXT_DATA_RE):
        match = pattern.search(html)
        if match:
            raw = match.group(1).strip()
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                continue
    return {}



def _walk(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk(item)



def _video_from_candidate(candidate: dict[str, Any], source_target: str) -> VideoRecord | None:
    video_id = candidate.get("id") or candidate.get("videoId")
    if not video_id:
        return None

    stats = candidate.get("stats") or {}
    video = candidate.get("video") or {}
    author = candidate.get("author") or {}

    username = (
        author.get("uniqueId")
        or candidate.get("authorName")
        or candidate.get("author", {}).get("uniqueId")
    )
    author_id = author.get("id") or candidate.get("authorId")

    video_id = str(video_id)
    url = f"https://www.tiktok.com/@{username}/video/{video_id}" if username else f"https://www.tiktok.com/video/{video_id}"

    return VideoRecord(
        video_id=video_id,
        url=url,
        author_username=username,
        author_id=str(author_id) if author_id is not None else None,
        description=candidate.get("desc") or candidate.get("description"),
        create_time_utc=_parse_epoch_to_iso(candidate.get("createTime")),
        digg_count=_to_int(stats.get("diggCount")),
        comment_count=_to_int(stats.get("commentCount")),
        share_count=_to_int(stats.get("shareCount")),
        play_count=_to_int(stats.get("playCount") or video.get("playCount")),
        source_target=source_target,
        collected_at_utc=VideoRecord.now_utc_iso(),
    )



def _collect_from_page_html(html: str, source_target: str, limit: int) -> list[VideoRecord]:
    blob = _extract_json_blob(html)
    found: dict[str, VideoRecord] = {}

    for node in _walk(blob):
        has_video_shape = (
            ("id" in node and ("stats" in node or "video" in node))
            or ("videoId" in node and ("description" in node or "desc" in node))
        )
        if not has_video_shape:
            continue

        record = _video_from_candidate(node, source_target)
        if record and record.video_id not in found:
            found[record.video_id] = record
            if limit > 0 and len(found) >= limit:
                break

    return list(found.values())


def _collect_from_payloads(payloads: list[dict[str, Any]], source_target: str, limit: int) -> list[VideoRecord]:
    found: dict[str, VideoRecord] = {}

    for payload in payloads:
        for node in _walk(payload):
            if not isinstance(node, dict):
                continue

            has_video_shape = (
                ("id" in node and ("stats" in node or "video" in node))
                or ("videoId" in node and ("description" in node or "desc" in node))
            )
            if not has_video_shape:
                continue

            record = _video_from_candidate(node, source_target)
            if record and record.video_id not in found:
                found[record.video_id] = record
                if limit > 0 and len(found) >= limit:
                    return list(found.values())

    return list(found.values())


def _is_candidate_api_url(url: str) -> bool:
    lowered = url.lower()
    if "tiktok.com/api/" not in lowered:
        return False

    candidates = (
        "post/item_list",
        "challenge/item_list",
        "item_list",
        "itemlist",
        "aweme",
    )
    return any(part in lowered for part in candidates)


def _attach_response_collector(page: Page, payloads: list[dict[str, Any]]) -> None:
    def _on_response(response):  # type: ignore[no-untyped-def]
        try:
            if not _is_candidate_api_url(response.url):
                return
            data = response.json()
            if isinstance(data, dict):
                payloads.append(data)
        except Exception:  # noqa: BLE001
            return

    page.on("response", _on_response)


def _collect_target_with_ytdlp(url: str, source_target: str, limit: int) -> list[VideoRecord]:
    ydl_opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "logger": _QuietYDLLogger(),
        "skip_download": True,
        "ignoreerrors": True,
        "extract_flat": True,
        "nocheckcertificate": True,
    }
    if limit > 0:
        ydl_opts["playlistend"] = limit

    found: dict[str, VideoRecord] = {}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not isinstance(info, dict):
        return []

    entries = info.get("entries") or []
    if not isinstance(entries, list):
        return []

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        video_id = entry.get("id")
        if not video_id:
            continue
        video_id = str(video_id)

        username = entry.get("uploader")
        author_id = entry.get("uploader_id")
        page_url = entry.get("webpage_url")
        if not page_url:
            if username:
                page_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
            else:
                page_url = f"https://www.tiktok.com/video/{video_id}"

        record = VideoRecord(
            video_id=video_id,
            url=str(page_url),
            author_username=str(username) if username is not None else None,
            author_id=str(author_id) if author_id is not None else None,
            description=entry.get("description") or entry.get("title"),
            create_time_utc=_parse_epoch_to_iso(entry.get("timestamp")),
            digg_count=_to_int(entry.get("like_count")),
            comment_count=_to_int(entry.get("comment_count")),
            share_count=_to_int(entry.get("repost_count")),
            play_count=_to_int(entry.get("view_count")),
            source_target=source_target,
            collected_at_utc=VideoRecord.now_utc_iso(),
        )
        found[record.video_id] = record
        if limit > 0 and len(found) >= limit:
            break

    return list(found.values())



def _new_browser(playwright: Playwright, headless: bool) -> Browser:
    proxy = os.getenv("TIKTOK_PROXY", "").strip()
    launch_kwargs: dict[str, Any] = {"headless": headless}
    if proxy:
        launch_kwargs["proxy"] = {"server": proxy}
    return playwright.chromium.launch(**launch_kwargs)



def _collect_target(url: str, source_target: str, config: AppConfig) -> list[VideoRecord]:
    # Preferred path: yt-dlp is usually more resilient to schema/anti-bot changes.
    try:
        ytdlp_records = _collect_target_with_ytdlp(
            url=url,
            source_target=source_target,
            limit=config.limits.max_videos_per_target,
        )
        if ytdlp_records:
            return ytdlp_records
    except Exception:  # noqa: BLE001
        pass

    # Fallback path: parse rendered page data via Playwright.
    user_agent = os.getenv("TIKTOK_USER_AGENT", "").strip() or None

    with sync_playwright() as p:
        browser = _new_browser(p, config.run.headless)
        try:
            context = browser.new_context(
                user_agent=user_agent,
                locale="en-US",
            )
            page = context.new_page()
            page.set_default_timeout(config.run.timeout_ms)
            page.set_extra_http_headers({"Accept-Language": "en-US,en;q=0.9"})
            payloads: list[dict[str, Any]] = []
            _attach_response_collector(page, payloads)

            last_error: Exception | None = None
            for attempt in range(config.run.retries + 1):
                try:
                    page.goto(url, wait_until="domcontentloaded")
                    page.wait_for_timeout(int(config.run.delay_seconds * 1000))

                    for _ in range(3):
                        page.mouse.wheel(0, 3500)
                        page.wait_for_timeout(int(config.run.delay_seconds * 600))

                    html = page.content()
                    records = _collect_from_page_html(
                        html=html,
                        source_target=source_target,
                        limit=config.limits.max_videos_per_target,
                    )
                    if records:
                        return records

                    records = _collect_from_payloads(
                        payloads=payloads,
                        source_target=source_target,
                        limit=config.limits.max_videos_per_target,
                    )
                    return records
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    time.sleep(min(8, 1.5 ** (attempt + 1)))

            if last_error:
                raise last_error
            return []
        finally:
            browser.close()


def _load_user_targets(config: AppConfig) -> list[str]:
    users = [u.strip().lstrip("@") for u in config.targets.users if u.strip()]

    users_file = config.targets.users_file
    if users_file:
        path = Path(users_file)
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                value = line.strip()
                if not value or value.startswith("#"):
                    continue
                users.append(value.lstrip("@"))

    dedup: dict[str, None] = {}
    for username in users:
        dedup[username] = None
    return list(dedup.keys())


def _contains_any_keyword(text: str | None, keywords: list[str]) -> bool:
    if not text or not keywords:
        return False
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords if keyword)


def _is_influencer_author(records: list[VideoRecord], config: AppConfig) -> bool:
    if not records:
        return False

    filters = config.filters
    if len(records) < filters.min_videos_per_author:
        return False

    username = records[0].author_username
    if _contains_any_keyword(username, filters.excluded_username_keywords):
        return False

    if filters.excluded_description_keywords:
        for record in records:
            if _contains_any_keyword(record.description, filters.excluded_description_keywords):
                return False

    views = [r.play_count for r in records if r.play_count is not None]
    likes = [r.digg_count for r in records if r.digg_count is not None]

    median_views = int(statistics.median(views)) if views else 0
    avg_likes = int(sum(likes) / len(likes)) if likes else 0

    if median_views < filters.min_median_play_count:
        return False
    if avg_likes < filters.min_avg_like_count:
        return False

    return True


def _apply_influencer_filters(records: list[VideoRecord], config: AppConfig) -> list[VideoRecord]:
    filters = config.filters
    has_any_filter = any(
        [
            filters.min_videos_per_author > 1,
            filters.min_median_play_count > 0,
            filters.min_avg_like_count > 0,
            len(filters.excluded_username_keywords) > 0,
            len(filters.excluded_description_keywords) > 0,
        ]
    )
    if not has_any_filter:
        return records

    by_author: dict[str, list[VideoRecord]] = {}
    for record in records:
        author_key = record.author_username or record.author_id or ""
        if not author_key:
            continue
        by_author.setdefault(author_key, []).append(record)

    kept: list[VideoRecord] = []
    for author_records in by_author.values():
        if _is_influencer_author(author_records, config):
            kept.extend(author_records)

    return kept



def collect_all(config: AppConfig) -> list[VideoRecord]:
    all_records: list[VideoRecord] = []

    for user in _load_user_targets(config):
        source_target = f"user:{user}"
        url = f"https://www.tiktok.com/@{user}"
        try:
            all_records.extend(_collect_target(url=url, source_target=source_target, config=config))
        except Exception as exc:  # noqa: BLE001
            print(f"[SKIP] {user}: {exc}")

    for hashtag in config.targets.hashtags:
        source_target = f"hashtag:{hashtag}"
        url = f"https://www.tiktok.com/tag/{hashtag}"
        try:
            all_records.extend(_collect_target(url=url, source_target=source_target, config=config))
        except Exception as exc:  # noqa: BLE001
            print(f"[SKIP] #{hashtag}: {exc}")

    dedup: dict[tuple[str, str], VideoRecord] = {}
    for record in all_records:
        dedup[(record.video_id, record.source_target)] = record

    return _apply_influencer_filters(list(dedup.values()), config)
