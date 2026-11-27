# Model card

No refusal classifier or embedding model is included in this release. The regex rules in `research/ingestion/wildchat.py` generate candidate-review cues; they do not classify or label responses. They have not been validated across languages and may match quotations, negation, or responses that otherwise comply.

No classifier performance or model-generated refusal judgments are reported. An unnecessary-refusal judgment requires human review under the documented rubric.
