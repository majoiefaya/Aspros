from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class Storage:
    """Petite couche SQLite, remplaçable plus tard par PostgreSQL."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection: sqlite3.Connection | None = None
        self._initialize()

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:  # pragma: no cover - protection défensive pour les fermetures lors de la destruction.
            pass

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS device_states (
                    device_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def save_device_state(self, device_id: str, state: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO device_states(device_id, state_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                  state_json = excluded.state_json,
                  updated_at = excluded.updated_at
                """,
                (device_id, json.dumps(state), self._now()),
            )

    def load_device_state(self, device_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT state_json FROM device_states WHERE device_id = ?", (device_id,)
            ).fetchone()
            return json.loads(row["state_json"]) if row else None

    def log(self, source: str, event_type: str, payload: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO audit_logs(created_at, source, event_type, payload_json) VALUES (?, ?, ?, ?)",
                (self._now(), source, event_type, json.dumps(payload)),
            )

    def recent_logs(self, limit: int = 30) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, created_at, source, event_type, payload_json
                FROM audit_logs ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [
                {
                    "id": row["id"],
                    "created_at": row["created_at"],
                    "source": row["source"],
                    "event_type": row["event_type"],
                    "payload": json.loads(row["payload_json"]),
                }
                for row in rows
            ]

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
