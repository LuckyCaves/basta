"""DuckDB persistence for Basta game rounds and words."""
from datetime import datetime
from typing import Any, Dict, List
import duckdb

DB_FILE = "basta_history.duckdb"


def get_connection(db_path: str = DB_FILE) -> duckdb.DuckDBPyConnection:
    """Connect to DuckDB and ensure schema exists."""
    conn = duckdb.connect(db_path)
    init_schema(conn)
    return conn


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create required tables if they do not exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rounds (
            round_id VARCHAR,
            letter VARCHAR,
            model_name VARCHAR,
            timestamp TIMESTAMP,
            total_points INT
        );
        CREATE TABLE IF NOT EXISTS round_words (
            round_id VARCHAR,
            category VARCHAR,
            word VARCHAR,
            is_valid BOOLEAN,
            points INT
        );
    """)


def save_round(
    conn: duckdb.DuckDBPyConnection,
    round_id: str,
    letter: str,
    model_name: str,
    timestamp: datetime,
    total_points: int,
    words: List[Dict[str, Any]],
) -> None:
    """Commit a completed round and its category words into DuckDB."""
    conn.execute(
        """
        INSERT INTO rounds (round_id, letter, model_name, timestamp, total_points)
        VALUES (?, ?, ?, ?, ?)
        """,
        [round_id, letter, model_name, timestamp, total_points],
    )
    for item in words:
        conn.execute(
            """
            INSERT INTO round_words (round_id, category, word, is_valid, points)
            VALUES (?, ?, ?, ?, ?)
            """,
            [round_id, item["category"], item["word"], item["is_valid"], item["points"]],
        )


def fetch_stats(conn: duckdb.DuckDBPyConnection) -> Dict[str, Any]:
    """Retrieve global game statistics from DuckDB."""
    count = conn.execute("SELECT COUNT(*) FROM rounds").fetchone()[0]
    if count == 0:
        return {"rounds": 0, "avg_points": 0.0, "best_score": 0, "valid_words": 0}
    avg_pts, max_pts = conn.execute(
        "SELECT AVG(total_points), MAX(total_points) FROM rounds"
    ).fetchone()
    valid_words = conn.execute(
        "SELECT COUNT(*) FROM round_words WHERE is_valid = true"
    ).fetchone()[0]
    return {
        "rounds": count,
        "avg_points": round(avg_pts or 0.0, 1),
        "best_score": max_pts or 0,
        "valid_words": valid_words,
    }
