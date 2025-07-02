from typing import Any, List
import sqlite3
import pandas as pd

from app.settings import Settings


settings = Settings()  # type: ignore

DB_PATH = settings.DB_PATH


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """  
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            type TEXT,
            repo_name TEXT,
            created_at TEXT
        )
    """
    )
    conn.commit()
    conn.close()


def insert_events(events: List[dict[str, Any]]):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for event in events:
        try:
            c.execute(
                """
                INSERT OR IGNORE INTO events (id, type, repo_name, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (event["id"], event["type"], event["repo"], event["created_at"]),
            )
        except Exception as e:
            print(f"Error inserting event {event['id']}: {e}")
    conn.commit()
    conn.close()


def offset_metric(offset: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            """
            SELECT count(id) as Total_events_count, type
            FROM events
            WHERE created_at >= datetime('now', '-' || ? || ' minutes')
            GROUP BY type
            """,
            (offset,),
        )
        return c.fetchall()
    finally:
        conn.close()


def avg_pull_request_interval() -> dict[str, float | str]:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """
        SELECT repo_name, created_at
        FROM events
        WHERE type = 'PullRequestEvent'
        ORDER BY repo_name, created_at ASC
        """,
        conn,
    )
    conn.close()

    if df.empty:
        return {}

    df["created_at"] = pd.to_datetime(df["created_at"])

    def interval_avg(group: pd.DataFrame) -> float | None:
        if len(group) < 2:
            return None
        diffs = group["created_at"].diff().dropna().dt.total_seconds()
        return diffs.mean()

    result: dict[str, float] = (
        df.groupby("repo_name").apply(interval_avg).dropna().to_dict()
    )

    return result
