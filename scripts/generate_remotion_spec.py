#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from generate_drafts import SalesInfo, parse_sales_info


def _now_stamp() -> str:
  return datetime.now().strftime("%Y%m%d-%H%M")


def _ensure_dir(p: Path) -> None:
  p.mkdir(parents=True, exist_ok=True)


def _first_nonempty(values: list[str]) -> str:
  for v in values:
    if str(v).strip():
      return str(v).strip()
  return ""


def _limit_list(values: list[str], n: int) -> list[str]:
  return [str(v).strip() for v in values if str(v).strip()][:n]


def _load_flow_manifest(path: Path) -> dict[str, Any]:
  raw = json.loads(path.read_text(encoding="utf-8"))
  if not isinstance(raw, dict):
    raise ValueError("Flow manifest root must be an object.")
  modules = raw.get("modules")
  if not isinstance(modules, list) or not modules:
    raise ValueError("Flow manifest must contain non-empty modules.")
  return raw


def _bernays_frame(si: SalesInfo) -> dict[str, str]:
  pain = si.pains[0] if si.pains else ""
  old_belief = _first_nonempty([si.current_alternatives, "기존 방식"])
  hidden_cost = _first_nonempty([si.pains[1] if len(si.pains) > 1 else "", "시간과 리스크"])
  new_standard = _first_nonempty([si.value_prop, si.one_liner, "새 기준"])
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


def _fit_font_profile(*, base: dict[str, dict[str, Any]], width: int, height: int) -> dict[str, dict[str, Any]]:
  scale = min(width, height) / 1080.0
  out: dict[str, dict[str, Any]] = {}
  for key, item in base.items():
    out[key] = {
      "family": str(item.get("family", "")).strip(),
      "weight": int(item.get("weight", 600)),
      "size": max(18, int(float(item.get("size", 42)) * scale)),
      "line_height": float(item.get("line_height", 1.2)),
    }
  return out


def _channel_profiles() -> dict[str, dict[str, Any]]:
  return {
    "instagram-reel": {"label": "Instagram Reel", "default_format": "square", "safe_area": {"top": 88, "right": 88, "bottom": 88, "left": 88}},
    "instagram-feed": {"label": "Instagram Feed", "default_format": "square", "safe_area": {"top": 86, "right": 86, "bottom": 106, "left": 86}},
    "threads-post": {"label": "Threads Feed", "default_format": "square", "safe_area": {"top": 88, "right": 88, "bottom": 120, "left": 88}},
    "linkedin-feed": {"label": "LinkedIn Feed", "default_format": "landscape", "safe_area": {"top": 84, "right": 144, "bottom": 84, "left": 144}},
    "youtube-short": {"label": "YouTube Short", "default_format": "square", "safe_area": {"top": 88, "right": 88, "bottom": 88, "left": 88}},
    "youtube-landscape": {"label": "YouTube Landscape", "default_format": "landscape", "safe_area": {"top": 80, "right": 180, "bottom": 80, "left": 180}},
  }


def _format_profiles() -> dict[str, dict[str, Any]]:
  return {
    "portrait": {"width": 1080, "height": 1920, "fps": 30, "safe_area": {"top": 160, "right": 88, "bottom": 210, "left": 88}},
    "square": {"width": 1080, "height": 1080, "fps": 30, "safe_area": {"top": 88, "right": 88, "bottom": 88, "left": 88}},
    "landscape": {"width": 1920, "height": 1080, "fps": 30, "safe_area": {"top": 78, "right": 170, "bottom": 78, "left": 170}},
  }


def _scene_weight(scene: dict[str, Any]) -> float:
  title = str(scene.get("title", "")).strip()
  lines = scene.get("lines", [])
  line_count = len(lines) if isinstance(lines, list) else 0
  return max(1.0, 1.0 + (len(title) * 0.01) + (line_count * 0.3))


def _allocate_scene_seconds(scenes: list[dict[str, Any]], total_seconds: float) -> list[float]:
  if not scenes:
    return []
  target = max(float(total_seconds), float(len(scenes)) * 2.2)
  weights = [_scene_weight(s) for s in scenes]
  weight_sum = sum(weights) or 1.0
  raw = [(w / weight_sum) * target for w in weights]
  clamped = [max(2.2, min(6.4, v)) for v in raw]
  delta = target - sum(clamped)
  i = 0
  while abs(delta) > 0.01 and scenes:
    idx = i % len(clamped)
    step = 0.1 if delta > 0 else -0.1
    next_value = clamped[idx] + step
    if 2.2 <= next_value <= 7.2:
      clamped[idx] = next_value
      delta -= step
    i += 1
    if i > 5000:
      break
  return [round(v, 2) for v in clamped]


def render_remotion_spec(
  si: SalesInfo,
  *,
  style: str,
  duration_seconds: float,
  video_format: str,
  channel_profile: str,
  device_profile: str,
  flow_video: Path | None = None,
  flow_manifest: dict[str, Any] | None = None,
  flow_title: str = "",
  flow_caption: str = "",
) -> dict[str, Any]:
  f = _bernays_frame(si)
  channels = _channel_profiles()
  channel = channels.get(channel_profile, channels["instagram-reel"])
  formats = _format_profiles()
  chosen_format = channel["default_format"] if video_format == "auto" else video_format
  fmt = formats.get(chosen_format, formats["portrait"])

  pain = _first_nonempty([f["pain"], si.pains[0] if si.pains else "", "문제가 반복되는 구조"])
  hidden_cost = _first_nonempty([f["hidden_cost"], "시간과 리스크"])
  new_standard = _first_nonempty([f["new_standard"], si.value_prop, si.one_liner, "새 기준"])
  cta = _first_nonempty([f["cta"], si.primary_cta, si.contact_channel, "문의/데모 요청"])

  if style == "comeback":
    scenes: list[dict[str, Any]] = [
      {"id": "cover", "title": _first_nonempty([si.one_liner, si.project_name, "최근 업데이트"]), "lines": ["짧게 핵심만 공유드립니다.", _first_nonempty([si.value_prop, new_standard])]},
      {"id": "problem", "title": "아직 남아있는 문제", "lines": _limit_list(si.pains, 3) or [pain, hidden_cost]},
      {"id": "approach", "title": "지금 적용 중인 방식", "lines": _limit_list([si.value_prop, *si.features], 3) or [new_standard]},
      {"id": "cta", "title": "다음 단계", "lines": [cta]},
    ]
  elif style == "plain":
    scenes = [
      {"id": "problem", "title": pain, "lines": _limit_list(si.pains, 3) or [hidden_cost]},
      {"id": "value", "title": "해결 기준", "lines": _limit_list([new_standard, si.value_prop], 2) or [new_standard]},
      {"id": "method", "title": "실행 방법", "lines": _limit_list(si.features, 3) or _limit_list(si.differentiators, 3) or ["(핵심 기능 추가)"]},
      {"id": "cta", "title": "CTA", "lines": [cta]},
    ]
  else:
    scenes = [
      {"id": "cover", "title": _first_nonempty([si.one_liner, si.value_prop, "새 기준"]), "lines": [f"기존 {f['old_belief']} 중심 사고를 재정의합니다."]},
      {"id": "pain", "title": "숨은 비용", "lines": _limit_list([hidden_cost, *si.pains], 3) or [hidden_cost]},
      {"id": "standard", "title": "새 방법", "lines": _limit_list([new_standard, *si.features], 3) or [new_standard]},
      {"id": "proof", "title": "근거", "lines": _limit_list([si.proof, *si.differentiators], 3) or ["(근거 추가)"]},
      {"id": "cta", "title": "다음 단계", "lines": [cta]},
    ]

  flow_recording: dict[str, Any] | None = None
  flow_recordings: list[dict[str, Any]] = []
  if isinstance(flow_manifest, dict):
    modules = flow_manifest.get("modules", [])
    if isinstance(modules, list):
      for i, module in enumerate(modules, start=1):
        if not isinstance(module, dict):
          continue
        video_path = str(module.get("video_path", "")).strip()
        if not video_path:
          continue
        module_id = str(module.get("id", "")).strip() or f"module-{i:02d}"
        title = _first_nonempty([str(module.get("title", "")).strip(), f"기능 데모 {i}"])
        caption = _first_nonempty([str(module.get("caption", "")).strip(), "실제 기능 흐름"])
        flow_recordings.append(
          {
            "id": module_id,
            "video_path": video_path,
            "title": title,
            "caption": caption,
            "fit": "cover",
          }
        )
    if flow_recordings:
      insert_at = max(1, len(scenes) - 1)
      for rec in flow_recordings:
        scenes.insert(
          insert_at,
          {
            "id": f"flow-demo-{rec['id']}",
            "kind": "flow-demo",
            "flow_module_id": rec["id"],
            "title": rec["title"],
            "lines": [rec["caption"]],
          },
        )
        insert_at += 1

  if flow_video is not None:
    flow_recording = {
      "video_path": str(flow_video),
      "title": _first_nonempty([flow_title, "실행 플로우 데모"]),
      "caption": _first_nonempty([flow_caption, "입력 플로우 기반 실제 화면"]),
      "fit": "cover",
    }
    if not flow_recordings:
      insert_at = max(1, len(scenes) - 1)
      scenes.insert(
        insert_at,
        {
          "id": "flow-demo",
          "kind": "flow-demo",
          "title": _first_nonempty([flow_title, "실행 플로우 데모"]),
          "lines": [_first_nonempty([flow_caption, "실제 동작 화면을 그대로 보여줍니다."])],
        },
      )

  scene_seconds = _allocate_scene_seconds(scenes, duration_seconds)
  timed_scenes: list[dict[str, Any]] = []
  at = 0.0
  for i, scene in enumerate(scenes):
    dur = scene_seconds[i] if i < len(scene_seconds) else 2.8
    start_at = round(at, 2)
    end_at = round(at + dur, 2)
    timed_scenes.append(
      {
        "id": scene.get("id", f"scene-{i+1}"),
        "kind": str(scene.get("kind", "")).strip() if str(scene.get("kind", "")).strip() else "text",
        "flow_module_id": str(scene.get("flow_module_id", "")).strip(),
        "title": str(scene.get("title", "")).strip(),
        "lines": _limit_list([str(x) for x in scene.get("lines", [])], 4),
        "start_sec": start_at,
        "end_sec": end_at,
      }
    )
    at = end_at

  mobile_base = {
    "title": {"family": "Pretendard", "weight": 700, "size": 86, "line_height": 1.08},
    "body": {"family": "Pretendard", "weight": 500, "size": 50, "line_height": 1.28},
    "caption": {"family": "Pretendard", "weight": 500, "size": 36, "line_height": 1.2},
  }
  desktop_base = {
    "title": {"family": "Pretendard", "weight": 700, "size": 78, "line_height": 1.1},
    "body": {"family": "Pretendard", "weight": 500, "size": 42, "line_height": 1.24},
    "caption": {"family": "Pretendard", "weight": 500, "size": 30, "line_height": 1.2},
  }
  font_base = mobile_base if device_profile == "mobile" else desktop_base
  fonts = _fit_font_profile(base=font_base, width=int(fmt["width"]), height=int(fmt["height"]))

  safe_area = dict(fmt["safe_area"])
  safe_area.update(channel.get("safe_area", {}))

  payload: dict[str, Any] = {
    "version": 1,
    "engine": "remotion",
    "style": style,
    "brand": {"name": si.project_name or "", "contact": si.contact_channel or "", "proof": si.proof or ""},
    "channel": {"id": channel_profile, "label": channel.get("label", channel_profile), "device_profile": device_profile, "format": chosen_format},
    "render": {"fps": int(fmt["fps"]), "width": int(fmt["width"]), "height": int(fmt["height"]), "duration_sec": round(at, 2), "safe_area": safe_area},
    "theme": {
      "background": {"kind": "solid", "color": "#FFFFFF", "from": "#FFFFFF", "to": "#F4F7FB"},
      "accent_primary": "#2563EB",
      "accent_secondary": "#0F172A",
      "panel_fill": "rgba(255,255,255,0.94)",
      "panel_border": "rgba(15,23,42,0.14)",
      "text_primary": "#0F172A",
      "text_dim": "#475569",
    },
    "fonts": {"profile": device_profile, "fallbacks": ["Pretendard", "Apple SD Gothic Neo", "Noto Sans KR", "sans-serif"], **fonts},
    "scenes": timed_scenes,
  }
  if flow_recording is not None:
    payload["flow_recording"] = flow_recording
  if flow_recordings:
    payload["flow_recordings"] = flow_recordings
  return payload


def write_remotion_spec(project_dir: Path, spec: dict[str, Any]) -> Path:
  out_dir = project_dir / "channels" / "instagram" / "remotion"
  _ensure_dir(out_dir)
  out_path = out_dir / f"{_now_stamp()}.json"
  out_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
  return out_path


def main() -> int:
  parser = argparse.ArgumentParser(description="Generate Remotion promo video spec from projects/<project>/SALES_INFO.md")
  parser.add_argument("--project", required=True, type=Path, help="Path like projects/<project-slug>")
  parser.add_argument("--style", default="bernays", choices=["bernays", "plain", "comeback"])
  parser.add_argument("--video-seconds", default=22.0, type=float)
  parser.add_argument("--video-format", default="square", choices=["auto", "portrait", "square", "landscape"])
  parser.add_argument("--channel-profile", default="instagram-reel", choices=["instagram-reel", "instagram-feed", "threads-post", "linkedin-feed", "youtube-short", "youtube-landscape"])
  parser.add_argument("--device-profile", default="mobile", choices=["mobile", "desktop"])
  parser.add_argument("--flow-video", default="", help="Optional local MP4 path recorded from real UI flow")
  parser.add_argument("--flow-manifest", default="", help="Optional flow manifest JSON from modular recordings")
  parser.add_argument("--flow-title", default="", help="Optional title for flow demo scene")
  parser.add_argument("--flow-caption", default="", help="Optional caption for flow demo scene")
  args = parser.parse_args()

  sales_path = args.project / "SALES_INFO.md"
  if not sales_path.exists():
    raise FileNotFoundError(f"Missing: {sales_path} (expected SALES_INFO.md)")

  flow_video: Path | None = None
  if str(args.flow_video).strip():
    flow_video = Path(str(args.flow_video).strip()).expanduser().resolve()
    if not flow_video.exists():
      raise FileNotFoundError(f"Missing flow video: {flow_video}")
    if flow_video.suffix.lower() not in {".mp4", ".mov", ".webm", ".m4v"}:
      raise ValueError(f"Unsupported flow video format: {flow_video.suffix}")

  flow_manifest: dict[str, Any] | None = None
  if str(args.flow_manifest).strip():
    manifest_path = Path(str(args.flow_manifest).strip()).expanduser().resolve()
    if not manifest_path.exists():
      raise FileNotFoundError(f"Missing flow manifest: {manifest_path}")
    flow_manifest = _load_flow_manifest(manifest_path)
    modules = flow_manifest.get("modules", [])
    if isinstance(modules, list):
      for i, module in enumerate(modules, start=1):
        if not isinstance(module, dict):
          raise ValueError(f"Invalid flow manifest modules[{i}]")
        vp = Path(str(module.get("video_path", "")).strip()).expanduser().resolve()
        if not vp.exists():
          raise FileNotFoundError(f"Missing flow module video: {vp}")

  si = parse_sales_info(sales_path)
  spec = render_remotion_spec(
    si,
    style=args.style,
    duration_seconds=max(8.0, min(90.0, float(args.video_seconds))),
    video_format=args.video_format,
    channel_profile=args.channel_profile,
    device_profile=args.device_profile,
    flow_video=flow_video,
    flow_manifest=flow_manifest,
    flow_title=str(args.flow_title).strip(),
    flow_caption=str(args.flow_caption).strip(),
  )
  out = write_remotion_spec(args.project, spec)
  print(str(out))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
