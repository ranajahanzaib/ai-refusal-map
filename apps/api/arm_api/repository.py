"""Constrained read-only access to normalized Parquet analytical data."""

from typing import Any

import duckdb

from .settings import Settings


class ResearchRepository:
    """Runs fixed analytical queries over local Parquet files."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def files(self) -> list[str]:
        """Return Parquet files beneath the configured processed-data directory."""
        root = self.settings.data_dir.resolve()
        if not root.exists():
            return []
        return [
            str(path) for path in root.rglob("*.parquet") if path.resolve().is_relative_to(root)
        ]

    def available(self) -> bool:
        return bool(self.files())

    def query(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        """Execute a fixed internal query, with the file list supplied as a value."""
        files = self.files()
        if not files:
            return []
        self.settings.duckdb_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.settings.duckdb_file.exists():
            bootstrap = duckdb.connect(database=str(self.settings.duckdb_file))
            bootstrap.close()
        connection = duckdb.connect(database=str(self.settings.duckdb_file), read_only=True)
        try:
            result = connection.execute(sql.replace("$files", "?"), [files, *(params or [])])
            columns = [item[0] for item in result.description]
            return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
        finally:
            connection.close()

    def filters(self) -> dict[str, list[str]]:
        if not self.available():
            return {name: [] for name in ("models", "languages", "domains", "outcomes")}
        rows = self.query(
            """SELECT DISTINCT model, language, request_domain, predicted_outcome
               FROM read_parquet($files) LIMIT 100000"""
        )
        return {
            "models": sorted({str(row["model"]) for row in rows if row.get("model")}),
            "languages": sorted({str(row["language"]) for row in rows if row.get("language")}),
            "domains": sorted(
                {str(row["request_domain"]) for row in rows if row.get("request_domain")}
            ),
            "outcomes": sorted(
                {str(row["predicted_outcome"]) for row in rows if row.get("predicted_outcome")}
            ),
        }


def query_fragment(filters: dict[str, str | None]) -> tuple[str, list[Any]]:
    """Build a parameterized filter fragment from an allowlist of dimensions."""
    allowed = {
        "model": "model",
        "language": "language",
        "domain": "request_domain",
        "outcome": "predicted_outcome",
    }
    clauses: list[str] = []
    values: list[Any] = []
    for key, column in allowed.items():
        value = filters.get(key)
        if value:
            clauses.append(f"{column} = ?")
            values.append(value)
    return (" WHERE " + " AND ".join(clauses) if clauses else ""), values
