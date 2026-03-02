#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
  return datetime.now(timezone.utc).isoformat()


def _claude_dir() -> Path:
  v = (os.environ.get("CLAUDE_CONFIG_DIR") or os.environ.get("CLAUDE_HOME") or "").strip()
  if v:
    return Path(v).expanduser()
  return (Path.home() / ".claude").expanduser()


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
  try:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else default
  except Exception:
    return default


def _write_json(path: Path, data: dict[str, Any]) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
  try:
    os.chmod(path, 0o600)
  except Exception:
    pass


def _merge_settings(cfg: dict[str, Any], updates: dict[str, str]) -> dict[str, Any]:
  cfg.setdefault("version", 1)
  cfg.setdefault("settings", {})
  cfg.setdefault("secrets", {})
  cfg.setdefault("meta", {})
  if not isinstance(cfg["settings"], dict):
    cfg["settings"] = {}
  for k, v in updates.items():
    if v == "":
      continue
    cfg["settings"][k] = v
  cfg["meta"]["setupCompletedAt"] = _now_iso()
  cfg["meta"]["setupBy"] = "justsell_setup.py"
  cfg["updated_at"] = _now_iso()
  return cfg


def main() -> int:
  p = argparse.ArgumentParser(description="Write JustSell plugin config into ~/.claude/.omc/justsell/config.json")
  p.add_argument("--claude-dir", type=Path, default=None, help="Override Claude config dir (default: env CLAUDE_CONFIG_DIR or ~/.claude)")

  p.add_argument("--public-base-url", default="", help="Public base URL for serving assets to Meta (optional)")

  p.add_argument("--threads-app-id", default="")
  p.add_argument("--threads-app-secret", default="")

  p.add_argument("--meta-app-id", default="")
  p.add_argument("--meta-app-secret", default="")
  p.add_argument("--graph-api-version", default="")

  args = p.parse_args()

  claude_dir = args.claude_dir.expanduser() if args.claude_dir else _claude_dir()
  justsell_dir = claude_dir / ".omc" / "justsell"
  config_path = justsell_dir / "config.json"

  cfg = _read_json(config_path, {"version": 1, "settings": {}, "secrets": {}, "meta": {}})
  updates = {
    "public_base_url": args.public_base_url.strip(),
    "threads_app_id": args.threads_app_id.strip(),
    "threads_app_secret": args.threads_app_secret.strip(),
    "meta_app_id": args.meta_app_id.strip(),
    "meta_app_secret": args.meta_app_secret.strip(),
    "graph_api_version": args.graph_api_version.strip(),
  }
  cfg = _merge_settings(cfg, updates)
  _write_json(config_path, cfg)

  print(str(config_path))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())

