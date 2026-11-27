"""Privacy and extraction contracts for the streaming normalizer."""

from research.ingestion.wildchat import detect_candidates, extract_pairs, sanitize


def test_sanitizer_redacts_common_direct_identifiers() -> None:
    result = sanitize("Contact person@example.org or +1 (212) 555-0144 from 192.168.1.10")
    assert "person@example.org" not in result
    assert "555-0144" not in result
    assert "192.168.1.10" not in result
    assert result.count("[REDACTED_") == 3


def test_pair_extraction_skips_orphan_assistant_and_uses_prior_request() -> None:
    record = {
        "conversation_hash": "source-hash",
        "model": "historical-model",
        "timestamp": "2025-01-01T00:00:00Z",
        "language": "English",
        "conversation": [
            {"role": "assistant", "content": "An orphan response."},
            {"role": "user", "content": "First request."},
            {"role": "user", "content": "A follow-up before the answer."},
            {
                "role": "assistant",
                "content": "I cannot help with that, but can explain safe options.",
            },
            {"role": "user", "content": "A later request."},
        ],
    }
    pairs = extract_pairs(record, 7, "revision-sha")
    assert len(pairs) == 1
    pair = pairs[0]
    assert pair["user_request"] == "First request.\nA follow-up before the answer."
    assert pair["assistant_response"].startswith("I cannot help")
    assert pair["predicted_outcome"] == "unreviewed"
    assert pair["candidate_signals"]
    assert pair["conversation_id"]


def test_candidate_detection_is_not_a_final_label() -> None:
    signals = detect_candidates('The quoted text says "I cannot help with this".')
    assert signals
    assert "full_refusal" not in signals


def test_sanitization_applies_to_both_request_and_response() -> None:
    record = {
        "conversation_hash": "hash",
        "model": "m",
        "timestamp": None,
        "language": "English",
        "conversation": [
            {"role": "user", "content": "Email me at a.person@example.org"},
            {"role": "assistant", "content": "I can help; call 2125550144."},
        ],
    }
    pair = extract_pairs(record, 1, "sha")[0]
    assert "a.person@example.org" not in pair["user_request"]
    assert "2125550144" not in pair["assistant_response"]
