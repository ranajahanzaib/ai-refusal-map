.PHONY: setup dev demo api ingest preprocess features sample test lint typecheck build
export UV_CACHE_DIR ?= /private/tmp/uv-cache-ai-refusal-map

setup:
	pnpm install
	uv sync --group dev

dev:
	pnpm dev

demo:
	pnpm dev

api:
	uv run uvicorn arm_api.main:app --app-dir apps/api --reload --port 8000

ingest:
	uv run python research/ingestion/wildchat.py --profile research --limit 1000 --revision main --resume

preprocess:
	uv run python research/ingestion/wildchat.py --profile research --limit 1000 --revision main --resume

features:
	@test -n "$(INPUT)" -a -n "$(OUTPUT)" || (echo "Usage: make features INPUT=data/processed/<revision>/pairs-0000000.parquet OUTPUT=data/features/requests.parquet"; exit 2)
	uv run python -m research.workflows features --input "$(INPUT)" --output "$(OUTPUT)"

sample:
	@test -n "$(INPUT)" -a -n "$(OUTPUT)" -a -n "$(SIZE)" || (echo "Usage: make sample INPUT=data/processed/<revision>/pairs-0000000.parquet OUTPUT=data/curated/annotation-queue.parquet SIZE=200 [SEED=42] [STRATIFIED=1]"; exit 2)
	uv run python -m research.workflows sample --input "$(INPUT)" --output "$(OUTPUT)" --size "$(SIZE)" --seed "$(or $(SEED),42)" $(if $(STRATIFIED),--stratified,)

test:
	uv run pytest

lint:
	uv run ruff check apps/api research tests
	pnpm lint

typecheck:
	uv run pyright
	pnpm typecheck

build:
	pnpm build
