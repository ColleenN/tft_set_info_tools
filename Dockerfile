# Image for the scheduled loader jobs. Runs `tft-scripts`; each job passes its
# arguments (e.g. `--env-file /job-configs/loaders/cdragon.env load cdragon`).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install ".[gcp]" && rm -rf /app/src

USER nobody

ENTRYPOINT ["tft-scripts"]
CMD ["load"]
