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
# --retry/--retry-all-errors/-C -: a connection reset mid-download (curl exit 56) otherwise fails the whole build; with these flags curl
# retries and resumes from the partial file. The bundle is immutable, so resuming cannot mix versions.
ARG DATA_BUNDLE_URL=https://github.com/iadityachourasia/VarshaSetu/releases/download/serving-data-v1/varshasetu-serving-data-v1.tar.gz
# The bundle is verified against its pinned SHA-256 (also published by GitHub as the release asset digest) before it is extracted:
# a truncated, tampered or substituted download fails the build instead of shipping unverified science artifacts.
# Overriding DATA_BUNDLE_URL requires overriding DATA_BUNDLE_SHA256 together.
ARG DATA_BUNDLE_SHA256=f5904aa9c8b1b96fb124b96396e854e3df840daa85efe05c20031e55fa22b262
RUN curl -fL --retry 8 --retry-delay 5 --retry-all-errors -C - "$DATA_BUNDLE_URL" -o /tmp/data.tar.gz \
    && echo "${DATA_BUNDLE_SHA256}  /tmp/data.tar.gz" | sha256sum -c - \
    && tar --no-same-owner --no-same-permissions -xzf /tmp/data.tar.gz -C /app \
    && rm /tmp/data.tar.gz

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
