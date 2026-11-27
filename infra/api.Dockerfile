FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY apps/api ./apps/api
COPY research ./research
RUN pip install --no-cache-dir uv && uv sync --no-dev --frozen
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "arm_api.main:app", "--app-dir", "apps/api", "--host", "0.0.0.0", "--port", "8000"]
