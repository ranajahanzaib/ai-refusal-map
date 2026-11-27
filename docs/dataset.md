# Dataset card: WildChat-4.8M

Source: [allenai/WildChat-4.8M](https://huggingface.co/datasets/allenai/WildChat-4.8M). The current card describes a Parquet dataset with one `train` split, 3,199,860 rows, ODC-BY license metadata, and a 2023-04-09 to 2025-08-01 collection window (upper bound excluded). The public version contains conversations retained after toxicity filtering. The repository name is not a count of the current accessible split.

The source schema includes conversation messages with role/content/timestamps and turn identifiers, model, conversation timestamp, language, moderation arrays, toxicity/redaction flags, and privacy-sensitive fields such as hashed IP, headers, state, and country. Moderation results align to message positions; empty messages can have empty metadata objects. This project does not assume one assistant message per user message or use moderation scores as labels.

## Selection and limitations

The accessible release excludes conversations flagged toxic by OpenAI Moderation or Detoxify. This creates selection bias for harmful-input research and distorts moderation distributions. It is not representative of the full interaction distribution. Model identifiers are historical, and observational model differences are confounded by dates, language, request mix, and conversation composition. No gated, unfiltered dataset is automatically downloaded or required.

## Processing contract

The stream is pinned to a resolved repository commit SHA and only the public `train` split is selected. The importer validates key column names before processing. It removes hashed IP, request headers, geography and raw moderation payloads, redacts common direct-identifier patterns, and writes a manifest/checkpoint alongside the normalized Parquet files. That redaction is a first pass, not a guarantee of complete de-identification.

Citation and attribution should follow the dataset card and WildChat papers linked there. The current local demo contains no WildChat conversations.
