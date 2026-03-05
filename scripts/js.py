#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from urllib.request import urlopen
import webbrowser
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.justsell_console.server import CONFIG_PATH, JUSTSELL_HOME, PROJECTS_DIR, _config_settings, _read_config, run_server  # noqa: E402


def _env(name: str, default: str = "") -> str:
  return os.environ.get(name, default).strip()


def _is_tty() -> bool:
  try:
    return sys.stdin.isatty() and sys.stdout.isatty()
  except Exception:
    return False


def _print_header(title: str) -> None:
  print(title)
  print("")


def _open_url(url: str, *, no_open: bool) -> None:
  if no_open:
    return
  try:
    webbrowser.open(url, new=2)
  except Exception:
    pass


def _run_wizard() -> int:
  cmd = ["python3", str(REPO_ROOT / "scripts" / "justsell_setup.py"), "--wizard"]
  return subprocess.call(cmd)


def _read_json(path: Path, default: dict) -> dict:
  try:
    import json

    raw = path.read_text(encoding="utf-8")
    obj = json.loads(raw) if raw else default
    return obj if isinstance(obj, dict) else default
  except Exception:
    return default


def _status() -> dict:
  cfg = _read_config()
  settings = _config_settings()
  secrets = cfg.get("secrets", {})
  if not isinstance(secrets, dict):
    secrets = {}

  cardnews = settings.get("cardnews", {})
  cardnews_ready = isinstance(cardnews, dict) and bool(
    str(cardnews.get("template", "")).strip() or cardnews.get("theme") or cardnews.get("fonts")
  )
  threads = secrets.get("threads", {})
  ig = secrets.get("instagram", {})
  threads_connected = isinstance(threads, dict) and bool(str(threads.get("access_token", "")).strip())
  ig_connected = isinstance(ig, dict) and bool(str(ig.get("access_token", "")).strip())
  ig_user_selected = isinstance(ig, dict) and bool(str(ig.get("ig_user_id", "")).strip())
  public_base = str(settings.get("public_base_url", "")).strip() or _env("JUSTSELL_PUBLIC_BASE_URL", "")
  public_base_ready = bool(str(public_base).strip())

  projects = []
  try:
    for p in sorted(PROJECTS_DIR.iterdir()):
      if p.is_dir() and p.name != "_template":
        projects.append(p.name)
  except Exception:
    projects = []

  next_hint = ""
  if not cardnews_ready:
    next_hint = "Open /connect and set template, key colors, and fonts."
  elif not threads_connected or not ig_connected:
    next_hint = "Open /connect and complete OAuth connect."
  elif ig_connected and not ig_user_selected:
    next_hint = "Open /connect and Discover accounts, then Select one ig_user_id."
  elif not projects:
    next_hint = "Open /connect and create a project slug."
  else:
    next_hint = "Go to / and Generate + Render. Publishing remains dry-run by default."

  return {
    "storage": str(JUSTSELL_HOME),
    "config_path": str(CONFIG_PATH),
    "projects_dir": str(PROJECTS_DIR),
    "cardnews_ready": cardnews_ready,
    "threads_connected": threads_connected,
    "ig_connected": ig_connected,
    "ig_user_selected": ig_user_selected,
    "public_base_ready": public_base_ready,
    "projects": projects[:20],
    "next_hint": next_hint,
  }


def _mark(ok: bool) -> str:
  return "[OK]" if ok else "[  ]"


def cmd_status(_: argparse.Namespace) -> int:
  s = _status()
  print("JustSell Status")
  print("")
  print(f"[i] Storage: {s['storage']}")
  print(f"[i] Config:  {s['config_path']}")
  print(f"[i] Projects:{s['projects_dir']}")
  print("")
  print(f"{_mark(bool(s['cardnews_ready']))} Cardnews defaults")
  print(f"{_mark(bool(s['threads_connected']))} Threads OAuth")
  print(f"{_mark(bool(s['ig_connected']))} Instagram OAuth")
  print(f"{_mark(bool(s['ig_user_selected']))} IG account select")
  print(f"{_mark(bool(s['public_base_ready']))} Public base URL")
  print("")
  if s.get("projects"):
    print("[i] Projects: " + ", ".join([str(x) for x in s["projects"]]))
  else:
    print("[i] Projects: (none)")
  print("")
  print("[i] Next: " + str(s.get("next_hint", "")).strip())
  return 0


def _is_up(host: str, port: int) -> bool:
  url = f"http://{host}:{port}/api/onboarding"
  try:
    with urlopen(url, timeout=1.5) as resp:
      return int(getattr(resp, "status", 0) or 0) == 200
  except Exception:
    return False


def cmd_start(args: argparse.Namespace) -> int:
  port = int(_env("JUSTSELL_CONSOLE_PORT", str(args.port)))
  host = str(args.host).strip()
  mode = str(args.mode).strip()
  if mode not in ["config", "console"]:
    mode = "config"

  target_url = f"http://{host}:{port}/connect" if mode == "config" else f"http://{host}:{port}/"
  if _is_up(host, port):
    _print_header("JustSell Console")
    print(f"[i] Already running: {target_url}")
    _open_url(target_url, no_open=bool(args.no_open))
    return 0

  # Start a detached server without relying on shell background/redirection.
  cmd = [
    "python3",
    str(REPO_ROOT / "scripts" / "js.py"),
    mode,
    "--host",
    host,
    "--port",
    str(port),
    "--no-open",
  ]
  try:
    p = subprocess.Popen(
      cmd,
      cwd=str(REPO_ROOT),
      stdout=subprocess.DEVNULL,
      stderr=subprocess.DEVNULL,
      start_new_session=True,
      env=os.environ.copy(),
    )
  except Exception as e:
    print(f"[!] Failed to start: {e}")
    return 1

  # Give it a moment, then open.
  time.sleep(0.4)
  _print_header("JustSell Console")
  print(f"[i] PID: {p.pid}")
  print(f"[i] Opening: {target_url}")
  _open_url(target_url, no_open=bool(args.no_open))
  return 0


def cmd_config(args: argparse.Namespace) -> int:
  port = int(_env("JUSTSELL_CONSOLE_PORT", str(args.port)))
  host = str(args.host).strip()
  url = f"http://{host}:{port}/connect"

  _print_header("JustSell Config Dashboard")
  print(f"[i] Storage: {JUSTSELL_HOME}")
  print("[i] Starting JustSellConsole...")
  print(f"[i] Opening: {url}")
  print("[i] Press Ctrl+C to stop")
  print("")

  _open_url(url, no_open=bool(args.no_open))
  time.sleep(0.1)
  run_server(host=host, port=port)
  return 0


def cmd_console(args: argparse.Namespace) -> int:
  port = int(_env("JUSTSELL_CONSOLE_PORT", str(args.port)))
  host = str(args.host).strip()
  url = f"http://{host}:{port}/"

  _print_header("JustSell Console")
  print(f"[i] Storage: {JUSTSELL_HOME}")
  print("[i] Starting JustSellConsole...")
  print(f"[i] Opening: {url}")
  print("[i] Press Ctrl+C to stop")
  print("")

  _open_url(url, no_open=bool(args.no_open))
  time.sleep(0.1)
  run_server(host=host, port=port)
  return 0


def cmd_init(args: argparse.Namespace) -> int:
  _print_header("JustSell Init")
  if _is_tty():
    print("[i] Step 1/2: Setup wizard (local-first)")
    rc = _run_wizard()
    if rc != 0:
      print("")
      print("[!] Wizard did not complete. You can still run config dashboard and use /connect Setup form.")
  else:
    print("[i] Step 1/2: Setup wizard (skipped - no interactive TTY)")
    print("[i] Use the /connect Setup section in the dashboard instead.")
  print("")
  try:
    cmd_status(args)
    print("")
  except Exception:
    pass
  print("[i] Step 2/2: Config dashboard")
  return cmd_config(args)


def cmd_version(_: argparse.Namespace) -> int:
  plugin_path = REPO_ROOT / ".claude-plugin" / "plugin.json"
  try:
    raw = plugin_path.read_text(encoding="utf-8")
  except Exception:
    raw = ""
  v = ""
  if raw:
    import json

    try:
      obj = json.loads(raw)
      v = str(obj.get("version", "")).strip()
    except Exception:
      v = ""
  print(v or "unknown")
  return 0


def main() -> int:
  p = argparse.ArgumentParser(prog="js", description="JustSell CLI (local-first)")
  sub = p.add_subparsers(dest="cmd", required=True)

  def add_common(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--host", default=_env("JUSTSELL_CONSOLE_HOST", "127.0.0.1"))
    sp.add_argument("--port", type=int, default=int(_env("JUSTSELL_CONSOLE_PORT", "5678")))
    sp.add_argument("--no-open", action="store_true", help="Do not open the browser automatically")

  sp = sub.add_parser("config", help="Open config dashboard (/connect)")
  add_common(sp)
  sp.set_defaults(func=cmd_config)

  sp = sub.add_parser("console", help="Open console home (/)")
  add_common(sp)
  sp.set_defaults(func=cmd_console)

  sp = sub.add_parser("init", help="Run wizard then open config dashboard")
  add_common(sp)
  sp.set_defaults(func=cmd_init)

  sp = sub.add_parser("start", help="Start console in background and open browser")
  add_common(sp)
  sp.add_argument("--mode", default="config", help="config|console (default: config)")
  sp.set_defaults(func=cmd_start)

  sp = sub.add_parser("status", help="Show local setup status")
  sp.set_defaults(func=cmd_status)

  sp = sub.add_parser("version", help="Print plugin version")
  sp.set_defaults(func=cmd_version)

  args = p.parse_args()
  return int(args.func(args))


if __name__ == "__main__":
  raise SystemExit(main())
