"""Versioned FastAPI endpoints for AI Refusal Map."""

from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import annotations
from .repository import ResearchRepository, query_fragment
from .schemas import Annotation, AnnotationInput
from .settings import Settings, get_settings
from .taxonomy import TAXONOMY, TAXONOMY_VERSION

app = FastAPI(
    title="AI Refusal Map API",
    version="0.1.0",
    description="Privacy-conscious research API for assistant response behavior.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


def settings_dep() -> Settings:
    return get_settings()


def repo_dep(settings: Annotated[Settings, Depends(settings_dep)]) -> ResearchRepository:
    return ResearchRepository(settings)


def require_write_auth(settings: Settings, authorization: str | None) -> None:
    if not settings.api_token:
        if settings.allow_unauthenticated_writes:
            return
        raise HTTPException(status_code=503, detail="Annotation writes are disabled until an API token is configured.")
    if authorization != f"Bearer {settings.api_token}":
        raise HTTPException(
            status_code=401, detail="A valid bearer token is required for annotation changes."
        )


@app.get("/api/v1/health")
def health(repo: Annotated[ResearchRepository, Depends(repo_dep)]) -> dict[str, Any]:
    return {
        "status": "ok",
        "dataset_loaded": repo.available(),
        "mode": "research" if repo.available() else "empty",
        "transcripts_public": False,
    }


@app.get("/api/v1/datasets")
def datasets(repo: Annotated[ResearchRepository, Depends(repo_dep)]) -> dict[str, Any]:
    return {
        "datasets": (
            [
                {
                    "id": "local-parquet",
                    "source": "local normalized Parquet",
                    "files": len(repo.files()),
                    "status": "loaded",
                }
            ]
            if repo.available()
            else []
        ),
        "demo_data": "frontend synthetic fixtures; not API research data",
    }


@app.get("/api/v1/taxonomy")
def taxonomy() -> dict[str, Any]:
    return {"version": TAXONOMY_VERSION, "dimensions": TAXONOMY}


@app.get("/api/v1/filters")
def filters(repo: Annotated[ResearchRepository, Depends(repo_dep)]) -> dict[str, Any]:
    return repo.filters()


@app.get("/api/v1/overview")
def overview(repo: Annotated[ResearchRepository, Depends(repo_dep)]) -> dict[str, Any]:
    if not repo.available():
        return {"status": "empty", "records": 0, "outcomes": [], "provenance": None}
    result = repo.query("SELECT count(*) AS records FROM read_parquet($files)")
    return {
        "status": "research",
        **result[0],
        "provenance": "normalized local Parquet; see dataset manifest",
    }


def _analysis_query(
    repo: ResearchRepository,
    group: str,
    model: str | None,
    language: str | None,
    domain: str | None,
    outcome: str | None,
) -> dict[str, Any]:
    if group not in {"predicted_outcome", "request_domain", "model", "language"}:
        raise HTTPException(status_code=404, detail="Unknown analysis dimension.")
    if not repo.available():
        return {"status": "empty", "dimension": group, "rows": [], "denominator": 0}
    clause, values = query_fragment(
        {"model": model, "language": language, "domain": domain, "outcome": outcome}
    )
    result = repo.query(
        f"SELECT {group} AS label, count(*) AS count FROM read_parquet($files){clause} GROUP BY 1 ORDER BY count DESC LIMIT 1000",
        values,
    )
    denominator = sum(int(row["count"]) for row in result)
    return {"status": "research", "dimension": group, "rows": result, "denominator": denominator}


@app.get("/api/v1/analysis/{dimension}")
def analysis(
    dimension: str,
    repo: Annotated[ResearchRepository, Depends(repo_dep)],
    model: str | None = None,
    language: str | None = None,
    domain: str | None = None,
    outcome: str | None = None,
) -> dict[str, Any]:
    aliases = {
        "outcomes": "predicted_outcome",
        "domains": "request_domain",
        "models": "model",
        "languages": "language",
    }
    return _analysis_query(
        repo, aliases.get(dimension, dimension), model, language, domain, outcome
    )


@app.get("/api/v1/conversations")
def conversations(
    repo: Annotated[ResearchRepository, Depends(repo_dep)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=10_000_000)] = 0,
    model: str | None = None,
    language: str | None = None,
    domain: str | None = None,
    outcome: str | None = None,
) -> dict[str, Any]:
    if not repo.available():
        return {"status": "empty", "rows": [], "limit": limit, "offset": offset}
    clause, values = query_fragment(
        {"model": model, "language": language, "domain": domain, "outcome": outcome}
    )
    rows = repo.query(
        "SELECT pair_id, conversation_id, turn_index, user_request, assistant_response, model, language, timestamp, request_domain, predicted_outcome, provenance FROM read_parquet($files)"
        + clause
        + " ORDER BY timestamp DESC LIMIT ? OFFSET ?",
        [*values, limit, offset],
    )
    return {
        "status": "research",
        "rows": rows,
        "limit": limit,
        "offset": offset,
        "transcript_access": "research-only; deployment must enforce authorization",
    }


@app.get("/api/v1/annotations", response_model=list[Annotation])
def get_annotations(
    settings: Annotated[Settings, Depends(settings_dep)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[Annotation]:
    return annotations.list_annotations(settings, limit)


@app.post("/api/v1/annotations", response_model=Annotation, status_code=201)
def post_annotation(
    payload: AnnotationInput,
    settings: Annotated[Settings, Depends(settings_dep)],
    authorization: Annotated[str | None, Header()] = None,
) -> Annotation:
    require_write_auth(settings, authorization)
    return annotations.create(settings, payload)


@app.patch("/api/v1/annotations/{annotation_id}", response_model=Annotation)
def patch_annotation(
    annotation_id: str,
    payload: AnnotationInput,
    settings: Annotated[Settings, Depends(settings_dep)],
    authorization: Annotated[str | None, Header()] = None,
) -> Annotation:
    require_write_auth(settings, authorization)
    updated = annotations.revise(settings, annotation_id, payload)
    if updated is None:
        raise HTTPException(status_code=404, detail="Annotation not found.")
    return updated
