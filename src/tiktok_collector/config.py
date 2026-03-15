from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class RunConfig:
    headless: bool
    timeout_ms: int
    delay_seconds: float
    retries: int


@dataclass(slots=True)
class TargetsConfig:
    users: list[str]
    hashtags: list[str]
    users_file: str | None


@dataclass(slots=True)
class LimitsConfig:
    max_videos_per_target: int


@dataclass(slots=True)
class FiltersConfig:
    min_videos_per_author: int
    min_median_play_count: int
    min_avg_like_count: int
    excluded_username_keywords: list[str]
    excluded_description_keywords: list[str]


@dataclass(slots=True)
class OutputConfig:
    csv_path: str
    sqlite_path: str


@dataclass(slots=True)
class AppConfig:
    run: RunConfig
    targets: TargetsConfig
    limits: LimitsConfig
    filters: FiltersConfig
    output: OutputConfig



def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()]



def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    run = raw.get("run", {})
    targets = raw.get("targets", {})
    limits = raw.get("limits", {})
    filters = raw.get("filters", {})
    output = raw.get("output", {})

    return AppConfig(
        run=RunConfig(
            headless=bool(run.get("headless", True)),
            timeout_ms=int(run.get("timeout_ms", 45000)),
            delay_seconds=float(run.get("delay_seconds", 2.0)),
            retries=max(0, int(run.get("retries", 2))),
        ),
        targets=TargetsConfig(
            users=_as_list(targets.get("users")),
            hashtags=_as_list(targets.get("hashtags")),
            users_file=(str(targets.get("users_file")).strip() if targets.get("users_file") else None),
        ),
        limits=LimitsConfig(
            max_videos_per_target=max(0, int(limits.get("max_videos_per_target", 30))),
        ),
        filters=FiltersConfig(
            min_videos_per_author=max(1, int(filters.get("min_videos_per_author", 1))),
            min_median_play_count=max(0, int(filters.get("min_median_play_count", 0))),
            min_avg_like_count=max(0, int(filters.get("min_avg_like_count", 0))),
            excluded_username_keywords=_as_list(filters.get("excluded_username_keywords")),
            excluded_description_keywords=_as_list(filters.get("excluded_description_keywords")),
        ),
        output=OutputConfig(
            csv_path=str(output.get("csv_path", "data/tiktok_videos.csv")),
            sqlite_path=str(output.get("sqlite_path", "data/tiktok_videos.db")),
        ),
    )
