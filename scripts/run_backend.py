#!/usr/bin/env python
"""CLI Runner to launch the Ocean Sentinel Backend API locally.

Usage:
    python scripts/run_backend.py [--host 127.0.0.1] [--port 8000] [--reload]
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

# Add src to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import uvicorn


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Ocean Sentinel Backend API server.")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port number (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on code changes")
    args = parser.parse_args()

    print("=" * 80)
    print("OCEAN SENTINEL — BACKEND API SERVER V1")
    print("=" * 80)
    print(f"  Host:         http://{args.host}:{args.port}")
    print(f"  Docs:         http://{args.host}:{args.port}/docs")
    print(f"  API Health:   http://{args.host}:{args.port}/api/v1/health")
    print(f"  Auto-reload:  {args.reload}")
    print("=" * 80)

    uvicorn.run(
        "ocean_sentinel.api.app:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
