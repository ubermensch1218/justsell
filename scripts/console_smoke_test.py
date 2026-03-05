from __future__ import annotations

import os
import subprocess
import time
from urllib.request import urlopen


def _get(url: str) -> str:
  with urlopen(url, timeout=5) as r:
    return r.read().decode("utf-8", errors="replace")


def main() -> int:
  port = "5679"
  env = os.environ.copy()
  env["JUSTSELL_CONSOLE_PORT"] = port
  p = subprocess.Popen(
    ["python3", "scripts/justsell_console.py"],
    cwd=os.getcwd(),
    env=env,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
  )
  try:
    ok = False
    for _ in range(25):
      try:
        _get(f"http://127.0.0.1:{port}/api/onboarding")
        ok = True
        break
      except Exception:
        time.sleep(0.2)
    if not ok:
      print("FAIL: server did not start")
      return 1

    home = _get(f"http://127.0.0.1:{port}/")
    if "<h2>Preview</h2>" not in home:
      print("FAIL: home preview panel missing")
      return 1

    setup = _get(f"http://127.0.0.1:{port}/connect?tab=setup")
    if "One section per view. Choose where to work." not in setup:
      print("FAIL: section navigation missing")
      return 1
    if 'id="setup" class="card" style="padding:14px;display:block"' not in setup:
      print("FAIL: setup tab should be visible")
      return 1
    if 'id="threads" class="card" style="padding:14px;display:none"' not in setup:
      print("FAIL: non-selected tab should be hidden")
      return 1

    threads = _get(f"http://127.0.0.1:{port}/connect?tab=threads")
    if 'id="threads" class="card" style="padding:14px;display:block"' not in threads:
      print("FAIL: threads tab should be visible")
      return 1

    saved = _get(f"http://127.0.0.1:{port}/connect?tab=setup&saved=1")
    if "Saved. Setup values were updated." not in saved:
      print("FAIL: saved notice missing")
      return 1

    print("OK: console smoke test passed")
    return 0
  finally:
    p.terminate()
    try:
      p.wait(timeout=2)
    except Exception:
      p.kill()


if __name__ == "__main__":
  raise SystemExit(main())

