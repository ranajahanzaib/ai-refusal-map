# Architecture

The app separates its self-contained synthetic browser demonstration from research data. The web app is Next.js App Router and TypeScript. The API is FastAPI with constrained filter parameters. Analytical queries read normalized Parquet through DuckDB read-only connections; mutable annotations live in SQLite. Raw source objects and mutable labels are not written into the analytical table.

The current normalized request-response schema includes pair and conversation surrogate IDs, turn position, sanitized request and response text, bounded preceding context, model identifier, timestamp, language, unknown request domain, character lengths, candidate review signals, unreviewed outcome state, provenance, and source revision. Raw moderation structures and unnecessary request metadata are omitted.

DuckDB access is internal only. The HTTP API exposes fixed aggregates and paginated selected columns; clients cannot submit SQL. Limits and filter dimensions are validated. Transcript endpoints should only be exposed behind authenticated research access controls in a deployment.

## Current scope

The API can report empty or loaded data state, available filters, outcomes by fixed dimensions, paginated pairs, taxonomy, and SQLite annotations. The frontend remains on synthetic fixture data by default. Embeddings, clustering, classifier training, model comparison inference, and reports have no executed artifacts yet.
