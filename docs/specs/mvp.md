# Spec: AutoVD MVP

## Status

Approved product intent. Deterministic backend implementation is complete through the MVP hardening slice; real ChatGPT temporal-analysis/evaluation evidence is still pending.

**Gate A is deferred, not passed.** The repository has proven timestamp/image transport over MCP and the full deterministic backend path, but it has not yet proven that real ChatGPT Developer Mode can locate AI-generation anomalies with the required cut precision.

Do not claim full MVP completion or production readiness until the pending real ChatGPT evaluation succeeds.

## Objective

Build a full-auto cleanup pipeline for AI-generated video clips. The user uploads one or more clips in ChatGPT Web. ChatGPT analyzes obvious AI-generation visual failures and produces a conservative edit plan. An MCP-backed backend validates and executes the plan, speeds up sustained low-motion regions, removes all source audio, concatenates clips in upload order, adds one random permitted music track, renders one final video, and returns it to ChatGPT.

The MVP optimizes for **safe automatic cleanup**, not creative editing.

## User flow

```text
User uploads 1..N AI clips in ChatGPT
        ↓
prepare_video_analysis
        ↓
backend downloads/validates/stages media in upload order
        ↓
get_analysis_chunk
        ↓
ChatGPT scans bounded timestamped frame evidence
        ↓
suspicious regions may be re-sampled densely
        ↓
ChatGPT emits structured CUT candidates only for clear anomalies
        ↓
render_video
        ↓
backend validates CUTs + detects sustained low motion
        ↓
backend applies cuts + speed-ups
        ↓
backend preserves upload order and concatenates clips
        ↓
backend removes all source audio
        ↓
backend selects one random track from curated music library
        ↓
backend renders one H.264/AAC MP4
        ↓
MCP output resource is returned
```

## Core product rules

### Full auto

There is no mandatory manual timeline review or approval step in the MVP.

### Clip ordering

Upload order is the source of truth. The MVP never reorders scenes.

### Visual anomaly categories

ChatGPT may mark a region for removal only when there is a clear generation failure such as:

- anatomy or face deformation;
- identity break;
- object mutation;
- object appearing/disappearing implausibly;
- object intersection;
- background break/melt;
- visual glitch;
- clearly impossible motion;
- another obvious generative failure.

The model must **not** cut a region merely because it is boring, aesthetically weak, poorly composed, stylistically unusual, or semantically unimportant.

### Conservative cut policy

The MVP prioritizes:

```text
cut precision > anomaly recall
```

When uncertain, keep the footage.

A suspicious region should not become a final CUT solely from a coarse scan when denser temporal evidence can reasonably be requested.

### Slow-scene handling

Slow-scene detection is deterministic backend logic and does not require semantic understanding in the MVP.

A region may be sped up when:

```text
motion_score < configured threshold
AND
low-motion duration >= configured minimum duration
```

The motion metric, threshold, minimum duration, frame interval, and speed factor are server-owned configuration.

The current MVP implementation uses bounded grayscale frame differences through FFmpeg; it does not use semantic pacing or OpenCV.

### Audio

All source audio is removed.

The output audio is supplied by exactly one track selected from a server-owned curated music library that the project is allowed to use. The selected track identifier is returned in render metadata.

### Rendering

Initial output target:

- MP4 container;
- H.264 video;
- AAC music audio.

Retained segments are normalized into the configured output resolution/FPS before concatenation.

## AI analysis contract

ChatGPT decides **what is visually broken**. The backend decides **how to execute media edits**.

The model operates against timestamped temporal frame sequences and never receives authority to issue raw FFmpeg/shell commands.

Candidate shape:

```json
{
  "clip_id": "clip_03",
  "decision": "CUT",
  "category": "ANATOMY_DEFORMATION",
  "start_ms": 4200,
  "end_ms": 5100,
  "certainty": "clear",
  "evidence": "The right hand changes into fused extra fingers across consecutive frames."
}
```

Backend acceptance rules include:

- allowed decision/category values;
- `certainty == clear` for a final cut;
- integer timestamp bounds;
- `0 <= start_ms < end_ms <= clip_duration_ms`;
- bounded number of candidate intervals;
- merge of touching/overlapping clear CUTs;
- uncertain candidates retained rather than cut.

Model output is untrusted input.

## Analysis workflow

Use a two-pass strategy:

1. **Coarse scan** — sample a clip/chunk sparsely and identify suspicious temporal regions.
2. **Dense verification** — request a narrower interval with denser sampling before a final CUT when evidence is ambiguous.

Sampling values remain configurable/tunable rather than product constants.

### Temporal evidence representation

The MCP-side representation has been runtime-verified with MCP Inspector:

```text
TextContent: analysis instruction
TextContent: timestamp_ms=0
ImageContent: image/png frame
TextContent: timestamp_ms=500
ImageContent: image/png frame
...
```

Analysis frames are downscaled before loading, with bounds on dimensions/pixels/encoded bytes and aggregate payload size. Invalid/unavailable media returns model-safe errors rather than internal filesystem paths.

This proves MCP transport only. It does **not** prove ChatGPT analysis quality.

## MCP surface

The production MVP surface is intentionally small.

### `prepare_video_analysis`

Current responsibilities:

- accept 1..N ChatGPT file values using the current file-parameter metadata contract;
- fetch temporary files through bounded HTTPS download logic;
- reject non-public/private-address destinations and unsafe redirects;
- enforce configured clip count/file size/duration limits;
- validate actual media with `ffprobe`;
- create isolated randomized job workspaces;
- preserve input order;
- return stable job/clip identifiers and media metadata.

### `get_analysis_chunk`

Current responsibilities:

- accept only job/clip identifiers and bounded temporal sampling arguments;
- return timestamped visual evidence for a clip subrange;
- support denser re-sampling around a suspicious interval;
- never expose arbitrary server paths.

### `render_video`

Current responsibilities:

- accept only structured typed edit requests;
- validate model CUT candidates;
- compute deterministic motion scores and sustained low-motion regions;
- resolve CUT/speed-up timeline segments with CUT precedence;
- render retained segments with FFmpeg argv, never shell command text;
- preserve upload order;
- remove source audio;
- add one selected curated music track;
- probe the final output;
- return render metadata plus an MCP `ResourceLink` to the output MP4.

### Temporary diagnostic/spike tools

- `health` — non-sensitive transport diagnostic;
- `get_temporal_analysis_demo` — operator-configured temporal fixture used to prove timestamp/image transport.

The spike fixture path comes only from server configuration (`AUTOVD_SPIKE_VIDEO`), not model input.

## Current implementation stack

Currently locked/used:

- Python package contract `>=3.12,<3.15`; CI executes Python 3.13;
- `mcp[cli]==2.0.0`;
- `pydantic==2.13.4`;
- FFmpeg as a system dependency;
- pytest `9.1.1`;
- Ruff `0.16.3`;
- mypy `2.3.0` with strict checking;
- `uv.lock` as authoritative dependency lockfile;
- MCP Inspector `2.2.0` in CI.

OpenCV is not part of the current implementation.

Version-sensitive MCP/OpenAI behavior must continue to be checked against current official documentation before changes.

## Current project structure

```text
src/autovd/
  contracts/
    edit_plan.py
    openai_files.py
  eval/
    scoring.py
  jobs/
    store.py
    workspace.py
  media/
    download.py
    frame_sampler.py
    ingest.py
    motion.py
    renderer.py
    timeline.py
  tools/
    analysis_spike.py
    workflow.py
  diagnostic.py
  mcp_server.py

tests/
  ... unit, integration, MCP, media, renderer, security/resource tests ...

docs/
  specs/
  adr/

tasks/
  plan.md
  todo.md

.github/workflows/ci.yml
pyproject.toml
uv.lock
```

## Repository commands

Commands exercised by CI:

```bash
uv sync --all-groups --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest -q
```

Run the MCP server:

```bash
uv run autovd-mcp
```

Current local endpoint: `http://127.0.0.1:8000/mcp`.

CI also exercises the running Streamable HTTP endpoint with MCP Inspector.

## Current operational bounds

Defaults are server-owned and configurable:

- active jobs: 8;
- job inactivity TTL: 1800 seconds;
- output resource size cap: 512 MiB;
- clips/job: 8;
- file size: 256 MiB/clip;
- clip duration: 120 seconds;
- render timeout: 180 seconds.

These are implementation defaults, not long-term product promises.

Expired jobs use lazy cleanup: access to an expired job removes its workspace, and creation of a new job purges expired jobs before enforcing the active-job cap. This keeps resource use bounded without introducing a background scheduler in the MVP.

## Testing strategy

### Deterministic/unit tests

Cover:

- edit-plan schema/range/category/certainty validation;
- cut merge and timeline conflict behavior;
- low-motion scoring/grouping;
- frame payload bounds;
- job TTL/output bounds;
- generic external errors;
- downloader scheme/private-address/size/filename boundaries.

### Media/integration tests

Use tiny synthetic videos to verify:

- media validation;
- cuts and speed-ups;
- upload-order preservation;
- source audio exclusion;
- one music track in output;
- H.264/AAC playable/probeable output;
- full backend prepare → analysis chunk → render → output-resource workflow.

### MCP contract/runtime tests

Verify:

- tool list and names;
- ChatGPT file-parameter metadata/schema;
- timestamp/image result transport;
- health and temporal spike invocation through MCP Inspector.

### AI evaluation — pending human gate

Maintain a human-labeled evaluation set containing clean footage and obvious anomaly categories.

Primary metric: **cut precision**.

Initial approved target to validate/tune:

- at least 90% of model-selected CUT regions overlap human-labeled clear anomalies;
- anomaly recall is secondary and may initially be substantially lower.

This evaluation has not yet been run against the real ChatGPT workflow.

## Security boundaries

Video uploads, temporary file references, model outputs, tool arguments, and externally fetched content are untrusted.

Implemented controls include:

- schema/range validation;
- content/size/duration/count bounds;
- isolated randomized job workspaces;
- no model-controlled filesystem paths;
- no `shell=True`;
- FFmpeg argument arrays rather than model command text;
- HTTPS/public-address/redirect/stream-size checks for server-side file fetching;
- bounded frame/render/job/output resources;
- generic model-safe tool/media errors;
- no normal logging of signed download URLs/raw media;
- job TTL/lazy cleanup;
- curated server-side music allowlist by directory/suffix;
- re-probing rendered output.

## Boundaries

### Always

- preserve upload order;
- keep uncertain visual regions;
- strip source audio;
- validate external/model data;
- use deterministic backend operations for editing;
- verify produced media before returning success;
- keep resource use bounded;
- update docs when product decisions or implemented truth change.

### Ask first

- adding a second AI provider/API;
- sending videos to any new third-party service;
- adding persistent user media storage;
- introducing accounts/auth/database;
- materially changing supported media limits;
- changing the product from full-auto to mandatory human review.

### Never

- execute model-generated shell/FFmpeg text;
- let the model pick arbitrary filesystem paths;
- silently reorder clips;
- cut footage only for aesthetic weakness in the MVP;
- retain input audio;
- silently introduce paid external AI dependencies.

## Success criteria

The MVP is successful when a user can upload multiple AI-generated clips in **real ChatGPT** and, without opening another application or approving timeline edits, receive one playable video where:

- obvious AI-generation failures are removed with high cut precision;
- ambiguous footage is normally retained;
- sustained low-motion regions are automatically accelerated;
- upload order is preserved;
- original audio is absent;
- exactly one permitted library music track supplies output audio;
- media operations are performed by validated deterministic backend logic.

The deterministic/backend acceptance criteria are implemented. The real ChatGPT anomaly-quality criterion remains pending.

## Non-goals for MVP

- standalone frontend/dashboard;
- manual timeline editor;
- semantic storytelling/pacing;
- scene rearrangement;
- captions/subtitles;
- speech preservation or repair;
- lip sync;
- color grading;
- complex transitions/effects;
- AI music generation;
- semantic music matching or beat synchronization;
- prompt-compliance/viral-hook optimization.

## Highest-risk assumption / remaining gate

The remaining highest-risk assumption is still temporal visual analysis through real ChatGPT:

```text
representative AI-generated clips
→ AutoVD prepares bounded timestamped frame evidence
→ real ChatGPT inspects evidence through MCP
→ ChatGPT returns structured anomaly intervals
→ compare with human labels
→ GO only if conservative cut precision is acceptable
```

The backend preparation, transport contract, deterministic editing core, rendering, and resource hardening are implemented. The real model interpretation/evaluation stage is intentionally left as the only unresolved MVP gate that requires human/workspace participation.
