#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]


def _chrome_bin() -> Path | None:
  env_bin = os.environ.get("JUSTSELL_CHROME_BIN", "").strip()
  candidates = [
    env_bin,
    shutil.which("google-chrome") or "",
    shutil.which("chromium") or "",
    shutil.which("chromium-browser") or "",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
  ]
  for raw in candidates:
    if not raw:
      continue
    p = Path(raw).expanduser()
    if p.exists():
      return p
  return None


def _is_up(port: int) -> bool:
  try:
    with urlopen(f"http://127.0.0.1:{port}/api/onboarding", timeout=1.5) as resp:
      return int(getattr(resp, "status", 0) or 0) == 200
  except Exception:
    return False


def _start_console(port: int) -> subprocess.Popen[str] | None:
  if _is_up(port):
    return None
  env = os.environ.copy()
  env["JUSTSELL_CONSOLE_PORT"] = str(port)
  return subprocess.Popen(
    ["python3", str(REPO_ROOT / "scripts" / "justsell_console.py")],
    cwd=str(REPO_ROOT),
    env=env,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    text=True,
  )


def _wait_for_console(port: int) -> bool:
  for _ in range(40):
    if _is_up(port):
      return True
    time.sleep(0.25)
  return False


def _capture(chrome_bin: Path, *, url: str, out_path: Path, width: int, height: int, budget_ms: int = 2500) -> bool:
  out_path.parent.mkdir(parents=True, exist_ok=True)
  cmd = [
    str(chrome_bin),
    "--headless=new",
    "--disable-gpu",
    "--hide-scrollbars",
    "--no-first-run",
    "--no-default-browser-check",
    "--run-all-compositor-stages-before-draw",
    f"--window-size={width},{height}",
    f"--virtual-time-budget={budget_ms}",
    f"--screenshot={str(out_path)}",
    url,
  ]
  p = subprocess.run(cmd, cwd=str(REPO_ROOT), check=False, text=True, capture_output=True, env=os.environ.copy())
  return p.returncode == 0 and out_path.exists()


def main() -> int:
  parser = argparse.ArgumentParser(description="Capture local JustSell console screenshots for cardnews image slides.")
  parser.add_argument("--project", required=True, type=Path, help="Project path for output grouping only")
  parser.add_argument("--out-dir", required=True, type=Path, help="Output directory for captured PNG files")
  parser.add_argument("--port", default=5687, type=int, help="Temporary console port")
  args = parser.parse_args()

  chrome_bin = _chrome_bin()
  if chrome_bin is None:
    print(json.dumps({"ok": False, "error": "chrome not found"}))
    return 0

  out_dir = args.out_dir.expanduser().resolve()
  out_dir.mkdir(parents=True, exist_ok=True)

  proc = _start_console(int(args.port))
  try:
    if not _wait_for_console(int(args.port)):
      print(json.dumps({"ok": False, "error": "console did not start"}))
      return 0

    base = f"http://127.0.0.1:{int(args.port)}"
    outputs: dict[str, str] = {}

    home_path = out_dir / "console-home.png"
    if _capture(
      chrome_bin,
      url=f"{base}/",
      out_path=home_path,
      width=1440,
      height=1600,
      budget_ms=3000,
    ):
      outputs["home"] = str(home_path)

    setup_path = out_dir / "console-setup.png"
    if _capture(
      chrome_bin,
      url=f"{base}/connect?tab=setup&saved=1#setup",
      out_path=setup_path,
      width=1440,
      height=1700,
      budget_ms=3000,
    ):
      outputs["setup"] = str(setup_path)

    print(json.dumps({"ok": True, "images": outputs}, ensure_ascii=False))
    return 0
  finally:
    if proc is not None:
      proc.terminate()
      try:
        proc.wait(timeout=3)
      except Exception:
        proc.kill()


if __name__ == "__main__":
  raise SystemExit(main())
