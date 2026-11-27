"""Streaming, privacy-minimizing WildChat normalization pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from datasets import IterableDataset, load_dataset
from huggingface_hub import HfApi

DATASET_ID = "allenai/WildChat-4.8M"
REQUIRED_FIELDS = {"conversation", "conversation_hash", "model", "timestamp", "language"}
EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d().\s-]{7,}\d)(?!\w)")
IP_ADDRESS = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
CANDIDATE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bI (?:can't|cannot|won't|will not) (?:help|assist|provide|participate|comply)\b",
        r"\bI(?:'m| am) unable to (?:help|assist|provide)\b",
        r"\bI must decline\b",
        r"\bI can help with .* instead\b",
        r"\bCould you clarify\b|\bWhat do you mean by\b",
    )
)


def sanitize(text: str) -> str:
    """Redact common direct identifiers before persistence or display."""
    text = EMAIL.sub("[REDACTED_EMAIL]", text)
    text = PHONE.sub("[REDACTED_PHONE]", text)
    return IP_ADDRESS.sub("[REDACTED_IP]", text)


def detect_candidates(response: str) -> list[str]:
    """Return review cues only; never assign a final refusal outcome."""
    found: list[str] = []
    if not response.strip():
        found.append("empty_response")
    for index, pattern in enumerate(CANDIDATE_PATTERNS):
        match = pattern.search(response)
        if match and not response[max(0, match.start() - 12) : match.start()].lower().endswith(
            "not "
        ):
            found.append(f"rule_{index + 1}")
    return found


def _message_text(message: dict[str, Any]) -> str:
    value = message.get("content", "")
    return value if isinstance(value, str) else ""


def extract_pairs(record: dict[str, Any], row_index: int, revision: str) -> list[dict[str, Any]]:
    """Pair each assistant response with the contiguous preceding user request."""
    messages = record.get("conversation")
    if not isinstance(messages, list):
        raise ValueError("conversation must be a list")
    conversation_hash = str(record.get("conversation_hash", ""))
    conversation_id = hashlib.sha256(
        f"{revision}:{row_index}:{conversation_hash}".encode()
    ).hexdigest()[:24]
    pairs: list[dict[str, Any]] = []
    pending_requests: list[str] = []
    recent_context: list[tuple[str, str]] = []
    assistant_turn = 0
    for message_index, message in enumerate(messages):
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        content = sanitize(_message_text(message)).strip()
        if role == "user":
            pending_requests.append(content)
            continue
        if role != "assistant":
            continue
        response = content
        if pending_requests:
            request = "\n".join(value for value in pending_requests if value)
            assistant_turn += 1
            source_id = message.get("turn_identifier") or message.get("openai_id")
            stable_key = (
                str(source_id) if source_id else f"{row_index}:{message_index}:{assistant_turn}"
            )
            pair_id = hashlib.sha256(f"{revision}:{stable_key}".encode()).hexdigest()[:32]
            timestamp = message.get("timestamp") or record.get("timestamp")
            pair_time = str(timestamp) if timestamp is not None else None
            pairs.append(
                {
                    "pair_id": pair_id,
                    "conversation_id": conversation_id,
                    "turn_index": assistant_turn,
                    "user_request": request,
                    "assistant_response": response,
                    "preceding_context": json.dumps(recent_context[-6:], ensure_ascii=False),
                    "model": str(record.get("model") or "unknown"),
                    "timestamp": pair_time,
                    "language": str(record.get("language") or "unknown"),
                    "request_domain": "unknown",
                    "request_chars": len(request),
                    "response_chars": len(response),
                    "candidate_signals": detect_candidates(response),
                    "predicted_outcome": "unreviewed",
                    "provenance": "wildchat_stream",
                    "dataset_revision": revision,
                }
            )
            recent_context.append(("user", request))
            recent_context.append(("assistant", response))
            pending_requests.clear()
        elif response:
            recent_context.append(("assistant", response))
    return pairs


def _write_batch(rows: list[dict[str, Any]], output: Path, batch_index: int) -> None:
    if not rows:
        return
    output.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, output / f"pairs-{batch_index:07d}.parquet", compression="zstd")


def run_ingestion(
    *,
    revision: str,
    output_dir: Path,
    limit: int | None,
    batch_size: int,
    seed: int,
    profile: str,
    languages: set[str],
    models: set[str],
    resume: bool,
) -> dict[str, Any]:
    """Stream a public dataset revision, sanitizing before writing normalized pairs."""
    info = HfApi().dataset_info(DATASET_ID, revision=revision)
    pinned_revision = info.sha
    if not pinned_revision:
        raise ValueError("The dataset Hub response did not include a commit SHA")
    dataset = load_dataset(DATASET_ID, split="train", streaming=True, revision=pinned_revision)
    if not isinstance(dataset, IterableDataset):
        raise TypeError("Expected the Hugging Face streaming dataset interface")
    if dataset.features is None:
        raise ValueError("The streaming dataset did not expose a schema")
    actual_fields = set(dataset.features)
    if not REQUIRED_FIELDS.issubset(actual_fields):
        raise ValueError(
            f"Source schema mismatch. Missing required fields: {sorted(REQUIRED_FIELDS - actual_fields)}"
        )
    if profile == "research" and limit is not None:
        dataset = dataset.shuffle(seed=seed, buffer_size=10_000)
    output = output_dir / pinned_revision
    checkpoint_path = output / "checkpoint.json"
    if output.exists() and not resume and any(output.glob("pairs-*.parquet")):
        raise FileExistsError(
            f"Output already exists at {output}; pass --resume or choose another --output"
        )
    start_row = 0
    batch_index = 0
    if resume and checkpoint_path.exists():
        checkpoint = json.loads(checkpoint_path.read_text())
        if checkpoint.get("dataset_revision") != pinned_revision:
            raise ValueError("Checkpoint revision differs from the selected dataset revision")
        start_row = int(checkpoint["source_rows_processed"])
        batch_index = int(checkpoint["next_batch_index"])
        dataset = dataset.skip(start_row)
    selected = 0
    source_rows = start_row
    batch: list[dict[str, Any]] = []
    bad_records = 0
    for record in dataset:
        row_index = source_rows
        source_rows += 1
        if languages and str(record.get("language", "unknown")).casefold() not in languages:
            continue
        if models and str(record.get("model", "unknown")).casefold() not in models:
            continue
        try:
            batch.extend(extract_pairs(record, row_index, pinned_revision))
        except (TypeError, ValueError, KeyError):
            bad_records += 1
        selected += 1
        if len(batch) >= batch_size:
            _write_batch(batch, output, batch_index)
            batch = []
            batch_index += 1
            checkpoint_path.write_text(
                json.dumps(
                    {
                        "dataset_revision": pinned_revision,
                        "source_rows_processed": source_rows,
                        "next_batch_index": batch_index,
                    },
                    indent=2,
                )
            )
        if limit is not None and selected >= limit:
            break
        if source_rows and source_rows % 1000 == 0:
            print(
                f"source_rows={source_rows} selected={selected} pairs_buffered={len(batch)}",
                file=sys.stderr,
            )
    _write_batch(batch, output, batch_index)
    manifest = {
        "dataset_id": DATASET_ID,
        "dataset_revision": pinned_revision,
        "split": "train",
        "profile": profile,
        "seed": seed,
        "limit": limit,
        "source_rows_processed": source_rows,
        "source_rows_selected_this_run": selected,
        "invalid_records_this_run": bad_records,
        "pair_files": len(list(output.glob("pairs-*.parquet"))),
        "created_at_utc": datetime.now(UTC).isoformat(),
        "columns_excluded": [
            "hashed_ip",
            "header",
            "state",
            "country",
            "raw moderation payloads",
            "unnecessary turn metadata",
        ],
        "classification_status": "candidate signals only; no human labels or model predictions",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=["research", "full"], default="research")
    parser.add_argument(
        "--revision",
        default="main",
        help="Hub branch/tag/commit; resolved to and recorded as a commit SHA",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximum source conversations; omit for full-corpus profile",
    )
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--language", action="append", default=[])
    parser.add_argument("--model", action="append", default=[])
    parser.add_argument("--output", type=Path, default=Path("data/processed"))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    if args.batch_size < 1 or (args.limit is not None and args.limit < 1):
        parser.error("--batch-size and --limit must be positive")
    if args.profile == "full":
        args.limit = None
    return args


def main(argv: Iterable[str] | None = None) -> None:
    args = parse_args(argv)
    result = run_ingestion(
        revision=args.revision,
        output_dir=args.output,
        limit=args.limit,
        batch_size=args.batch_size,
        seed=args.seed,
        profile=args.profile,
        languages={x.casefold() for x in args.language},
        models={x.casefold() for x in args.model},
        resume=args.resume,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
