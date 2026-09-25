"""Compatibility entry point; the canonical test command is `python -m pytest -q`."""

import pytest


if __name__ == "__main__":
    raise SystemExit(pytest.main(["-q"]))
