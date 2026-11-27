# Reproducibility

The frontend and Python dependency lockfiles record package resolution. Ingestion resolves a dataset ref to a commit SHA, records seed/profile/limits/source counts and schema exclusions in a manifest, and stores checkpoints for resumption. Use an immutable revision and seed for reruns. Streaming shuffle is bounded-buffer deterministic, not a probability sample with known inclusion weights; do not use it as a design-weighted population estimate.

Future experiments should also record code commit, Python/Node runtime, OS/hardware, configuration hash, model/tokenizer revisions, split assignment, annotation version, artifact checksums and UTC execution time. A reproducible report must be generated from executed artifacts and never include unrun results.
