from __future__ import annotations

import html
import json
import os
import copy
import secrets
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import parse_qs, unquote, urlparse

from apps.justsell_console.setup_validation import validate_setup_form


def _env(name: str, default: str = "") -> str:
  return os.environ.get(name, default).strip()


REPO_ROOT = Path(__file__).resolve().parents[2]

# Storage locations:
# - Installed tool storage (default): ~/.claude/.js/
# - Console state/logs/events: <JUSTSELL_HOME>/console/
# - Settings + OAuth tokens: <JUSTSELL_HOME>/config.json
CLAUDE_HOME = Path(
  _env(
    "CLAUDE_CONFIG_DIR",
    _env("CLAUDE_HOME", str(Path.home() / ".claude")),
  )
).expanduser()
JUSTSELL_HOME = Path(_env("JUSTSELL_HOME", str(CLAUDE_HOME / ".js"))).expanduser()
JUSTSELL_HOME.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = Path(_env("JUSTSELL_CONFIG_PATH", str(JUSTSELL_HOME / "config.json"))).expanduser()

# Projects live outside the plugin install dir so updates do not wipe them.
# Default: ~/.claude/.js/projects (respects CLAUDE_CONFIG_DIR and JUSTSELL_HOME).
PROJECTS_DIR = Path(_env("JUSTSELL_PROJECTS_DIR", str(JUSTSELL_HOME / "projects"))).expanduser()
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
PROJECTS_DIR_NAME = PROJECTS_DIR.name
PATH_ROOT = PROJECTS_DIR.parent

STATE_DIR = JUSTSELL_HOME / "console"
STATE_DIR.mkdir(parents=True, exist_ok=True)
STATE_PATH = STATE_DIR / "state.json"
LOG_PATH = STATE_DIR / "console.log"
SECRETS_PATH = JUSTSELL_HOME / "secrets.json"  # legacy/compat; prefer CONFIG_PATH
EVENTS_DIR = STATE_DIR / "events"
EVENTS_DIR.mkdir(parents=True, exist_ok=True)

LEGACY_STATE_DIR = REPO_ROOT / ".omx" / "justsell-console"
LEGACY_SECRETS_PATH = LEGACY_STATE_DIR / "secrets.json"

REPO_JST_CONSOLE_DIR = REPO_ROOT / ".jst" / "console"
REPO_JST_SECRETS_PATH = REPO_JST_CONSOLE_DIR / "secrets.json"

HOME_JST_CONSOLE_DIR = Path.home() / ".jst" / "console"
HOME_JST_SECRETS_PATH = HOME_JST_CONSOLE_DIR / "secrets.json"

HOME_CCS_JUSTSELL_CONFIG_PATH = Path.home() / ".ccs" / "justsell" / "config.json"


DEFAULT_CARDNEWS_SETTINGS: dict[str, object] = {
  "template": "channels/instagram/templates/cardnews.claude_code_like.yaml",
  "theme": {
    "accent_primary": "#2563EB",
    "accent_secondary": "#0F172A",
    "cover_fill": "#F3F8FF",
    "panel_fill": "#FFFFFF",
    "bg_kind": "solid",
    "bg_solid": "#FFFFFF",
    "bg_from": "",
    "bg_to": "",
  },
  "fonts": {
    "title_name": "Pretendard Bold",
    "body_name": "Pretendard Regular",
    "footer_name": "Pretendard Regular",
  },
}

LEGACY_CLAUDE_THEME: dict[str, str] = {
  "accent_primary": "#FF6A2A",
  "accent_secondary": "#111111",
  "cover_fill": "#FF6A2A",
  "panel_fill": "#141414",
  "bg_kind": "solid",
  "bg_solid": "#FFFFFF",
  "bg_from": "",
  "bg_to": "",
}


def _deep_merge_defaults(base: dict, defaults: dict) -> dict:
  for k, v in defaults.items():
    if isinstance(v, dict):
      cur = base.get(k)
      if not isinstance(cur, dict):
        cur = {}
      base[k] = _deep_merge_defaults(cur, v)
      continue
    if k not in base or base.get(k) is None:
      base[k] = v
  return base


def _norm_theme_value(v: object) -> str:
  s = str(v or "").strip()
  if s.startswith("#"):
    return s.upper()
  return s


def _migrate_legacy_claude_theme(settings: dict) -> dict:
  if _env("JUSTSELL_KEEP_LEGACY_THEME", "").lower() in {"1", "true", "yes", "on"}:
    return settings
  cardnews = settings.get("cardnews", {})
  if not isinstance(cardnews, dict):
    return settings
  template = str(cardnews.get("template", "") or "").strip()
  if "cardnews.claude_code_like" not in template:
    return settings
  theme = cardnews.get("theme", {})
  if not isinstance(theme, dict):
    return settings
  for k, legacy_v in LEGACY_CLAUDE_THEME.items():
    if _norm_theme_value(theme.get(k)) != _norm_theme_value(legacy_v):
      return settings

  cardnews["theme"] = copy.deepcopy(DEFAULT_CARDNEWS_SETTINGS["theme"])
  settings["cardnews"] = cardnews
  return settings


def _default_settings() -> dict:
  return {
    "cardnews": copy.deepcopy(DEFAULT_CARDNEWS_SETTINGS),
  }


def _now_iso() -> str:
  return datetime.now(timezone.utc).isoformat()


def _today_ymd() -> str:
  return datetime.now().strftime("%Y-%m-%d")


def _event_path(kind: str) -> Path:
  # kind: chat|jobs|events
  return EVENTS_DIR / f"{kind}-{_today_ymd()}.jsonl"


def _redact(obj: object) -> object:
  # Best-effort redaction for logs: never store tokens/secrets.
  if isinstance(obj, dict):
    out: dict = {}
    for k, v in obj.items():
      lk = str(k).lower()
      if any(
        s in lk
        for s in [
          "token",
          "secret",
          "client_secret",
          "access_token",
          "refresh_token",
          "app_secret",
          "api_key",
          "apikey",
        ]
      ):
        out[k] = "***"
      else:
        out[k] = _redact(v)
    return out
  if isinstance(obj, list):
    return [_redact(x) for x in obj]
  return obj


def _append_jsonl(path: Path, payload: dict) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  line = json.dumps(payload, ensure_ascii=False)
  with path.open("a", encoding="utf-8") as f:
    f.write(line + "\n")


def _append_event(event_type: str, data: dict) -> None:
  _append_jsonl(
    _event_path("events"),
    {
      "ts": _now_iso(),
      "type": event_type,
      "data": _redact(data),
    },
  )

  # Mirror high-level events into config metadata (no secrets).
  # Keep this tiny so the file stays stable for other tooling.
  try:
    existing = _read_json(CONFIG_PATH, {"version": 1, "settings": {}, "secrets": {}, "meta": {}})
    if not isinstance(existing, dict):
      existing = {"version": 1, "settings": {}, "secrets": {}, "meta": {}}
    meta = existing.get("meta", {})
    if not isinstance(meta, dict):
      meta = {}
    meta["last_event_type"] = event_type
    meta["last_event_at"] = _now_iso()
    existing["meta"] = meta
    existing["updated_at"] = _now_iso()
    _write_json(CONFIG_PATH, existing)
    try:
      os.chmod(CONFIG_PATH, 0o600)
    except Exception:
      pass
  except Exception:
    pass


def _read_json(path: Path, default: dict) -> dict:
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except Exception:
    return default


def _write_json(path: Path, data: dict) -> None:
  path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_config() -> dict:
  cfg = _read_json(CONFIG_PATH, {"version": 1, "settings": {}, "secrets": {}, "meta": {}})
  if not isinstance(cfg, dict):
    cfg = {"version": 1, "settings": {}, "secrets": {}, "meta": {}}
  cfg.setdefault("version", 1)
  cfg.setdefault("settings", {})
  cfg.setdefault("secrets", {})
  cfg.setdefault("meta", {})
  return cfg


def _write_config(cfg: dict) -> None:
  _write_json(CONFIG_PATH, cfg)
  try:
    os.chmod(CONFIG_PATH, 0o600)
  except Exception:
    pass


def _meta_set(key: str, value: object) -> None:
  cfg = _read_config()
  meta = cfg.get("meta", {})
  if not isinstance(meta, dict):
    meta = {}
  meta[key] = value
  cfg["meta"] = meta
  cfg["updated_at"] = _now_iso()
  _write_config(cfg)


_REPO_URL_CACHE: str | None = None


def _plugin_repo_url() -> str:
  # Prefer env override, then .claude-plugin/plugin.json.
  v = _env("JUSTSELL_REPO_URL", "")
  if v:
    return v

  global _REPO_URL_CACHE
  if _REPO_URL_CACHE is not None:
    return _REPO_URL_CACHE

  url = ""
  try:
    plugin_path = REPO_ROOT / ".claude-plugin" / "plugin.json"
    if plugin_path.exists():
      obj = json.loads(plugin_path.read_text(encoding="utf-8"))
      if isinstance(obj, dict):
        url = str(obj.get("repository", "") or obj.get("homepage", "") or "").strip()
  except Exception:
    url = ""

  if not (url.startswith("https://github.com/") or url.startswith("http://github.com/")):
    url = ""

  _REPO_URL_CACHE = url
  return url


def _append_log(line: str) -> None:
  LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
  with LOG_PATH.open("a", encoding="utf-8") as f:
    f.write(f"[{_now_iso()}] {line}\n")


def _read_secrets() -> dict:
  cfg = _read_config()
  sec = cfg.get("secrets", {})
  if isinstance(sec, dict) and sec:
    return sec
  return _read_json(SECRETS_PATH, {})  # legacy fallback


def _write_secrets(data: dict) -> None:
  cfg = _read_config()
  cfg["secrets"] = data
  cfg["updated_at"] = _now_iso()
  _write_config(cfg)

  # Legacy/compat file (optional)
  try:
    _write_json(SECRETS_PATH, data)
    os.chmod(SECRETS_PATH, 0o600)
  except Exception:
    pass


def _set_secret(path: list[str], value: dict) -> None:
  s = _read_secrets()
  cur = s
  for k in path[:-1]:
    nxt = cur.get(k, {})
    if not isinstance(nxt, dict):
      nxt = {}
    cur[k] = nxt
    cur = nxt
  cur[path[-1]] = value
  _write_secrets(s)


def _get_secret(path: list[str]) -> dict | None:
  s = _read_secrets()
  cur: object = s
  for k in path:
    if not isinstance(cur, dict):
      return None
    cur = cur.get(k)
  return cur if isinstance(cur, dict) else None


def _config_settings() -> dict:
  cfg = _read_config()
  s = cfg.get("settings", {})
  if not isinstance(s, dict):
    s = {}
  s = _migrate_legacy_claude_theme(s)
  return _deep_merge_defaults(s, _default_settings())


def _settings_get(path: list[str], default: object) -> object:
  cur: object = _config_settings()
  for k in path:
    if not isinstance(cur, dict):
      return default
    cur = cur.get(k)
  return cur if cur is not None else default


def _settings_set(path: list[str], value: object) -> None:
  cfg = _read_config()
  s = cfg.get("settings", {})
  if not isinstance(s, dict):
    s = {}
  cur: dict = s
  for k in path[:-1]:
    nxt = cur.get(k)
    if not isinstance(nxt, dict):
      nxt = {}
      cur[k] = nxt
    cur = nxt
  cur[path[-1]] = value
  cfg["settings"] = s
  cfg["updated_at"] = _now_iso()
  _write_config(cfg)


def _env_or_config(env_name: str, *, key: str, default: str = "") -> str:
  # Env wins, then config.json `settings`, then default.
  v = _env(env_name, "")
  if v:
    return v
  s = _config_settings()
  cv = str(s.get(key, "")).strip()
  return cv or default


def _cardnews_env_overrides() -> dict[str, str]:
  # Map config `settings.cardnews.theme` into env vars consumed by render_cardnews.py.
  theme = _settings_get(["cardnews", "theme"], {})
  if not isinstance(theme, dict):
    return {}

  mapping = {
    "accent_primary": "JUSTSELL_ACCENT_PRIMARY",
    "accent_secondary": "JUSTSELL_ACCENT_SECONDARY",
    "cover_fill": "JUSTSELL_COVER_FILL",
    "panel_fill": "JUSTSELL_PANEL_FILL",
    "bg_kind": "JUSTSELL_BG_KIND",
    "bg_solid": "JUSTSELL_BG_SOLID",
    "bg_from": "JUSTSELL_BG_FROM",
    "bg_to": "JUSTSELL_BG_TO",
    "font_path": "JUSTSELL_FONT_PATH",
  }
  out: dict[str, str] = {}
  for k, env_k in mapping.items():
    v2 = str(theme.get(k, "")).strip()
    if v2:
      out[env_k] = v2
  return out


def _available_cardnews_templates() -> list[str]:
  items: list[str] = []
  # 1) Repo-shipped templates (stable; good defaults)
  tdir = REPO_ROOT / "channels" / "instagram" / "templates"
  if tdir.exists():
    for p in sorted(tdir.glob("cardnews.*.yaml")):
      try:
        rel = p.relative_to(REPO_ROOT)
        items.append(str(rel))
      except Exception:
        continue

  # 2) User templates (local-first; survive repo/plugin updates)
  # Drop files here:
  # - ~/.claude/.js/templates/instagram/<anything>.yaml|yml|json
  user_dir = JUSTSELL_HOME / "templates" / "instagram"
  if user_dir.exists():
    for p in sorted(user_dir.glob("*")):
      if not p.is_file():
        continue
      if p.suffix.lower() not in [".yaml", ".yml", ".json"]:
        continue
      items.append(str(p))

  return items


def _safe_project_slug(value: str) -> str:
  # Keep slugs simple and filesystem-safe.
  s = str(value or "").strip()
  if not s:
    raise ValueError("missing slug")
  import re

  if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}", s):
    raise ValueError("invalid slug. use [a-z0-9-], 2-63 chars")
  return s


def _list_projects() -> list[str]:
  base = PROJECTS_DIR
  if not base.exists():
    return []
  out: list[str] = []
  for p in sorted(base.iterdir()):
    if not p.is_dir():
      continue
    name = p.name
    if name in ["_template"] or name.startswith("_smoke_"):
      continue
    out.append(name)
  return out


def _onboarding_status() -> dict:
  cfg = _read_config()
  settings = _config_settings()
  secrets_data = cfg.get("secrets", {})
  if not isinstance(secrets_data, dict):
    secrets_data = {}

  cardnews = settings.get("cardnews", {})
  cardnews_ready = isinstance(cardnews, dict) and bool(str(cardnews.get("template", "")).strip() or cardnews.get("theme") or cardnews.get("fonts"))

  gemini_key = (
    _env("JUSTSELL_GEMINI_API_KEY", "")
    or _env("GEMINI_API_KEY", "")
    or str(settings.get("gemini_api_key", "")).strip()
  )
  gemini_ready = bool(str(gemini_key).strip())

  threads = secrets_data.get("threads", {})
  ig = secrets_data.get("instagram", {})
  threads_connected = isinstance(threads, dict) and bool(str(threads.get("access_token", "")).strip())
  ig_connected = isinstance(ig, dict) and bool(str(ig.get("access_token", "")).strip())
  ig_user_selected = isinstance(ig, dict) and bool(str(ig.get("ig_user_id", "")).strip())

  public_base = _env_or_config("JUSTSELL_PUBLIC_BASE_URL", key="public_base_url", default="")
  public_base_ready = bool(public_base.strip())

  projects = _list_projects()
  has_project = bool(projects)

  # A simple “existing user” heuristic: tokens exist but no cardnews defaults set.
  existing_user = (threads_connected or ig_connected) and not cardnews_ready

  steps = [
    {"id": "setup", "label": "Setup", "ok": bool(settings)},
    {"id": "cardnews", "label": "Cardnews defaults", "ok": cardnews_ready},
    {"id": "gemini", "label": "Gemini (optional)", "ok": gemini_ready},
    {"id": "threads", "label": "Threads OAuth", "ok": threads_connected},
    {"id": "instagram", "label": "Instagram OAuth", "ok": ig_connected},
    {"id": "ig_user", "label": "IG account select", "ok": ig_user_selected},
    {"id": "public_base", "label": "Public base URL", "ok": public_base_ready},
    {"id": "project", "label": "Project", "ok": has_project},
  ]

  next_hint = ""
  if not cardnews_ready:
    next_hint = "Open /connect and set template, key colors, and fonts."
  elif not threads_connected or not ig_connected:
    next_hint = "Open /connect and complete OAuth connect."
  elif ig_connected and not ig_user_selected:
    next_hint = "Open /connect and Discover accounts, then Select one ig_user_id."
  elif not has_project:
    next_hint = f"Open /connect and create a project under {PROJECTS_DIR_NAME}/<slug>."
  else:
    next_hint = "Go to / and Generate + Render. Publishing remains dry-run by default."

  return {
    "existing_user": existing_user,
    "steps": steps,
    "projects": projects[:20],
    "public_base_ready": public_base_ready,
    "next_hint": next_hint,
  }


def _http_json(method: str, url: str, *, data: dict | None = None, headers: dict | None = None) -> dict:
  body: bytes | None = None
  hdrs = {"Accept": "application/json"}
  if headers:
    hdrs.update(headers)

  if data is not None:
    encoded = "&".join([f"{k}={_urlencode(str(v))}" for k, v in data.items()]).encode("utf-8")
    body = encoded
    hdrs["Content-Type"] = "application/x-www-form-urlencoded"

  req = Request(url, method=method.upper(), data=body, headers=hdrs)
  try:
    with urlopen(req, timeout=30) as resp:
      raw = resp.read().decode("utf-8")
      return json.loads(raw) if raw else {}
  except HTTPError as e:
    raw = e.read().decode("utf-8") if hasattr(e, "read") else ""
    raise RuntimeError(f"HTTP {e.code} {url}: {raw[:1000]}") from e
  except URLError as e:
    raise RuntimeError(f"Network error {url}: {e}") from e


def _extract_error_payload(msg: str) -> dict | None:
  # Best-effort: try to parse trailing JSON from RuntimeError strings.
  s = str(msg or "")
  start = s.find("{")
  end = s.rfind("}")
  if start < 0 or end < 0 or end <= start:
    return None
  try:
    payload = json.loads(s[start : end + 1])
    return payload if isinstance(payload, dict) else None
  except Exception:
    return None


def _urlencode(s: str) -> str:
  from urllib.parse import quote

  return quote(s, safe="")


def _safe_rel_path(value: str) -> Path:
  # Only allow paths under PATH_ROOT to avoid traversal.
  p = Path(unquote(value)).expanduser()
  if p.is_absolute():
    rel = p.resolve().relative_to(PATH_ROOT)
    return rel
  rel = p
  resolved = (PATH_ROOT / rel).resolve()
  resolved.relative_to(PATH_ROOT)  # raises if outside
  return rel


def _safe_asset_path(value: str) -> Path:
  rel = _safe_rel_path(value)
  if rel.suffix.lower() != ".png":
    raise ValueError("Only .png assets are allowed")
  parts = rel.parts
  # Allow only: <projects_dir>/<project>/channels/instagram/exports/*.png
  if len(parts) < 6:
    raise ValueError("Invalid asset path")
  if parts[0] != PROJECTS_DIR_NAME:
    raise ValueError("Invalid asset path")
  if not (len(parts) >= 6 and parts[2] == "channels" and parts[3] == "instagram" and parts[4] == "exports"):
    raise ValueError("Invalid asset path")
  return rel


def _safe_project_file_path(value: str) -> Path:
  # Allow only files under the projects directory (no config/secrets reads).
  rel = _safe_rel_path(value)
  parts = rel.parts
  if len(parts) < 2:
    raise ValueError("Invalid file path")
  if parts[0] != PROJECTS_DIR_NAME:
    raise ValueError("Invalid file path")
  return rel


def _load_project_policy(project_rel: Path) -> dict:
  # Reads `<projects_dir>/<project>/CONVERSATION_POLICY.md` and parses the first ```justsell-policy JSON block.
  policy_path = (PATH_ROOT / project_rel / "CONVERSATION_POLICY.md").resolve()
  try:
    policy_path.relative_to(PATH_ROOT)
  except Exception:
    return {"mode": "DRAFT_ONLY", "policy_version": 1, "team": "marketing"}

  if not policy_path.exists():
    return {"mode": "DRAFT_ONLY", "policy_version": 1, "team": "marketing"}

  raw = policy_path.read_text(encoding="utf-8")
  start = raw.find("```justsell-policy")
  if start < 0:
    return {"mode": "DRAFT_ONLY", "policy_version": 1, "team": "marketing"}
  start = raw.find("\n", start)
  if start < 0:
    return {"mode": "DRAFT_ONLY", "policy_version": 1, "team": "marketing"}
  end = raw.find("\n```", start)
  if end < 0:
    return {"mode": "DRAFT_ONLY", "policy_version": 1, "team": "marketing"}

  block = raw[start:end].strip()
  try:
    parsed = json.loads(block)
    if not isinstance(parsed, dict):
      raise ValueError("policy is not an object")
    # Normalize minimal fields
    mode = str(parsed.get("mode", "DRAFT_ONLY")).strip().upper()
    if mode not in ["AUTO_REPLY_OK", "DRAFT_ONLY", "NO_AI"]:
      mode = "DRAFT_ONLY"
    parsed["mode"] = mode
    parsed.setdefault("team", "marketing")
    parsed.setdefault("policy_version", 1)
    return parsed
  except Exception as e:
    _append_event("policy_parse_error", {"project": str(project_rel), "error": str(e)})
    return {"mode": "DRAFT_ONLY", "policy_version": 1, "team": "marketing"}


def _policy_snapshot_for_project(project_rel: Path) -> dict:
  p = _load_project_policy(project_rel)
  return {
    "mode": p.get("mode", "DRAFT_ONLY"),
    "team": p.get("team", "marketing"),
    "policy_version": p.get("policy_version", 1),
    "disclaimer_short": p.get("disclaimer_short", ""),
  }


def _list_specs() -> list[dict]:
  specs: list[dict] = []
  projects_dir = PROJECTS_DIR
  if not projects_dir.exists():
    return specs

  for spec in projects_dir.glob("*/channels/instagram/cardnews/*"):
    if spec.suffix.lower() not in [".yaml", ".yml", ".json"]:
      continue
    try:
      mtime = spec.stat().st_mtime
    except Exception:
      mtime = 0
    rel = spec.relative_to(PATH_ROOT)
    specs.append(
      {
        "path": str(rel),
        "name": spec.name,
        "project": rel.parts[1] if len(rel.parts) > 1 else "",
        "mtime": mtime,
      }
    )

  specs.sort(key=lambda x: x["mtime"], reverse=True)
  return specs[:200]


def _exports_for_spec(spec_rel: Path) -> list[str]:
  try:
    project_dir = PROJECTS_DIR / spec_rel.parts[1]
  except Exception:
    return []
  exports_dir = project_dir / "channels" / "instagram" / "exports"
  if not exports_dir.exists():
    return []
  stem = spec_rel.stem
  out = []
  for p in sorted(exports_dir.glob(f"{stem}-*.png")):
    try:
      rel = p.relative_to(PATH_ROOT)
      out.append(str(rel))
    except Exception:
      continue
  return out


def _run(cmd: list[str], *, extra_env: dict[str, str] | None = None) -> dict:
  _append_log("RUN " + " ".join(cmd))
  started = time.time()
  try:
    env = os.environ.copy()
    if extra_env:
      env.update({k: v for k, v in extra_env.items() if str(k).strip()})
    p = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, check=False, env=env)
    dur_ms = int((time.time() - started) * 1000)
    _append_log(f"EXIT {p.returncode} ({dur_ms}ms)")
    if p.stdout:
      _append_log("STDOUT " + p.stdout.strip().replace("\n", "\\n")[:2000])
    if p.stderr:
      _append_log("STDERR " + p.stderr.strip().replace("\n", "\\n")[:2000])
    res = {"ok": p.returncode == 0, "code": p.returncode, "stdout": p.stdout, "stderr": p.stderr, "ms": dur_ms}
    _append_event("command", {"cmd": cmd, "result": {"ok": res["ok"], "code": res["code"], "ms": res["ms"]}})
    return res
  except Exception as e:
    _append_log(f"EXC {e}")
    _append_event("command_error", {"cmd": cmd, "error": str(e)})
    return {"ok": False, "code": -1, "stdout": "", "stderr": str(e), "ms": int((time.time() - started) * 1000)}


def _render_spec(spec_rel: Path) -> dict:
  project = spec_rel.parts[1] if len(spec_rel.parts) > 1 else ""
  out_dir = PROJECTS_DIR / project / "channels" / "instagram" / "exports"
  spec_abs = (PATH_ROOT / spec_rel).resolve()
  _append_event("render_start", {"spec": str(spec_rel), "out_dir": str(out_dir)})
  res = _run(
    ["python3", "scripts/render_cardnews.py", "--spec", str(spec_abs), "--out", str(out_dir)],
    extra_env=_cardnews_env_overrides(),
  )
  exports = _exports_for_spec(spec_rel)
  _append_event("render_done", {"spec": str(spec_rel), "ok": bool(res.get("ok")), "exports": exports[:10]})
  return {"result": res, "exports": exports}


def _generate_instagram(project_rel: Path, style: str, fmt: str) -> dict:
  _append_event(
    "generate_instagram_start",
    {"project": str(project_rel), "style": style, "format": fmt, "policy": _policy_snapshot_for_project(project_rel)},
  )
  project_abs = (PATH_ROOT / project_rel).resolve()
  template = _settings_get(["cardnews", "template"], "")
  template_str = str(template or "").strip()
  cmd = [
    "python3",
    "scripts/generate_drafts.py",
    "instagram-cardnews",
    "--project",
    str(project_abs),
    "--style",
    style,
    "--format",
    fmt,
  ]
  if template_str:
    cmd += ["--template", template_str]
  res = _run(cmd)
  spec_path = ""
  if res.get("stdout"):
    spec_path = res["stdout"].strip().splitlines()[-1].strip()
  _append_event(
    "generate_instagram_done",
    {"project": str(project_rel), "ok": bool(res.get("ok")), "spec": spec_path, "policy": _policy_snapshot_for_project(project_rel)},
  )
  return {"result": res, "spec": spec_path}


def _generate_threads(project_rel: Path, style: str) -> dict:
  _append_event(
    "generate_threads_start",
    {"project": str(project_rel), "style": style, "policy": _policy_snapshot_for_project(project_rel)},
  )
  project_abs = (PATH_ROOT / project_rel).resolve()
  res = _run(
    [
      "python3",
      "scripts/generate_drafts.py",
      "threads",
      "--project",
      str(project_abs),
      "--style",
      style,
    ]
  )
  out_path = ""
  if res.get("stdout"):
    out_path = res["stdout"].strip().splitlines()[-1].strip()
  _append_event(
    "generate_threads_done",
    {"project": str(project_rel), "ok": bool(res.get("ok")), "draft": out_path, "policy": _policy_snapshot_for_project(project_rel)},
  )
  return {"result": res, "draft": out_path}


def _threads_oauth_config() -> dict:
  return {
    "client_id": _env_or_config("JUSTSELL_THREADS_APP_ID", key="threads_app_id"),
    "client_secret": _env_or_config("JUSTSELL_THREADS_APP_SECRET", key="threads_app_secret"),
    "redirect_uri": _env_or_config(
      "JUSTSELL_THREADS_REDIRECT_URI",
      key="threads_redirect_uri",
      default="http://127.0.0.1:5678/oauth/threads/callback",
    ),
    "scope": _env_or_config(
      "JUSTSELL_THREADS_SCOPES",
      key="threads_scopes",
      default="threads_basic,threads_content_publish,threads_manage_insights,threads_manage_replies,threads_read_replies",
    ),
    "authorize_url": _env_or_config(
      "JUSTSELL_THREADS_AUTHORIZE_URL",
      key="threads_authorize_url",
      default="https://threads.net/oauth/authorize",
    ),
    "token_url": _env_or_config(
      "JUSTSELL_THREADS_TOKEN_URL",
      key="threads_token_url",
      default="https://graph.threads.net/oauth/access_token",
    ),
    "exchange_url": _env_or_config(
      "JUSTSELL_THREADS_EXCHANGE_URL",
      key="threads_exchange_url",
      default="https://graph.threads.net/access_token",
    ),
    "refresh_url": _env_or_config(
      "JUSTSELL_THREADS_REFRESH_URL",
      key="threads_refresh_url",
      default="https://graph.threads.net/refresh_access_token",
    ),
    "api_base": _env_or_config(
      "JUSTSELL_THREADS_API_BASE",
      key="threads_api_base",
      default="https://graph.threads.net/v1.0",
    ),
  }


def _ig_oauth_config() -> dict:
  ver = _env_or_config("JUSTSELL_GRAPH_API_VERSION", key="graph_api_version", default="v20.0")
  return {
    "client_id": _env_or_config("JUSTSELL_META_APP_ID", key="meta_app_id"),
    "client_secret": _env_or_config("JUSTSELL_META_APP_SECRET", key="meta_app_secret"),
    "redirect_uri": _env_or_config(
      "JUSTSELL_IG_REDIRECT_URI",
      key="ig_redirect_uri",
      default="http://127.0.0.1:5678/oauth/ig/callback",
    ),
    "scope": _env_or_config(
      "JUSTSELL_IG_SCOPES",
      key="ig_scopes",
      default="instagram_basic,pages_show_list,pages_read_engagement,instagram_content_publish,instagram_manage_comments",
    ),
    "dialog_url": _env_or_config(
      "JUSTSELL_META_DIALOG_OAUTH_URL",
      key="meta_dialog_oauth_url",
      default=f"https://www.facebook.com/{ver}/dialog/oauth",
    ),
    "token_url": _env_or_config(
      "JUSTSELL_META_TOKEN_URL",
      key="meta_token_url",
      default=f"https://graph.facebook.com/{ver}/oauth/access_token",
    ),
    "api_base": _env_or_config(
      "JUSTSELL_GRAPH_API_BASE",
      key="graph_api_base",
      default=f"https://graph.facebook.com/{ver}",
    ),
  }


def _threads_start_url(state: str) -> str:
  cfg = _threads_oauth_config()
  if not cfg["client_id"] or not cfg["redirect_uri"]:
    raise RuntimeError("Missing JUSTSELL_THREADS_APP_ID or JUSTSELL_THREADS_REDIRECT_URI")
  return (
    f"{cfg['authorize_url']}?"
    f"client_id={_urlencode(cfg['client_id'])}"
    f"&redirect_uri={_urlencode(cfg['redirect_uri'])}"
    f"&scope={_urlencode(cfg['scope'])}"
    f"&response_type=code"
    f"&state={_urlencode(state)}"
  )


def _ig_start_url(state: str) -> str:
  cfg = _ig_oauth_config()
  if not cfg["client_id"] or not cfg["redirect_uri"]:
    raise RuntimeError("Missing JUSTSELL_META_APP_ID or JUSTSELL_IG_REDIRECT_URI")
  return (
    f"{cfg['dialog_url']}?"
    f"client_id={_urlencode(cfg['client_id'])}"
    f"&redirect_uri={_urlencode(cfg['redirect_uri'])}"
    f"&scope={_urlencode(cfg['scope'])}"
    f"&response_type=code"
    f"&state={_urlencode(state)}"
  )


def _threads_exchange_code(code: str) -> dict:
  cfg = _threads_oauth_config()
  if not cfg["client_id"] or not cfg["client_secret"]:
    raise RuntimeError("Missing JUSTSELL_THREADS_APP_ID or JUSTSELL_THREADS_APP_SECRET")
  return _http_json(
    "POST",
    cfg["token_url"],
    data={
      "client_id": cfg["client_id"],
      "client_secret": cfg["client_secret"],
      "grant_type": "authorization_code",
      "redirect_uri": cfg["redirect_uri"],
      "code": code,
    },
  )


def _threads_exchange_long_lived(short_token: str) -> dict:
  cfg = _threads_oauth_config()
  return _http_json(
    "GET",
    f"{cfg['exchange_url']}?grant_type=th_exchange_token&client_secret={_urlencode(cfg['client_secret'])}&access_token={_urlencode(short_token)}",
  )


def _threads_refresh_long_lived(long_token: str) -> dict:
  cfg = _threads_oauth_config()
  # Based on common Threads docs pattern; keep overrideable via env.
  return _http_json(
    "GET",
    f"{cfg['refresh_url']}?grant_type=th_refresh_token&access_token={_urlencode(long_token)}",
  )


def _threads_publish_text(*, user_id: str, access_token: str, text: str) -> dict:
  cfg = _threads_oauth_config()
  base = cfg["api_base"].rstrip("/")
  create = _http_json(
    "POST",
    f"{base}/{_urlencode(user_id)}/threads",
    data={"media_type": "TEXT", "text": text, "access_token": access_token},
  )
  creation_id = str(create.get("id", "") or create.get("creation_id", "") or "").strip()
  if not creation_id:
    return {"ok": False, "error": "missing creation id", "create": create}
  time.sleep(2.0)
  publish = _http_json(
    "POST",
    f"{base}/{_urlencode(user_id)}/threads_publish",
    data={"creation_id": creation_id, "access_token": access_token},
  )
  return {"ok": True, "create": create, "publish": publish}


def _ig_discover_accounts(*, access_token: str) -> dict:
  cfg = _ig_oauth_config()
  base = cfg["api_base"].rstrip("/")
  # Try to include instagram_business_account if available.
  return _http_json(
    "GET",
    f"{base}/me/accounts?fields=id,name,instagram_business_account&access_token={_urlencode(access_token)}",
  )


def _ig_publish_carousel(
  *,
  ig_user_id: str,
  access_token: str,
  caption: str,
  image_paths: list[str],
  public_base_url: str,
) -> dict:
  cfg = _ig_oauth_config()
  base = cfg["api_base"].rstrip("/")
  children_ids: list[str] = []

  def public_url(rel_png: str) -> str:
    return public_base_url.rstrip("/") + "/asset/" + _urlencode(rel_png)

  # Create carousel item containers
  for rel_png in image_paths:
    create = _http_json(
      "POST",
      f"{base}/{_urlencode(ig_user_id)}/media",
      data={
        "image_url": public_url(rel_png),
        "is_carousel_item": "true",
        "access_token": access_token,
      },
    )
    cid = str(create.get("id", "") or "").strip()
    if not cid:
      return {"ok": False, "error": "failed to create item container", "response": create}
    children_ids.append(cid)

  # Create carousel container
  carousel = _http_json(
    "POST",
    f"{base}/{_urlencode(ig_user_id)}/media",
    data={
      "media_type": "CAROUSEL",
      "children": ",".join(children_ids),
      "caption": caption,
      "access_token": access_token,
    },
  )
  creation_id = str(carousel.get("id", "") or "").strip()
  if not creation_id:
    return {"ok": False, "error": "failed to create carousel container", "response": carousel}

  # Publish (retry a few times to allow processing)
  last_err: str | None = None
  for _ in range(6):
    time.sleep(5.0)
    try:
      published = _http_json(
        "POST",
        f"{base}/{_urlencode(ig_user_id)}/media_publish",
        data={"creation_id": creation_id, "access_token": access_token},
      )
      return {"ok": True, "children": children_ids, "carousel": carousel, "publish": published}
    except Exception as e:
      last_err = str(e)
      continue

  return {"ok": False, "error": last_err or "publish failed", "children": children_ids, "carousel": carousel}


def _html_page(title: str, body: str, *, include_preview: bool = True, left_title: str = "Instagram specs") -> bytes:
  status = _onboarding_status()
  cfg = _read_config()
  meta = cfg.get("meta", {})
  if not isinstance(meta, dict):
    meta = {}

  badge_targets = {
    "Setup": "/connect?tab=setup#setup",
    "Cardnews defaults": "/connect?tab=setup#setup",
    "Gemini (optional)": "/connect?tab=setup#setup",
    "Threads OAuth": "/connect?tab=threads#threads",
    "Instagram OAuth": "/connect?tab=instagram#instagram",
    "IG account select": "/connect?tab=instagram#instagram",
    "Public base URL": "/connect?tab=setup#setup",
    "Project": "/connect?tab=project#project",
  }
  badges = []
  for s in status.get("steps", []):
    if not isinstance(s, dict):
      continue
    ok = bool(s.get("ok"))
    label = str(s.get("label", "")).strip()
    if not label:
      continue
    badge_class = "ok" if ok else "no"
    href = badge_targets.get(label, "/connect")
    safe_label = html.escape(label)
    badges.append(f"<a class='badge guard-nav {badge_class}' href='{href}' title='Open setup section'>{safe_label}</a>")
  badge_row = "<div style='display:flex;flex-wrap:wrap;gap:8px'>" + "".join(badges) + "</div>" if badges else ""
  badge_help = "<div class='hint' style='margin-top:8px'>Status chips are clickable.</div>" if badges else ""
  hint = str(status.get("next_hint", "")).strip()
  hint_html = f"<div class='hint' style='margin-top:8px'>{hint}</div>" if hint else ""
  existing_html = ""
  if bool(status.get("existing_user")):
    existing_html = "<div class='hint' style='margin-top:8px'>Detected existing OAuth tokens. Recommended: set cardnews defaults (template, colors, fonts) in /connect Setup.</div>"

  repo_url = _plugin_repo_url()
  star_html = ""
  if repo_url and not str(meta.get("star_banner_dismissed_at", "")).strip():
    star_html = (
      "<div class='card' style='margin-top:12px;border-radius:16px'>"
      "<div class='list' style='padding:12px 14px;display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap'>"
      "<div style='display:flex;flex-direction:column;gap:2px'>"
      "<div style='font-weight:650'>Support</div>"
      f"<div class='hint'>If this tool helps, open the repository and star it: <a href='{repo_url}' target='_blank' rel='noreferrer'>{repo_url}</a></div>"
      "</div>"
      "<div style='display:flex;gap:10px;align-items:center'>"
      f"<a class='btn-link primary' href='{repo_url}' target='_blank' rel='noreferrer'>Open GitHub</a>"
      "<form method='POST' action='/api/meta/star_dismiss' style='margin:0'>"
      "<button type='submit'>Hide</button>"
      "</form>"
      "</div>"
      "</div>"
      "</div>"
    )

  wrap_class = "wrap" if include_preview else "wrap single"
  left_block = (
    f"<div class='card'><h2>{left_title}</h2><div class='list'>{body}</div></div>"
    if include_preview
    else body
  )
  preview_block = ""
  if include_preview:
    preview_block = """
    <div class="card">
      <h2>Preview</h2>
      <div class="preview">
        <div class="hint">Selected: <span id="selected">(none)</span></div>
        <div class="hint">Project: <span id="selected-project"></span></div>
        <div class="hint">Policy: <span id="policy-mode">DRAFT_ONLY</span></div>
        <div class="hint" id="policy-disclaimer"></div>
        <div class="grid2">
          <div class="field">
            <label>Instagram generate style</label>
            <select id="ig-style">
              <option value="bernays" selected>bernays</option>
              <option value="comeback">comeback</option>
              <option value="plain">plain</option>
            </select>
          </div>
          <div class="field">
            <label>Spec format</label>
            <select id="ig-format">
              <option value="json" selected>json</option>
              <option value="yaml">yaml</option>
            </select>
          </div>
        </div>
        <div style="display:flex;gap:10px">
          <button id="render-btn" class="primary" disabled>Render</button>
          <button id="gen-btn" disabled>Generate + Render</button>
        </div>
        <div id="thumbs" class="thumbs"><div class="hint">Select a spec from the left list to enable Render/Generate.</div></div>
        <div class="card" style="border-radius:14px">
          <h2>Publish</h2>
          <div class="list" style="padding-top:0">
          <div class="hint">Threads (text)</div>
            <div class="field" style="margin-top:8px">
              <label>Threads draft style</label>
              <select id="threads-style">
                <option value="bernays" selected>bernays</option>
                <option value="comeback">comeback</option>
                <option value="plain">plain</option>
              </select>
            </div>
            <textarea id="threads-text" style="width:100%;min-height:80px;background:rgba(0,0,0,0.22);border:1px solid rgba(255,255,255,0.10);border-radius:12px;color:#fff;padding:10px;resize:vertical"></textarea>
            <div style="display:flex;gap:10px;margin-top:10px;flex-wrap:wrap">
              <button onclick="generateThreadsDraft()">Generate draft</button>
              <button onclick="publishThreads(false)">Threads dry-run</button>
              <button class="primary" onclick="publishThreads(true)">Threads publish</button>
            </div>
            <div style="height:12px"></div>
            <div class="hint">Instagram (carousel)</div>
            <div class="hint">Spec: <span id="ig-spec"></span></div>
            <input id="ig-caption" placeholder="caption" style="width:100%;background:rgba(0,0,0,0.22);border:1px solid rgba(255,255,255,0.10);border-radius:12px;color:#fff;padding:10px" />
            <div style="display:flex;gap:10px;margin-top:10px;flex-wrap:wrap">
              <button onclick="publishInstagram(false)">IG dry-run</button>
              <button class="primary" onclick="publishInstagram(true)">IG publish</button>
            </div>
            <div class="hint" style="margin-top:8px">Requires: connect tokens in <a href="/connect?tab=setup#setup">/connect</a>, set <code>ig_user_id</code>, and set a public base URL (ENV <code>JUSTSELL_PUBLIC_BASE_URL</code> or config <code>settings.public_base_url</code>).</div>
          </div>
        </div>
      </div>
      <pre id="log">(logs)</pre>
    </div>
    """.strip()

  return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    :root {{
      --bg: #0b0f19;
      --panel: rgba(255,255,255,0.06);
      --border: rgba(255,255,255,0.10);
      --text: #ffffff;
      --dim: #a0a0a0;
      --accent: #ff6a2a;
    }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
      background: radial-gradient(1200px 800px at 10% 10%, rgba(255,106,42,0.18), transparent 55%),
                  radial-gradient(1000px 700px at 90% 20%, rgba(88,86,214,0.16), transparent 60%),
                  var(--bg);
      color: var(--text);
    }}
    a {{ color: inherit; }}
    header {{
      position: sticky;
      top: 0;
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      background: rgba(0,0,0,0.35);
      border-bottom: 1px solid var(--border);
      padding: 14px 18px;
      display: flex;
      gap: 14px;
      align-items: center;
      justify-content: space-between;
    }}
    .wrap {{ padding: 18px; display: grid; grid-template-columns: 1fr 420px; gap: 18px; }}
    .wrap.single {{ grid-template-columns: 1fr; }}
    .card {{
      border: 1px solid var(--border);
      background: var(--panel);
      border-radius: 16px;
      overflow: hidden;
    }}
    .card h2 {{ margin: 0; padding: 14px 14px 0; font-size: 14px; color: var(--dim); font-weight: 600; }}
    .list {{ padding: 10px 14px 14px; }}
    .row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 10px 10px;
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 12px;
      margin-top: 10px;
      background: rgba(0,0,0,0.20);
    }}
    .meta {{ display: flex; flex-direction: column; gap: 2px; }}
    .meta .name {{ font-weight: 650; }}
    .meta .sub {{ color: var(--dim); font-size: 12px; }}
    button {{
      border: 1px solid rgba(255,255,255,0.14);
      background: rgba(255,255,255,0.06);
      color: var(--text);
      padding: 8px 10px;
      border-radius: 10px;
      cursor: pointer;
      font-weight: 600;
    }}
    button.primary {{
      border-color: rgba(255,106,42,0.45);
      background: rgba(255,106,42,0.18);
    }}
    button:disabled {{ opacity: 0.5; cursor: not-allowed; }}
    a.btn-link {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border: 1px solid rgba(255,255,255,0.14);
      background: rgba(255,255,255,0.06);
      color: var(--text);
      padding: 8px 10px;
      border-radius: 10px;
      cursor: pointer;
      font-weight: 600;
      text-decoration: none;
      line-height: 1.1;
    }}
    a.btn-link.primary {{
      border-color: rgba(255,106,42,0.45);
      background: rgba(255,106,42,0.18);
    }}
    input[type="text"], input[type="password"], input[type="number"], select {{
      width: 100%;
      box-sizing: border-box;
      border: 1px solid rgba(255,255,255,0.14);
      background: rgba(0,0,0,0.25);
      color: var(--text);
      padding: 8px 10px;
      border-radius: 10px;
      outline: none;
      font-weight: 600;
    }}
    label {{ display: block; font-size: 12px; color: var(--dim); margin-bottom: 6px; }}
    .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    .grid3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }}
    .field {{ margin-top: 10px; }}
    .divider {{ margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.10); }}
    .preview {{
      padding: 14px;
      display: grid;
      gap: 12px;
    }}
    .thumbs {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }}
    img {{ width: 100%; border-radius: 14px; border: 1px solid rgba(255,255,255,0.10); background: rgba(0,0,0,0.25); }}
    pre {{
      margin: 0;
      padding: 12px;
      border-top: 1px solid var(--border);
      color: var(--dim);
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 12px;
    }}
    .hint {{ color: var(--dim); font-size: 12px; }}
    .section-title {{
      margin-top: 12px;
      margin-bottom: 6px;
      padding-left: 10px;
      border-left: 3px solid rgba(255,106,42,0.55);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.2px;
      color: rgba(255,255,255,0.90);
      text-transform: uppercase;
    }}
    .field-help {{
      margin-top: 4px;
      font-size: 11px;
      color: rgba(255,255,255,0.62);
    }}
    .field-error {{
      margin-top: 4px;
      min-height: 14px;
      font-size: 11px;
      color: #ff9f9f;
    }}
    .input-with-action {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      align-items: center;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,0.12);
      background: rgba(0,0,0,0.25);
      font-size: 12px;
      color: var(--dim);
      white-space: nowrap;
      text-decoration: none;
    }}
    .badge.ok {{ color: rgba(0,230,118,0.95); border-color: rgba(0,230,118,0.28); background: rgba(0,230,118,0.08); }}
    .badge.no {{ color: rgba(255,255,255,0.72); }}
    @media (max-width: 980px) {{
      .wrap {{ grid-template-columns: 1fr; }}
    }}
  </style>
  <script>
    async function api(path) {{
      const r = await fetch(path);
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || 'request failed');
      return j;
    }}

    async function renderSpec(specPath) {{
      const btn = document.getElementById('render-btn');
      btn.disabled = true;
      try {{
        const j = await api('/api/render?spec=' + encodeURIComponent(specPath));
        document.getElementById('log').textContent = (j.result.stdout || '') + (j.result.stderr ? '\\n' + j.result.stderr : '');
        setPreview(j.exports || []);
      }} catch (e) {{
        document.getElementById('log').textContent = String(e);
      }} finally {{
        btn.disabled = false;
      }}
    }}

    async function generateAndRender(projectPath) {{
      const btn = document.getElementById('gen-btn');
      btn.disabled = true;
      try {{
        const style = (document.getElementById('ig-style').value || 'bernays');
        const format = (document.getElementById('ig-format').value || 'json');
        const g = await api('/api/generate_instagram?project=' + encodeURIComponent(projectPath) + '&style=' + encodeURIComponent(style) + '&format=' + encodeURIComponent(format));
        const spec = g.spec || '';
        document.getElementById('selected').textContent = spec || '(none)';
        document.getElementById('ig-spec').textContent = spec || '';
        document.getElementById('ig-caption').value = (spec.split('/').pop() || '').replace(/\\.(json|ya?ml)$/,'');
        document.getElementById('log').textContent = (g.result.stdout || '') + (g.result.stderr ? '\\n' + g.result.stderr : '');
        if (spec) {{
          await renderSpec(spec);
        }}
      }} catch (e) {{
        document.getElementById('log').textContent = String(e);
      }} finally {{
        btn.disabled = false;
      }}
    }}

    async function publishThreads(confirm) {{
      const text = (document.getElementById('threads-text').value || '').trim();
      const project = (document.getElementById('selected-project').textContent || '').trim();
      if (!text) {{
        document.getElementById('log').textContent = 'Missing Threads text';
        return;
      }}
      try {{
        const j = await api('/api/threads/publish_text?text=' + encodeURIComponent(text) + '&confirm=' + (confirm ? '1' : '0') + '&project=' + encodeURIComponent(project));
        document.getElementById('log').textContent = JSON.stringify(j, null, 2);
      }} catch (e) {{
        document.getElementById('log').textContent = String(e);
      }}
    }}

    async function generateThreadsDraft() {{
      const project = (document.getElementById('selected-project').textContent || '').trim();
      const style = (document.getElementById('threads-style').value || 'bernays');
      if (!project) {{
        document.getElementById('log').textContent = 'Pick a spec (project) first';
        return;
      }}
      try {{
        const j = await api('/api/generate_threads?project=' + encodeURIComponent(project) + '&style=' + encodeURIComponent(style));
        document.getElementById('log').textContent = (j.result.stdout || '') + (j.result.stderr ? '\\n' + j.result.stderr : '');
        if (j.draft) {{
          const r = await fetch('/file/' + encodeURIComponent(j.draft));
          if (r.ok) {{
            const txt = await r.text();
            document.getElementById('threads-text').value = txt.trim();
          }}
        }}
      }} catch (e) {{
        document.getElementById('log').textContent = String(e);
      }}
    }}

    async function publishInstagram(confirm) {{
      const spec = (document.getElementById('ig-spec').textContent || '').trim();
      const caption = (document.getElementById('ig-caption').value || '').trim();
      if (!spec) {{
        document.getElementById('log').textContent = 'Pick a spec first';
        return;
      }}
      try {{
        const j = await api('/api/ig/publish_carousel?spec=' + encodeURIComponent(spec) + '&caption=' + encodeURIComponent(caption) + '&confirm=' + (confirm ? '1' : '0'));
        document.getElementById('log').textContent = JSON.stringify(j, null, 2);
      }} catch (e) {{
        document.getElementById('log').textContent = String(e);
      }}
    }}

    function setPreview(paths) {{
      const box = document.getElementById('thumbs');
      box.innerHTML = '';
      if (!paths.length) {{
        box.innerHTML = '<div class=\"hint\">No exports yet.</div>';
        return;
      }}
      for (const p of paths.slice(0, 6)) {{
        const img = document.createElement('img');
        img.src = '/file/' + encodeURIComponent(p);
        img.loading = 'lazy';
        box.appendChild(img);
      }}
    }}

    function pick(specPath, projectPath) {{
      document.getElementById('selected').textContent = specPath;
      document.getElementById('ig-spec').textContent = specPath;
      document.getElementById('ig-caption').value = (specPath.split('/').pop() || '').replace(/\\.(json|ya?ml)$/,'');
      document.getElementById('selected-project').textContent = projectPath || '';
      document.getElementById('render-btn').disabled = false;
      document.getElementById('gen-btn').disabled = false;
      document.getElementById('render-btn').onclick = () => renderSpec(specPath);
      document.getElementById('gen-btn').onclick = () => generateAndRender(projectPath);
      api('/api/exports?spec=' + encodeURIComponent(specPath)).then(j => setPreview(j.exports || [])).catch(() => setPreview([]));
      if (projectPath) {{
        api('/api/policy?project=' + encodeURIComponent(projectPath)).then(j => {{
          const p = j.policy || {{}};
          document.getElementById('policy-mode').textContent = p.mode || 'DRAFT_ONLY';
          document.getElementById('policy-disclaimer').textContent = p.disclaimer_short || '';
        }}).catch(() => {{
          document.getElementById('policy-mode').textContent = 'DRAFT_ONLY';
          document.getElementById('policy-disclaimer').textContent = '';
        }});
      }}
    }}

    function autoPickFirstSpec() {{
      const selected = (document.getElementById('selected')?.textContent || '').trim();
      if (selected && selected !== '(none)') return;
      const firstPick = document.querySelector('.list .row button.primary[onclick^="pick("]');
      if (firstPick) firstPick.click();
    }}

    function setupSecretField(inputId) {{
      const el = document.getElementById(inputId);
      if (!el) return;
      el.addEventListener('focus', () => {{
        if (el.dataset.masked === '1') {{
          el.value = '';
          el.dataset.masked = '0';
          el.type = 'password';
        }}
      }});
    }}

    function toggleSecretMask(inputId) {{
      const el = document.getElementById(inputId);
      if (!el) return;
      el.type = el.type === 'password' ? 'text' : 'password';
    }}

    function showFieldError(form, fieldName, message) {{
      const err = form.querySelector('[data-error-for=\"' + fieldName + '\"]');
      if (err) err.textContent = message || '';
    }}

    function isHexColor(value) {{
      return /^#([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/.test(value || '');
    }}

    function validateSetupFormClient(form) {{
      const errors = {{}};
      const get = (name) => (form.elements.namedItem(name)?.value || '').trim();

      const publicBase = get('public_base_url');
      if (publicBase) {{
        try {{
          const u = new URL(publicBase);
          if (!(u.protocol === 'http:' || u.protocol === 'https:')) {{
            errors.public_base_url = 'Use http:// or https:// URL.';
          }}
        }} catch (_) {{
          errors.public_base_url = 'Use valid URL.';
        }}
      }}

      const bgKind = get('cardnews_bg_kind');
      if (bgKind && bgKind !== 'solid' && bgKind !== 'gradient') {{
        errors.cardnews_bg_kind = 'Choose solid or gradient.';
      }}

      const colorFields = [
        'cardnews_accent_primary',
        'cardnews_accent_secondary',
        'cardnews_cover_fill',
        'cardnews_panel_fill',
        'cardnews_bg_solid',
        'cardnews_bg_from',
        'cardnews_bg_to',
      ];
      for (const k of colorFields) {{
        const v = get(k);
        if (v && !isHexColor(v)) errors[k] = 'Use HEX like #RRGGBB.';
      }}

      if (bgKind === 'gradient') {{
        if (!get('cardnews_bg_from')) errors.cardnews_bg_from = 'Required for gradient.';
        if (!get('cardnews_bg_to')) errors.cardnews_bg_to = 'Required for gradient.';
      }}

      for (const name of ['public_base_url', 'cardnews_bg_kind', ...colorFields]) {{
        showFieldError(form, name, errors[name] || '');
      }}
      return errors;
    }}

    function setupConfigFormUX() {{
      const form = document.querySelector('form[action=\"/api/config/update\"]');
      if (!form) return;
      const unsaved = document.getElementById('unsaved-indicator');
      let dirty = false;
      const markDirty = () => {{
        dirty = true;
        if (unsaved) unsaved.style.display = 'block';
      }};
      const clearDirty = () => {{
        dirty = false;
        if (unsaved) unsaved.style.display = 'none';
      }};

      form.addEventListener('input', () => {{
        markDirty();
        validateSetupFormClient(form);
      }});
      form.addEventListener('change', () => {{
        markDirty();
        validateSetupFormClient(form);
      }});
      form.addEventListener('submit', (e) => {{
        const errs = validateSetupFormClient(form);
        if (Object.keys(errs).length > 0) {{
          e.preventDefault();
          return;
        }}
        clearDirty();
      }});

      window.addEventListener('beforeunload', (e) => {{
        if (!dirty) return;
        e.preventDefault();
        e.returnValue = '';
      }});

      document.querySelectorAll('a.guard-nav').forEach((a) => {{
        a.addEventListener('click', (e) => {{
          if (!dirty) return;
          const ok = window.confirm('Unsaved changes will be lost. Move anyway?');
          if (!ok) e.preventDefault();
        }});
      }});
    }}

    window.addEventListener('DOMContentLoaded', () => {{
      autoPickFirstSpec();
      setupSecretField('threads_app_secret');
      setupSecretField('meta_app_secret');
      setupSecretField('gemini_api_key');
      setupConfigFormUX();
    }});
  </script>
</head>
<body>
  <header>
    <div style="display:flex;flex-direction:column;gap:2px">
      <div style="font-weight:800;letter-spacing:0.2px">JustSellConsole</div>
      <div class="hint">preview · generate · render · jobs</div>
    </div>
    <div style="display:flex;gap:10px;align-items:center">
      <a class="hint" href="/connect">connect</a>
      <a class="hint" href="/jobs">jobs</a>
      <a class="hint" href="/events">events</a>
      <a class="hint" href="/chat">chat</a>
      <a class="hint" href="/logs">logs</a>
    </div>
  </header>
  <div style="padding:14px 18px;border-bottom:1px solid rgba(255,255,255,0.10);background:rgba(0,0,0,0.18)">
    {badge_row}
    {badge_help}
    {hint_html}
    {existing_html}
    {star_html}
  </div>
  <div class="{wrap_class}">
    {left_block}
    {preview_block}
  </div>
</body>
</html>""".encode("utf-8")


def _spec_rows_html(specs: list[dict]) -> str:
  rows = []
  for s in specs:
    spec_path = s["path"]
    project = s.get("project", "")
    project_path = f"{PROJECTS_DIR_NAME}/{project}" if project else ""
    rows.append(
      f"""
      <div class="row">
        <div class="meta">
          <div class="name">{s.get("name","")}</div>
          <div class="sub">{spec_path}</div>
        </div>
        <div style="display:flex;gap:10px">
          <button class="primary" onclick="pick('{spec_path}','{project_path}')">Pick</button>
        </div>
      </div>
      """.strip()
    )
  if not rows:
    return f'<div class="hint">No specs found under {PROJECTS_DIR_NAME}/*/channels/instagram/cardnews</div>'
  return "\n".join(rows)


def _connect_page(*, qs: dict[str, list[str]] | None = None) -> bytes:
  threads_cfg = _threads_oauth_config()
  ig_cfg = _ig_oauth_config()
  t = _get_secret(["threads"]) or {}
  ig = _get_secret(["instagram"]) or {}
  settings = _config_settings()
  cardnews = _settings_get(["cardnews"], {})
  if not isinstance(cardnews, dict):
    cardnews = {}
  card_theme = cardnews.get("theme", {})
  if not isinstance(card_theme, dict):
    card_theme = {}
  card_fonts = cardnews.get("fonts", {})
  if not isinstance(card_fonts, dict):
    card_fonts = {}
  selected_template = str(cardnews.get("template", "")).strip()
  templates = _available_cardnews_templates()
  saved_notice = bool(qs and str((qs.get("saved", [""])[0] or "")).strip() == "1")
  tab_raw = str((qs.get("tab", ["setup"])[0] or "setup")).strip().lower() if qs else "setup"
  allowed_tabs = {"setup", "project", "threads", "instagram"}
  selected_tab = tab_raw if tab_raw in allowed_tabs else "setup"
  errors_map: dict[str, str] = {}
  if qs:
    errors_raw = str((qs.get("errors", [""])[0] or "")).strip()
    if errors_raw:
      try:
        parsed_errors = json.loads(unquote(errors_raw))
        if isinstance(parsed_errors, dict):
          errors_map = {str(k): str(v) for k, v in parsed_errors.items() if str(v).strip()}
      except Exception:
        errors_map = {}

  def masked(key: str) -> str:
    v = str(settings.get(key, "")).strip()
    if not v:
      return "(unset)"
    lk = key.lower()
    if ("secret" in lk) or ("api_key" in lk) or lk.endswith("_key"):
      return "(set)"
    return v

  def masked_secret_value(key: str) -> str:
    return "********" if masked(key) == "(set)" else ""

  def theme_val(k: str, fallback: str = "") -> str:
    return str(card_theme.get(k, fallback)).strip()

  def font_val(k: str, fallback: str = "") -> str:
    return str(card_fonts.get(k, fallback)).strip()

  def fmt_exp(v: object) -> str:
    s = str(v or "").strip()
    return s if s else "(unknown)"

  template_opts = "\n".join(
    [
      f"<option value='{p}' {'selected' if p == selected_template else ''}>{p}</option>"
      for p in templates
    ]
  )
  bg_kind_value = theme_val("bg_kind", "solid") or "solid"
  font_name_options = "\n".join(
    [
      "<option value='Pretendard Bold'></option>",
      "<option value='Pretendard Regular'></option>",
      "<option value='GDmarket Bold'></option>",
      "<option value='Noto Sans KR Bold'></option>",
      "<option value='Noto Sans KR Regular'></option>",
    ]
  )
  def field_error(name: str) -> str:
    msg = str(errors_map.get(name, "")).strip()
    return f"<div class='field-error' data-error-for='{name}'>{html.escape(msg)}</div>"

  tab_buttons = "\n".join(
    [
      f"<a class='btn-link guard-nav {'primary' if selected_tab == t else ''}' href='/connect?tab={t}#{t}'>{label}</a>"
      for t, label in [
        ("setup", "Setup"),
        ("project", "Project"),
        ("threads", "Threads"),
        ("instagram", "Instagram"),
      ]
    ]
  )

  projects = _list_projects()
  project_rows = []
  for slug in projects[:30]:
    project_rows.append(
      "<div class='row'>"
      f"<div class='meta'><div class='name'>{slug}</div><div class='sub'>{PROJECTS_DIR_NAME}/{slug}</div></div>"
      f"<div style='display:flex;gap:10px;flex-wrap:wrap'><a class='btn-link' href='/?project={PROJECTS_DIR_NAME}/{slug}'>Open</a></div>"
      "</div>"
    )
  project_list_html = "<div class='divider hint'>Projects</div>" + ("\n".join(project_rows) if project_rows else "<div class='hint'>(none)</div>")

  ig_accounts_html = ""
  if qs and str((qs.get("ig_discover", [""])[0] or "")).strip() == "1":
    token = str(ig.get("access_token", "")).strip()
    if token:
      try:
        disc = _ig_discover_accounts(access_token=token)
        pages = disc.get("data", [])
        rows: list[str] = []
        if isinstance(pages, list):
          for p in pages[:40]:
            if not isinstance(p, dict):
              continue
            page_name = str(p.get("name", "")).strip()
            iba = p.get("instagram_business_account", {})
            ig_id = str(iba.get("id", "")).strip() if isinstance(iba, dict) else ""
            if not ig_id:
              continue
            rows.append(
              "<div class='row'>"
              f"<div class='meta'><div class='name'>{page_name or 'Instagram account'}</div>"
              f"<div class='sub'>ig_user_id: {ig_id}</div></div>"
              f"<div style='display:flex;gap:10px'><a class='btn-link primary' href='/api/ig/set_user?ig_user_id={_urlencode(ig_id)}'>Select</a></div>"
              "</div>"
            )
        if rows:
          ig_accounts_html = "<div class='divider hint'>Discovered Instagram accounts</div>" + "\n".join(rows)
        else:
          ig_accounts_html = "<div class='divider hint'>Discovered Instagram accounts</div><div class='hint'>(none found)</div>"
      except Exception as e:
        ig_accounts_html = "<div class='divider hint'>Discovered Instagram accounts</div>" + f"<div class='hint'>Error: {str(e)}</div>"
    else:
      ig_accounts_html = "<div class='divider hint'>Discovered Instagram accounts</div><div class='hint'>Connect Instagram first.</div>"

  body = f"""
  <div class="card" style="padding:14px;margin-bottom:14px">
    <h2 style="padding:0;margin:0 0 8px 0">Sections</h2>
    <div class="hint">One section per view. Choose where to work.</div>
    <div style="margin-top:10px;display:flex;gap:10px;flex-wrap:wrap">
      {tab_buttons}
    </div>
  </div>

  <div id="setup" class="card" style="padding:14px;display:{"block" if selected_tab == "setup" else "none"}">
    <h2 style="padding:0;margin:0 0 8px 0">Setup</h2>
    {"<div style='margin:8px 0 10px;padding:10px 12px;border:1px solid rgba(37,99,235,0.28);border-radius:10px;background:rgba(37,99,235,0.08);font-size:12px;color:rgba(37,99,235,0.95);font-weight:700'>Saved. Setup values were updated.</div>" if saved_notice else ""}
    <div class="hint">Config: <code>~/.claude/.js/config.json</code> (respects <code>CLAUDE_CONFIG_DIR</code>)</div>
    <div class="hint">Custom templates: put YAML/JSON files in <code>~/.claude/.js/templates/instagram/</code> and they appear in the dropdown.</div>
    <form method="POST" action="/api/config/update" style="margin-top:12px">
      <div class="hint">Edit fields, then click <b>Save setup</b>. Nothing is applied until save.</div>
      <div id="unsaved-indicator" class="hint" style="display:none;margin-top:6px;color:#ffcc8a">Unsaved changes</div>
      <div style="margin-top:10px;display:flex;gap:10px;flex-wrap:wrap">
        <button class="primary" type="submit">Save setup</button>
        <a class="btn-link" href="/api/config">View config (redacted)</a>
      </div>

      <div class="section-title">1. Runtime + Template</div>
      <div class="grid2">
        <div class="field">
          <label>public_base_url (required for Instagram publish)</label>
          <input type="text" name="public_base_url" value="{masked("public_base_url") if masked("public_base_url") != "(unset)" else ""}" placeholder="https://xxxxx.ngrok.app" />
          <div class="field-help">Public URL where exported images are reachable.</div>
          {field_error("public_base_url")}
        </div>
        <div class="field">
          <label>Instagram cardnews template</label>
          <select name="cardnews_template">
            <option value="">(keep current)</option>
            {template_opts}
          </select>
          <div class="field-help">Selector field. Pick one template file.</div>
        </div>
      </div>

      <div class="section-title">2. Card Colors</div>
      <div class="hint">Saved to config. Renderer ENV can still override.</div>
      <div class="grid3">
        <div class="field"><label>accent_primary</label><input type="text" name="cardnews_accent_primary" value="{theme_val("accent_primary")}" placeholder="#2563EB" />{field_error("cardnews_accent_primary")}</div>
        <div class="field"><label>accent_secondary</label><input type="text" name="cardnews_accent_secondary" value="{theme_val("accent_secondary")}" placeholder="#0F172A" />{field_error("cardnews_accent_secondary")}</div>
        <div class="field"><label>cover_fill</label><input type="text" name="cardnews_cover_fill" value="{theme_val("cover_fill")}" placeholder="#F3F8FF" />{field_error("cardnews_cover_fill")}</div>
      </div>
      <div class="grid3">
        <div class="field"><label>panel_fill</label><input type="text" name="cardnews_panel_fill" value="{theme_val("panel_fill")}" placeholder="#FFFFFF" />{field_error("cardnews_panel_fill")}</div>
        <div class="field">
          <label>bg_kind</label>
          <select name="cardnews_bg_kind">
            <option value="solid" {"selected" if bg_kind_value == "solid" else ""}>solid</option>
            <option value="gradient" {"selected" if bg_kind_value == "gradient" else ""}>gradient</option>
          </select>
          <div class="field-help">Selector field. Do not type this manually.</div>
          {field_error("cardnews_bg_kind")}
        </div>
        <div class="field"><label>bg_solid</label><input type="text" name="cardnews_bg_solid" value="{theme_val("bg_solid")}" placeholder="#FFFFFF" />{field_error("cardnews_bg_solid")}</div>
      </div>
      <div class="grid2">
        <div class="field"><label>bg_from</label><input type="text" name="cardnews_bg_from" value="{theme_val("bg_from")}" placeholder="#FFFFFF" />{field_error("cardnews_bg_from")}</div>
        <div class="field"><label>bg_to</label><input type="text" name="cardnews_bg_to" value="{theme_val("bg_to")}" placeholder="#F4F7FB" />{field_error("cardnews_bg_to")}</div>
      </div>

      <div class="section-title">3. Fonts</div>
      <div class="hint">Text input with autocomplete suggestions. You can type custom font names.</div>
      <datalist id="font-name-options">
        {font_name_options}
      </datalist>
      <div class="grid3">
        <div class="field">
          <label>title_name</label>
          <input type="text" list="font-name-options" name="cardnews_title_name" value="{font_val("title_name")}" placeholder="Pretendard Bold" />
          <div class="field-help">Input field (custom value allowed).</div>
        </div>
        <div class="field">
          <label>body_name</label>
          <input type="text" list="font-name-options" name="cardnews_body_name" value="{font_val("body_name")}" placeholder="Pretendard Regular" />
          <div class="field-help">Input field (custom value allowed).</div>
        </div>
        <div class="field">
          <label>footer_name</label>
          <input type="text" list="font-name-options" name="cardnews_footer_name" value="{font_val("footer_name")}" placeholder="Pretendard Regular" />
          <div class="field-help">Input field (custom value allowed).</div>
        </div>
      </div>

      <div class="section-title">4. OAuth App Settings</div>
      <div class="hint">Secret fields show masked placeholder when already configured.</div>
      <div class="grid2">
        <div class="field"><label>threads_app_id</label><input type="text" name="threads_app_id" value="{masked("threads_app_id") if masked("threads_app_id") != "(unset)" else ""}" /></div>
        <div class="field">
          <label>threads_app_secret</label>
          <div class="input-with-action">
            <input id="threads_app_secret" type="password" name="threads_app_secret" data-masked="{"1" if masked_secret_value("threads_app_secret") else "0"}" value="{masked_secret_value("threads_app_secret")}" placeholder="(unset)" />
            <button type="button" onclick="toggleSecretMask('threads_app_secret')" aria-label="Toggle threads app secret visibility">View</button>
          </div>
        </div>
      </div>
      <div class="grid2">
        <div class="field"><label>meta_app_id</label><input type="text" name="meta_app_id" value="{masked("meta_app_id") if masked("meta_app_id") != "(unset)" else ""}" /></div>
        <div class="field">
          <label>meta_app_secret</label>
          <div class="input-with-action">
            <input id="meta_app_secret" type="password" name="meta_app_secret" data-masked="{"1" if masked_secret_value("meta_app_secret") else "0"}" value="{masked_secret_value("meta_app_secret")}" placeholder="(unset)" />
            <button type="button" onclick="toggleSecretMask('meta_app_secret')" aria-label="Toggle meta app secret visibility">View</button>
          </div>
        </div>
      </div>
      <div class="field">
        <label>graph_api_version</label>
        <input type="text" name="graph_api_version" value="{masked("graph_api_version") if masked("graph_api_version") != "(unset)" else ""}" placeholder="v20.0" />
      </div>

      <div class="section-title">5. Gemini (Optional)</div>
      <div class="grid2">
        <div class="field">
          <label>gemini_api_key</label>
          <div class="input-with-action">
            <input id="gemini_api_key" type="password" name="gemini_api_key" data-masked="{"1" if masked_secret_value("gemini_api_key") else "0"}" value="{masked_secret_value("gemini_api_key")}" placeholder="(unset)" />
            <button type="button" onclick="toggleSecretMask('gemini_api_key')" aria-label="Toggle gemini api key visibility">View</button>
          </div>
        </div>
        <div class="field"><label>gemini_monthly_budget_usd</label><input type="number" step="0.01" min="0" name="gemini_monthly_budget_usd" value="{str(settings.get("gemini_monthly_budget_usd", "")).strip()}" placeholder="0" /></div>
      </div>

      <div style="margin-top:12px;display:flex;gap:10px;flex-wrap:wrap">
        <button class="primary" type="submit">Save setup</button>
      </div>
    </form>

    <div class="divider hint">Presets</div>
    <div class="hint">Use presets to fill template, key colors, and fonts. You can edit before saving.</div>
    <div style="margin-top:10px;display:flex;gap:10px;flex-wrap:wrap">
      <button type="button" class="primary" onclick="applyPreset('claude')">Claude-like (default)</button>
      <button type="button" onclick="applyPreset('boc')">BOC-like</button>
    </div>
  </div>

  <div id="project" class="card" style="padding:14px;margin-top:14px;display:{"block" if selected_tab == "project" else "none"}">
    <h2 style="padding:0;margin:0 0 8px 0">Project</h2>
    <div class="hint">Projects directory: <code>{str(PROJECTS_DIR)}</code></div>
    <div class="hint">Template source (plugin): <code>{str(REPO_ROOT / "projects" / "_template")}</code></div>
    <form method="POST" action="/api/project/create" style="margin-top:12px">
      <div class="grid2">
        <div class="field">
          <label>project slug</label>
          <input type="text" name="slug" placeholder="example: my-product" />
        </div>
        <div class="field" style="display:flex;align-items:end">
          <button class="primary" type="submit">Create</button>
        </div>
      </div>
    </form>
    {project_list_html}
  </div>

  <div id="threads" class="card" style="padding:14px;display:{"block" if selected_tab == "threads" else "none"}">
    <h2 style="padding:0;margin:0 0 8px 0">Threads</h2>
    <div class="hint">status: {"connected" if t.get("access_token") else "not connected"}</div>
    <div class="hint">user_id: {t.get("user_id","(none)")}</div>
    <div class="hint">expires_at: {fmt_exp(t.get("expires_at"))}</div>
    <div style="margin-top:10px;display:flex;gap:10px;flex-wrap:wrap">
      <a class="btn-link primary" href="/oauth/threads/start">Connect Threads (OAuth)</a>
      <a class="btn-link" href="/api/threads/refresh">Refresh token</a>
    </div>
    <pre style="margin-top:12px">ENV required:
JUSTSELL_THREADS_APP_ID
JUSTSELL_THREADS_APP_SECRET
JUSTSELL_THREADS_REDIRECT_URI (default http://127.0.0.1:5678/oauth/threads/callback)
JUSTSELL_THREADS_SCOPES (default {threads_cfg.get("scope","")})
    </pre>
  </div>

  <div id="instagram" class="card" style="padding:14px;margin-top:14px;display:{"block" if selected_tab == "instagram" else "none"}">
    <h2 style="padding:0;margin:0 0 8px 0">Instagram (Graph)</h2>
    <div class="hint">status: {"connected" if ig.get("access_token") else "not connected"}</div>
    <div class="hint">expires_at: {fmt_exp(ig.get("expires_at"))}</div>
    <div class="hint">ig_user_id: {ig.get("ig_user_id","(unset)")}</div>
    <div style="margin-top:10px;display:flex;gap:10px;flex-wrap:wrap">
      <a class="btn-link primary" href="/oauth/ig/start">Connect Instagram (OAuth)</a>
      <a class="btn-link guard-nav" href="/connect?tab=instagram&ig_discover=1#instagram">Discover accounts</a>
    </div>
    {ig_accounts_html}
    <div class="hint" style="margin-top:10px">Publishing carousels requires a public URL. Set a tunnel base URL (ENV <code>JUSTSELL_PUBLIC_BASE_URL</code> or Setup form <code>public_base_url</code>).</div>
    <pre style="margin-top:12px">ENV required:
JUSTSELL_META_APP_ID
JUSTSELL_META_APP_SECRET
JUSTSELL_IG_REDIRECT_URI (default http://127.0.0.1:5678/oauth/ig/callback)
JUSTSELL_IG_SCOPES (default {ig_cfg.get("scope","")})
JUSTSELL_GRAPH_API_VERSION (default v20.0)
    </pre>
  </div>

  <script>
    function setValue(name, value) {{
      const el = document.querySelector('[name=\"' + name + '\"]');
      if (!el) return;
      el.value = value;
    }}
    function applyPreset(kind) {{
      if (kind === 'boc') {{
        setValue('cardnews_template', 'channels/instagram/templates/cardnews.boc_like.yaml');
        setValue('cardnews_accent_primary', '#00E676');
        setValue('cardnews_accent_secondary', '#111111');
        setValue('cardnews_cover_fill', '#00E676');
        setValue('cardnews_panel_fill', '#2B2B2B');
        setValue('cardnews_bg_kind', 'solid');
        setValue('cardnews_bg_solid', '#2B2B2B');
        setValue('cardnews_bg_from', '');
        setValue('cardnews_bg_to', '');
        setValue('cardnews_title_name', 'GDmarket Bold');
        setValue('cardnews_body_name', 'Pretendard Regular');
        setValue('cardnews_footer_name', 'Pretendard Regular');
      }} else if (kind === 'claude') {{
        setValue('cardnews_template', 'channels/instagram/templates/cardnews.claude_code_like.yaml');
        setValue('cardnews_accent_primary', '#2563EB');
        setValue('cardnews_accent_secondary', '#0F172A');
        setValue('cardnews_cover_fill', '#F3F8FF');
        setValue('cardnews_panel_fill', '#FFFFFF');
        setValue('cardnews_bg_kind', 'solid');
        setValue('cardnews_bg_solid', '#FFFFFF');
        setValue('cardnews_bg_from', '');
        setValue('cardnews_bg_to', '');
        setValue('cardnews_title_name', 'Pretendard Bold');
        setValue('cardnews_body_name', 'Pretendard Regular');
        setValue('cardnews_footer_name', 'Pretendard Regular');
      }}
    }}
  </script>
  """.strip()
  return _html_page("connect", body, include_preview=False, left_title="Settings")


def _events_page() -> bytes:
  ev_path = _event_path("events")
  raw = ev_path.read_text(encoding="utf-8") if ev_path.exists() else ""
  pre = (
        "<div class='hint'>Events: <code>~/.claude/.js/console/events/events-YYYY-MM-DD.jsonl</code></div>"
    "<pre style='margin:0;padding:12px;border:1px solid rgba(255,255,255,0.10);border-radius:12px;white-space:pre-wrap'>"
    + (raw[-12000:] if raw else "(empty)")
    + "</pre>"
  )
  return _html_page("events", pre)


@dataclass(frozen=True)
class JobsConfig:
  jobs: list[dict]


def _load_jobs() -> JobsConfig:
  cfg_path = REPO_ROOT / "apps" / "justsell_console" / "config" / "jobs.json"
  cfg = _read_json(cfg_path, {"jobs": []})
  jobs = cfg.get("jobs", [])
  if not isinstance(jobs, list):
    jobs = []
  return JobsConfig(jobs=jobs)


def _weekday3(dt: datetime) -> str:
  return ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"][dt.weekday()]


def _is_due(job: dict, now: datetime, last_run_iso: str | None) -> bool:
  schedule = job.get("schedule", {})
  if not isinstance(schedule, dict):
    return False
  kind = str(schedule.get("kind", "")).strip().lower()
  if kind != "weekly":
    return False

  days = schedule.get("days", [])
  if not isinstance(days, list) or _weekday3(now) not in [str(d).upper() for d in days]:
    return False

  hour = int(schedule.get("hour", 0))
  minute = int(schedule.get("minute", 0))

  # Due if we're past scheduled time and haven't run today.
  if now.hour < hour or (now.hour == hour and now.minute < minute):
    return False

  if not last_run_iso:
    return True
  try:
    last = datetime.fromisoformat(last_run_iso.replace("Z", "+00:00")).astimezone(now.tzinfo)
  except Exception:
    return True
  return last.date() != now.date()


def _execute_job(job: dict) -> dict:
  action = job.get("action", {})
  if not isinstance(action, dict):
    return {"ok": False, "error": "invalid action"}

  kind = str(action.get("kind", "")).strip()
  if kind == "generate_instagram_and_render":
    project = str(action.get("project", "")).strip()
    style = str(action.get("style", "bernays")).strip()
    fmt = str(action.get("format", "json")).strip()
    if not project:
      return {"ok": False, "error": "missing project"}
    project_rel = _safe_rel_path(project)
    gen = _generate_instagram(project_rel, style=style, fmt=fmt)
    spec = str(gen.get("spec", "")).strip()
    if not spec:
      return {"ok": False, "error": "generate failed", "gen": gen}
    spec_rel = _safe_rel_path(spec)
    rend = _render_spec(spec_rel)
    return {"ok": True, "gen": gen, "render": rend}

  if kind == "generate_threads_draft":
    project = str(action.get("project", "")).strip()
    style = str(action.get("style", "bernays")).strip()
    if not project:
      return {"ok": False, "error": "missing project"}
    project_rel = _safe_rel_path(project)
    project_abs = (PATH_ROOT / project_rel).resolve()
    res = _run(["python3", "scripts/generate_drafts.py", "threads", "--project", str(project_abs), "--style", style])
    out_path = ""
    if res.get("stdout"):
      out_path = res["stdout"].strip().splitlines()[-1].strip()
    return {"ok": bool(res.get("ok")), "draft": out_path, "result": res}

  return {"ok": False, "error": f"unknown action kind: {kind}"}


class JobRunner(threading.Thread):
  daemon = True

  def __init__(self) -> None:
    super().__init__()
    self._stop = threading.Event()

  def stop(self) -> None:
    self._stop.set()

  def run(self) -> None:
    while not self._stop.is_set():
      try:
        cfg = _load_jobs()
        state = _read_json(STATE_PATH, {})
        last_runs = state.get("last_runs", {})
        if not isinstance(last_runs, dict):
          last_runs = {}

        now = datetime.now().astimezone()
        for job in cfg.jobs:
          if not isinstance(job, dict):
            continue
          if not job.get("enabled", False):
            continue
          job_id = str(job.get("id", "")).strip()
          if not job_id:
            continue
          last = str(last_runs.get(job_id, "")).strip() or None
          if not _is_due(job, now, last):
            continue

          _append_log(f"JOB_START {job_id}")
          _append_jsonl(_event_path("jobs"), {"ts": _now_iso(), "job_id": job_id, "event": "start"})
          _append_event("job_start", {"job_id": job_id, "job": job})
          res = _execute_job(job)
          _append_log(f"JOB_DONE {job_id} ok={res.get('ok')}")
          _append_jsonl(
            _event_path("jobs"),
            {"ts": _now_iso(), "job_id": job_id, "event": "done", "ok": bool(res.get("ok"))},
          )
          _append_event("job_done", {"job_id": job_id, "ok": bool(res.get("ok"))})
          last_runs[job_id] = _now_iso()
          state["last_runs"] = last_runs
          _write_json(STATE_PATH, state)

      except Exception as e:
        _append_log(f"JOB_LOOP_ERR {e}")
        _append_event("job_loop_error", {"error": str(e)})
      self._stop.wait(30.0)


class Handler(BaseHTTPRequestHandler):
  server_version = "JustSellConsole/0.1"

  def _send_json(self, status: int, payload: dict) -> None:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    self.send_response(status)
    self.send_header("Content-Type", "application/json; charset=utf-8")
    self.send_header("Content-Length", str(len(raw)))
    self.end_headers()
    self.wfile.write(raw)

  def _send_bytes(self, status: int, content_type: str, raw: bytes) -> None:
    self.send_response(status)
    self.send_header("Content-Type", content_type)
    self.send_header("Content-Length", str(len(raw)))
    self.end_headers()
    self.wfile.write(raw)

  def do_GET(self) -> None:  # noqa: N802
    parsed = urlparse(self.path)
    path = parsed.path
    qs = parse_qs(parsed.query)

    # Basic request log (no query string by default)
    _append_event("http_get", {"path": path})

    if path == "/":
      specs = _list_specs()
      body = _spec_rows_html(specs)
      self._send_bytes(200, "text/html; charset=utf-8", _html_page("JustSellConsole", body))
      return

    if path == "/jobs":
      cfg_path = REPO_ROOT / "apps" / "justsell_console" / "config" / "jobs.json"
      state = _read_json(STATE_PATH, {"last_runs": {}})
      cfg = _read_json(cfg_path, {"jobs": []})
      raw = (
        "<div class='hint'>Edit jobs in <code>apps/justsell_console/config/jobs.json</code></div>"
        "<pre style='margin:0;padding:12px;border:1px solid rgba(255,255,255,0.10);border-radius:12px;white-space:pre-wrap'>"
        + json.dumps({"config": cfg, "state": state}, ensure_ascii=False, indent=2)
        + "</pre>"
      )
      self._send_bytes(200, "text/html; charset=utf-8", _html_page("jobs", raw))
      return

    if path == "/connect":
      self._send_bytes(200, "text/html; charset=utf-8", _connect_page(qs=qs))
      return

    if path == "/events":
      self._send_bytes(200, "text/html; charset=utf-8", _events_page())
      return

    if path == "/api/config":
      cfg = _read_config()
      out = {"version": cfg.get("version", 1), "settings": _config_settings(), "meta": cfg.get("meta", {}), "updated_at": cfg.get("updated_at", "")}
      self._send_json(200, _redact(out) if isinstance(out, dict) else {"error": "invalid"})
      return

    if path == "/api/onboarding":
      self._send_json(200, _onboarding_status())
      return

    if path == "/api/projects":
      self._send_json(200, {"projects": _list_projects()})
      return

    if path == "/logs":
      raw = LOG_PATH.read_text(encoding="utf-8") if LOG_PATH.exists() else ""
      pre = (
        "<div class='hint'>Logs: <code>~/.claude/.js/console/console.log</code></div>"
        "<pre style='margin:0;padding:12px;border:1px solid rgba(255,255,255,0.10);border-radius:12px;white-space:pre-wrap'>"
        + (raw[-12000:] if raw else "(empty)")
        + "</pre>"
      )
      self._send_bytes(200, "text/html; charset=utf-8", _html_page("logs", pre))
      return

    if path == "/chat":
      chat_path = _event_path("chat")
      raw = chat_path.read_text(encoding="utf-8") if chat_path.exists() else ""
      pre = (
        "<div class='hint'>Chat log: <code>~/.claude/.js/console/events/chat-YYYY-MM-DD.jsonl</code></div>"
        "<pre style='margin:0;padding:12px;border:1px solid rgba(255,255,255,0.10);border-radius:12px;white-space:pre-wrap'>"
        + (raw[-12000:] if raw else "(empty)")
        + "</pre>"
      )
      self._send_bytes(200, "text/html; charset=utf-8", _html_page("chat", pre))
      return

    if path.startswith("/file/"):
      rel = path[len("/file/") :]
      try:
        rel_path = _safe_project_file_path(rel)
      except Exception:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid path"})
        return
      fs = (PATH_ROOT / rel_path).resolve()
      try:
        fs.relative_to(PATH_ROOT)
      except Exception:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid path"})
        return
      if not fs.exists() or not fs.is_file():
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
        return
      suf = fs.suffix.lower()
      if suf == ".png":
        self._send_bytes(200, "image/png", fs.read_bytes())
        return
      if suf in [".md", ".txt", ".json", ".yaml", ".yml"]:
        self._send_bytes(200, "text/plain; charset=utf-8", fs.read_bytes())
        return
      self._send_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "unsupported file type"})
      return

    if path.startswith("/asset/"):
      rel = path[len("/asset/") :]
      try:
        rel_path = _safe_asset_path(rel)
      except Exception:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid asset path"})
        return
      fs = (PATH_ROOT / rel_path).resolve()
      if not fs.exists() or not fs.is_file():
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
        return
      self._send_bytes(200, "image/png", fs.read_bytes())
      return

    if path == "/oauth/threads/start":
      state = secrets.token_urlsafe(18)
      st = _read_json(STATE_PATH, {})
      states = st.get("oauth_states", {})
      if not isinstance(states, dict):
        states = {}
      states[state] = {"kind": "threads", "created_at": _now_iso()}
      st["oauth_states"] = states
      _write_json(STATE_PATH, st)
      try:
        url = _threads_start_url(state)
      except Exception as e:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(e)})
        return
      self.send_response(302)
      self.send_header("Location", url)
      self.end_headers()
      return

    if path == "/oauth/threads/callback":
      code = (qs.get("code", [""])[0] or "").strip()
      state = (qs.get("state", [""])[0] or "").strip()
      if not code or not state:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "missing code/state"})
        return
      st = _read_json(STATE_PATH, {})
      states = st.get("oauth_states", {})
      if not isinstance(states, dict) or state not in states:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid state"})
        return
      try:
        tok = _threads_exchange_code(code)
        short = str(tok.get("access_token", "")).strip()
        user_id = str(tok.get("user_id", "")).strip()
        if not short or not user_id:
          self._send_json(HTTPStatus.BAD_REQUEST, {"error": "token exchange failed", "response": tok})
          return
        long_tok = _threads_exchange_long_lived(short)
        access_token = str(long_tok.get("access_token", "")).strip() or short
        expires_in = int(long_tok.get("expires_in", 0) or 0)
        expires_at = ""
        if expires_in > 0:
          expires_at = datetime.fromtimestamp(time.time() + expires_in, tz=timezone.utc).isoformat()
        _set_secret(["threads"], {"access_token": access_token, "user_id": user_id, "expires_at": expires_at})
        self.send_response(302)
        self.send_header("Location", "/connect?tab=threads#threads")
        self.end_headers()
        return
      except Exception as e:
        hint = ""
        payload = _extract_error_payload(str(e))
        if isinstance(payload, dict):
          ec = payload.get("error_code") or payload.get("code")
          em = str(payload.get("error_message", "") or payload.get("message", "") or "")
          if str(ec).strip() == "1349187" or "redirect" in em.lower() or "redirect_uri" in em.lower():
            hint = "Redirect URI mismatch. In your Threads app settings, add the exact redirect URI: http://127.0.0.1:5678/oauth/threads/callback"
        if not hint:
          hint = "If this is an OAuth error, verify your app redirect URI matches the console callback URL."
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(e), "hint": hint})
        return

    if path == "/oauth/ig/start":
      state = secrets.token_urlsafe(18)
      st = _read_json(STATE_PATH, {})
      states = st.get("oauth_states", {})
      if not isinstance(states, dict):
        states = {}
      states[state] = {"kind": "ig", "created_at": _now_iso()}
      st["oauth_states"] = states
      _write_json(STATE_PATH, st)
      try:
        url = _ig_start_url(state)
      except Exception as e:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(e)})
        return
      self.send_response(302)
      self.send_header("Location", url)
      self.end_headers()
      return

    if path == "/oauth/ig/callback":
      code = (qs.get("code", [""])[0] or "").strip()
      state = (qs.get("state", [""])[0] or "").strip()
      if not code or not state:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "missing code/state"})
        return
      st = _read_json(STATE_PATH, {})
      states = st.get("oauth_states", {})
      if not isinstance(states, dict) or state not in states:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid state"})
        return
      cfg = _ig_oauth_config()
      try:
        tok = _http_json(
          "GET",
          f"{cfg['token_url']}?client_id={_urlencode(cfg['client_id'])}"
          f"&client_secret={_urlencode(cfg['client_secret'])}"
          f"&redirect_uri={_urlencode(cfg['redirect_uri'])}"
          f"&code={_urlencode(code)}",
        )
        access_token = str(tok.get("access_token", "")).strip()
        expires_in = int(tok.get("expires_in", 0) or 0)
        expires_at = ""
        if expires_in > 0:
          expires_at = datetime.fromtimestamp(time.time() + expires_in, tz=timezone.utc).isoformat()
        if not access_token:
          self._send_json(HTTPStatus.BAD_REQUEST, {"error": "token exchange failed", "response": tok})
          return
        _set_secret(["instagram"], {"access_token": access_token, "expires_at": expires_at})
        self.send_response(302)
        self.send_header("Location", "/connect?tab=instagram#instagram")
        self.end_headers()
        return
      except Exception as e:
        hint = "Verify Meta app settings include the exact redirect URI: http://127.0.0.1:5678/oauth/ig/callback"
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(e), "hint": hint})
        return

    if path == "/api/exports":
      spec = (qs.get("spec", [""])[0] or "").strip()
      if not spec:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "missing spec"})
        return
      try:
        spec_rel = _safe_rel_path(spec)
      except Exception:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid spec"})
        return
      self._send_json(200, {"exports": _exports_for_spec(spec_rel)})
      return

    if path == "/api/render":
      spec = (qs.get("spec", [""])[0] or "").strip()
      if not spec:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "missing spec"})
        return
      try:
        spec_rel = _safe_rel_path(spec)
      except Exception:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid spec"})
        return
      self._send_json(200, _render_spec(spec_rel))
      return

    if path == "/api/generate_instagram":
      project = (qs.get("project", [""])[0] or "").strip()
      style = (qs.get("style", ["bernays"])[0] or "bernays").strip()
      fmt = (qs.get("format", ["json"])[0] or "json").strip()
      if not project:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "missing project"})
        return
      try:
        project_rel = _safe_rel_path(project)
      except Exception:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid project"})
        return
      self._send_json(200, _generate_instagram(project_rel, style=style, fmt=fmt))
      return

    if path == "/api/generate_threads":
      project = (qs.get("project", [""])[0] or "").strip()
      style = (qs.get("style", ["bernays"])[0] or "bernays").strip()
      if not project:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "missing project"})
        return
      try:
        project_rel = _safe_rel_path(project)
      except Exception:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid project"})
        return
      self._send_json(200, _generate_threads(project_rel, style=style))
      return

    if path == "/api/policy":
      project = (qs.get("project", [""])[0] or "").strip()
      if not project:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "missing project"})
        return
      try:
        project_rel = _safe_rel_path(project)
      except Exception:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid project"})
        return
      policy = _load_project_policy(project_rel)
      self._send_json(200, {"project": str(project_rel), "policy": policy})
      return

    if path == "/api/chat/append":
      role = (qs.get("role", ["user"])[0] or "user").strip()
      text = (qs.get("text", [""])[0] or "").strip()
      if role not in ["user", "assistant", "system"]:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid role"})
        return
      if not text:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "missing text"})
        return
      payload = {"ts": _now_iso(), "role": role, "text": text[:8000]}
      _append_jsonl(_event_path("chat"), payload)
      _append_event("chat_append", {"role": role, "chars": len(text)})
      self._send_json(200, {"ok": True})
      return

    if path == "/api/threads/publish_text":
      text = (qs.get("text", [""])[0] or "").strip()
      confirm = (qs.get("confirm", ["0"])[0] or "0").strip() == "1"
      project = (qs.get("project", [""])[0] or "").strip()
      if not text:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "missing text"})
        return
      policy_snap = {"mode": "DRAFT_ONLY"}
      if project:
        try:
          project_rel = _safe_rel_path(project)
          policy_snap = _policy_snapshot_for_project(project_rel)
        except Exception:
          policy_snap = {"mode": "DRAFT_ONLY"}
      if str(policy_snap.get("mode", "DRAFT_ONLY")) == "NO_AI":
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Policy mode is NO_AI (reply blocked)"})
        return
      sec = _get_secret(["threads"]) or {}
      token = str(sec.get("access_token", "")).strip()
      user_id = str(sec.get("user_id", "")).strip()
      if not token or not user_id:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "threads not connected. open /connect"})
        return
      if not confirm:
        _append_jsonl(_event_path("chat"), {"ts": _now_iso(), "role": "user", "text": f"[threads dry-run]\n{text[:4000]}"})
        _append_event("threads_dry_run", {"chars": len(text), "policy": policy_snap})
        self._send_json(200, {"dry_run": True, "text": text[:600]})
        return
      try:
        _append_jsonl(_event_path("chat"), {"ts": _now_iso(), "role": "user", "text": f"[threads publish]\n{text[:4000]}"})
        _append_event("threads_publish_start", {"chars": len(text), "policy": policy_snap})
        res = _threads_publish_text(user_id=user_id, access_token=token, text=text)
        _append_event("threads_publish_done", {"ok": bool(res.get("ok")), "ids": _redact(res)})
        self._send_json(200, res)
        return
      except Exception as e:
        _append_event("threads_publish_error", {"error": str(e)})
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(e)})
        return

    if path == "/api/threads/refresh":
      sec = _get_secret(["threads"]) or {}
      token = str(sec.get("access_token", "")).strip()
      user_id = str(sec.get("user_id", "")).strip()
      if not token or not user_id:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "threads not connected"})
        return
      try:
        refreshed = _threads_refresh_long_lived(token)
        new_token = str(refreshed.get("access_token", "")).strip() or token
        expires_in = int(refreshed.get("expires_in", 0) or 0)
        expires_at = ""
        if expires_in > 0:
          expires_at = datetime.fromtimestamp(time.time() + expires_in, tz=timezone.utc).isoformat()
        _set_secret(["threads"], {"access_token": new_token, "user_id": user_id, "expires_at": expires_at})
        self._send_json(200, {"ok": True, "expires_at": expires_at})
        return
      except Exception as e:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(e)})
        return

    if path == "/api/ig/discover":
      sec = _get_secret(["instagram"]) or {}
      token = str(sec.get("access_token", "")).strip()
      if not token:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "instagram not connected. open /connect"})
        return
      try:
        res = _ig_discover_accounts(access_token=token)
        self._send_json(200, res)
        return
      except Exception as e:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(e)})
        return

    if path == "/api/ig/set_user":
      ig_user_id = (qs.get("ig_user_id", [""])[0] or "").strip()
      if not ig_user_id:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "missing ig_user_id"})
        return
      sec = _get_secret(["instagram"]) or {}
      if not sec.get("access_token"):
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "instagram not connected"})
        return
      sec["ig_user_id"] = ig_user_id
      _set_secret(["instagram"], sec)
      self.send_response(302)
      self.send_header("Location", "/connect?tab=instagram#instagram")
      self.end_headers()
      return

    if path == "/api/ig/publish_carousel":
      spec = (qs.get("spec", [""])[0] or "").strip()
      caption = (qs.get("caption", [""])[0] or "").strip()
      confirm = (qs.get("confirm", ["0"])[0] or "0").strip() == "1"
      if not spec:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "missing spec"})
        return
      try:
        spec_rel = _safe_rel_path(spec)
      except Exception:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid spec"})
        return
      policy_snap = {"mode": "DRAFT_ONLY"}
      try:
        project_rel = Path("projects") / spec_rel.parts[1]
        policy_snap = _policy_snapshot_for_project(project_rel)
      except Exception:
        policy_snap = {"mode": "DRAFT_ONLY"}
      if str(policy_snap.get("mode", "DRAFT_ONLY")) == "NO_AI":
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Policy mode is NO_AI (publish blocked)"})
        return

      sec = _get_secret(["instagram"]) or {}
      token = str(sec.get("access_token", "")).strip()
      ig_user_id = str(sec.get("ig_user_id", "")).strip()
      if not token:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "instagram not connected"})
        return
      if not ig_user_id:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "missing ig_user_id. call /api/ig/set_user"})
        return

      exports = _exports_for_spec(spec_rel)
      if len(exports) < 2:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "need at least 2 exported images for carousel", "exports": exports})
        return

      public_base = _env_or_config("JUSTSELL_PUBLIC_BASE_URL", key="public_base_url", default="")
      if not public_base:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "missing public base URL. set JUSTSELL_PUBLIC_BASE_URL or config settings.public_base_url"})
        return

      if not caption:
        caption = spec_rel.stem

      if not confirm:
        _append_jsonl(
          _event_path("chat"),
          {"ts": _now_iso(), "role": "user", "text": f"[ig dry-run]\nspec={spec_rel}\ncaption={caption}"},
        )
        _append_event("ig_dry_run", {"spec": str(spec_rel), "assets": len(exports), "policy": policy_snap})
        self._send_json(
          200,
          {
            "dry_run": True,
            "ig_user_id": ig_user_id,
            "caption": caption,
            "assets": exports[:10],
            "public_base": public_base,
            "hint": "Call again with confirm=1 to publish",
          },
        )
        return

      try:
        _append_jsonl(
          _event_path("chat"),
          {"ts": _now_iso(), "role": "user", "text": f"[ig publish]\nspec={spec_rel}\ncaption={caption}"},
        )
        _append_event("ig_publish_start", {"spec": str(spec_rel), "assets": len(exports), "policy": policy_snap})
        res = _ig_publish_carousel(
          ig_user_id=ig_user_id,
          access_token=token,
          caption=caption,
          image_paths=exports[:10],
          public_base_url=public_base,
        )
        _append_event("ig_publish_done", {"ok": bool(res.get("ok")), "policy": policy_snap})
        self._send_json(200, res)
        return
      except Exception as e:
        _append_event("ig_publish_error", {"error": str(e)})
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(e)})
        return

    self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

  def do_POST(self) -> None:  # noqa: N802
    parsed = urlparse(self.path)
    path = parsed.path

    length = int(self.headers.get("Content-Length", "0") or "0")
    raw = self.rfile.read(length) if length > 0 else b""
    ctype = (self.headers.get("Content-Type", "") or "").split(";")[0].strip().lower()

    data: dict[str, object] = {}
    try:
      if ctype == "application/json":
        obj = json.loads(raw.decode("utf-8") or "{}") if raw else {}
        if isinstance(obj, dict):
          data = obj
      else:
        # Default: urlencoded form
        form = parse_qs(raw.decode("utf-8") if raw else "")
        data = {k: (v[0] if isinstance(v, list) and v else "") for k, v in form.items()}
    except Exception:
      data = {}

    _append_event("http_post", {"path": path, "content_type": ctype, "keys": list(data.keys())[:40]})

    if path == "/api/config/update":
      # Flat settings (empty means "keep current")
      def get_str(k: str) -> str:
        v = data.get(k, "")
        return str(v or "").strip()

      validation_errors = validate_setup_form({str(k): str(v) for k, v in data.items()})
      if validation_errors:
        encoded = _urlencode(json.dumps(validation_errors, ensure_ascii=False))
        self.send_response(302)
        self.send_header("Location", f"/connect?tab=setup&errors={encoded}#setup")
        self.end_headers()
        return

      updates: dict[str, str] = {}
      secret_keys = {"threads_app_secret", "meta_app_secret", "gemini_api_key"}
      for k in [
        "public_base_url",
        "threads_app_id",
        "threads_app_secret",
        "meta_app_id",
        "meta_app_secret",
        "graph_api_version",
        "gemini_api_key",
      ]:
        v = get_str(k)
        if v and not (k in secret_keys and v == "********"):
          updates[k] = v

      budget_raw = get_str("gemini_monthly_budget_usd")
      budget_value: float | None = None
      if budget_raw != "":
        try:
          budget_value = float(budget_raw)
          if budget_value < 0:
            budget_value = 0.0
        except Exception:
          budget_value = None

      # Apply flat updates
      if updates or budget_value is not None:
        cfg = _read_config()
        s = cfg.get("settings", {})
        if not isinstance(s, dict):
          s = {}
        if updates:
          s.update(updates)
        if budget_value is not None:
          s["gemini_monthly_budget_usd"] = budget_value
        cfg["settings"] = s
        cfg["updated_at"] = _now_iso()
        _write_config(cfg)

      # Cardnews template + theme + fonts
      tmpl = get_str("cardnews_template")
      if tmpl:
        _settings_set(["cardnews", "template"], tmpl)

      theme_updates: dict[str, str] = {}
      theme_map = {
        "cardnews_accent_primary": "accent_primary",
        "cardnews_accent_secondary": "accent_secondary",
        "cardnews_cover_fill": "cover_fill",
        "cardnews_panel_fill": "panel_fill",
        "cardnews_bg_kind": "bg_kind",
        "cardnews_bg_solid": "bg_solid",
        "cardnews_bg_from": "bg_from",
        "cardnews_bg_to": "bg_to",
      }
      for form_key, theme_key in theme_map.items():
        v = get_str(form_key)
        if v:
          theme_updates[theme_key] = v
      if theme_updates:
        existing = _settings_get(["cardnews", "theme"], {})
        if not isinstance(existing, dict):
          existing = {}
        existing.update(theme_updates)
        _settings_set(["cardnews", "theme"], existing)

      font_updates: dict[str, str] = {}
      font_map = {
        "cardnews_title_name": "title_name",
        "cardnews_body_name": "body_name",
        "cardnews_footer_name": "footer_name",
      }
      for form_key, font_key in font_map.items():
        v = get_str(form_key)
        if v:
          font_updates[font_key] = v
      if font_updates:
        existing_f = _settings_get(["cardnews", "fonts"], {})
        if not isinstance(existing_f, dict):
          existing_f = {}
        existing_f.update(font_updates)
        _settings_set(["cardnews", "fonts"], existing_f)

      self.send_response(302)
      self.send_header("Location", "/connect?tab=setup&saved=1#setup")
      self.end_headers()
      return

    if path == "/api/project/create":
      slug_raw = str(data.get("slug", "") or "").strip()
      try:
        slug = _safe_project_slug(slug_raw)
      except Exception as e:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(e)})
        return
      src = REPO_ROOT / "projects" / "_template"
      dst = PROJECTS_DIR / slug
      if not src.exists() or not src.is_dir():
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "missing projects/_template"})
        return
      if dst.exists():
        self._send_json(
          HTTPStatus.BAD_REQUEST,
          {"error": "project already exists", "project": f"{PROJECTS_DIR_NAME}/{slug}"},
        )
        return
      try:
        shutil.copytree(src, dst)
      except Exception as e:
        self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"copy failed: {e}"})
        return
      _append_event("project_create", {"project": f"{PROJECTS_DIR_NAME}/{slug}"})
      self.send_response(302)
      self.send_header("Location", "/connect?tab=project#project")
      self.end_headers()
      return

    if path == "/api/meta/star_dismiss":
      _meta_set("star_banner_dismissed_at", _now_iso())
      self.send_response(302)
      self.send_header("Location", "/connect?tab=setup#setup")
      self.end_headers()
      return

    self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

  def log_message(self, fmt: str, *args) -> None:
    _append_log("HTTP " + (fmt % args))


def run_server(*, host: str = "127.0.0.1", port: int = 5678) -> None:
  # One-time migration (best-effort): keep existing tokens from older storage locations.
  try:
    cfg = _read_config()
    has_secrets = isinstance(cfg.get("secrets", None), dict) and bool(cfg.get("secrets"))
    has_settings = isinstance(cfg.get("settings", None), dict) and bool(cfg.get("settings"))

    if not has_secrets:
      # 1) Migrate from old config.json (when we stored under ~/.ccs/justsell/config.json)
      if HOME_CCS_JUSTSELL_CONFIG_PATH.exists():
        legacy_cfg = _read_json(HOME_CCS_JUSTSELL_CONFIG_PATH, {})
        if isinstance(legacy_cfg, dict):
          legacy_sec = legacy_cfg.get("secrets", {})
          legacy_set = legacy_cfg.get("settings", {})
          if isinstance(legacy_set, dict) and legacy_set and not (isinstance(cfg.get("settings"), dict) and cfg.get("settings")):
            cfg["settings"] = legacy_set
          if isinstance(legacy_sec, dict) and legacy_sec:
            cfg["secrets"] = legacy_sec
            cfg["updated_at"] = _now_iso()
            _write_config(cfg)
            _append_log(f"MIGRATE legacy config -> {CONFIG_PATH} (from {HOME_CCS_JUSTSELL_CONFIG_PATH})")
            has_secrets = True

    if not has_secrets:
      # 2) Migrate from old secrets.json locations
      for src in [HOME_JST_SECRETS_PATH, REPO_JST_SECRETS_PATH, LEGACY_SECRETS_PATH]:
        if not src.exists():
          continue
        legacy = _read_json(src, {})
        if isinstance(legacy, dict) and legacy:
          _write_secrets(legacy)
          _append_log(f"MIGRATE legacy secrets -> {CONFIG_PATH} (from {src})")
          break
  except Exception as e:
    _append_log(f"MIGRATE failed: {e}")

  runner = JobRunner()
  runner.start()
  _append_log(f"SERVER_START http://{host}:{port}")
  httpd = ThreadingHTTPServer((host, port), Handler)
  try:
    httpd.serve_forever(poll_interval=0.5)
  finally:
    runner.stop()
    _append_log("SERVER_STOP")
