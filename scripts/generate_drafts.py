#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import re
from typing import Any
import json


@dataclass(frozen=True)
class SalesInfo:
  project_name: str
  one_liner: str
  contact_channel: str
  icp_role: str
  icp_stage: str
  current_alternatives: str
  pains: list[str]
  value_prop: str
  features: list[str]
  differentiators: list[str]
  proof: str
  primary_cta: str


def _clean_placeholder(s: str) -> str:
  s = s.strip()
  s = re.sub(r"\{[^}]+\}", "", s).strip()
  return s


def _find_section_lines(lines: list[str], heading_prefix: str) -> list[str]:
  in_block = False
  out: list[str] = []
  for line in lines:
    if re.match(rf"^\s*##\s*{re.escape(heading_prefix)}", line):
      in_block = True
      continue
    if in_block and line.startswith("## "):
      break
    if in_block:
      out.append(line)
  return out


def _extract_bullet_value(lines: list[str], prefix: str) -> str:
  for line in lines:
    m = re.match(rf"^\s*-\s*{re.escape(prefix)}\s*:\s*(.+)\s*$", line)
    if m:
      return _clean_placeholder(m.group(1))
  return ""


def _extract_numbered(lines: list[str], start_re: str) -> list[str]:
  out: list[str] = []
  in_block = False
  for line in lines:
    if re.match(start_re, line):
      in_block = True
      continue
    if in_block and line.startswith("## "):
      break
    if not in_block:
      continue
    m = re.match(r"^\s*\d+\)\s*(.+)\s*$", line)
    if m:
      v = _clean_placeholder(m.group(1))
      if v:
        out.append(v)
  return out


def _extract_simple_bullets(lines: list[str], heading: str) -> list[str]:
  out: list[str] = []
  in_block = False
  for line in lines:
    if line.strip() == f"## {heading}":
      in_block = True
      continue
    if in_block and line.startswith("## "):
      break
    if not in_block:
      continue
    m = re.match(r"^\s*-\s*(.+)\s*$", line)
    if m:
      v = _clean_placeholder(m.group(1))
      if v:
        out.append(v)
  return out


def parse_sales_info(path: Path) -> SalesInfo:
  raw = path.read_text(encoding="utf-8")
  lines = raw.splitlines()

  project_name = _extract_bullet_value(lines, "프로젝트명")
  one_liner = _extract_bullet_value(lines, "한 줄 소개")
  contact_channel = _extract_bullet_value(lines, "웹/데모/문의 채널")

  icp_role = _extract_bullet_value(lines, "산업/직무")
  icp_stage = _extract_bullet_value(lines, "규모/단계")
  current_alternatives = _extract_bullet_value(lines, "현재 쓰는 대안")

  pains = _extract_numbered(lines, r"^\s*##\s*고객 문제")
  features = _extract_numbered(lines, r"^\s*##\s*핵심 기능")
  differentiators = _extract_simple_bullets(lines, "차별점")

  value_prop = ""
  vp_lines = _find_section_lines(lines, "제공 가치")
  for line in vp_lines:
    m = re.match(r"^\s*-\s*(.+)\s*$", line)
    if not m:
      continue
    candidate = _clean_placeholder(m.group(1))
    if candidate:
      value_prop = candidate
      break

  proof_lines = _extract_simple_bullets(lines, "근거/증거 (있을 때만)")
  proof = "; ".join(proof_lines[:3]).strip()

  primary_cta = ""
  in_cta = False
  for line in lines:
    if line.strip() == "## 대표 CTA (1개)":
      in_cta = True
      continue
    if in_cta and line.startswith("## "):
      break
    if not in_cta:
      continue
    m = re.match(r"^\s*-\s*(.+)\s*$", line)
    if m:
      primary_cta = _clean_placeholder(m.group(1))
      break

  return SalesInfo(
    project_name=project_name,
    one_liner=one_liner,
    contact_channel=contact_channel,
    icp_role=icp_role,
    icp_stage=icp_stage,
    current_alternatives=current_alternatives,
    pains=pains,
    value_prop=value_prop,
    features=features,
    differentiators=differentiators,
    proof=proof,
    primary_cta=primary_cta,
  )


def _now_stamp() -> str:
  return datetime.now().strftime("%Y%m%d-%H%M")


def _ensure_dir(p: Path) -> None:
  p.mkdir(parents=True, exist_ok=True)


def _first_nonempty(values: list[str]) -> str:
  for v in values:
    if v.strip():
      return v.strip()
  return ""


def _limit_list(values: list[str], n: int) -> list[str]:
  return [v for v in values if v.strip()][:n]


def _bernays_frame(si: SalesInfo) -> dict[str, str]:
  pain = si.pains[0] if si.pains else ""
  old_belief = _first_nonempty(
    [
      si.current_alternatives,
      "기존 방식",
    ]
  )
  hidden_cost = _first_nonempty(
    [
      si.pains[1] if len(si.pains) > 1 else "",
      "시간과 리스크",
    ]
  )
  new_standard = _first_nonempty(
    [
      si.value_prop,
      si.one_liner,
      "새 기준",
    ]
  )
  proof = si.proof
  cta = _first_nonempty([si.primary_cta, si.contact_channel])
  return {
    "pain": pain,
    "old_belief": old_belief,
    "hidden_cost": hidden_cost,
    "new_standard": new_standard,
    "proof": proof,
    "cta": cta,
  }


def render_twitter(si: SalesInfo, style: str) -> str:
  if style == "comeback":
    hook = _first_nonempty([si.one_liner, si.project_name, "짧게 근황 공유드립니다."])
    proof = _first_nonempty([si.proof, ""])
    cta = _first_nonempty([si.primary_cta, si.contact_channel, "필요하면 한 줄만 남겨주세요."])
    lines = [hook, ""]
    if si.value_prop:
      lines.append(si.value_prop)
    if proof:
      lines += ["", f"근거(공개 범위): {proof}"]
    lines += ["", cta]
    return "\n".join([l for l in lines if l is not None]).strip() + "\n"

  if style != "bernays":
    hook = _first_nonempty([si.one_liner, si.value_prop, si.pains[0] if si.pains else ""])
    points = _limit_list([si.value_prop, *si.differentiators, *(si.features[:2] if si.features else [])], 3)
    cta = _first_nonempty([si.primary_cta, si.contact_channel])
    body_lines = "\n".join([f"- {p}" for p in points]) if points else "- (포인트 추가)"
    return "\n".join([hook, "", body_lines, "", cta]).strip() + "\n"

  f = _bernays_frame(si)
  lead = _first_nonempty([si.one_liner, si.project_name, "새 기준이 필요합니다."])
  bullets = _limit_list(
    [
      f"기존의 {f['old_belief']}는 보통 {f['hidden_cost']}를 남깁니다.",
      f"이제 기준은 이겁니다: {f['new_standard']}",
      f"다음 단계: {f['cta']}" if f["cta"] else "",
    ],
    3,
  )
  body = "\n".join([f"- {b}" for b in bullets]) if bullets else "- (내용 추가)"
  return f"{lead}\n\n{body}\n"


def render_threads(si: SalesInfo, style: str) -> str:
  if style == "comeback":
    opening = _first_nonempty([si.pains[0] if si.pains else "", si.one_liner, "짧게 근황 공유드립니다."])
    change = _first_nonempty([si.value_prop, si.differentiators[0] if si.differentiators else ""])
    proof = _first_nonempty([si.proof, ""])
    cta = _first_nonempty([si.primary_cta, si.contact_channel, "원하시면 지금 상황만 알려주시면 됩니다."])
    out = [opening, "", change]
    if proof:
      out += ["", f"근거(공개 범위): {proof}"]
    out += ["", cta]
    return "\n".join(out).strip() + "\n"

  if style != "bernays":
    opening = _first_nonempty([si.pains[0] if si.pains else "", si.one_liner])
    insight = _first_nonempty([si.value_prop, "문제를 해결하는 방식이 바뀌어야 합니다."])
    example = _first_nonempty(
      [si.features[0] if si.features else "", si.differentiators[0] if si.differentiators else ""]
    )
    question = "이런 문제 겪고 있나요? 어떤 방식으로 풀고 있는지 궁금합니다."

    parts = [opening, "", insight]
    if example:
      parts += ["", f"예: {example}"]
    parts += ["", question]
    return "\n".join([p for p in parts if p is not None]).strip() + "\n"

  f = _bernays_frame(si)
  opening = _first_nonempty([f["pain"], si.one_liner, "요즘 이게 반복되면, 시스템의 문제일 가능성이 큽니다."])
  shift = _first_nonempty([f["new_standard"], si.value_prop, "새 기준"])
  example = _first_nonempty([si.features[0] if si.features else "", si.differentiators[0] if si.differentiators else ""])
  parts = [
    opening,
    "",
    f"생각해보면, {f['old_belief']}가 ‘당연’하다고 믿는 순간 {f['hidden_cost']}가 고정비가 됩니다.",
    "",
    f"그래서 저는 기준을 이렇게 잡고 있어요: {shift}",
  ]
  if example:
    parts += ["", f"예: {example}"]
  parts += ["", "지금 어떤 방식이 ‘당연’해져 있나요?"]
  return "\n".join(parts).strip() + "\n"


def render_linkedin(si: SalesInfo, style: str) -> str:
  if style == "comeback":
    title = _first_nonempty([si.one_liner, si.project_name, "최근 업데이트"])
    proof = _first_nonempty([si.proof, ""])
    cta = _first_nonempty([si.primary_cta, si.contact_channel, "원하시면 현재 상황만 공유해 주세요."])
    bullets = _limit_list([si.value_prop, *(si.features[:2] if si.features else []), *(si.differentiators[:1] if si.differentiators else [])], 3)
    body = "\n".join([f"- {b}" for b in bullets]) if bullets else "- (내용 추가)"
    out = [title, "", body]
    if proof:
      out += ["", f"근거(공개 범위): {proof}"]
    out += ["", cta]
    return "\n".join(out).strip() + "\n"

  if style != "bernays":
    pain = si.pains[0] if si.pains else ""
    lead = _first_nonempty([si.one_liner, pain, si.value_prop])
    context = _first_nonempty([f"대상: {si.icp_role} ({si.icp_stage})", "대상: (ICP 추가)"])
    steps = _limit_list(si.features or si.differentiators, 3)
    while len(steps) < 3:
      steps.append("(내용 추가)")
    cta = _first_nonempty([si.primary_cta, si.contact_channel, "필요하면 자료 공유드릴게요."])
    return (
      f"{lead}\n\n"
      f"{context}\n\n"
      "What we did / learned\n"
      f"1) {steps[0]}\n"
      f"2) {steps[1]}\n"
      f"3) {steps[2]}\n\n"
      f"{cta}\n"
    )

  f = _bernays_frame(si)
  lead = _first_nonempty([si.one_liner, "이제 기준을 바꿔야 합니다."])
  context = _first_nonempty([f"대상: {si.icp_role} ({si.icp_stage})", "대상: (ICP 추가)"])

  # “새 기준”을 먼저 선언하고, 그 다음에 기존 믿음/숨은 비용을 해체
  new_standard = _first_nonempty([f["new_standard"], si.value_prop, si.one_liner])
  dismantle = _first_nonempty([f["old_belief"], "기존 방식"])
  hidden = _first_nonempty([f["hidden_cost"], "숨은 비용"])

  method = _limit_list(si.features, 3) or _limit_list(si.differentiators, 3)
  while len(method) < 3:
    method.append("(프로세스/기능 추가)")

  proof = f["proof"]
  cta = _first_nonempty([f["cta"], "원하면 데모/자료 공유 가능합니다."])

  out = [
    lead,
    "",
    f"저는 요즘 이렇게 프레임을 바꿔서 보고 있습니다: {new_standard}",
    "",
    f"그런데 {dismantle}가 당연해지는 순간, {hidden}는 비용이 아니라 ‘상수’가 됩니다.",
    "",
    "그래서 실행은 이렇게 단순화합니다:",
    f"1) {method[0]}",
    f"2) {method[1]}",
    f"3) {method[2]}",
  ]
  if proof:
    out += ["", f"근거(공개 범위): {proof}"]
  out += ["", context, "", cta]
  return "\n".join(out).strip() + "\n"


def render_instagram_cardnews_spec(si: SalesInfo, *, style: str) -> dict[str, Any]:
  f = _bernays_frame(si)
  title = _first_nonempty([si.one_liner, si.value_prop, si.project_name])
  new_standard = _first_nonempty([f["new_standard"], si.value_prop, title])
  old_belief = _first_nonempty([f["old_belief"], si.current_alternatives])
  hidden_cost = _first_nonempty([f["hidden_cost"], "시간/리스크/기회비용"])
  proof = f["proof"]
  cta = _first_nonempty([f["cta"], si.contact_channel])

  pain_lines = _limit_list(si.pains, 3)
  diff_lines = _limit_list(si.differentiators, 3)
  feat_lines = _limit_list(si.features, 3)

  if style == "comeback":
    slides: list[dict[str, Any]] = [
      {"kind": "cover", "title": title or "근황", "body": ["짧게 근황 공유드립니다.", si.value_prop or new_standard], "footer": si.project_name or ""},
      {"kind": "bullets", "title": "여전히 흔한 문제", "body": pain_lines or [hidden_cost], "footer": si.project_name or ""},
      {"kind": "bullets", "title": "지금 이렇게 단순화", "body": _limit_list([si.value_prop, *(feat_lines[:2] if feat_lines else [])], 3) or ["(제공 가치 추가)"], "footer": si.project_name or ""},
      {"kind": "cover", "title": "CTA", "body": [cta or "(CTA 추가)"], "footer": si.project_name or ""},
    ]
  else:
    slides = [
      {
        "kind": "cover",
        "title": title or "새 기준",
        "body": [f"이제 기준은 이겁니다:", new_standard],
        "footer": si.project_name or "",
      },
      {
        "kind": "pills",
        "title": "혹시 이런 생각,\n해보신 적 있나요?",
        "body": _limit_list(
          [
            f"\"{pain_lines[0]}\"" if pain_lines else "\"AI를 어디서부터 써야 할지 모르겠어요\"",
            f"\"{pain_lines[1]}\"" if len(pain_lines) > 1 else f"\"{old_belief}가 당연해졌어요\"",
            f"\"{hidden_cost}\"",
            "\"실전 사례가 더 필요해요\"",
          ],
          4,
        ),
        "footer": si.project_name or "",
      },
      {
        "kind": "bullets",
        "title": "숨은 비용",
        "body": [
          hidden_cost,
          *(pain_lines[:2] if pain_lines else []),
        ],
        "footer": si.project_name or "",
      },
      {
        "kind": "bullets",
        "title": "새 방법",
        "body": _limit_list([si.value_prop, *(feat_lines[:2] if feat_lines else [])], 3) or ["(제공 가치 추가)"],
        "footer": si.project_name or "",
      },
      {
        "kind": "bullets",
        "title": "차별점",
        "body": diff_lines or ["(차별점 추가)"],
        "footer": si.project_name or "",
      },
    ]

  if proof:
    slides.append({"title": "근거", "body": [proof], "footer": si.project_name or ""})

  slides.append({"kind": "cover", "title": "CTA", "body": [cta or "(CTA 추가)"], "footer": si.project_name or ""})

  return {
    "canvas": {"width": 1080, "height": 1350},
    "theme": {
      "background": {"kind": "gradient", "from": "#050505", "to": "#0B0F19"},
      "accent_primary": "#FF3B30",
      "accent_secondary": "#5856D6",
      "card": {"fill": "rgba(255,255,255,0.03)", "border": "rgba(255,255,255,0.08)", "radius": 40},
      "text": {"title": "#FFFFFF", "body": "#FFFFFF", "dim": "#A0A0A0"},
    },
    "brand": {"name": si.project_name or "", "contact": si.contact_channel or ""},
    "font": {"path": "", "title_size": 84, "body_size": 46, "footer_size": 30},
    "layout": {"padding": 88, "card_padding": 72, "line_spacing": 14, "bullet_prefix": "", "show_slide_number": False},
    "slides": slides,
  }


def write_draft(project_dir: Path, channel: str, content: str) -> Path:
  out_dir = project_dir / "channels" / channel / "drafts"
  _ensure_dir(out_dir)
  out_path = out_dir / f"{_now_stamp()}.md"
  out_path.write_text(content, encoding="utf-8")
  return out_path


def write_instagram_spec(project_dir: Path, spec: dict[str, Any], *, out_format: str) -> Path:
  out_dir = project_dir / "channels" / "instagram" / "cardnews"
  _ensure_dir(out_dir)
  if out_format == "json":
    out_path = out_dir / f"{_now_stamp()}.json"
    out_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path

  out_path = out_dir / f"{_now_stamp()}.yaml"
  import yaml  # type: ignore
  out_path.write_text(yaml.safe_dump(spec, sort_keys=False, allow_unicode=True), encoding="utf-8")
  return out_path


def _repo_root() -> Path:
  return Path(__file__).resolve().parents[1]


def _claude_dir() -> Path:
  v = (os.environ.get("CLAUDE_CONFIG_DIR") or os.environ.get("CLAUDE_HOME") or "").strip()
  if v:
    return Path(v).expanduser()
  return (Path.home() / ".claude").expanduser()


def _read_config_settings() -> dict[str, Any]:
  if os.environ.get("JUSTSELL_CONFIG_PATH"):
    cfg_path = Path(os.environ.get("JUSTSELL_CONFIG_PATH", "")).expanduser()
  else:
    base = _claude_dir()
    cfg_path = base / ".js" / "config.json"
  try:
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
  except Exception:
    return {}
  if not isinstance(data, dict):
    return {}
  s = data.get("settings", {})
  return s if isinstance(s, dict) else {}


def _settings_get(settings: dict[str, Any], path: list[str], default: object) -> object:
  cur: object = settings
  for k in path:
    if not isinstance(cur, dict):
      return default
    cur = cur.get(k)
  return cur if cur is not None else default


def _load_template(path: Path) -> dict[str, Any]:
  raw = path.read_text(encoding="utf-8")
  suf = path.suffix.lower()
  if suf == ".json":
    obj = json.loads(raw)
    if not isinstance(obj, dict):
      raise ValueError("template root must be an object")
    return obj

  try:
    import yaml  # type: ignore
  except Exception as e:  # pragma: no cover
    raise RuntimeError("PyYAML is required to read .yaml/.yml templates") from e

  obj = yaml.safe_load(raw)
  if not isinstance(obj, dict):
    raise ValueError("template root must be an object")
  return obj


def _deep_merge(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
  for k, v in src.items():
    if isinstance(v, dict) and isinstance(dst.get(k), dict):
      dst[k] = _deep_merge(dst[k], v)  # type: ignore[index]
    else:
      dst[k] = v
  return dst


def main() -> int:
  parser = argparse.ArgumentParser(description="Generate channel drafts from projects/<project>/SALES_INFO.md")
  parser.add_argument("channel", choices=["twitter", "threads", "linkedin", "instagram-cardnews"])
  parser.add_argument("--project", required=True, type=Path, help="Path like projects/<project-slug>")
  parser.add_argument("--style", default="bernays", choices=["bernays", "plain", "comeback"])
  parser.add_argument("--format", default="yaml", choices=["yaml", "json"], help="Spec output format (instagram-cardnews only)")
  parser.add_argument("--template", default="", help="Base template for instagram-cardnews (YAML/JSON). If omitted, uses config settings.cardnews.template when available.")
  args = parser.parse_args()

  sales_path = args.project / "SALES_INFO.md"
  if not sales_path.exists():
    raise FileNotFoundError(f"Missing: {sales_path} (expected SALES_INFO.md)")

  si = parse_sales_info(sales_path)

  if args.channel == "twitter":
    out = write_draft(args.project, "twitter", render_twitter(si, args.style))
    print(str(out))
    return 0
  if args.channel == "threads":
    out = write_draft(args.project, "threads", render_threads(si, args.style))
    print(str(out))
    return 0
  if args.channel == "linkedin":
    out = write_draft(args.project, "linkedin", render_linkedin(si, args.style))
    print(str(out))
    return 0

  spec = render_instagram_cardnews_spec(si, style=args.style)

  # Apply template + config defaults (local-first).
  settings = _read_config_settings()
  template_str = str(args.template or "").strip()
  if not template_str:
    template_str = str(_settings_get(settings, ["cardnews", "template"], "") or "").strip()

  if template_str:
    tpl_path = Path(template_str).expanduser()
    if not tpl_path.is_absolute():
      tpl_path = (_repo_root() / tpl_path).resolve()
    if tpl_path.exists():
      tpl = _load_template(tpl_path)
      # Template is a style preset: it should override generated canvas/theme/font/layout.
      for k in ["canvas", "theme", "font", "layout"]:
        if k in tpl:
          spec[k] = tpl[k]

  # Config overrides: key colors and fonts
  cfg_theme = _settings_get(settings, ["cardnews", "theme"], {})
  if isinstance(cfg_theme, dict) and cfg_theme:
    theme_patch: dict[str, Any] = {}
    if "accent_primary" in cfg_theme:
      theme_patch.setdefault("theme", {})["accent_primary"] = str(cfg_theme.get("accent_primary", "")).strip()
    if "accent_secondary" in cfg_theme:
      theme_patch.setdefault("theme", {})["accent_secondary"] = str(cfg_theme.get("accent_secondary", "")).strip()
    cover_fill = str(cfg_theme.get("cover_fill", "")).strip()
    if cover_fill:
      theme_patch.setdefault("theme", {}).setdefault("cover", {})["fill"] = cover_fill
    panel_fill = str(cfg_theme.get("panel_fill", "")).strip()
    if panel_fill:
      theme_patch.setdefault("theme", {}).setdefault("panel", {})["fill"] = panel_fill
    bg_kind = str(cfg_theme.get("bg_kind", "")).strip()
    if bg_kind:
      theme_patch.setdefault("theme", {}).setdefault("background", {})["kind"] = bg_kind
    bg_solid = str(cfg_theme.get("bg_solid", "")).strip()
    if bg_solid:
      theme_patch.setdefault("theme", {}).setdefault("background", {})["color"] = bg_solid
    bg_from = str(cfg_theme.get("bg_from", "")).strip()
    bg_to = str(cfg_theme.get("bg_to", "")).strip()
    if bg_from:
      theme_patch.setdefault("theme", {}).setdefault("background", {})["from"] = bg_from
    if bg_to:
      theme_patch.setdefault("theme", {}).setdefault("background", {})["to"] = bg_to
    spec = _deep_merge(spec, theme_patch)

  cfg_fonts = _settings_get(settings, ["cardnews", "fonts"], {})
  if isinstance(cfg_fonts, dict) and cfg_fonts:
    font_patch: dict[str, Any] = {"font": {}}
    title_name = str(cfg_fonts.get("title_name", "")).strip()
    body_name = str(cfg_fonts.get("body_name", "")).strip()
    footer_name = str(cfg_fonts.get("footer_name", "")).strip()
    if title_name:
      font_patch["font"]["title_name"] = title_name
      font_patch["font"]["title_path"] = ""
    if body_name:
      font_patch["font"]["body_name"] = body_name
      font_patch["font"]["body_path"] = ""
    if footer_name:
      font_patch["font"]["footer_name"] = footer_name
      font_patch["font"]["footer_path"] = ""
    if font_patch["font"]:
      font_patch["font"]["path"] = ""
      spec = _deep_merge(spec, font_patch)

  out_spec = write_instagram_spec(args.project, spec, out_format=args.format)
  print(str(out_spec))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
