# AutoVD Architecture & Workflow

## Purpose

This document records the current MVP architecture and the remaining unverified boundary so future implementation sessions do not reconstruct decisions from chat history.

## System overview

```text
User in ChatGPT Web
│
├─ uploads 1..N AI-generated clips
└─ asks AutoVD to edit them
        ↓
ChatGPT
│
├─ calls prepare_video_analysis
├─ inspects timestamped temporal evidence via get_analysis_chunk
├─ classifies only obvious AI-generation anomalies
└─ emits conservative structured CUT candidates
        ↓
AutoVD MCP server
│
├─ validates file/tool/model inputs
├─ safely fetches temporary uploaded files
├─ manages isolated bounded jobs
├─ probes/stages media in upload order
├─ exposes bounded timestamp/image evidence
├─ validates edit candidates
└─ delegates deterministic media work
        ↓
Deterministic media pipeline
│
├─ grayscale motion scoring
├─ sustained low-motion detection
├─ CUT + speed-up timeline generation
├─ normalize retained segments
├─ concatenate in upload order
├─ remove all source audio
├─ choose one curated music track
└─ render + probe H.264/AAC MP4
        ↓
MCP ResourceLink
        ↓
Playable output resource for ChatGPT
```

## Responsibility split

### ChatGPT owns

- visual anomaly reasoning;
- anomaly taxonomy classification;
- approximate temporal localization;
- deciding whether evidence is clear enough for a CUT candidate;
- requesting denser evidence when coarse sampling is insufficient.

### Backend owns

- temporary file retrieval and SSRF-oriented URL controls;
- media validation and configured resource limits;
- frame extraction and payload bounds;
- motion scoring and low-motion grouping;
- job state/workspaces/TTL;
- edit schema/timestamp validation;
- clear-cut filtering and interval merge;
- CUT vs speed-up timeline resolution;
- FFmpeg invocation;
- normalization/concatenation;
- source-audio removal;
- music selection;
- final render validation;
- output-resource bounds.

This boundary is deliberate: the model expresses conservative visual intent; deterministic code executes privileged media transformations.

## Visual anomaly analysis

The model is not asked to "make the video better." It identifies **clear visual generation failures only**.

```text
CUT only when a normal viewer would clearly perceive the temporal sequence
as malformed, impossible, or broken because of AI generation.

Do not CUT merely for:
- low motion;
- boredom;
- weak composition;
- unusual but plausible perspective;
- occlusion;
- intentional style;
- uncertain evidence.

When uncertain: KEEP.
```

### Two-pass temporal workflow

```text
clip/subrange
 │
 ├─ coarse timestamped sampling
 │       ↓
 │   suspicious region?
 │      /       \
 │    no         yes
 │    ↓           ↓
 │   KEEP     dense subrange sampling
 │                ↓
 │          clear anomaly?
 │             /      \
 │           no        yes
 │           ↓          ↓
 │          KEEP     CUT candidate
 │                       ↓
 │                backend validation
 │                       ↓
 └────────────────── final edit plan
```

Dense verification is important because the product is fully automatic and prioritizes false-cut avoidance.

## Temporal evidence transport

The MCP-side representation is runtime-verified over Streamable HTTP:

```text
TextContent: analysis instruction
TextContent: timestamp_ms=0
ImageContent: image/png frame
TextContent: timestamp_ms=500
ImageContent: image/png frame
...
```

Verified backend/protocol facts:

- FFmpeg extracts deterministic timestamped PNG frames;
- analysis frames are downscaled and bounded by dimensions/pixels/per-frame bytes/aggregate bytes;
- MCP serializes image data as `ImageContent`;
- MCP Inspector can list and invoke the endpoint through Streamable HTTP;
- production tool schemas and ChatGPT file-parameter metadata are visible through the protocol.

Still **unverified**:

- whether real ChatGPT Developer Mode grounds/interprets the interleaved timestamps/images with enough temporal fidelity;
- whether model-selected anomaly intervals meet the conservative cut-precision target.

Successful transport is not evidence of model-analysis quality.

## Production MCP surface

### `prepare_video_analysis`

Input:

```text
videos: list[ChatGPT file value]
```

Current flow:

```text
file values
→ validate HTTPS/public destination
→ bounded download with redirect re-validation
→ isolated temporary staging
→ ffprobe actual media
→ enforce count/size/duration limits
→ randomized job workspace paths
→ preserve input order
→ stable job_id + clip_id metadata
```

The tool declares the ChatGPT file parameter through `_meta["openai/fileParams"]` and does not accept model-selected local paths.

### `get_analysis_chunk`

Input is job/clip identity plus bounded temporal parameters. It returns timestamp/image evidence for a subrange and supports denser sampling without exposing filesystem paths.

### `render_video`

Input is structured typed edit requests only.

```text
model CUT candidates
→ schema/category/range/clip validation
→ keep uncertain candidates
→ merge clear cuts
→ deterministic motion scoring
→ sustained low-motion regions
→ CUT-precedence timeline
→ FFmpeg render
→ output probe
→ ResourceLink + render metadata
```

No model-generated shell or FFmpeg command text is accepted.

### Diagnostic/spike tools

- `health` — non-sensitive transport diagnostic;
- `get_temporal_analysis_demo` — operator-controlled fixture tool retained for temporal transport testing.

## Deterministic motion/pacing

Motion pacing is separate from ChatGPT reasoning.

```text
bounded grayscale frame samples
        ↓
mean frame-difference score
        ↓
sustained score below configured threshold?
        ├─ no  → retain normal speed
        └─ yes → configured speed-up region
```

The MVP does not ask ChatGPT whether footage is narratively boring or semantically slow.

## Edit-plan/timeline safety

Before rendering:

1. parse strict typed candidate schemas;
2. require known clip IDs/categories;
3. validate timestamp ranges against clip duration;
4. discard uncertain candidates from the CUT set;
5. sort and merge touching/overlapping clear cuts;
6. derive low-motion speed regions independently;
7. split the timeline deterministically;
8. give CUT precedence over overlapping speed-up regions;
9. reject a render where all content is removed.

## Renderer

The renderer receives only trusted typed `ClipRenderPlan` state.

It:

- sorts clips by trusted upload-order metadata;
- trims only retained timeline segments;
- applies configured speed factors;
- normalizes video to configured dimensions/FPS/pixel format;
- concatenates retained video segments;
- never maps source audio into the output graph;
- selects one server-owned curated music file;
- loops/trims music to video duration;
- encodes H.264 video + AAC audio;
- probes the output before returning success.

FFmpeg is invoked with argument arrays, never `shell=True` or model-provided command strings.

## Data/trust boundaries

```text
ChatGPT file value / download URL = untrusted external input
MCP tool arguments                = untrusted external input
model analysis/edit candidates    = untrusted model output
downloaded media bytes            = untrusted external bytes
media metadata                    = untrusted until validated
curated music directory           = server-owned input
validated typed timeline state    = trusted internal state
rendered output                   = trusted only after probe + size checks
```

Prompt text is never treated as a permission boundary.

## Job lifecycle/resource model

Jobs are currently in-process and ephemeral; no database or persistent user-media store exists.

```text
prepare
→ randomized workspace
→ active job in bounded registry
→ analysis/render calls refresh inactivity TTL
→ rendered output stored inside same workspace
→ output read through MCP resource
→ expired/accessed job is removed
→ new job creation purges expired entries before max-job enforcement
```

Current defaults:

- `max_jobs = 8`;
- inactivity TTL = 1800 seconds;
- output resource cap = 512 MiB;
- input file cap = 256 MiB/clip;
- clip duration cap = 120 seconds;
- clips/job = 8.

All are server-owned configuration. Lazy expiry avoids a background scheduler while `max_jobs` keeps abandoned-job resource growth bounded.

## Server-side file retrieval

The ChatGPT adapter treats temporary download URLs as untrusted. Current controls:

- HTTPS only;
- no embedded credentials;
- standard HTTPS port only;
- hostname must resolve to global/public addresses;
- redirects are not followed implicitly;
- each redirect target is re-validated;
- redirect count is bounded;
- download timeout is bounded;
- `Content-Length` and streamed bytes are capped;
- user/model filenames are never used for staged paths.

## Verification architecture

Repository CI runs, in order:

1. locked dependency sync;
2. Ruff lint;
3. Ruff format check;
4. strict mypy;
5. bounded/retryable FFmpeg setup;
6. full pytest suite including real FFmpeg integration tests;
7. MCP Inspector smoke against the running Streamable HTTP server.

Synthetic integration coverage proves the deterministic backend prepare → analysis chunk → render → output-resource path without claiming real ChatGPT model quality.

## Remaining Gate A

The only unresolved product assumption requiring user/workspace participation is:

```text
representative AI-generated footage
→ real ChatGPT receives AutoVD temporal evidence
→ ChatGPT returns conservative anomaly intervals
→ compare against human labels
→ verify cut precision target
```

If that gate fails, revise the analysis representation/prompting before claiming the MVP succeeds. The deterministic editing core should remain reusable because it is isolated from model reasoning.

## Post-MVP direction

Possible future actions such as semantic pacing, reordering, best-take selection, transitions, voice preservation, prompt compliance, or music matching remain explicitly out of scope until the cleanup MVP is proven.
