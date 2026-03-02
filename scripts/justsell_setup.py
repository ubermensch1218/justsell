#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
  return datetime.now(timezone.utc).isoformat()


def _is_tty() -> bool:
  try:
    return sys.stdin.isatty() and sys.stdout.isatty()
  except Exception:
    return False


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


def _repo_root() -> Path:
  return Path(__file__).resolve().parents[1]


def _get_path(cfg: dict[str, Any], path: list[str], default: object) -> object:
  cur: object = cfg
  for k in path:
    if not isinstance(cur, dict):
      return default
    cur = cur.get(k)
  return cur if cur is not None else default


def _prompt(label: str, *, default: str | None = None) -> str:
  suffix = f" [{default}]" if (default is not None and default != "") else ""
  try:
    v = input(f"{label}{suffix}: ").strip()
  except (EOFError, KeyboardInterrupt):
    raise SystemExit(130)
  if v == "" and default is not None:
    return str(default)
  return v


def _prompt_secret(label: str, *, default_set: bool) -> str:
  suffix = " [set]" if default_set else ""
  try:
    v = getpass.getpass(f"{label}{suffix}: ").strip()
  except (EOFError, KeyboardInterrupt):
    raise SystemExit(130)
  return v


def _prompt_choice(label: str, options: list[str], *, default_index: int = 0) -> int:
  if not options:
    raise ValueError("no options")
  for i, opt in enumerate(options, start=1):
    mark = "*" if (i - 1) == default_index else " "
    print(f"  {mark} {i}) {opt}")
  raw = _prompt(label, default=str(default_index + 1))
  try:
    idx = int(raw) - 1
  except Exception:
    return default_index
  if idx < 0 or idx >= len(options):
    return default_index
  return idx


def _available_cardnews_templates() -> list[str]:
  tdir = _repo_root() / "channels" / "instagram" / "templates"
  items: list[str] = []
  if tdir.exists():
    for p in sorted(tdir.glob("cardnews.*.yaml")):
      try:
        rel = p.relative_to(_repo_root())
        items.append(str(rel))
      except Exception:
        continue

  # User templates (local-first; survive repo/plugin updates):
  # ~/.claude/.js/templates/instagram/<anything>.yaml|yml|json
  try:
    user_dir = _claude_dir() / ".js" / "templates" / "instagram"
    if user_dir.exists():
      for p in sorted(user_dir.glob("*")):
        if not p.is_file():
          continue
        if p.suffix.lower() not in [".yaml", ".yml", ".json"]:
          continue
        items.append(str(p))
  except Exception:
    pass
  return items


def _apply_cardnews_updates(
  cfg: dict[str, Any],
  *,
  template: str,
  theme_updates: dict[str, str],
  font_updates: dict[str, str],
) -> None:
  cfg.setdefault("settings", {})
  if not isinstance(cfg["settings"], dict):
    cfg["settings"] = {}
  s = cfg["settings"]

  cardnews: dict[str, Any] = s.get("cardnews", {})
  if not isinstance(cardnews, dict):
    cardnews = {}

  if template.strip():
    cardnews["template"] = template.strip()

  theme: dict[str, Any] = cardnews.get("theme", {})
  if not isinstance(theme, dict):
    theme = {}
  for k, v in theme_updates.items():
    vv = (v or "").strip()
    if vv:
      theme[k] = vv
  if theme:
    cardnews["theme"] = theme

  fonts: dict[str, Any] = cardnews.get("fonts", {})
  if not isinstance(fonts, dict):
    fonts = {}
  for k, v in font_updates.items():
    vv = (v or "").strip()
    if vv:
      fonts[k] = vv
  if fonts:
    cardnews["fonts"] = fonts

  if cardnews:
    s["cardnews"] = cardnews
    cfg["settings"] = s
    cfg["updated_at"] = _now_iso()


def _wizard(config_path: Path) -> dict[str, Any]:
  if not _is_tty():
    raise SystemExit("Wizard requires a TTY (interactive terminal). Use flags instead.")

  cfg = _read_json(config_path, {"version": 1, "settings": {}, "secrets": {}, "meta": {}})
  if not isinstance(cfg, dict):
    cfg = {"version": 1, "settings": {}, "secrets": {}, "meta": {}}

  if config_path.exists():
    print("Detected existing config:")
    public_base = str(_get_path(cfg, ["settings", "public_base_url"], "") or "").strip()
    threads_app_id = str(_get_path(cfg, ["settings", "threads_app_id"], "") or "").strip()
    meta_app_id = str(_get_path(cfg, ["settings", "meta_app_id"], "") or "").strip()
    graph_ver = str(_get_path(cfg, ["settings", "graph_api_version"], "") or "").strip()
    template = str(_get_path(cfg, ["settings", "cardnews", "template"], "") or "").strip()
    print(f"- public_base_url: {'set' if public_base else 'empty'}")
    print(f"- threads_app_id: {'set' if threads_app_id else 'empty'}")
    print(f"- meta_app_id: {'set' if meta_app_id else 'empty'}")
    print(f"- graph_api_version: {graph_ver or '(empty)'}")
    print(f"- cardnews.template: {template or '(empty)'}")
    print("")

    choice = _prompt_choice(
      "Choose",
      [
        "Keep existing and update some fields",
        "Reset config and re-run setup",
        "Cancel",
      ],
      default_index=0,
    )
    if choice == 2:
      raise SystemExit(0)
    if choice == 1:
      cfg = {"version": 1, "settings": {}, "secrets": cfg.get("secrets", {}), "meta": {}}

  print("")
  print("Step 1/4: Cardnews preset (design defaults)")
  presets = ["BOC-like (solid dark + neon accent)", "Claude-like (orange cover + dark slides)", "Custom / keep current"]
  preset_idx = _prompt_choice("Select preset", presets, default_index=0)
  preset: dict[str, str] = {}
  if preset_idx == 0:
    preset = {
      "template": "channels/instagram/templates/cardnews.boc_like.yaml",
      "accent_primary": "#00E676",
      "accent_secondary": "#111111",
      "cover_fill": "#00E676",
      "panel_fill": "#2B2B2B",
      "bg_kind": "solid",
      "bg_solid": "#2B2B2B",
      "bg_from": "",
      "bg_to": "",
      "title_name": "Pretendard Bold",
      "body_name": "Pretendard Regular",
      "footer_name": "Pretendard Regular",
    }
  elif preset_idx == 1:
    preset = {
      "template": "channels/instagram/templates/cardnews.claude_code_like.yaml",
      "accent_primary": "#FF6A2A",
      "accent_secondary": "#111111",
      "cover_fill": "#FF6A2A",
      "panel_fill": "#141414",
      "bg_kind": "solid",
      "bg_solid": "#FFFFFF",
      "bg_from": "",
      "bg_to": "",
      "title_name": "Pretendard Bold",
      "body_name": "Pretendard Regular",
      "footer_name": "Pretendard Regular",
    }

  print("")
  print("Step 2/4: App settings (empty keeps current where possible)")
  updates = {
    "public_base_url": _prompt("public_base_url (optional)", default=str(_get_path(cfg, ["settings", "public_base_url"], "") or "")),
    "threads_app_id": _prompt("threads_app_id", default=str(_get_path(cfg, ["settings", "threads_app_id"], "") or "")),
    "threads_app_secret": "",
    "meta_app_id": _prompt("meta_app_id", default=str(_get_path(cfg, ["settings", "meta_app_id"], "") or "")),
    "meta_app_secret": "",
    "graph_api_version": _prompt("graph_api_version", default=str(_get_path(cfg, ["settings", "graph_api_version"], "") or "v20.0") or "v20.0"),
  }
  existing_threads_secret = bool(str(_get_path(cfg, ["settings", "threads_app_secret"], "") or "").strip())
  existing_meta_secret = bool(str(_get_path(cfg, ["settings", "meta_app_secret"], "") or "").strip())
  v = _prompt_secret("threads_app_secret (optional)", default_set=existing_threads_secret)
  if v.strip():
    updates["threads_app_secret"] = v.strip()
  v = _prompt_secret("meta_app_secret (optional)", default_set=existing_meta_secret)
  if v.strip():
    updates["meta_app_secret"] = v.strip()
  cfg = _merge_settings(cfg, updates)

  print("")
  print("Step 3/4: Cardnews defaults (optional)")
  templates = _available_cardnews_templates()
  existing_template = str(_get_path(cfg, ["settings", "cardnews", "template"], "") or "").strip()
  template_choice = ""
  if templates:
    default_template = existing_template or preset.get("template", "")
    default_idx = templates.index(default_template) if default_template in templates else 0
    print("Available templates:")
    idx = _prompt_choice("Select template", templates + ["(keep current / skip)"], default_index=default_idx)
    if idx < len(templates):
      template_choice = templates[idx]
  else:
    template_choice = _prompt("cardnews.template path (optional)", default=(existing_template or preset.get("template", "")))

  theme_updates = {
    "accent_primary": _prompt(
      "theme.accent_primary (optional)",
      default=str(_get_path(cfg, ["settings", "cardnews", "theme", "accent_primary"], "") or "") or preset.get("accent_primary", ""),
    ),
    "accent_secondary": _prompt(
      "theme.accent_secondary (optional)",
      default=str(_get_path(cfg, ["settings", "cardnews", "theme", "accent_secondary"], "") or "") or preset.get("accent_secondary", ""),
    ),
    "cover_fill": _prompt(
      "theme.cover_fill (optional)",
      default=str(_get_path(cfg, ["settings", "cardnews", "theme", "cover_fill"], "") or "") or preset.get("cover_fill", ""),
    ),
    "panel_fill": _prompt(
      "theme.panel_fill (optional)",
      default=str(_get_path(cfg, ["settings", "cardnews", "theme", "panel_fill"], "") or "") or preset.get("panel_fill", ""),
    ),
    "bg_kind": _prompt(
      "theme.bg_kind (solid|gradient, optional)",
      default=str(_get_path(cfg, ["settings", "cardnews", "theme", "bg_kind"], "") or "") or preset.get("bg_kind", ""),
    ),
    "bg_solid": _prompt(
      "theme.bg_solid (optional)",
      default=str(_get_path(cfg, ["settings", "cardnews", "theme", "bg_solid"], "") or "") or preset.get("bg_solid", ""),
    ),
    "bg_from": _prompt(
      "theme.bg_from (optional)",
      default=str(_get_path(cfg, ["settings", "cardnews", "theme", "bg_from"], "") or "") or preset.get("bg_from", ""),
    ),
    "bg_to": _prompt(
      "theme.bg_to (optional)",
      default=str(_get_path(cfg, ["settings", "cardnews", "theme", "bg_to"], "") or "") or preset.get("bg_to", ""),
    ),
  }
  font_updates = {
    "title_name": _prompt(
      "fonts.title_name (optional)",
      default=str(_get_path(cfg, ["settings", "cardnews", "fonts", "title_name"], "") or "") or preset.get("title_name", ""),
    ),
    "body_name": _prompt(
      "fonts.body_name (optional)",
      default=str(_get_path(cfg, ["settings", "cardnews", "fonts", "body_name"], "") or "") or preset.get("body_name", ""),
    ),
    "footer_name": _prompt(
      "fonts.footer_name (optional)",
      default=str(_get_path(cfg, ["settings", "cardnews", "fonts", "footer_name"], "") or "") or preset.get("footer_name", ""),
    ),
  }
  _apply_cardnews_updates(cfg, template=template_choice, theme_updates=theme_updates, font_updates=font_updates)

  print("")
  print("Step 4/4: OAuth connect")
  print("- Start console: python3 scripts/justsell_console.py")
  print("- Open: http://127.0.0.1:5678/connect")
  print("  - Connect Threads (OAuth)")
  print("  - Connect Instagram (OAuth)")
  print("  - Discover accounts and Select one ig_user_id")
  print("")

  return cfg


def main() -> int:
  p = argparse.ArgumentParser(description="Write JustSell plugin config into ~/.claude/.js/config.json")
  p.add_argument("--claude-dir", type=Path, default=None, help="Override Claude config dir (default: env CLAUDE_CONFIG_DIR or ~/.claude)")
  p.add_argument("--wizard", action="store_true", help="Interactive wizard (recommended for /js init)")
  p.add_argument("--dry-run", action="store_true", help="Do not write config.json (print path only)")

  p.add_argument("--public-base-url", default="", help="Public base URL for serving assets to Meta (optional)")

  p.add_argument("--threads-app-id", default="")
  p.add_argument("--threads-app-secret", default="")

  p.add_argument("--meta-app-id", default="")
  p.add_argument("--meta-app-secret", default="")
  p.add_argument("--graph-api-version", default="")

  # Cardnews defaults (optional)
  p.add_argument("--cardnews-template", default="", help="Template path under repo (optional)")
  p.add_argument("--accent-primary", default="")
  p.add_argument("--accent-secondary", default="")
  p.add_argument("--cover-fill", default="")
  p.add_argument("--panel-fill", default="")
  p.add_argument("--bg-kind", default="", help="solid|gradient")
  p.add_argument("--bg-solid", default="")
  p.add_argument("--bg-from", default="")
  p.add_argument("--bg-to", default="")
  p.add_argument("--title-font", default="", help="Font name (example: GDmarket Bold)")
  p.add_argument("--body-font", default="", help="Font name (example: Pretendard Regular)")
  p.add_argument("--footer-font", default="", help="Font name (example: Pretendard Regular)")

  args = p.parse_args()

  claude_dir = args.claude_dir.expanduser() if args.claude_dir else _claude_dir()
  js_dir = claude_dir / ".js"
  config_path = js_dir / "config.json"

  if args.wizard:
    cfg = _wizard(config_path)
    if args.dry_run:
      print(str(config_path))
      return 0
    _write_json(config_path, cfg)
    print(str(config_path))
    return 0

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

  _apply_cardnews_updates(
    cfg,
    template=args.cardnews_template,
    theme_updates={
      "accent_primary": args.accent_primary,
      "accent_secondary": args.accent_secondary,
      "cover_fill": args.cover_fill,
      "panel_fill": args.panel_fill,
      "bg_kind": args.bg_kind,
      "bg_solid": args.bg_solid,
      "bg_from": args.bg_from,
      "bg_to": args.bg_to,
    },
    font_updates={
      "title_name": args.title_font,
      "body_name": args.body_font,
      "footer_name": args.footer_font,
    },
  )

  if args.dry_run:
    print(str(config_path))
    return 0

  _write_json(config_path, cfg)

  print(str(config_path))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
