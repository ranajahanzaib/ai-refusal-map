"""Reproducible request feature extraction and annotation sampling."""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import polars as pl
import pyarrow.parquet as pq


def _word_count(value: str) -> int:
    return len(re.findall(r"\b[\w']+\b", value, flags=re.UNICODE))


def _sentence_count(value: str) -> int:
    return len([part for part in re.split(r"[.!?]+", value) if part.strip()])


def _has_question(value: str) -> bool:
    return "?" in value


def _has_negation(value: str) -> bool:
    return bool(re.search(r"\b(?:not|never|no|cannot|can't|don't|doesn't|won't|without)\b", value, re.I))


def _has_quoted_text(value: str) -> bool:
    return bool(re.search(r"(?:\"[^\"]+\"|'[^']+')", value))


def extract_request_features(source: Path, output: Path) -> int:
    """Write request-only features; response and labels never enter this table."""
    frame = pl.read_parquet(source)
    required = {"pair_id", "conversation_id", "user_request"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Input is missing required columns: {sorted(missing)}")
    request = pl.col("user_request").fill_null("")
    result = frame.select(
        pl.col("pair_id"), pl.col("conversation_id"),
        *[pl.col(c) for c in ("turn_index", "model", "timestamp", "language", "dataset_revision") if c in frame.columns],
        request.str.len_chars().alias("request_chars"),
        request.map_elements(_word_count, return_dtype=pl.UInt32).alias("request_words"),
        request.map_elements(_sentence_count, return_dtype=pl.UInt32).alias("request_sentences"),
        request.str.contains("?", literal=True).alias("contains_question"),
        request.map_elements(_has_negation, return_dtype=pl.Boolean).alias("contains_negation"),
        request.map_elements(_has_quoted_text, return_dtype=pl.Boolean).alias("contains_quoted_text"),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    result.write_parquet(output, compression="zstd")
    return result.height


def sample_annotation_queue(
    source: Path, output: Path, *, size: int, seed: int, stratified: bool = False
) -> dict[str, Any]:
    """Sample rows reproducibly, retaining inclusion probability and sampling stratum."""
    if size < 1:
        raise ValueError("size must be positive")
    parquet = pq.ParquetFile(source)
    if "pair_id" not in parquet.schema_arrow.names:
        raise ValueError("Input is missing pair_id")
    rng = random.Random(seed)
    counts: dict[str, int] = defaultdict(int)
    reservoirs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, int] = defaultdict(int)
    # Two passes keep memory bounded by the requested sample size.
    for batch in parquet.iter_batches(batch_size=8192):
        for row in batch.to_pylist():
            stratum = "all"
            if stratified:
                stratum = "candidate_signal" if row.get("candidate_signals") else "no_candidate_signal"
            counts[stratum] += 1
    population = sum(counts.values())
    if population == 0:
        raise ValueError("Cannot sample an empty Parquet file")
    target = min(size, population)
    # Proportional allocation, with deterministic remainder assignment.
    quotas = {key: int(target * count / population) for key, count in counts.items()} if population else {}
    for key in sorted(counts, key=lambda k: (-(target * counts[k] / population - quotas[k]), k)):
        if sum(quotas.values()) >= target:
            break
        quotas[key] += 1
    for batch in parquet.iter_batches(batch_size=8192):
        for row in batch.to_pylist():
            stratum = "all"
            if stratified:
                stratum = "candidate_signal" if row.get("candidate_signals") else "no_candidate_signal"
            seen[stratum] += 1
            reservoir = reservoirs[stratum]
            quota = quotas[stratum]
            if len(reservoir) < quota:
                reservoir.append(row)
            elif quota:
                position = rng.randrange(seen[stratum])
                if position < quota:
                    reservoir[position] = row
    selected: list[dict[str, Any]] = []
    for key, rows in reservoirs.items():
        n = quotas.get(key, 0)
        probability = n / counts[key] if counts[key] else 0.0
        for row in rows:
            selected.append({**row, "sampling_stratum": key, "sampling_probability": probability, "sampling_seed": seed})
    rng.shuffle(selected)
    output.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(selected).write_parquet(output, compression="zstd")
    return {"population": population, "sampled": len(selected), "seed": seed, "stratified": stratified}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    features = commands.add_parser("features", help="Extract pre-response request features")
    features.add_argument("--input", type=Path, required=True)
    features.add_argument("--output", type=Path, required=True)
    sample = commands.add_parser("sample", help="Create a reproducible annotation queue")
    sample.add_argument("--input", type=Path, required=True)
    sample.add_argument("--output", type=Path, required=True)
    sample.add_argument("--size", type=int, required=True)
    sample.add_argument("--seed", type=int, default=42)
    sample.add_argument("--stratified", action="store_true", help="Stratify on candidate signal presence")
    args = parser.parse_args()
    if args.command == "features":
        print(json.dumps({"rows": extract_request_features(args.input, args.output), "output": str(args.output)}))
    else:
        print(json.dumps(sample_annotation_queue(args.input, args.output, size=args.size, seed=args.seed, stratified=args.stratified)))


if __name__ == "__main__":
    main()
