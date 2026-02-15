FROM python:3.12-slim

WORKDIR /app

ARG APP_VERSION=0.0.0-dev

COPY pyproject.toml .
RUN mkdir -p app && SETUPTOOLS_SCM_PRETEND_VERSION=${APP_VERSION} pip install --no-cache-dir .

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
