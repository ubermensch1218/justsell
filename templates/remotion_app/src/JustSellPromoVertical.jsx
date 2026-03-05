import React from "react";
import {
  AbsoluteFill,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  Video,
} from "remotion";

const fadeOut = (frame, duration) =>
  interpolate(frame, [Math.max(0, duration - 12), duration], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

const Scene = ({scene, spec, durationInFrames, flowSrcDefault, flowSrcByModule, flowFitByModule}) => {
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
  const isFlowScene = scene?.kind === "flow-demo";
  const moduleId = String(scene?.flow_module_id || "").trim();
  const moduleFlowSrc = moduleId ? flowSrcByModule[moduleId] : "";
  const flowSrc = moduleFlowSrc || flowSrcDefault;
  const moduleFit = moduleId ? flowFitByModule[moduleId] : "";
  const fit = moduleFit === "contain" ? "contain" : spec?.flow_recording?.fit === "contain" ? "contain" : "cover";

  if (isFlowScene && flowSrc) {
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
            border: `1px solid ${theme.panel_border || "rgba(15,23,42,0.14)"}`,
            background: theme.panel_fill || "rgba(255,255,255,0.94)",
            padding: 28,
            boxShadow: "0 24px 64px rgba(15,23,42,0.10)",
            opacity,
            transform: `translateY(${translateY}px)`,
          }}
        >
          <div
            style={{
              fontFamily: fonts.title?.family || "sans-serif",
              fontWeight: fonts.title?.weight || 700,
              fontSize: Math.round((fonts.title?.size || 72) * 0.72),
              lineHeight: fonts.title?.line_height || 1.1,
              color: theme.text_primary || "#0F172A",
              letterSpacing: "-0.01em",
              whiteSpace: "pre-wrap",
            }}
          >
            {scene.title}
          </div>
          <div
            style={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              borderRadius: 20,
              overflow: "hidden",
              border: `1px solid ${theme.panel_border || "rgba(15,23,42,0.14)"}`,
              background: "#F8FAFC",
              marginTop: 14,
              marginBottom: 14,
            }}
          >
            <Video
              src={flowSrc}
              muted
              style={{
                width: "100%",
                height: "100%",
                objectFit: fit,
              }}
            />
          </div>
          <div
            style={{
              fontFamily: fonts.caption?.family || "sans-serif",
              fontWeight: fonts.caption?.weight || 500,
              fontSize: fonts.caption?.size || 30,
              lineHeight: fonts.caption?.line_height || 1.2,
              color: theme.text_dim || "#475569",
            }}
          >
            {(scene.lines || [])[0] || spec.flow_recording?.caption || ""}
          </div>
        </AbsoluteFill>
      </AbsoluteFill>
    );
  }

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
          border: `1px solid ${theme.panel_border || "rgba(15,23,42,0.14)"}`,
          background: theme.panel_fill || "rgba(255,255,255,0.94)",
          padding: 44,
          boxShadow: "0 24px 64px rgba(15,23,42,0.10)",
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
            color: theme.text_primary || "#0F172A",
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
                  color: i === 0 ? (theme.text_primary || "#0F172A") : (theme.text_dim || "#475569"),
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
            color: theme.text_dim || "#475569",
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
  const bgFrom = bg.from || "#FFFFFF";
  const bgTo = bg.to || "#F4F7FB";
  const flowPublicSrc = String(spec?.flow_recording?.public_src || "").trim();
  const flowSrcDefault = flowPublicSrc ? staticFile(flowPublicSrc.replace(/^\/+/, "")) : "";
  const flowSrcByModule = {};
  const flowFitByModule = {};
  const flowRecordings = Array.isArray(spec?.flow_recordings) ? spec.flow_recordings : [];
  flowRecordings.forEach((item) => {
    if (!item || typeof item !== "object") {
      return;
    }
    const id = String(item.id || "").trim();
    const publicSrc = String(item.public_src || "").trim();
    if (!id || !publicSrc) {
      return;
    }
    flowSrcByModule[id] = staticFile(publicSrc.replace(/^\/+/, ""));
    flowFitByModule[id] = String(item.fit || "cover").trim().toLowerCase();
  });

  return (
    <AbsoluteFill
      style={{
        background:
          bg.kind === "solid"
            ? bg.color || bgFrom
            : `radial-gradient(circle at 0% 0%, rgba(37,99,235,0.10), transparent 45%), radial-gradient(circle at 100% 0%, rgba(15,23,42,0.06), transparent 50%), linear-gradient(140deg, ${bgFrom} 0%, ${bgTo} 100%)`,
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
            <Scene
              scene={scene}
              spec={spec}
              durationInFrames={durationInFrames}
              flowSrcDefault={flowSrcDefault}
              flowSrcByModule={flowSrcByModule}
              flowFitByModule={flowFitByModule}
            />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
