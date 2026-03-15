from __future__ import annotations

import sqlite3
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from .models import VideoRecord


CSV_COLUMNS = [
    "video_id",
    "url",
    "author_username",
    "author_id",
    "description",
    "create_time_utc",
    "digg_count",
    "comment_count",
    "share_count",
    "play_count",
    "source_target",
    "collected_at_utc",
]


def save_to_csv(records: list[VideoRecord], csv_path: str) -> None:
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    frame = pd.DataFrame([asdict(r) for r in records], columns=CSV_COLUMNS)
    frame.drop_duplicates(subset=["video_id", "source_target"], inplace=True)
    if not frame.empty:
        frame.sort_values(by=["collected_at_utc", "video_id"], inplace=True)
    frame.to_csv(path, index=False)


def save_to_sqlite(records: list[VideoRecord], sqlite_path: str) -> None:
    path = Path(sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tiktok_videos (
                video_id TEXT NOT NULL,
                url TEXT NOT NULL,
                author_username TEXT,
                author_id TEXT,
                description TEXT,
                create_time_utc TEXT,
                digg_count INTEGER,
                comment_count INTEGER,
                share_count INTEGER,
                play_count INTEGER,
                source_target TEXT NOT NULL,
                collected_at_utc TEXT NOT NULL,
                PRIMARY KEY (video_id, source_target)
            )
            """
        )

        rows = [
            (
                r.video_id,
                r.url,
                r.author_username,
                r.author_id,
                r.description,
                r.create_time_utc,
                r.digg_count,
                r.comment_count,
                r.share_count,
                r.play_count,
                r.source_target,
                r.collected_at_utc,
            )
            for r in records
        ]

        conn.executemany(
            """
            INSERT INTO tiktok_videos (
                video_id, url, author_username, author_id, description, create_time_utc,
                digg_count, comment_count, share_count, play_count, source_target, collected_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id, source_target) DO UPDATE SET
                url=excluded.url,
                author_username=excluded.author_username,
                author_id=excluded.author_id,
                description=excluded.description,
                create_time_utc=excluded.create_time_utc,
                digg_count=excluded.digg_count,
                comment_count=excluded.comment_count,
                share_count=excluded.share_count,
                play_count=excluded.play_count,
                collected_at_utc=excluded.collected_at_utc
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()
