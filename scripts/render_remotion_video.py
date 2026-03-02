#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_APP_DIR = REPO_ROOT / "templates" / "remotion_app"


def _claude_dir() -> Path:
  v = (os.environ.get("CLAUDE_CONFIG_DIR") or os.environ.get("CLAUDE_HOME") or "").strip()
  if v:
    return Path(v).expanduser()
  return (Path.home() / ".claude").expanduser()


def _justsell_home() -> Path:
  v = (os.environ.get("JUSTSELL_HOME") or "").strip()
  if v:
    return Path(v).expanduser()
  return (_claude_dir() / ".js").expanduser()


def _load_spec(path: Path) -> dict[str, Any]:
  raw = path.read_text(encoding="utf-8")
  spec = json.loads(raw)
  if not isinstance(spec, dict):
    raise ValueError("Spec root must be an object")
  render = spec.get("render", {})
  if not isinstance(render, dict):
    raise ValueError("Spec.render must be an object")
  _ = int(render.get("width", 1080))
  _ = int(render.get("height", 1920))
  _ = int(render.get("fps", 30))
  _ = float(render.get("duration_sec", 0))
  return spec


def _sync_template(src: Path, dst: Path) -> None:
  dst.mkdir(parents=True, exist_ok=True)
  for p in src.rglob("*"):
    rel = p.relative_to(src)
    target = dst / rel
    if p.is_dir():
      target.mkdir(parents=True, exist_ok=True)
      continue
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, target)


def _run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
  return subprocess.run(
    cmd,
    cwd=str(cwd),
    check=False,
    text=True,
    capture_output=True,
    env=os.environ.copy(),
  )


def _default_out_dir(spec_path: Path) -> Path:
  parts = spec_path.parts
  try:
    idx = parts.index("projects")
    if len(parts) > idx + 4 and parts[idx + 3] == "instagram" and parts[idx + 4] == "remotion":
      return spec_path.parents[2] / "videos"
  except Exception:
    pass
  return spec_path.parent


def main() -> int:
  parser = argparse.ArgumentParser(description="Render Remotion promo video from projects/<project>/channels/instagram/remotion/<spec>.json")
  parser.add_argument("--spec", required=True, type=Path, help="Path to remotion JSON spec")
  parser.add_argument("--out", default="", help="Output directory (default: sibling channels/instagram/videos)")
  parser.add_argument("--skip-install", action="store_true", help="Skip npm install even if node_modules is missing")
  args = parser.parse_args()

  spec_abs = args.spec.expanduser().resolve()
  if not spec_abs.exists():
    raise FileNotFoundError(f"Missing spec: {spec_abs}")
  spec = _load_spec(spec_abs)

  runtime_root = _justsell_home() / "remotion-runtime"
  app_root = runtime_root / "app"
  _sync_template(TEMPLATE_APP_DIR, app_root)

  remotion_bin = app_root / "node_modules" / ".bin" / "remotion"
  if not args.skip_install and (not (app_root / "node_modules").exists() or not remotion_bin.exists()):
    p = _run(["npm", "install", "--no-audit", "--no-fund"], cwd=app_root)
    if p.returncode != 0:
      raise RuntimeError(f"npm install failed\n{p.stdout}\n{p.stderr}")

  if args.out.strip():
    out_dir = Path(args.out).expanduser().resolve()
  else:
    out_dir = _default_out_dir(spec_abs)
  out_dir.mkdir(parents=True, exist_ok=True)
  out_path = out_dir / f"{spec_abs.stem}.mp4"

  props = json.dumps({"spec": spec}, ensure_ascii=False)
  cmd = [
    "npx",
    "remotion",
    "render",
    "src/index.jsx",
    "JustSellPromo",
    str(out_path),
    "--props",
    props,
    "--codec",
    "h264",
    "--pixel-format",
    "yuv420p",
  ]
  p2 = _run(cmd, cwd=app_root)
  if p2.returncode != 0:
    raise RuntimeError(f"remotion render failed\n{p2.stdout}\n{p2.stderr}")

  print(str(out_path))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
