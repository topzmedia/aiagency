"""
Run manifest management — tracks state across a run for resumability.
Uses a local SQLite database + JSON file for cross-process durability.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.schemas import RunManifest
from .io import write_json, read_json

logger = logging.getLogger("ai_ad_agency.manifest")


class ManifestManager:
    """
    Manages the run manifest — a record of everything generated in a run.
    Persists to both SQLite and JSON for resilience.
    """

    def __init__(self, db_path: str = "ai_ad_agency/data/metadata/runs.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    offer_name TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    status TEXT,
                    manifest_json TEXT
                );

                CREATE TABLE IF NOT EXISTS assets (
                    asset_id TEXT PRIMARY KEY,
                    run_id TEXT,
                    asset_type TEXT,
                    status TEXT,
                    file_path TEXT,
                    metadata_json TEXT,
                    created_at TEXT,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );

                CREATE INDEX IF NOT EXISTS idx_assets_run ON assets(run_id);
                CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);
                CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status);
            """)
        logger.debug("Manifest DB initialized at %s", self.db_path)

    # ------------------------------------------------------------------
    # Run management
    # ------------------------------------------------------------------

    def create_run(self, manifest: RunManifest) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO runs (run_id, offer_name, started_at, status, manifest_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    manifest.run_id,
                    manifest.offer_name,
                    manifest.started_at.isoformat(),
                    manifest.status.value,
                    manifest.model_dump_json(),
                ),
            )
        logger.info("Created run manifest: %s", manifest.run_id)

    def update_run(self, manifest: RunManifest) -> None:
        with self._conn() as conn:
            conn.execute(
                """UPDATE runs SET status=?, completed_at=?, manifest_json=? WHERE run_id=?""",
                (
                    manifest.status.value,
                    manifest.completed_at.isoformat() if manifest.completed_at else None,
                    manifest.model_dump_json(),
                    manifest.run_id,
                ),
            )

    def get_run(self, run_id: str) -> Optional[RunManifest]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT manifest_json FROM runs WHERE run_id=?", (run_id,)
            ).fetchone()
        if row:
            return RunManifest(**json.loads(row["manifest_json"]))
        return None

    def get_latest_run(self) -> Optional[RunManifest]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT manifest_json FROM runs ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
        if row:
            return RunManifest(**json.loads(row["manifest_json"]))
        return None

    def list_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT run_id, offer_name, started_at, status FROM runs ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Asset tracking
    # ------------------------------------------------------------------

    def upsert_asset(
        self,
        run_id: str,
        asset_id: str,
        asset_type: str,
        status: str,
        file_path: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO assets
                   (asset_id, run_id, asset_type, status, file_path, metadata_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    asset_id,
                    run_id,
                    asset_type,
                    status,
                    file_path,
                    json.dumps(metadata or {}),
                    datetime.utcnow().isoformat(),
                ),
            )

    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM assets WHERE asset_id=?", (asset_id,)
            ).fetchone()
        if row:
            d = dict(row)
            d["metadata"] = json.loads(d.pop("metadata_json", "{}"))
            return d
        return None

    def get_assets_by_type(
        self, run_id: str, asset_type: str
    ) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM assets WHERE run_id=? AND asset_type=?",
                (run_id, asset_type),
            ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["metadata"] = json.loads(d.pop("metadata_json", "{}"))
            result.append(d)
        return result

    def asset_exists(self, asset_id: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM assets WHERE asset_id=?", (asset_id,)
            ).fetchone()
        return row is not None

    def count_assets(self, run_id: str, asset_type: Optional[str] = None) -> int:
        with self._conn() as conn:
            if asset_type:
                row = conn.execute(
                    "SELECT COUNT(*) FROM assets WHERE run_id=? AND asset_type=?",
                    (run_id, asset_type),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) FROM assets WHERE run_id=?", (run_id,)
                ).fetchone()
        return row[0] if row else 0

    # ------------------------------------------------------------------
    # JSON export
    # ------------------------------------------------------------------

    def save_manifest_json(self, manifest: RunManifest, output_dir: str) -> Path:
        """Save the full run manifest as JSON alongside the outputs."""
        path = Path(output_dir) / "run_manifest.json"
        write_json(manifest.model_dump(mode="json"), path)
        logger.info("Saved run manifest JSON → %s", path)
        return path
