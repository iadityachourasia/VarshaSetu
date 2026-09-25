"""Checksum-verified immutable HTTP cache for authoritative source bytes."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.request import Request, urlopen
from urllib.error import HTTPError


class CacheIntegrityError(RuntimeError):
    """Raised when cached bytes or their receipt are incomplete or inconsistent."""


@dataclass(frozen=True)
class FetchResponse:
    payload: bytes
    status: int
    headers: dict[str, str]


@dataclass(frozen=True)
class CacheResult:
    path: Path
    sha256: str
    byte_size: int
    from_cache: bool
    network_bytes: int
    attempts: int
    elapsed_seconds: float


Fetcher = Callable[[str, tuple[int, int] | None, float], FetchResponse]


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def receipt_path(path: str | Path) -> Path:
    path = Path(path)
    return path.with_name(path.name + ".receipt.json")


def default_fetcher(
    url: str, byte_range: tuple[int, int] | None, timeout_seconds: float
) -> FetchResponse:
    headers = {"User-Agent": "VarshaSetu-Authoritative-Corpus/1.0"}
    if byte_range is not None:
        headers["Range"] = f"bytes={byte_range[0]}-{byte_range[1]}"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=timeout_seconds) as response:
        payload = response.read()
        status = int(getattr(response, "status", 0) or 0)
        response_headers = {key.lower(): value for key, value in response.headers.items()}
    return FetchResponse(payload=payload, status=status, headers=response_headers)


def _receipt_payload(
    *, url: str, byte_range: tuple[int, int] | None, payload: bytes
) -> dict:
    return {
        "url": url,
        "byte_range": list(byte_range) if byte_range is not None else None,
        "byte_size": len(payload),
        "sha256": sha256_bytes(payload),
    }


def _validate_cached(path: Path, url: str, byte_range: tuple[int, int] | None) -> CacheResult:
    receipt = receipt_path(path)
    if path.exists() != receipt.exists():
        raise CacheIntegrityError(f"partial cache state for {path}")
    if not path.exists():
        raise FileNotFoundError(path)
    metadata = json.loads(receipt.read_text(encoding="utf-8"))
    expected_range = list(byte_range) if byte_range is not None else None
    if metadata.get("url") != url or metadata.get("byte_range") != expected_range:
        raise CacheIntegrityError(f"cache identity mismatch for {path}")
    actual_size = path.stat().st_size
    actual_hash = sha256_file(path)
    if metadata.get("byte_size") != actual_size or metadata.get("sha256") != actual_hash:
        raise CacheIntegrityError(f"cache checksum mismatch for {path}")
    return CacheResult(path, actual_hash, actual_size, True, 0, 0, 0.0)


def store_verified_bytes(
    path: str | Path,
    *,
    url: str,
    byte_range: tuple[int, int] | None,
    payload: bytes,
) -> CacheResult:
    """Atomically store bytes plus a checksum receipt; never overwrite valid data."""

    path = Path(path)
    try:
        existing = _validate_cached(path, url, byte_range)
    except FileNotFoundError:
        existing = None
    if existing is not None:
        if existing.sha256 != sha256_bytes(payload):
            raise CacheIntegrityError(f"new payload differs from immutable cache {path}")
        return existing

    path.parent.mkdir(parents=True, exist_ok=True)
    receipt = receipt_path(path)
    if path.exists() or receipt.exists():
        raise CacheIntegrityError(f"refusing to overwrite invalid cache state for {path}")
    part = path.with_name(path.name + ".part")
    receipt_part = receipt.with_name(receipt.name + ".part")
    if part.exists() or receipt_part.exists():
        raise CacheIntegrityError(f"stale partial download exists for {path}")
    try:
        with part.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        metadata = _receipt_payload(url=url, byte_range=byte_range, payload=payload)
        receipt_part.write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        part.replace(path)
        receipt_part.replace(receipt)
    except Exception:
        part.unlink(missing_ok=True)
        receipt_part.unlink(missing_ok=True)
        raise
    return CacheResult(path, metadata["sha256"], metadata["byte_size"], False, 0, 1, 0.0)


def fetch_cached(
    url: str,
    path: str | Path,
    *,
    byte_range: tuple[int, int] | None = None,
    retries: int = 5,
    timeout_seconds: float = 120.0,
    backoff_seconds: float = 2.0,
    fetcher: Fetcher = default_fetcher,
) -> CacheResult:
    """Fetch into an immutable cache with independent retries and atomic finalize."""

    path = Path(path)
    try:
        return _validate_cached(path, url, byte_range)
    except FileNotFoundError:
        pass

    if retries < 1:
        raise ValueError("retries must be at least one")
    started = time.perf_counter()
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = fetcher(url, byte_range, timeout_seconds)
            expected_status = 206 if byte_range is not None else 200
            if response.status != expected_status:
                raise IOError(
                    f"unexpected HTTP status {response.status}; expected {expected_status}"
                )
            if byte_range is not None:
                expected_size = byte_range[1] - byte_range[0] + 1
                if len(response.payload) != expected_size:
                    raise IOError(
                        f"truncated range: expected {expected_size}, got {len(response.payload)}"
                    )
                content_range = response.headers.get("content-range", "")
                expected_prefix = f"bytes {byte_range[0]}-{byte_range[1]}/"
                if not content_range.startswith(expected_prefix):
                    raise IOError(
                        "missing or inconsistent Content-Range header: "
                        f"expected prefix {expected_prefix!r}, got {content_range!r}"
                    )
            stored = store_verified_bytes(
                path, url=url, byte_range=byte_range, payload=response.payload
            )
            return CacheResult(
                path=stored.path,
                sha256=stored.sha256,
                byte_size=stored.byte_size,
                from_cache=False,
                network_bytes=len(response.payload),
                attempts=attempt,
                elapsed_seconds=time.perf_counter() - started,
            )
        except (CacheIntegrityError, KeyboardInterrupt):
            raise
        except HTTPError as exc:
            last_error = exc
            if exc.code not in {408, 425, 429, 500, 502, 503, 504}:
                raise IOError(f"non-retryable HTTP status {exc.code} for {url}") from exc
            if attempt < retries:
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                delay = float(retry_after) if retry_after and retry_after.isdigit() else backoff_seconds * (2 ** (attempt - 1))
                if delay:
                    time.sleep(delay)
        except Exception as exc:
            last_error = exc
            if attempt < retries and backoff_seconds:
                time.sleep(backoff_seconds * (2 ** (attempt - 1)))
    raise IOError(f"failed to fetch {url} after {retries} attempts") from last_error
