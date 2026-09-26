# Deploys the read-only VarshaSetu science API (backend/) for free hosting
# (e.g. Render). Serves only frozen, hash-verified presentation artifacts;
# never retrains, never decodes GRIB, never writes to data/ or experiments/
# at request time. See AGENTS.md and docs/101 for the scientific-freeze rules
# this deployment must not violate.
FROM python:3.12-slim

# libgomp1: OpenMP runtime some scikit-learn/xgboost wheels dynamically link
# against. curl: fetches the frozen data bundle below.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/

# Bakes in the exact frozen artifacts backend/app/api/science.py and
# operational.py read at request time (~750MB: data/manifests/phase2b,
# data/manifests/phase2c, data/operational_derived/operational_features_2023_2025_v1,
# experiments/recent_historical/phase4f|4i|4j). These directories are
# .gitignore'd (too large for a normal git push) and are instead published as
# a GitHub Release asset -- a one-time, immutable, already-frozen bundle,
# never regenerated or altered by this build.
ARG DATA_BUNDLE_URL=https://github.com/iadityachourasia/VarshaSetu/releases/download/serving-data-v1/varshasetu-serving-data-v1.tar.gz
RUN curl -fL "$DATA_BUNDLE_URL" -o /tmp/data.tar.gz \
    && tar --no-same-owner --no-same-permissions -xzf /tmp/data.tar.gz -C /app \
    && rm /tmp/data.tar.gz

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
