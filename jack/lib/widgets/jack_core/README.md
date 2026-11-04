# JackCore

`JackCore` is a Flutter Canvas 2D rendering component. It receives a normalized
graph and a cognitive state; it does not read the backend, chat, settings, or
AI services itself.

## Demo data

`jack_core_demo_data.dart` contains twelve neutral synthetic nodes and twelve
synthetic links. `JackCoreGraphOrigin.demo`, `demo-*` identifiers, and the
`Dataset demo` provenance mark this fixture at the model/API level. It is never
written to SQLite or presented as personal memory.

The `surface` and `interior` shell assignments are stable layout coordinates
only. They do not represent importance, category, trust, or retrieval status.

The visual mapper uses source type for node color, importance for node size,
verification for a fine secondary ring, exclusion for reduced opacity, and link
strength for arc weight. Category and source text stay on the node model and
are exposed when a node is selected; the blueprint does not specify a separate
category color system, so the renderer does not invent one.

## Motion profiles

Blueprint §6 lists the profile axes `spin`, `glow`, `breathe`, `cluster`,
`scan`, `pulse`, `jitter`, and `dim`, and gives `0.028/0.44` for `waiting` and
`0.22/0.88` for `executing` without explicitly naming the paired axes. This
implementation interprets those pairs as `spin/glow`. The remaining state
values are conservative, centralized implementation defaults, not official
Base44 values. Edit `JackCoreMotionProfile.profiles` to tune them.

The four orbit radii and opacities come directly from §6. Orbit plane tilts,
internal shell scale, node sizing, and perspective camera distance are rendering
defaults because the blueprint does not specify them numerically.

The `error` state's four-second timeout belongs to the future session/pipeline
state source. `JackCore` renders the state it receives and does not invent or
advance cognitive state on its own.

## Current data and state boundary

The Flutter memory API currently provides only title, content, category, and
timestamps, with categories that differ from the blueprint. It has no memory
links, provenance, verification, importance, exclusion, or last-used fields.
Therefore the home screen supplies only the explicitly marked demo graph.

The home screen passes `idle` only. Listening, pipeline, memory-save, waiting,
and pipeline-error states remain available in the component API but must only
be supplied by real services when those services exist. Backend connectivity
is not a cognitive state. Reduced motion stops the animation ticker while
preserving a static rendering of the current state.
