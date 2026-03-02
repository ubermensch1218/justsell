#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.justsell_console.server import run_server  # noqa: E402


def main() -> None:
  port = int(os.environ.get("JUSTSELL_CONSOLE_PORT", "5678"))
  run_server(port=port)


if __name__ == "__main__":
  main()
