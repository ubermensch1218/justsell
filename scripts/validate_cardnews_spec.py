#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_spec(path: Path) -> dict[str, Any]:
  raw = path.read_text(encoding="utf-8")
  suf = path.suffix.lower()
  if suf == ".json":
    obj = json.loads(raw)
    if not isinstance(obj, dict):
      raise ValueError("spec root must be an object")
    return obj
  try:
    import yaml  # type: ignore
  except Exception as e:  # pragma: no cover
    raise RuntimeError("PyYAML is required for YAML specs") from e
  obj = yaml.safe_load(raw)
  if not isinstance(obj, dict):
    raise ValueError("spec root must be an object")
  return obj


def _norm(s: str) -> str:
  return " ".join(str(s).strip().lower().split())


def validate_spec(spec: dict[str, Any]) -> list[str]:
  issues: list[str] = []

  slides = spec.get("slides", [])
  if not isinstance(slides, list) or len(slides) < 6:
    issues.append("slides must contain at least 6 items")
    return issues

  theme = spec.get("theme", {})
  if not isinstance(theme, dict):
    issues.append("theme must be an object")
  else:
    for key in ["accent_primary", "accent_secondary"]:
      if not str(theme.get(key, "")).strip():
        issues.append(f"theme.{key} is required")

  has_cta = False
  for idx, slide in enumerate(slides, start=1):
    if not isinstance(slide, dict):
      issues.append(f"slide[{idx}] must be an object")
      continue
    title = str(slide.get("title", "")).strip()
    body = slide.get("body", [])
    if not title:
      issues.append(f"slide[{idx}] title is empty")
    if len(title) > 64:
      issues.append(f"slide[{idx}] title is too long ({len(title)} chars)")
    if not isinstance(body, list) or not body:
      issues.append(f"slide[{idx}] body must be a non-empty list")
      continue
    for line_idx, line in enumerate(body, start=1):
      t = str(line).strip()
      if not t:
        issues.append(f"slide[{idx}] body[{line_idx}] is empty")
      if len(t) > 92:
        issues.append(f"slide[{idx}] body[{line_idx}] is too long ({len(t)} chars)")
      if "cta" in _norm(title) or "문의" in t or "신청" in t:
        has_cta = True

  if not has_cta:
    issues.append("no clear CTA slide/content detected")

  return issues


def main() -> int:
  p = argparse.ArgumentParser(description="Validate cardnews spec for production-readiness.")
  p.add_argument("--spec", required=True, type=Path, help="Path to spec (yaml/json)")
  args = p.parse_args()

  spec = _load_spec(args.spec.expanduser().resolve())
  issues = validate_spec(spec)
  if issues:
    print("FAILED")
    for issue in issues:
      print(f"- {issue}")
    return 1
  print("OK")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())

