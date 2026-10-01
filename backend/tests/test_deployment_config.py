"""Deployment configuration guards: the data bundle is retried, checksum-verified before extraction and documented consistently."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8").replace("\r\n", "\n")
DOC_102 = (ROOT / "docs/102_FREE_DEPLOYMENT.md").read_text(encoding="utf-8")


def _bundle_run_block() -> str:
    start = DOCKERFILE.index("RUN curl -fL")
    end = DOCKERFILE.index("\n\n", start)
    return DOCKERFILE[start:end]


def test_bundle_digest_is_a_full_sha256_and_matches_the_documented_one():
    digest = re.search(r"^ARG DATA_BUNDLE_SHA256=([0-9a-f]+)$", DOCKERFILE, re.M).group(1)
    assert len(digest) == 64
    assert f"`{digest}`" in DOC_102, "docs/102 must record the same, complete digest the Dockerfile verifies"
    assert not re.search(r"sha256: `[0-9a-f]{63}`", DOC_102), "docs/102 must not carry a truncated digest"


def test_download_is_retried_resumed_and_verified_before_extraction():
    block = _bundle_run_block()
    assert "--retry" in block and "--retry-all-errors" in block and "-C -" in block
    assert block.index("sha256sum -c") < block.index("tar ") < block.index("rm /tmp/data.tar.gz")
    assert "${DATA_BUNDLE_SHA256}  /tmp/data.tar.gz" in block, "two spaces: the format sha256sum -c requires"
    assert "&&" in block.split("sha256sum -c")[0] and "&&" in block.split("sha256sum -c")[1]       # a failed check stops the chain


def test_image_ships_only_backend_code_and_the_pinned_bundle():
    assert "COPY backend/ backend/" in DOCKERFILE and DOCKERFILE.count("COPY ") == 2
    ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    for excluded in ("data/", "experiments/", ".git/", "frontend-v2/"):
        assert excluded in ignore
    assert "releases/download/serving-data-v1/" in DOCKERFILE and "latest" not in DOCKERFILE.split("ARG DATA_BUNDLE_URL")[1].split("\n")[0]


def test_ci_workflow_uses_the_same_pinned_bundle_as_the_dockerfile():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    docker_digest = re.search(r"^ARG DATA_BUNDLE_SHA256=([0-9a-f]{64})$", DOCKERFILE, re.M).group(1)
    docker_url = re.search(r"^ARG DATA_BUNDLE_URL=(\S+)$", DOCKERFILE, re.M).group(1)
    assert f"DATA_BUNDLE_SHA256: {docker_digest}" in workflow and f"DATA_BUNDLE_URL: {docker_url}" in workflow
    assert "sha256sum -c" in workflow and workflow.index("sha256sum -c") < workflow.index("tar --no-same-owner")
    assert "--retry-all-errors" in workflow and "permissions:\n  contents: read" in workflow
    assert "pytest backend/tests" in workflow and "-rs" in workflow, "skips must be printed, never silent"
