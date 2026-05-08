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
    "author_category",
    "description",
    "create_time_utc",
    "duration_seconds",
    "hashtag_count",
    "engagement_rate",
    "is_weekend",
    "digg_count",
    "comment_count",
    "share_count",
    "play_count",
    "source_target",
    "collected_at_utc",
]


def _ensure_schema_columns(conn: sqlite3.Connection) -> None:
    existing_columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(tiktok_videos)").fetchall()
    }
    required_columns: dict[str, str] = {
        "author_category": "TEXT",
        "duration_seconds": "REAL",
        "hashtag_count": "INTEGER",
        "engagement_rate": "REAL",
        "is_weekend": "INTEGER",
    }

    for column_name, column_type in required_columns.items():
        if column_name not in existing_columns:
            conn.execute(f"ALTER TABLE tiktok_videos ADD COLUMN {column_name} {column_type}")


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
                author_category TEXT,
                description TEXT,
                create_time_utc TEXT,
                duration_seconds REAL,
                hashtag_count INTEGER,
                engagement_rate REAL,
                is_weekend INTEGER,
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
        _ensure_schema_columns(conn)

        rows = [
            (
                r.video_id,
                r.url,
                r.author_username,
                r.author_id,
                r.author_category,
                r.description,
                r.create_time_utc,
                r.duration_seconds,
                r.hashtag_count,
                r.engagement_rate,
                r.is_weekend,
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
                video_id, url, author_username, author_id, author_category, description, create_time_utc,
                duration_seconds, hashtag_count, engagement_rate, is_weekend,
                digg_count, comment_count, share_count, play_count, source_target, collected_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id, source_target) DO UPDATE SET
                url=excluded.url,
                author_username=excluded.author_username,
                author_id=excluded.author_id,
                author_category=excluded.author_category,
                description=excluded.description,
                create_time_utc=excluded.create_time_utc,
                duration_seconds=excluded.duration_seconds,
                hashtag_count=excluded.hashtag_count,
                engagement_rate=excluded.engagement_rate,
                is_weekend=excluded.is_weekend,
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
