from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass(slots=True)
class VideoRecord:
    video_id: str
    url: str
    author_username: Optional[str]
    author_id: Optional[str]
    author_category: Optional[str]
    description: Optional[str]
    create_time_utc: Optional[str]
    duration_seconds: Optional[float]
    hashtag_count: Optional[int]
    engagement_rate: Optional[float]
    is_weekend: Optional[int]
    digg_count: Optional[int]
    comment_count: Optional[int]
    share_count: Optional[int]
    play_count: Optional[int]
    source_target: str
    collected_at_utc: str

    @staticmethod
    def now_utc_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
