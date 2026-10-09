"""Vercel serverless entry point for the read-only API."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for extra in (ROOT, ROOT / "app"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from app.backend.main import app

__all__ = ["app"]
