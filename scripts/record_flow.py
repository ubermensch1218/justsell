#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any


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


def _now_stamp() -> str:
  return datetime.now().strftime("%Y%m%d-%H%M%S")


def _slug(s: str) -> str:
  v = re.sub(r"[^a-zA-Z0-9_-]+", "-", s.strip()).strip("-").lower()
  return v or "module"


def _load_steps(path: Path) -> dict[str, Any]:
  payload = json.loads(path.read_text(encoding="utf-8"))
  if not isinstance(payload, dict):
    raise ValueError("Flow steps file root must be an object.")

  modules = payload.get("modules")
  if isinstance(modules, list) and modules:
    valid = 0
    for i, m in enumerate(modules, start=1):
      if not isinstance(m, dict):
        raise ValueError(f"modules[{i}] must be an object.")
      steps = m.get("steps")
      if not isinstance(steps, list) or not steps:
        raise ValueError(f"modules[{i}] must contain non-empty 'steps'.")
      valid += 1
    if valid:
      return payload

  steps = payload.get("steps")
  if not isinstance(steps, list) or not steps:
    raise ValueError("Flow steps file must contain either non-empty 'steps' or non-empty 'modules'.")
  return payload


def _default_out_dir(project: Path | None) -> Path:
  if project is not None:
    return project / "channels" / "instagram" / "flow-recordings"
  return Path.cwd() / "out" / "flow-recordings"


def _normalize_modules(payload: dict[str, Any]) -> list[dict[str, Any]]:
  modules_raw = payload.get("modules")
  if isinstance(modules_raw, list) and modules_raw:
    modules: list[dict[str, Any]] = []
    for idx, m in enumerate(modules_raw, start=1):
      assert isinstance(m, dict)
      mid = _slug(str(m.get("id", "") or str(m.get("name", "")) or f"module-{idx:02d}"))
      title = str(m.get("title", "")).strip() or f"Module {idx}"
      caption = str(m.get("caption", "")).strip()
      start_url = str(m.get("start_url", payload.get("start_url", "")) or "").strip()
      modules.append(
        {
          "id": mid,
          "title": title,
          "caption": caption,
          "start_url": start_url,
          "steps": m.get("steps", []),
        }
      )
    return modules

  return [
    {
      "id": "module-01",
      "title": "Main Flow",
      "caption": "",
      "start_url": str(payload.get("start_url", "") or "").strip(),
      "steps": payload.get("steps", []),
    }
  ]


def _run_steps(page: Any, steps: list[dict[str, Any]]) -> None:
  for idx, step in enumerate(steps):
    if not isinstance(step, dict):
      raise ValueError(f"Step #{idx+1} must be an object.")
    action = str(step.get("action", "")).strip().lower()
    timeout_ms = int(step.get("timeout_ms", 30000))
    if action == "goto":
      url = str(step.get("url", "")).strip()
      if not url:
        raise ValueError(f"Step #{idx+1}: goto requires 'url'.")
      wait_until = str(step.get("wait_until", "networkidle")).strip() or "networkidle"
      page.goto(url, wait_until=wait_until, timeout=timeout_ms)
      continue
    if action == "click":
      selector = str(step.get("selector", "")).strip()
      if not selector:
        raise ValueError(f"Step #{idx+1}: click requires 'selector'.")
      page.locator(selector).first.click(timeout=timeout_ms)
      continue
    if action == "fill":
      selector = str(step.get("selector", "")).strip()
      value = str(step.get("value", ""))
      if not selector:
        raise ValueError(f"Step #{idx+1}: fill requires 'selector'.")
      page.locator(selector).first.fill(value, timeout=timeout_ms)
      continue
    if action == "press":
      selector = str(step.get("selector", "")).strip()
      key = str(step.get("key", "")).strip()
      if not selector or not key:
        raise ValueError(f"Step #{idx+1}: press requires 'selector' and 'key'.")
      page.locator(selector).first.press(key, timeout=timeout_ms)
      continue
    if action == "wait":
      wait_ms = int(step.get("ms", 1000))
      page.wait_for_timeout(max(0, wait_ms))
      continue
    raise ValueError(f"Step #{idx+1}: unsupported action '{action}'.")


def _record_single_module(*, playwright: Any, module: dict[str, Any], out_dir: Path, profile_dir: Path, width: int, height: int, headless: bool, start_url_override: str) -> Path:
  raw_video_dir = out_dir / ".tmp-recordings" / str(module["id"])
  raw_video_dir.mkdir(parents=True, exist_ok=True)

  context = playwright.chromium.launch_persistent_context(
    user_data_dir=str(profile_dir),
    headless=headless,
    viewport={"width": width, "height": height},
    record_video_dir=str(raw_video_dir),
    record_video_size={"width": width, "height": height},
  )
  page = context.pages[0] if context.pages else context.new_page()

  initial_url = start_url_override or str(module.get("start_url", "")).strip()
  if initial_url:
    page.goto(initial_url, wait_until="networkidle")

  _run_steps(page, module["steps"])
  page.wait_for_timeout(400)
  video = page.video
  context.close()

  if video is None:
    raise RuntimeError(f"Flow recording failed for module={module['id']}: video handle not created.")
  raw_video_path = Path(video.path()).resolve()
  if not raw_video_path.exists():
    raise FileNotFoundError(f"Recorded video not found for module={module['id']}: {raw_video_path}")

  suffix = raw_video_path.suffix.lower() or ".webm"
  final_path = out_dir / f"{_now_stamp()}-{_slug(str(module['id']))}{suffix}"
  shutil.move(str(raw_video_path), str(final_path))
  return final_path


def _stitch_videos(video_paths: list[Path], *, out_dir: Path) -> Path | None:
  if len(video_paths) < 2:
    return None

  out_path = out_dir / f"{_now_stamp()}-flow-stitched.mp4"
  with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tf:
    concat_path = Path(tf.name)
    for p in video_paths:
      safe = str(p).replace("'", "'\\''")
      tf.write(f"file '{safe}'\n")

  try:
    cmd = [
      "ffmpeg",
      "-y",
      "-f",
      "concat",
      "-safe",
      "0",
      "-i",
      str(concat_path),
      "-c:v",
      "libx264",
      "-pix_fmt",
      "yuv420p",
      "-c:a",
      "aac",
      str(out_path),
    ]
    p = subprocess.run(cmd, check=False, text=True, capture_output=True, env=os.environ.copy())
    if p.returncode != 0:
      return None
    return out_path if out_path.exists() else None
  finally:
    try:
      concat_path.unlink(missing_ok=True)
    except Exception:
      pass


def main() -> int:
  parser = argparse.ArgumentParser(description="Record real browser flow video(s) for Remotion input.")
  parser.add_argument("--steps", required=True, type=Path, help="Path to flow-steps JSON file")
  parser.add_argument("--project", default="", help="Optional project path for default output location")
  parser.add_argument("--out-dir", default="", help="Video output directory")
  parser.add_argument("--profile-dir", default="", help="Persistent browser profile directory")
  parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
  parser.add_argument("--start-url", default="", help="Optional initial URL override")
  parser.add_argument("--manifest-out", default="", help="Optional output path for flow manifest JSON")
  parser.add_argument("--no-stitch", action="store_true", help="Disable automatic stitching for multi-module recording")
  args = parser.parse_args()

  try:
    from playwright.sync_api import sync_playwright
  except Exception as exc:
    raise RuntimeError(
      "playwright is required. Install with `python3 -m pip install playwright` "
      "and browser runtime with `python3 -m playwright install chromium`."
    ) from exc

  steps_path = args.steps.expanduser().resolve()
  if not steps_path.exists():
    raise FileNotFoundError(f"Missing steps file: {steps_path}")
  payload = _load_steps(steps_path)

  project_path: Path | None = None
  if str(args.project).strip():
    project_path = Path(str(args.project).strip()).expanduser().resolve()
  out_dir = Path(str(args.out_dir).strip()).expanduser().resolve() if str(args.out_dir).strip() else _default_out_dir(project_path)
  out_dir.mkdir(parents=True, exist_ok=True)

  profile_dir = Path(str(args.profile_dir).strip()).expanduser().resolve() if str(args.profile_dir).strip() else (_justsell_home() / "browser-profile")
  profile_dir.mkdir(parents=True, exist_ok=True)

  viewport = payload.get("viewport", {})
  width = int(viewport.get("width", 1280)) if isinstance(viewport, dict) else 1280
  height = int(viewport.get("height", 720)) if isinstance(viewport, dict) else 720

  modules = _normalize_modules(payload)
  module_results: list[dict[str, Any]] = []

  with sync_playwright() as p:
    for mod in modules:
      video_path = _record_single_module(
        playwright=p,
        module=mod,
        out_dir=out_dir,
        profile_dir=profile_dir,
        width=width,
        height=height,
        headless=bool(args.headless),
        start_url_override=str(args.start_url).strip(),
      )
      module_results.append(
        {
          "id": mod["id"],
          "title": mod["title"],
          "caption": mod.get("caption", ""),
          "video_path": str(video_path),
        }
      )

  stitched_path: Path | None = None
  if (not bool(args.no_stitch)) and len(module_results) > 1:
    stitched_path = _stitch_videos([Path(m["video_path"]).resolve() for m in module_results], out_dir=out_dir)

  manifest = {
    "version": 1,
    "generated_at": datetime.now().isoformat(),
    "steps_file": str(steps_path),
    "viewport": {"width": width, "height": height},
    "module_count": len(module_results),
    "modules": module_results,
  }
  if stitched_path is not None:
    manifest["stitched_video_path"] = str(stitched_path)

  manifest_path: Path | None = None
  if str(args.manifest_out).strip():
    manifest_path = Path(str(args.manifest_out).strip()).expanduser().resolve()
  elif len(module_results) > 1:
    manifest_path = out_dir / f"{_now_stamp()}-flow-manifest.json"

  if manifest_path is not None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

  try:
    tmp_root = out_dir / ".tmp-recordings"
    if tmp_root.exists():
      shutil.rmtree(tmp_root, ignore_errors=True)
  except Exception:
    pass

  if stitched_path is not None:
    print(str(stitched_path))
    return 0

  if module_results:
    print(str(module_results[0]["video_path"]))
    return 0

  raise RuntimeError("No recorded modules were produced.")


if __name__ == "__main__":
  raise SystemExit(main())
