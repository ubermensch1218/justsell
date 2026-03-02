#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any
import re

from PIL import Image, ImageDraw, ImageFont
from PIL import ImageFilter


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSETS_FONTS_DIR = REPO_ROOT / "assets" / "fonts"


def _env(name: str) -> str:
  return os.environ.get(name, "").strip()


def _load_spec(path: Path) -> dict[str, Any]:
  raw = path.read_text(encoding="utf-8")
  suffix = path.suffix.lower()

  if suffix == ".json":
    data = json.loads(raw)
    if not isinstance(data, dict):
      raise ValueError("Spec root must be a JSON object")
    return data

  # Default: YAML (also accepts .yml/.yaml)
  try:
    import yaml  # type: ignore
  except Exception as e:  # pragma: no cover
    raise RuntimeError("PyYAML is required to read .yaml/.yml specs") from e

  data = yaml.safe_load(raw)
  if not isinstance(data, dict):
    raise ValueError("Spec root must be an object")
  return data


def _parse_color(hex_color: str) -> tuple[int, int, int]:
  s = hex_color.strip()
  if s.startswith("#"):
    s = s[1:]
  if len(s) != 6:
    raise ValueError(f"Invalid color: {hex_color}")
  return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def _parse_rgba(value: str) -> tuple[int, int, int, int]:
  v = value.strip()
  if v.startswith("#"):
    r, g, b = _parse_color(v)
    return (r, g, b, 255)
  m = __import__("re").match(r"^rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9.]+)\s*\)$", v)
  if not m:
    raise ValueError(f"Invalid color: {value}")
  r = int(m.group(1))
  g = int(m.group(2))
  b = int(m.group(3))
  a = float(m.group(4))
  if a <= 1:
    alpha = int(max(0.0, min(1.0, a)) * 255)
  else:
    alpha = int(max(0.0, min(255.0, a)))
  return (r, g, b, alpha)


def _resolve_font_path(spec_font_path: str | None) -> Path | None:
  env_path = os.environ.get("JUSTSELL_FONT_PATH", "").strip()
  candidates: list[str] = []
  if spec_font_path:
    candidates.append(spec_font_path)
  if env_path:
    candidates.append(env_path)
  candidates.extend(
    [
      # Common local project fonts
      "assets/fonts/Pretendard-Bold.ttf",
      "assets/fonts/Pretendard-Regular.ttf",
      "assets/fonts/Pretendard-Medium.ttf",
      "assets/fonts/Pretendard-SemiBold.ttf",
      "assets/fonts/NotoSansKR-Regular.ttf",
      # macOS common Korean fonts
      "/System/Library/Fonts/AppleSDGothicNeo.ttc",
      "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
      "/Library/Fonts/AppleSDGothicNeo.ttc",
      "/Library/Fonts/AppleGothic.ttf",
      # Linux common Noto CJK locations
      "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
      "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
      "/usr/share/fonts/opentype/noto/NotoSansCJKkr-Regular.otf",
    ]
  )

  for c in candidates:
    p = Path(c).expanduser()
    if p.exists():
      return p
    if not p.is_absolute():
      rp = (REPO_ROOT / p).expanduser()
      if rp.exists():
        return rp
  return None


def _norm_font_query(s: str) -> str:
  q = re.sub(r"[^a-z0-9]+", "", s.lower())
  # Common alias: some users type "GDmarket" but the file/face is often "Gmarket...".
  q = q.replace("gdmarket", "gmarket")
  return q


def _find_font_by_name(font_name: str) -> Path | None:
  # Resolve a font by a human-provided "name" (usually close to file name).
  # This is intentionally simple and local-first: search common font dirs and assets/fonts/.
  q = _norm_font_query(font_name.strip())
  if not q:
    return None

  search_dirs = [
    ASSETS_FONTS_DIR,
    Path.home() / "Library/Fonts",
    Path("/Library/Fonts"),
    Path("/System/Library/Fonts"),
    Path("/System/Library/Fonts/Supplemental"),
  ]

  candidates: list[Path] = []
  for d in search_dirs:
    try:
      if not d.exists():
        continue
      for p in d.rglob("*"):
        if not p.is_file():
          continue
        suf = p.suffix.lower()
        if suf not in [".ttf", ".otf", ".ttc"]:
          continue
        n = _norm_font_query(p.stem)
        if q == n:
          return p
        if q in n:
          candidates.append(p)
    except Exception:
      continue

  if not candidates:
    return None

  # Prefer shorter, "closer" matches (heuristic).
  candidates.sort(key=lambda p: (len(p.name), len(str(p))))
  return candidates[0]


def _resolve_font_from_spec(
  *,
  font_spec: dict[str, Any],
  key: str,
  fallback_path: Path | None,
  strict: bool,
) -> Path | None:
  # Priority:
  # 1) <key>_path
  # 2) <key>_name
  # 3) name (shared)
  # 4) path (shared)
  # 5) fallback_path
  path_value = str(font_spec.get(f"{key}_path", "")).strip()
  if path_value:
    return _resolve_font_path(path_value)

  name_value = str(font_spec.get(f"{key}_name", "")).strip()
  if name_value:
    found = _find_font_by_name(name_value)
    if found:
      return found
    if strict:
      raise RuntimeError(f"Font not found by name: {name_value} (key={key})")
    return fallback_path

  shared_name = str(font_spec.get("name", "")).strip()
  if shared_name:
    found = _find_font_by_name(shared_name)
    if found:
      return found
    if strict:
      raise RuntimeError(f"Font not found by name: {shared_name} (key={key}, shared)")
    return fallback_path

  shared_path = str(font_spec.get("path", "")).strip()
  if shared_path:
    return _resolve_font_path(shared_path) or fallback_path

  return fallback_path


def _load_font(
  path: Path | None,
  size: int,
  *,
  index: int | None = None,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
  if path is None:
    # Default bitmap font can't render Korean and will show tofu boxes.
    raise RuntimeError(
      "No Korean-capable font found. Set JUSTSELL_FONT_PATH or set font.path in the spec, "
      f"or place a .ttf/.ttc in {ASSETS_FONTS_DIR} (e.g. Pretendard/NotoSansKR)."
    )
  if index is None:
    return ImageFont.truetype(str(path), size=size)
  return ImageFont.truetype(str(path), size=size, index=index)


def _wrap_lines(
  draw: ImageDraw.ImageDraw,
  text: str,
  font: ImageFont.ImageFont,
  max_width: int,
) -> list[str]:
  words = text.split(" ")
  if len(words) == 1:
    # For CJK or no spaces, fall back to char-wrap.
    if draw.textlength(text, font=font) <= max_width:
      return [text]
    lines: list[str] = []
    current = ""
    for ch in text:
      trial = current + ch
      if trial and draw.textlength(trial, font=font) > max_width:
        lines.append(current)
        current = ch
      else:
        current = trial
    if current:
      lines.append(current)
    return lines

  lines: list[str] = []
  current = words[0]
  for w in words[1:]:
    trial = f"{current} {w}"
    if draw.textlength(trial, font=font) <= max_width:
      current = trial
    else:
      lines.append(current)
      current = w
  lines.append(current)
  return lines


def _build_gradient_bg(
  width: int,
  height: int,
  from_hex: str,
  to_hex: str,
) -> Image.Image:
  from_color = _parse_color(from_hex)
  to_color = _parse_color(to_hex)

  # Create an L gradient mask and blend two solid images
  try:
    mask = Image.linear_gradient("L")
  except Exception:  # pragma: no cover
    # Fallback for older Pillow
    mask = Image.new("L", (256, 256))
    for y in range(256):
      for x in range(256):
        mask.putpixel((x, y), int(y / 255 * 255))

  mask = mask.resize((1, height)).resize((width, height))
  a = Image.new("RGB", (width, height), from_color)
  b = Image.new("RGB", (width, height), to_color)
  return Image.composite(b, a, mask)


def _build_solid_bg(width: int, height: int, color_hex: str) -> Image.Image:
  return Image.new("RGB", (width, height), _parse_color(color_hex))


def _draw_glass_card(
  base: Image.Image,
  rect: tuple[int, int, int, int],
  radius: int,
  fill: tuple[int, int, int, int],
  border: tuple[int, int, int, int],
) -> None:
  overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
  od = ImageDraw.Draw(overlay)
  od.rounded_rectangle(rect, radius=radius, fill=fill, outline=border, width=2)
  base.alpha_composite(overlay)


def _draw_shadowed_panel(
  base: Image.Image,
  rect: tuple[int, int, int, int],
  radius: int,
  fill: tuple[int, int, int, int],
  border: tuple[int, int, int, int] | None,
  shadow_rgba: tuple[int, int, int, int] = (0, 0, 0, 60),
  shadow_offset: int = 18,
  shadow_spread: int = 18,
) -> None:
  # Cheap shadow: draw a few expanded rounded rects with decreasing alpha.
  overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
  od = ImageDraw.Draw(overlay)
  x1, y1, x2, y2 = rect

  if shadow_spread > 0 and shadow_rgba[3] > 0:
    steps = 6
    for i in range(steps):
      grow = int(shadow_spread * (i + 1) / steps)
      alpha = int(shadow_rgba[3] * (1 - (i / steps)) * 0.55)
      od.rounded_rectangle(
        (x1 - grow, y1 - grow + shadow_offset, x2 + grow, y2 + grow + shadow_offset),
        radius=radius + grow,
        fill=(shadow_rgba[0], shadow_rgba[1], shadow_rgba[2], alpha),
      )

  od.rounded_rectangle(rect, radius=radius, fill=fill, outline=border, width=2 if border else 0)
  base.alpha_composite(overlay)


def _cover_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
  src_w, src_h = img.size
  if src_w <= 0 or src_h <= 0:
    return img.resize((target_w, target_h))
  scale = max(target_w / src_w, target_h / src_h)
  new_w = max(1, int(round(src_w * scale)))
  new_h = max(1, int(round(src_h * scale)))
  resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
  left = max(0, (new_w - target_w) // 2)
  top = max(0, (new_h - target_h) // 2)
  return resized.crop((left, top, left + target_w, top + target_h))


def _paste_rounded_image(
  *,
  base: Image.Image,
  img: Image.Image,
  rect: tuple[int, int, int, int],
  radius: int,
  shadow: tuple[int, int, int, int] | None = (0, 0, 0, 70),
  shadow_blur: int = 18,
  shadow_offset: int = 18,
) -> None:
  x1, y1, x2, y2 = rect
  w = max(1, x2 - x1)
  h = max(1, y2 - y1)

  cropped = _cover_crop(img.convert("RGBA"), w, h)

  mask = Image.new("L", (w, h), 0)
  md = ImageDraw.Draw(mask)
  md.rounded_rectangle((0, 0, w, h), radius=radius, fill=255)

  overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
  if shadow and shadow[3] > 0:
    shadow_layer = Image.new("RGBA", (w, h), shadow)
    shadow_layer.putalpha(mask)
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=max(0, shadow_blur)))
    overlay.alpha_composite(shadow_layer, (x1, y1 + shadow_offset))

  cropped.putalpha(mask)
  overlay.alpha_composite(cropped, (x1, y1))
  base.alpha_composite(overlay)


def _draw_badge_pill(
  *,
  base: Image.Image,
  draw: ImageDraw.ImageDraw,
  x: int,
  y: int,
  text: str,
  font: ImageFont.ImageFont,
  fill: tuple[int, int, int, int],
  border: tuple[int, int, int, int] | None,
  text_fill: tuple[int, int, int],
  radius: int,
  padding_x: int,
  padding_y: int,
) -> tuple[int, int]:
  tw = _safe_textlength(draw, text, font)
  th = int(getattr(font, "size", 12))
  w = tw + padding_x * 2
  h = th + padding_y * 2

  overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
  od = ImageDraw.Draw(overlay)
  od.rounded_rectangle((x, y, x + w, y + h), radius=radius, fill=fill, outline=border, width=2 if border else 0)
  base.alpha_composite(overlay)

  tx = x + padding_x
  ty = y + padding_y - 2
  draw.text((tx, ty), text, font=font, fill=text_fill)
  return (w, h)


def _safe_textlength(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
  try:
    return int(draw.textlength(text, font=font))
  except Exception:  # pragma: no cover
    return len(text) * int(getattr(font, "size", 12))


def _draw_wrapped_paragraph(
  *,
  draw: ImageDraw.ImageDraw,
  x: int,
  y: int,
  text: str,
  font: ImageFont.ImageFont,
  fill: tuple[int, int, int],
  max_width: int,
  line_spacing: int,
) -> int:
  wrapped: list[str] = []
  for line in text.split("\n"):
    wrapped.extend(_wrap_lines(draw, line, font, max_width))
  for line in wrapped:
    draw.text((x, y), line, font=font, fill=fill)
    y += int(getattr(font, "size", 12)) + line_spacing
  return y


def _draw_bullets(
  *,
  draw: ImageDraw.ImageDraw,
  x: int,
  y: int,
  items: list[str],
  font: ImageFont.ImageFont,
  text_fill: tuple[int, int, int],
  dot_fill: tuple[int, int, int],
  max_width: int,
  line_spacing: int,
  bullet_gap: int = 10,
  dot_radius: int = 5,
  indent: int = 28,
) -> int:
  for raw in items:
    text = raw.strip()
    if not text:
      continue
    wrapped = _wrap_lines(draw, text, font, max_width - indent)

    # Dot aligned to first line.
    cy = y + int(getattr(font, "size", 12)) // 2
    draw.ellipse((x, cy - dot_radius, x + dot_radius * 2, cy + dot_radius), fill=dot_fill)

    tx = x + indent
    for i, line in enumerate(wrapped):
      draw.text((tx, y), line, font=font, fill=text_fill)
      y += int(getattr(font, "size", 12)) + line_spacing
      if i == 0:
        # after first line, align subsequent lines to text indent
        pass
    y += bullet_gap
  return y


def _draw_pills(
  *,
  base: Image.Image,
  draw: ImageDraw.ImageDraw,
  x: int,
  y: int,
  items: list[str],
  font: ImageFont.ImageFont,
  text_fill: tuple[int, int, int],
  pill_fill: tuple[int, int, int, int],
  pill_border: tuple[int, int, int, int] | None,
  max_width: int,
  line_spacing: int,
  pill_radius: int = 26,
  padding_x: int = 28,
  padding_y: int = 18,
  gap: int = 18,
) -> int:
  for raw in items:
    text = raw.strip()
    if not text:
      continue
    wrapped = _wrap_lines(draw, text, font, max_width - padding_x * 2)
    line_h = int(getattr(font, "size", 12)) + line_spacing
    pill_h = padding_y * 2 + line_h * len(wrapped) - line_spacing
    rect = (x, y, x + max_width, y + pill_h)

    # Draw pill on separate overlay for alpha.
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle(rect, radius=pill_radius, fill=pill_fill, outline=pill_border, width=1 if pill_border else 0)
    base.alpha_composite(overlay)

    ty = y + padding_y
    for line in wrapped:
      draw.text((x + padding_x, ty), line, font=font, fill=text_fill)
      ty += line_h

    y += pill_h + gap
  return y


def render_cardnews(spec_path: Path, out_dir: Path) -> list[Path]:
  spec_path = spec_path.expanduser().resolve()
  spec = _load_spec(spec_path)

  canvas = spec.get("canvas", {})
  theme = spec.get("theme", {})
  brand = spec.get("brand", {})
  font_spec = spec.get("font", {})
  layout = spec.get("layout", {})
  slides = spec.get("slides", [])

  if (
    not isinstance(canvas, dict)
    or (theme is not None and not isinstance(theme, dict))
    or (brand is not None and not isinstance(brand, dict))
    or not isinstance(font_spec, dict)
    or not isinstance(layout, dict)
  ):
    raise ValueError("canvas/theme/brand/font/layout must be objects")
  if not isinstance(slides, list) or not slides:
    raise ValueError("slides must be a non-empty list")

  width = int(canvas.get("width", 1080))
  height = int(canvas.get("height", 1350))

  # Theme (dhmag-ish defaults)
  bg_kind = "gradient"
  bg_from = "#050505"
  bg_to = "#0B0F19"
  bg_solid = "#0B0F19"
  accent_primary = "#FF3B30"
  accent_secondary = "#5856D6"
  card_fill = "rgba(255,255,255,0.03)"
  card_border = "rgba(255,255,255,0.08)"
  card_radius = 40
  panel_fill = "#121212"
  panel_border = "rgba(255,255,255,0.0)"
  text_title = "#FFFFFF"
  text_body = "#FFFFFF"
  text_dim = "#A0A0A0"
  cover_fill = accent_primary
  cover_text = "#111111"
  cover_dim = "rgba(0,0,0,0.65)"
  pill_fill = "rgba(255,255,255,0.06)"
  pill_border = "rgba(255,255,255,0.10)"
  pill_radius = 26
  pill_max_width_ratio = 1.0
  bullet_gap = 18
  bullet_indent = 28
  bullet_dot_radius = 5
  cover_subtitle_gap = 120
  title_rule_width = 180
  title_rule_height = 6
  title_rule_gap = 26
  badge_fill = "rgba(17,17,17,0.92)"
  badge_border = "rgba(255,255,255,0.0)"
  badge_text = "#FFFFFF"
  badge_radius = 999
  badge_padding_x = 26
  badge_padding_y = 14
  badge_gap = 30
  accent_bar_width = 10
  accent_bar_gap = 24
  slide_number_position = "bottom_left"
  slide_number_pad = 2
  slide_number_sep = " / "
  slide_number_margin_x = 0
  slide_number_margin_y = 0
  slide_number_color_override = ""
  slide_number_font_size: int | None = None

  if isinstance(theme, dict) and theme:
    bg = theme.get("background", {})
    if isinstance(bg, dict):
      kind = str(bg.get("kind", "gradient"))
      if kind == "solid":
        bg_kind = "solid"
        bg_solid = str(bg.get("color", bg_solid))
      elif kind == "gradient":
        bg_kind = "gradient"
        bg_from = str(bg.get("from", bg_from))
        bg_to = str(bg.get("to", bg_to))
    accent_primary = str(theme.get("accent_primary", accent_primary))
    accent_secondary = str(theme.get("accent_secondary", accent_secondary))
    card = theme.get("card", {})
    if isinstance(card, dict):
      card_fill = str(card.get("fill", card_fill))
      card_border = str(card.get("border", card_border))
      card_radius = int(card.get("radius", card_radius))
    panel = theme.get("panel", {})
    if isinstance(panel, dict):
      panel_fill = str(panel.get("fill", panel_fill))
      panel_border = str(panel.get("border", panel_border))
      card_radius = int(panel.get("radius", card_radius))
    text = theme.get("text", {})
    if isinstance(text, dict):
      text_title = str(text.get("title", text_title))
      text_body = str(text.get("body", text_body))
      text_dim = str(text.get("dim", text_dim))
    cover = theme.get("cover", {})
    if isinstance(cover, dict):
      cover_fill = str(cover.get("fill", cover_fill))
      cover_text = str(cover.get("text", cover_text))
      cover_dim = str(cover.get("dim", cover_dim))
    pills = theme.get("pills", {})
    if isinstance(pills, dict):
      pill_fill = str(pills.get("fill", pill_fill))
      pill_border = str(pills.get("border", pill_border))
      pill_radius = int(pills.get("radius", pill_radius))
      try:
        pill_max_width_ratio = float(pills.get("max_width_ratio", pill_max_width_ratio))
      except Exception:
        pill_max_width_ratio = pill_max_width_ratio
    bullets = theme.get("bullets", {})
    if isinstance(bullets, dict):
      bullet_gap = int(bullets.get("gap", bullet_gap))
      bullet_indent = int(bullets.get("indent", bullet_indent))
      bullet_dot_radius = int(bullets.get("dot_radius", bullet_dot_radius))
    cover_layout = theme.get("cover_layout", {})
    if isinstance(cover_layout, dict):
      cover_subtitle_gap = int(cover_layout.get("subtitle_gap", cover_subtitle_gap))
    title_rule = theme.get("title_rule", {})
    if isinstance(title_rule, dict):
      title_rule_width = int(title_rule.get("width", title_rule_width))
      title_rule_height = int(title_rule.get("height", title_rule_height))
      title_rule_gap = int(title_rule.get("gap", title_rule_gap))
    badge = theme.get("badge", {})
    if isinstance(badge, dict):
      badge_fill = str(badge.get("fill", badge_fill))
      badge_border = str(badge.get("border", badge_border))
      badge_text = str(badge.get("text", badge_text))
      badge_radius = int(badge.get("radius", badge_radius))
      badge_padding_x = int(badge.get("padding_x", badge_padding_x))
      badge_padding_y = int(badge.get("padding_y", badge_padding_y))
      badge_gap = int(badge.get("gap", badge_gap))
    accent_bar = theme.get("accent_bar", {})
    if isinstance(accent_bar, dict):
      accent_bar_width = int(accent_bar.get("width", accent_bar_width))
      accent_bar_gap = int(accent_bar.get("gap", accent_bar_gap))

  # Env overrides (marketing-wide theming)
  # Use this when you want a per-run/per-client "key color" without touching specs.
  env_accent_primary = _env("JUSTSELL_ACCENT_PRIMARY")
  env_accent_secondary = _env("JUSTSELL_ACCENT_SECONDARY")
  env_cover_fill = _env("JUSTSELL_COVER_FILL")
  env_panel_fill = _env("JUSTSELL_PANEL_FILL")
  env_bg_kind = _env("JUSTSELL_BG_KIND")  # solid|gradient
  env_bg_solid = _env("JUSTSELL_BG_SOLID")
  env_bg_from = _env("JUSTSELL_BG_FROM")
  env_bg_to = _env("JUSTSELL_BG_TO")

  if env_accent_primary:
    accent_primary = env_accent_primary
  if env_accent_secondary:
    accent_secondary = env_accent_secondary
  if env_cover_fill:
    cover_fill = env_cover_fill
  if env_panel_fill:
    panel_fill = env_panel_fill
  if env_bg_kind in ["solid", "gradient"]:
    bg_kind = env_bg_kind
  if env_bg_solid:
    bg_solid = env_bg_solid
  if env_bg_from:
    bg_from = env_bg_from
  if env_bg_to:
    bg_to = env_bg_to

  # Backward compatible solid background
  solid_bg = canvas.get("background", None)

  # Font resolution:
  # - You can set explicit file paths (<key>_path), or provide human-friendly names (<key>_name).
  # - Example:
  #   font:
  #     title_name: "GDmarket Bold"
  #     body_name: "Pretendard Regular"
  #     footer_name: "Pretendard Regular"
  # - Fallback: env `JUSTSELL_FONT_PATH` or common Korean-capable system fonts.
  strict_fonts = str(font_spec.get("strict", "")).strip().lower() in ["1", "true", "yes", "on"] or _env("JUSTSELL_STRICT_FONTS").lower() in ["1", "true", "yes", "on"]
  debug_fonts = _env("JUSTSELL_DEBUG_FONTS").lower() in ["1", "true", "yes", "on"]

  font_path = _resolve_font_path(str(font_spec.get("path", "")).strip() or None)
  title_font_path = _resolve_font_from_spec(font_spec=font_spec, key="title", fallback_path=font_path, strict=strict_fonts)
  body_font_path = _resolve_font_from_spec(font_spec=font_spec, key="body", fallback_path=font_path, strict=strict_fonts)
  footer_font_path = _resolve_font_from_spec(font_spec=font_spec, key="footer", fallback_path=font_path, strict=strict_fonts)

  if debug_fonts:
    print(f"[fonts] title={title_font_path} body={body_font_path} footer={footer_font_path}")

  default_index = font_spec.get("index", None)
  title_index = font_spec.get("title_index", default_index)
  body_index = font_spec.get("body_index", default_index)
  footer_index = font_spec.get("footer_index", default_index)

  title_font = _load_font(title_font_path, int(font_spec.get("title_size", 80)), index=int(title_index) if title_index is not None else None)
  body_font = _load_font(body_font_path, int(font_spec.get("body_size", 48)), index=int(body_index) if body_index is not None else None)
  subtitle_font = _load_font(
    body_font_path,
    int(font_spec.get("subtitle_size", int(font_spec.get("body_size", 48)) - 8)),
    index=int(body_index) if body_index is not None else None,
  )
  footer_font = _load_font(footer_font_path, int(font_spec.get("footer_size", 32)), index=int(footer_index) if footer_index is not None else None)

  padding = int(layout.get("padding", 90))
  card_padding = int(layout.get("card_padding", 72))
  line_spacing = int(layout.get("line_spacing", 16))
  bullet_prefix = str(layout.get("bullet_prefix", "- "))
  show_slide_number = bool(layout.get("show_slide_number", False))
  slide_number = layout.get("slide_number", {})
  if isinstance(slide_number, dict):
    show_slide_number = bool(slide_number.get("enabled", show_slide_number))
    slide_number_position = str(slide_number.get("position", slide_number_position)).strip().lower()
    slide_number_pad = int(slide_number.get("pad", slide_number_pad))
    slide_number_sep = str(slide_number.get("sep", slide_number_sep))
    slide_number_margin_x = int(slide_number.get("margin_x", slide_number_margin_x))
    slide_number_margin_y = int(slide_number.get("margin_y", slide_number_margin_y))
    slide_number_color_override = str(slide_number.get("color", slide_number_color_override)).strip()
    if "font_size" in slide_number:
      try:
        slide_number_font_size = int(slide_number.get("font_size"))
      except Exception:
        slide_number_font_size = slide_number_font_size
  default_footer_align = str(layout.get("footer_align", "left")).strip().lower()

  title_color = _parse_color(text_title)
  body_color = _parse_color(text_body)
  dim_color = _parse_color(text_dim)
  cover_title_color = _parse_color(cover_text)
  cover_body_color = _parse_color(cover_text)
  cover_dim_color = _parse_rgba(cover_dim)
  accent_primary_rgb = _parse_color(accent_primary)
  accent_secondary_rgb = _parse_color(accent_secondary)

  brand_name = ""
  brand_contact = ""
  if isinstance(brand, dict):
    brand_name = str(brand.get("name", "")).strip()
    brand_contact = str(brand.get("contact", "")).strip()

  use_kinds = any(isinstance(s, dict) and "kind" in s for s in slides) or (isinstance(theme, dict) and "panel" in theme)

  out_dir.mkdir(parents=True, exist_ok=True)

  outputs: list[Path] = []
  for idx, slide in enumerate(slides, start=1):
    if not isinstance(slide, dict):
      raise ValueError("Each slide must be an object")
    kind = str(slide.get("kind", "")).strip().lower()
    title = str(slide.get("title", "")).strip()
    body = slide.get("body", [])
    footer = str(slide.get("footer", "")).strip()
    footer_align = str(slide.get("footer_align", default_footer_align)).strip().lower()
    if footer_align not in ["left", "center", "right"]:
      footer_align = "left"

    if not isinstance(body, list):
      raise ValueError("slide.body must be a list of strings")
    body_lines = [str(x) for x in body if str(x).strip()]
    badge = slide.get("badge", None)
    image_spec = slide.get("image", None)
    callout = slide.get("callout", None)
    accent_bar = slide.get("accent_bar", None)
    slide_bg = slide.get("background", None)
    slide_title_color_override = str(slide.get("title_color", "")).strip()
    slide_body_color_override = str(slide.get("body_color", "")).strip()
    slide_dim_color_override = str(slide.get("dim_color", "")).strip()
    slide_number_color_this_slide = str(slide.get("slide_number_color", "")).strip()

    if isinstance(slide_bg, dict):
      sb_kind = str(slide_bg.get("kind", "")).strip().lower()
      if sb_kind == "solid":
        base = _build_solid_bg(width, height, str(slide_bg.get("color", bg_solid)))
      elif sb_kind == "gradient":
        base = _build_gradient_bg(
          width,
          height,
          str(slide_bg.get("from", bg_from)),
          str(slide_bg.get("to", bg_to)),
        )
      else:
        base = _build_solid_bg(width, height, bg_solid)
    else:
      if solid_bg:
        base = _build_solid_bg(width, height, str(solid_bg))
      elif bg_kind == "solid":
        base = _build_solid_bg(width, height, bg_solid)
      else:
        base = _build_gradient_bg(width, height, bg_from, bg_to)
    img = base.convert("RGBA")
    draw = ImageDraw.Draw(img)

    card_rect = (padding, padding, width - padding, height - padding)
    if not use_kinds:
      _draw_glass_card(
        img,
        rect=card_rect,
        radius=card_radius,
        fill=_parse_rgba(card_fill),
        border=_parse_rgba(card_border),
      )
    else:
      if kind == "cover":
        fill = _parse_rgba(str(slide.get("cover_fill", cover_fill)))
        border = None
      else:
        fill = _parse_rgba(str(slide.get("panel_fill", panel_fill)))
        border_raw = str(slide.get("panel_border", panel_border)).strip()
        border = _parse_rgba(border_raw) if border_raw else None
      full_bleed = padding <= 0
      _draw_shadowed_panel(
        img,
        rect=card_rect,
        radius=card_radius,
        fill=fill,
        border=border,
        shadow_offset=0 if full_bleed else 18,
        shadow_spread=0 if full_bleed else 18,
      )

    x = padding + card_padding
    y = padding + card_padding
    max_width = width - (padding + card_padding) * 2
    content_x = x
    content_max_width = max_width

    # Per-slide text color overrides (useful for light slides)
    slide_title_color = title_color
    slide_body_color = body_color
    slide_dim_color = dim_color
    if slide_title_color_override:
      try:
        slide_title_color = _parse_color(slide_title_color_override)
      except Exception:
        slide_title_color = slide_title_color
    if slide_body_color_override:
      try:
        slide_body_color = _parse_color(slide_body_color_override)
      except Exception:
        slide_body_color = slide_body_color
    if slide_dim_color_override:
      try:
        slide_dim_color = _parse_color(slide_dim_color_override)
      except Exception:
        slide_dim_color = slide_dim_color

    # Optional badge pill (top-left)
    if badge:
      badge_text_value = ""
      badge_cfg: dict[str, Any] = {}
      if isinstance(badge, str):
        badge_text_value = badge.strip()
      elif isinstance(badge, dict):
        badge_text_value = str(badge.get("text", "")).strip()
        badge_cfg = badge
      else:
        badge_text_value = str(badge).strip()

      if badge_text_value:
        badge_font = _load_font(
          footer_font_path,
          int(badge_cfg.get("font_size", int(getattr(footer_font, "size", 32)))),
          index=int(footer_index) if footer_index is not None else None,
        )
        bw, bh = _draw_badge_pill(
          base=img,
          draw=draw,
          x=int(badge_cfg.get("x", x)),
          y=int(badge_cfg.get("y", y)),
          text=badge_text_value,
          font=badge_font,
          fill=_parse_rgba(str(badge_cfg.get("fill", badge_fill))),
          border=_parse_rgba(str(badge_cfg.get("border", badge_border))) if str(badge_cfg.get("border", badge_border)).strip() else None,
          text_fill=_parse_color(str(badge_cfg.get("text_color", badge_text))),
          radius=int(badge_cfg.get("radius", badge_radius)),
          padding_x=int(badge_cfg.get("padding_x", badge_padding_x)),
          padding_y=int(badge_cfg.get("padding_y", badge_padding_y)),
        )
        y = max(y, int(badge_cfg.get("y", y)) + bh + int(badge_cfg.get("gap", badge_gap)))

    # Title
    title_bottom_y = y

    if title:
      title_wrapped: list[str] = []
      for line in title.split("\n"):
        title_wrapped.extend(_wrap_lines(draw, line, title_font, content_max_width))

      # Optional left accent bar for title block
      use_accent_bar = False
      bar_cfg: dict[str, Any] = {}
      if accent_bar is True:
        use_accent_bar = True
      elif isinstance(accent_bar, dict):
        use_accent_bar = bool(accent_bar.get("enabled", True))
        bar_cfg = accent_bar
      elif isinstance(accent_bar, str):
        use_accent_bar = accent_bar.strip().lower() in ["1", "true", "yes", "on"]

      title_x = content_x
      bar_w = int(bar_cfg.get("width", accent_bar_width))
      bar_gap = int(bar_cfg.get("gap", accent_bar_gap))
      if use_accent_bar:
        title_x = x + bar_w + bar_gap
        content_x = title_x
        content_max_width = width - (padding + card_padding) * 2 - (bar_w + bar_gap)
        # Re-wrap with adjusted width
        title_wrapped = []
        for line in title.split("\n"):
          title_wrapped.extend(_wrap_lines(draw, line, title_font, content_max_width))

        block_h = len(title_wrapped) * (int(getattr(title_font, "size", 12)) + line_spacing) - line_spacing
        bar_h = int(bar_cfg.get("height", max(120, block_h)))
        bar_y = int(bar_cfg.get("y", y))
        bar_color = _parse_color(str(bar_cfg.get("color", accent_primary)))
        draw.rounded_rectangle(
          (x, bar_y, x + bar_w, bar_y + bar_h),
          radius=min(bar_w // 2, 12),
          fill=bar_color,
        )

      for line in title_wrapped:
        draw.text((title_x, y), line, font=title_font, fill=cover_title_color if (use_kinds and kind == "cover") else slide_title_color)
        y += int(getattr(title_font, "size", 12)) + line_spacing
      title_bottom_y = y
      y += line_spacing * 2

      # Title rule (under-title short line, like the reference)
      rule_color = cover_title_color if (use_kinds and kind == "cover") else accent_primary_rgb
      rule_w = min(title_rule_width, content_max_width)
      rule_h = title_rule_height
      rule_y = y - line_spacing - rule_h  # under title block
      if rule_w > 0 and rule_h > 0:
        draw.rounded_rectangle((title_x, rule_y, title_x + rule_w, rule_y + rule_h), radius=max(0, rule_h // 2), fill=rule_color)
        y += title_rule_gap

    # Body
    if not use_kinds:
      for raw in body_lines:
        text = raw
        if bullet_prefix.strip() and not text.startswith(bullet_prefix.strip()):
          text = f"{bullet_prefix}{text}"
        y = _draw_wrapped_paragraph(
          draw=draw,
          x=content_x,
          y=y,
          text=text,
          font=body_font,
          fill=slide_body_color,
          max_width=content_max_width,
          line_spacing=line_spacing,
        )
        y += line_spacing
    else:
      if kind == "pills":
        pills_width = int(content_max_width * max(0.5, min(1.0, pill_max_width_ratio)))
        y = _draw_pills(
          base=img,
          draw=draw,
          x=content_x,
          y=y,
          items=body_lines,
          font=body_font,
          text_fill=slide_body_color,
          pill_fill=_parse_rgba(pill_fill),
          pill_border=_parse_rgba(pill_border) if pill_border else None,
          max_width=pills_width,
          line_spacing=line_spacing,
          pill_radius=pill_radius,
        )
      elif kind == "cover":
        # Cover subtitle: place near bottom like the reference, avoiding footer overlap.
        subtitle_lines: list[str] = []
        for raw in body_lines:
          subtitle_lines.extend(_wrap_lines(draw, raw, subtitle_font, content_max_width))

        sub_line_h = int(getattr(subtitle_font, "size", 12)) + max(8, line_spacing - 4)
        subtitle_h = max(0, len(subtitle_lines) * sub_line_h - max(8, line_spacing - 4))

        footer_text_for_measure = ""
        if footer:
          footer_text_for_measure = footer
        elif brand_name:
          footer_text_for_measure = brand_name
        if brand_contact:
          footer_text_for_measure = f"{footer_text_for_measure}  ·  {brand_contact}".strip("  ·")

        footer_lines_for_measure = _wrap_lines(draw, footer_text_for_measure, footer_font, content_max_width) if footer_text_for_measure else []
        footer_h = len(footer_lines_for_measure) * (int(getattr(footer_font, "size", 12)) + line_spacing)

        target_y = height - card_padding - footer_h - subtitle_h - cover_subtitle_gap
        y_sub = max(y + 24, target_y)
        for line in subtitle_lines:
          draw.text((content_x, y_sub), line, font=subtitle_font, fill=(cover_dim_color[0], cover_dim_color[1], cover_dim_color[2]))
          y_sub += sub_line_h
      else:
        y = _draw_bullets(
          draw=draw,
          x=content_x,
          y=y,
          items=body_lines,
          font=body_font,
          text_fill=slide_body_color,
          dot_fill=accent_primary_rgb,
          max_width=content_max_width,
          line_spacing=line_spacing,
          bullet_gap=bullet_gap,
          dot_radius=bullet_dot_radius,
          indent=bullet_indent,
        )

    # Optional image (e.g. product/photo)
    if isinstance(image_spec, dict):
      image_path = str(image_spec.get("path", "")).strip()
      if image_path:
        p = Path(image_path)
        if not p.is_absolute():
          p = (spec_path.parent / p).resolve()
        if p.exists():
          try:
            rect_list = image_spec.get("rect", None)
            if isinstance(rect_list, (list, tuple)) and len(rect_list) == 4:
              rect = (int(rect_list[0]), int(rect_list[1]), int(rect_list[2]), int(rect_list[3]))
            else:
              # Default: bottom-right square-ish
              iw = int(image_spec.get("width", 520))
              ih = int(image_spec.get("height", 520))
              ix2 = width - padding - card_padding
              iy2 = height - padding - card_padding - 120
              rect = (ix2 - iw, iy2 - ih, ix2, iy2)
            radius = int(image_spec.get("radius", 40))
            shadow = image_spec.get("shadow", True)
            shadow_rgba = (0, 0, 0, 70) if shadow else None
            _paste_rounded_image(base=img, img=Image.open(p), rect=rect, radius=radius, shadow=shadow_rgba)
          except Exception:
            pass

    # Optional callout box (e.g. TIP)
    if isinstance(callout, dict):
      callout_text = str(callout.get("text", "")).strip()
      callout_lines = callout.get("lines", None)
      if not callout_text and isinstance(callout_lines, list):
        callout_text = "\n".join([str(x).strip() for x in callout_lines if str(x).strip()])
      if callout_text:
        rect_list = callout.get("rect", None)
        if isinstance(rect_list, (list, tuple)) and len(rect_list) == 4:
          rect = (int(rect_list[0]), int(rect_list[1]), int(rect_list[2]), int(rect_list[3]))
        else:
          rect = (padding + card_padding, height - padding - card_padding - 260, width - padding - card_padding, height - padding - card_padding - 120)

        radius = int(callout.get("radius", 28))
        fill = _parse_rgba(str(callout.get("fill", "rgba(255,255,255,0.10)")))
        border_raw = str(callout.get("border", "")).strip()
        border = _parse_rgba(border_raw) if border_raw else None
        text_fill = _parse_color(str(callout.get("text_color", "#111111")))
        callout_font = _load_font(
          body_font_path,
          int(callout.get("font_size", int(getattr(body_font, "size", 48)) - 10)),
          index=int(body_index) if body_index is not None else None,
        )

        _draw_shadowed_panel(base=img, rect=rect, radius=radius, fill=fill, border=border, shadow_rgba=(0, 0, 0, 40), shadow_offset=10, shadow_spread=10)
        cx1, cy1, cx2, cy2 = rect
        padding_x = int(callout.get("padding_x", 34))
        padding_y = int(callout.get("padding_y", 28))
        _draw_wrapped_paragraph(
          draw=draw,
          x=cx1 + padding_x,
          y=cy1 + padding_y,
          text=callout_text,
          font=callout_font,
          fill=text_fill,
          max_width=(cx2 - cx1) - padding_x * 2,
          line_spacing=line_spacing,
        )

    # Footer (inside card, bottom)
    footer_text = footer or ""
    if brand_name and not footer_text:
      footer_text = brand_name
    if brand_contact:
      footer_text = f"{footer_text}  ·  {brand_contact}".strip("  ·")

    if footer_text:
      footer_lines = _wrap_lines(draw, footer_text, footer_font, max_width)
      footer_height = len(footer_lines) * (int(footer_font.size) + line_spacing)
      fy = height - padding - card_padding - footer_height
      for line in footer_lines:
        fx = x
        if footer_align == "center":
          fx = x + (max_width - _safe_textlength(draw, line, footer_font)) // 2
        elif footer_align == "right":
          fx = x + (max_width - _safe_textlength(draw, line, footer_font))
        if use_kinds and kind == "cover":
          draw.text((fx, fy), line, font=footer_font, fill=(cover_dim_color[0], cover_dim_color[1], cover_dim_color[2]))
        else:
          draw.text((fx, fy), line, font=footer_font, fill=slide_dim_color)
        fy += int(footer_font.size) + line_spacing

    if show_slide_number:
      pad = max(0, int(slide_number_pad))
      if pad <= 1:
        slide_label = f"{idx}{slide_number_sep}{len(slides)}"
      else:
        slide_label = f"{str(idx).zfill(pad)}{slide_number_sep}{str(len(slides)).zfill(pad)}"

      sn_font = footer_font
      if slide_number_font_size and slide_number_font_size > 0:
        sn_font = _load_font(footer_font_path, slide_number_font_size, index=int(footer_index) if footer_index is not None else None)
      label_w = _safe_textlength(draw, slide_label, sn_font)
      label_h = int(getattr(sn_font, "size", 12))

      pos = slide_number_position
      if pos == "bottom_left":
        lx = padding + card_padding + slide_number_margin_x
        ly = height - padding - card_padding - label_h + slide_number_margin_y
      else:
        lx = width - padding - card_padding - label_w + slide_number_margin_x
        ly = padding + card_padding - 48 + slide_number_margin_y

      sn_color = slide_dim_color
      if slide_number_color_this_slide:
        try:
          sn_color = _parse_color(slide_number_color_this_slide)
        except Exception:
          sn_color = sn_color
      elif slide_number_color_override:
        try:
          sn_color = _parse_color(slide_number_color_override)
        except Exception:
          sn_color = sn_color
      draw.text((lx, ly), slide_label, font=sn_font, fill=sn_color)

    out_path = out_dir / f"{spec_path.stem}-{idx:02d}.png"
    img.convert("RGB").save(out_path)
    outputs.append(out_path)

  return outputs


def main() -> int:
  parser = argparse.ArgumentParser(description="Render Instagram cardnews PNGs from YAML spec.")
  parser.add_argument("--spec", required=True, type=Path, help="Path to YAML spec")
  parser.add_argument("--out", required=True, type=Path, help="Output directory")
  args = parser.parse_args()

  outputs = render_cardnews(args.spec, args.out)
  for p in outputs:
    print(str(p))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
