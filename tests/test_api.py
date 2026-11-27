"""API and SQLite annotation contracts."""

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from fastapi.testclient import TestClient

from apps.api.arm_api import annotations
from apps.api.arm_api.main import app, settings_dep
from apps.api.arm_api.repository import ResearchRepository
from apps.api.arm_api.schemas import AnnotationInput
from apps.api.arm_api.settings import Settings


def test_taxonomy_endpoint_exposes_versioned_dimensions() -> None:
    response = TestClient(app).get("/api/v1/taxonomy")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "0.1.0"
    assert "compliance_outcome" in body["dimensions"]
    assert "justification" in body["dimensions"]


def test_health_reports_empty_state_without_corpus() -> None:
    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["transcripts_public"] is False


def test_annotation_write_is_disabled_without_a_token() -> None:
    previous = app.dependency_overrides.get(settings_dep)
    app.dependency_overrides[settings_dep] = lambda: Settings(api_token="")
    try:
        response = TestClient(app).post(
            "/api/v1/annotations",
            json={
                "pair_id": "pair-1",
                "annotator_id": "reviewer-1",
                "outcome": "full_refusal",
            },
        )
    finally:
        if previous is None:
            app.dependency_overrides.pop(settings_dep)
        else:
            app.dependency_overrides[settings_dep] = previous
    assert response.status_code == 503


def test_annotation_create_and_revision(tmp_path: Path) -> None:
    settings = Settings(annotation_db=tmp_path / "labels.sqlite3")
    payload = AnnotationInput(pair_id="pair-1", annotator_id="reviewer-1", outcome="full_refusal")
    created = annotations.create(settings, payload)
    assert created.revision == 1
    assert created.outcome == "full_refusal"
    revised = annotations.revise(
        settings,
        created.annotation_id,
        payload.model_copy(update={"outcome": "partial_compliance"}),
    )
    assert revised is not None
    assert revised.revision == 2
    assert annotations.revise(settings, "missing", payload) is None


def test_annotation_http_post_and_patch_with_auth(tmp_path: Path) -> None:
    token = "secret-token-123"
    db_file = tmp_path / "test_api_annotations.sqlite3"
    previous = app.dependency_overrides.get(settings_dep)
    app.dependency_overrides[settings_dep] = lambda: Settings(
        api_token=token,
        annotation_db=db_file,
    )
    client = TestClient(app)
    try:
        # Invalid token -> 401
        res_unauth = client.post(
            "/api/v1/annotations",
            json={"pair_id": "pair-1", "annotator_id": "rev-1", "outcome": "full_refusal"},
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert res_unauth.status_code == 401

        # Valid token -> 201
        res = client.post(
            "/api/v1/annotations",
            json={
                "pair_id": "pair-1",
                "annotator_id": "rev-1",
                "outcome": "full_refusal",
                "stated_reasons": ["safety"],
                "alternative_types": ["safe_adjacent_assistance"],
                "justification": "justified",
                "comment": "Accurate refusal",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["pair_id"] == "pair-1"
        assert data["revision"] == 1
        annotation_id = data["annotation_id"]

        # List annotations -> 200
        res_list = client.get("/api/v1/annotations")
        assert res_list.status_code == 200
        assert len(res_list.json()) == 1

        # Patch annotation -> 200
        res_patch = client.patch(
            f"/api/v1/annotations/{annotation_id}",
            json={
                "pair_id": "pair-1",
                "annotator_id": "rev-1",
                "outcome": "partial_compliance",
                "stated_reasons": ["safety"],
                "alternative_types": ["partial_fulfillment"],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_patch.status_code == 200
        assert res_patch.json()["revision"] == 2
        assert res_patch.json()["outcome"] == "partial_compliance"
    finally:
        if previous is None:
            app.dependency_overrides.pop(settings_dep)
        else:
            app.dependency_overrides[settings_dep] = previous


def test_repository_runs_fixed_queries_over_parquet(tmp_path: Path) -> None:
    data_dir = tmp_path / "processed"
    data_dir.mkdir()
    pq.write_table(
        pa.Table.from_pylist(
            [
                {
                    "pair_id": "p1",
                    "conversation_id": "c1",
                    "turn_index": 1,
                    "user_request": "Explain photosynthesis.",
                    "assistant_response": "Plants convert light into chemical energy.",
                    "model": "historical-a",
                    "language": "English",
                    "timestamp": "2025-01-01T00:00:00Z",
                    "request_domain": "Science",
                    "predicted_outcome": "unreviewed",
                    "provenance": "test_fixture",
                }
            ]
        ),
        data_dir / "pairs.parquet",
    )
    settings = Settings(
        data_dir=data_dir,
        duckdb_file=tmp_path / "analysis.duckdb",
        annotation_db=tmp_path / "annotations.sqlite3",
    )
    repository = ResearchRepository(settings)
    result = repository.query("SELECT count(*) AS records FROM read_parquet($files)")
    assert result == [{"records": 1}]
    assert repository.filters()["models"] == ["historical-a"]
