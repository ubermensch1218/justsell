#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.justsell_console.server import JUSTSELL_HOME, run_server  # noqa: E402


def _env(name: str, default: str = "") -> str:
  return os.environ.get(name, default).strip()


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
  print("[i] Step 1/2: Setup wizard (local-first)")
  rc = _run_wizard()
  if rc != 0:
    print("")
    print("[!] Wizard did not complete. You can still run config dashboard and use /connect Setup form.")
  print("")
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

  sp = sub.add_parser("version", help="Print plugin version")
  sp.set_defaults(func=cmd_version)

  args = p.parse_args()
  return int(args.func(args))


if __name__ == "__main__":
  raise SystemExit(main())

