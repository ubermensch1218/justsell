import React from "react";
import {
  AbsoluteFill,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const fadeOut = (frame, duration) =>
  interpolate(frame, [Math.max(0, duration - 12), duration], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

const Scene = ({scene, spec, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const theme = spec.theme || {};
  const fonts = spec.fonts || {};
  const safe = spec.render?.safe_area || {top: 0, right: 0, bottom: 0, left: 0};
  const enter = spring({
    fps,
    frame,
    config: {
      damping: 18,
      stiffness: 120,
      mass: 0.8,
    },
  });
  const opacity = Math.min(1, enter) * fadeOut(frame, durationInFrames);
  const translateY = interpolate(enter, [0, 1], [26, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        paddingTop: safe.top,
        paddingRight: safe.right,
        paddingBottom: safe.bottom,
        paddingLeft: safe.left,
      }}
    >
      <AbsoluteFill
        style={{
          justifyContent: "space-between",
          borderRadius: 28,
          border: `1px solid ${theme.panel_border || "rgba(255,255,255,0.12)"}`,
          background: theme.panel_fill || "rgba(255,255,255,0.05)",
          padding: 44,
          opacity,
          transform: `translateY(${translateY}px)`,
        }}
      >
        <div
          style={{
            fontFamily: fonts.title?.family || "sans-serif",
            fontWeight: fonts.title?.weight || 700,
            fontSize: fonts.title?.size || 72,
            lineHeight: fonts.title?.line_height || 1.08,
            color: theme.text_primary || "#FFFFFF",
            letterSpacing: "-0.02em",
            whiteSpace: "pre-wrap",
          }}
        >
          {scene.title}
        </div>
        <div style={{display: "grid", gap: 14}}>
          {(scene.lines || []).map((line, i) => {
            return (
              <div
                key={`line-${scene.id}-${i}`}
                style={{
                  fontFamily: fonts.body?.family || "sans-serif",
                  fontWeight: fonts.body?.weight || 500,
                  fontSize: fonts.body?.size || 44,
                  lineHeight: fonts.body?.line_height || 1.24,
                  color: i === 0 ? (theme.text_primary || "#FFFFFF") : (theme.text_dim || "#A0A0A0"),
                  whiteSpace: "pre-wrap",
                }}
              >
                {line}
              </div>
            );
          })}
        </div>
        <div
          style={{
            fontFamily: fonts.caption?.family || "sans-serif",
            fontWeight: fonts.caption?.weight || 500,
            fontSize: fonts.caption?.size || 30,
            lineHeight: fonts.caption?.line_height || 1.2,
            color: theme.text_dim || "#A0A0A0",
          }}
        >
          {spec.brand?.name || ""}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const JustSellPromo = ({spec}) => {
  const {fps} = useVideoConfig();
  const theme = spec.theme || {};
  const scenes = Array.isArray(spec.scenes) ? spec.scenes : [];
  const bg = theme.background || {};
  const bgFrom = bg.from || "#050505";
  const bgTo = bg.to || "#0B0F19";

  return (
    <AbsoluteFill
      style={{
        background:
          bg.kind === "solid"
            ? bg.color || bgFrom
            : `radial-gradient(circle at 0% 0%, rgba(255,106,42,0.24), transparent 42%), radial-gradient(circle at 100% 0%, rgba(88,86,214,0.22), transparent 48%), linear-gradient(140deg, ${bgFrom} 0%, ${bgTo} 100%)`,
      }}
    >
      {scenes.map((scene, i) => {
        const start = Number(scene.start_sec || 0);
        const end = Number(scene.end_sec || start + 2.6);
        const durationSec = Math.max(0.7, end - start);
        const from = Math.max(0, Math.round(start * fps));
        const durationInFrames = Math.max(1, Math.round(durationSec * fps));
        return (
          <Sequence key={`${scene.id || i}-${from}`} from={from} durationInFrames={durationInFrames}>
            <Scene scene={scene} spec={spec} durationInFrames={durationInFrames} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
