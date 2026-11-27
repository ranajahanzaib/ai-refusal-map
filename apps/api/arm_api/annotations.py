"""SQLite persistence for mutable human annotations."""

import json
import sqlite3
import uuid
from datetime import UTC, datetime

from .schemas import Annotation, AnnotationInput
from .settings import Settings


def connect(settings: Settings) -> sqlite3.Connection:
    """Initialize the SQLite annotation store and return a row-aware connection."""
    settings.annotation_db.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(settings.annotation_db, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute(
        """CREATE TABLE IF NOT EXISTS annotations (
            annotation_id TEXT PRIMARY KEY,
            pair_id TEXT NOT NULL,
            annotator_id TEXT NOT NULL,
            outcome TEXT NOT NULL,
            stated_reasons TEXT NOT NULL,
            alternative_types TEXT NOT NULL,
            justification TEXT,
            comment TEXT,
            revision INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    return db


def _parse(row: sqlite3.Row) -> Annotation:
    return Annotation(
        annotation_id=row["annotation_id"],
        pair_id=row["pair_id"],
        annotator_id=row["annotator_id"],
        outcome=row["outcome"],
        stated_reasons=json.loads(row["stated_reasons"]),
        alternative_types=json.loads(row["alternative_types"]),
        justification=row["justification"],
        comment=row["comment"],
        revision=row["revision"],
        created_at=row["created_at"],
    )


def create(settings: Settings, payload: AnnotationInput) -> Annotation:
    annotation_id = str(uuid.uuid4())
    created_at = datetime.now(UTC).isoformat()
    with connect(settings) as db:
        db.execute(
            """INSERT INTO annotations VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
            (
                annotation_id,
                payload.pair_id,
                payload.annotator_id,
                payload.outcome,
                json.dumps(payload.stated_reasons),
                json.dumps(payload.alternative_types),
                payload.justification,
                payload.comment,
                created_at,
            ),
        )
        row = db.execute(
            "SELECT * FROM annotations WHERE annotation_id = ?", (annotation_id,)
        ).fetchone()
    return _parse(row)


def revise(settings: Settings, annotation_id: str, payload: AnnotationInput) -> Annotation | None:
    with connect(settings) as db:
        db.execute(
            """UPDATE annotations SET pair_id=?, annotator_id=?, outcome=?, stated_reasons=?,
               alternative_types=?, justification=?, comment=?, revision=revision+1, created_at=?
               WHERE annotation_id=?""",
            (
                payload.pair_id,
                payload.annotator_id,
                payload.outcome,
                json.dumps(payload.stated_reasons),
                json.dumps(payload.alternative_types),
                payload.justification,
                payload.comment,
                datetime.now(UTC).isoformat(),
                annotation_id,
            ),
        )
        row = db.execute(
            "SELECT * FROM annotations WHERE annotation_id = ?", (annotation_id,)
        ).fetchone()
    return _parse(row) if row else None


def list_annotations(settings: Settings, limit: int) -> list[Annotation]:
    with connect(settings) as db:
        rows = db.execute(
            "SELECT * FROM annotations ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_parse(row) for row in rows]
