import {Composition} from "remotion";
import {z} from "zod";
import {JustSellPromo} from "./JustSellPromoVertical";

export const RenderInputSchema = z.object({
  spec: z.object({
    render: z.object({
      fps: z.number(),
      width: z.number(),
      height: z.number(),
      duration_sec: z.number(),
      safe_area: z.object({
        top: z.number(),
        right: z.number(),
        bottom: z.number(),
        left: z.number(),
      }),
    }),
    scenes: z.array(
      z.object({
        id: z.string(),
        title: z.string(),
        lines: z.array(z.string()),
        start_sec: z.number(),
        end_sec: z.number(),
      }),
    ),
  }),
});

const calculateMetadata = async ({props}) => {
  const spec = props.spec;
  const render = spec.render || {};
  const fps = Number(render.fps || 30);
  const width = Number(render.width || 1080);
  const height = Number(render.height || 1920);
  const durationSec = Number(render.duration_sec || 20);
  const durationInFrames = Math.max(1, Math.round(durationSec * fps));

  return {
    fps,
    width,
    height,
    durationInFrames,
    props: {
      spec,
    },
  };
};

export const RemotionRoot = () => {
  return (
    <Composition
      id="JustSellPromo"
      component={JustSellPromo}
      durationInFrames={1}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{
        spec: {
          render: {
            fps: 30,
            width: 1080,
            height: 1920,
            duration_sec: 1,
            safe_area: {top: 0, right: 0, bottom: 0, left: 0},
          },
          scenes: [],
        },
      }}
      schema={RenderInputSchema}
      calculateMetadata={calculateMetadata}
    />
  );
};
