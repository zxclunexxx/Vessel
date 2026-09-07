# Vessel visual system

## Direction

Vessel uses a dark futuristic liquid-glass identity rather than a Discord clone. The visual language combines deep graphite/navy surfaces, translucent glass panels, soft cyan/violet/magenta light, subtle texture, generous spacing and restrained motion.

## Core rules

- Preserve runtime behavior: visual work should not weaken auth, RLS, realtime, messaging or calls.
- Prefer CSS transforms and opacity for interaction motion.
- Keep large blur layers limited to the main shell surfaces.
- Avoid permanent high-frequency animation and heavy canvas/WebGL effects in the core UI.
- Every interactive control must have hover, pressed and `:focus-visible` feedback.
- Respect `prefers-reduced-motion`.
- Mobile keeps the same identity with lighter spacing/effects and the existing channel drawer behavior.

## Tokens

The source-of-truth implementation lives in the `VESSEL_UI_FOUNDATION_SHELL_V1` block in `src/style.css`.

Primary atmosphere:
- `--v-bg-0` / `--v-bg-1` / `--v-bg-2`: deep background layers
- `--v-surface*`: glass surfaces
- `--v-border*`: translucent edge lighting
- `--v-cyan`, `--v-blue`, `--v-violet`, `--v-magenta`: Vessel accent spectrum
- `--v-green`: healthy/online state
- `--v-danger`: destructive state

Geometry:
- controls: 14 px
- cards: 18 px
- main panels: 26 px

Motion:
- fast: 140 ms
- normal: 220 ms
- slow: 340 ms
- UI easing: `cubic-bezier(.2,.8,.2,1)`
- spring-like entrance/selection easing: `cubic-bezier(.16,1,.3,1)`

## Batch 1 scope

The foundation/shell batch restyles without changing application logic:

- ambient gradient + fine texture background
- glass app shell surfaces
- server rail with glowing active indicator
- server/channel hover and active states
- channel navigation hierarchy
- user card as a lower navigation dock
- workspace header and action controls
- chat surface and composer foundation
- members panel
- auth surface, dialogs and toasts aligned with the same visual language
- responsive/mobile shell preservation
- keyboard focus and reduced-motion support

## Next batches

1. Messaging + Social: dedicated friend cards, DM rows, message grouping, richer empty/loading states and composer polish.
2. Voice + Calls: participant cards, speaking visualization, audio/video stages, reconnect state and floating controls.
3. Motion + Polish: page/modal transitions, refined microinteractions, ambient motion, mobile polish and performance pass.
