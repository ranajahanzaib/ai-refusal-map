"""Synthetic-only unit tests for deterministic workflow mechanics."""

import polars as pl

from research.workflows import extract_request_features, sample_annotation_queue


def test_features_use_request_only(tmp_path):
    source = tmp_path / "pairs.parquet"
    output = tmp_path / "features.parquet"
    pl.DataFrame(
        {
            "pair_id": ["p1"],
            "conversation_id": ["c1"],
            "user_request": ["Could you explain this? I do not understand."],
            "assistant_response": ["I cannot help with that."],
            "predicted_outcome": ["full_refusal"],
        }
    ).write_parquet(source)
    assert extract_request_features(source, output) == 1
    result = pl.read_parquet(output)
    assert result["request_words"].to_list() == [8]
    assert result["contains_question"].to_list() == [True]
    assert result["contains_negation"].to_list() == [True]
    assert "assistant_response" not in result.columns
    assert "predicted_outcome" not in result.columns


def test_sampling_is_seeded_and_records_probability(tmp_path):
    source = tmp_path / "pairs.parquet"
    pl.DataFrame(
        {
            "pair_id": [f"p{i}" for i in range(10)],
            "candidate_signals": [["rule_1"] if i < 4 else [] for i in range(10)],
        }
    ).write_parquet(source)
    first, second = tmp_path / "one.parquet", tmp_path / "two.parquet"
    summary = sample_annotation_queue(source, first, size=5, seed=17, stratified=True)
    sample_annotation_queue(source, second, size=5, seed=17, stratified=True)
    left = pl.read_parquet(first).sort("pair_id")
    right = pl.read_parquet(second).sort("pair_id")
    assert summary == {"population": 10, "sampled": 5, "seed": 17, "stratified": True}
    assert left.equals(right)
    assert all(isinstance(value, (int, float)) and value > 0 for value in left["sampling_probability"].to_list())
    assert set(left["sampling_stratum"].to_list()) == {"candidate_signal", "no_candidate_signal"}
