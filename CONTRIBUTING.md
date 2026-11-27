# Contributing

Contributions are welcome. For substantial changes, open an issue to discuss the proposal before implementation.

## Development setup

Fork the repository, then clone your fork:

```sh
git clone https://github.com/ranajahanzaib/ai-refusal-map.git
cd ai-refusal-map
make setup
```

Create a branch for the change and start the relevant services with `make dev` or `make api`.

## Before opening a pull request

- Add or update tests for changed behavior.
- Run `make test`, `make lint`, `make typecheck`, and `make build` when applicable.
- Update documentation when commands, data contracts, or research interpretations change.
- Keep real transcripts, private annotations, credentials, model weights, and generated research artifacts out of Git.
- Label synthetic examples clearly and do not describe unreviewed model output as human annotation.

Open a pull request against `main` with a concise summary, the motivation, and the checks performed. Report security vulnerabilities through the process in [SECURITY.md](.github/SECURITY.md), not in a public issue.

Bug reports and feature proposals can be submitted through the repository's issue templates.
