# Spec: AutoVD MVP

## Status

Approved product intent; implementation not started.

## Objective

Build a full-auto cleanup pipeline for AI-generated video clips. The user uploads one or more clips in ChatGPT Web. ChatGPT analyzes obvious AI-generation visual failures and produces a conservative edit plan. An MCP-backed backend validates and executes the plan, speeds up sustained low-motion regions, removes all source audio, concatenates clips in upload order, adds one random licensed music track, renders one final video, and returns it to ChatGPT.

The MVP optimizes for **safe automatic cleanup**, not creative editing.

## User flow

```text
User uploads 1..N AI clips in ChatGPT
        ↓
ChatGPT invokes AutoVD MCP
        ↓
Backend validates media and extracts timestamped analysis frames
        ↓
ChatGPT scans chunks for obvious AI visual anomalies
        ↓
Suspicious regions may be re-sampled densely for verification
        ↓
ChatGPT emits structured CUT intervals only for clear anomalies
        ↓
Backend validates/merges/clamps intervals
        ↓
Backend detects sustained low-motion regions
        ↓
Backend applies cuts + speed-ups
        ↓
Backend preserves upload order and concatenates clips
        ↓
Backend removes all input audio
        ↓
Backend selects one random track from curated music library
        ↓
Backend renders one output video
        ↓
ChatGPT returns the result
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

A suspicious region should not become a final CUT solely from a coarse scan when denser temporal evidence can be requested.

### Slow-scene handling

Slow-scene detection is deterministic backend logic and does not require semantic understanding in the MVP.

A region may be sped up when:

```text
motion_score < configured threshold
AND
low-motion duration > configured minimum duration
```

The motion metric, threshold, minimum duration, and speed factor must be configurable rather than scattered as magic constants.

### Audio

All source audio is removed.

The output audio is supplied by exactly one track selected from a curated music library that the project is allowed to use. The selected track identifier should be recorded in job metadata for reproducibility/audit.

### Rendering

Initial output target:

- MP4 container;
- H.264 video;
- AAC music audio.

Inputs with incompatible resolution/FPS/codec properties must be normalized before concatenation.

## AI analysis contract

ChatGPT decides **what is visually broken**. The backend decides **how to execute media edits**.

The model should operate against timestamped temporal frame sequences rather than receiving authority to issue raw FFmpeg/shell commands.

Recommended model output shape:

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

Backend acceptance rules for a final CUT must include at least:

- allowed decision/category values;
- `certainty == clear`;
- finite integer timestamps;
- `0 <= start_ms < end_ms <= clip_duration_ms`;
- bounded number/total duration of edit intervals;
- overlap merge before render.

Model output is untrusted input.

## Analysis workflow

Use a two-pass strategy for the MVP:

1. **Coarse scan** — sample a chunk sparsely and identify suspicious temporal regions.
2. **Dense verification** — re-sample suspicious regions more densely before a final CUT when needed.

Initial chunk/sampling values are hypotheses, not locked requirements. They must be tuned against an evaluation set.

The first technical spike must prove that ChatGPT + MCP can consume enough timestamped temporal visual context to locate obvious AI-generation anomalies reliably enough for a full-auto workflow.

## Proposed MCP surface

Keep the surface intentionally small.

### `prepare_video_analysis`

Responsibilities:

- accept 1..N uploaded video files;
- validate media and configured limits;
- create an isolated job workspace;
- probe metadata;
- extract timestamped analysis frames/chunks;
- compute motion metadata;
- return stable job/clip/chunk identifiers.

### `get_analysis_chunk`

Responsibilities:

- return model-consumable timestamped visual assets for one analysis chunk;
- support denser temporal sampling around a suspicious region;
- avoid exposing arbitrary server paths.

### `render_video`

Responsibilities:

- accept a structured edit plan;
- validate the plan;
- merge/clamp intervals;
- compute low-motion speed-up regions;
- perform deterministic media editing;
- remove original audio;
- add one random library track;
- render and return output metadata/file reference.

The backend must never accept arbitrary shell or FFmpeg command text from the model.

## Proposed tech stack

Not dependency-locked yet:

- Python
- official/current MCP SDK compatible with ChatGPT
- FFmpeg
- OpenCV
- Pydantic or equivalent schema validation
- pytest

Framework/library versions must be selected from current official documentation when implementation begins.

## Proposed project structure

```text
src/
  autovd/
    mcp_server.py
    tools/
    contracts/
    media/
    jobs/
    config.py
music/
  library/
tests/
  unit/
  integration/
  fixtures/
docs/
  specs/
  adr/
tasks/
```

The MCP transport/handlers should remain thin. Core timeline/media logic belongs in testable modules outside the handlers.

## Commands

No runnable project scaffold exists yet, so exact repository commands are **not defined**. Do not pretend proposed commands have been executed.

The implementation plan must establish canonical commands for:

- dev server;
- focused/full tests;
- lint/format;
- type checking;
- MCP protocol inspection.

## Code style

Prefer typed explicit domain contracts and small deterministic functions.

Example target style:

```python
class CutInterval(BaseModel):
    start_ms: int
    end_ms: int
    category: AnomalyCategory

    @model_validator(mode="after")
    def validate_interval(self) -> "CutInterval":
        if self.start_ms >= self.end_ms:
            raise ValueError("start_ms must be before end_ms")
        return self
```

Conventions:

- `snake_case` functions/variables;
- `PascalCase` types;
- explicit typed/schema boundaries;
- no model-generated shell execution;
- no feature policy hidden in MCP handlers;
- no unrelated abstractions before the spike proves the core flow.

## Testing strategy

### Unit tests

Prioritize deterministic behavior:

- interval validation and overlap merge;
- clip ordering;
- motion scoring;
- slow-region extraction;
- speed-plan generation;
- music selection;
- timeline calculations;
- safe command argument generation;
- workspace/path isolation.

### Integration tests

Use small fixture videos to verify:

- cuts remove the intended interval;
- low-motion regions are accelerated;
- source audio is absent;
- output includes selected library music;
- upload order is preserved;
- output media is playable/probeable;
- malformed edit plans are rejected.

### AI evaluation

Maintain a human-labeled evaluation set containing clean footage and obvious anomaly categories.

Primary metric: **cut precision**.

Initial product target to validate/tune, not a research guarantee:

- at least 90% of model-selected CUT regions overlap human-labeled clear anomalies;
- anomaly recall is secondary and may initially be substantially lower.

## Security boundaries

Video uploads, temporary file references, model outputs, tool arguments, and any externally fetched content are untrusted.

Required design controls include:

- content/size/duration/count validation;
- isolated per-job workspaces;
- randomized internal filenames;
- no model-controlled filesystem paths;
- no `shell=True`;
- invoke FFmpeg with argument arrays;
- URL/redirect/SSRF controls wherever server-side fetching is used;
- bounded render/resource consumption;
- no sensitive temporary URLs or raw media in normal logs;
- temporary media cleanup/TTL;
- explicit schema validation of every model-generated edit plan.

## Boundaries

### Always

- preserve upload order;
- keep uncertain visual regions;
- strip source audio;
- validate all external/model data;
- use deterministic backend operations for editing;
- verify produced media before returning success;
- update the spec when product decisions change.

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

The MVP is successful when a user can upload multiple AI-generated clips in ChatGPT and, without opening another application or approving timeline edits, receive one playable video where:

- obvious AI-generation failures are removed with high cut precision;
- ambiguous footage is normally retained;
- sustained low-motion regions are automatically accelerated;
- upload order is preserved;
- original audio is absent;
- exactly one permitted library music track supplies output audio;
- media operations are performed by validated deterministic backend logic.

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

## Highest-risk assumption

The highest-risk assumption is temporal visual analysis through ChatGPT + MCP. Before investing deeply in renderer architecture, build a narrow vertical spike:

```text
one short AI-generated clip
→ extract timestamped frame sequence
→ expose it through the MCP flow
→ ask ChatGPT for anomaly intervals
→ compare against human labels
```

If that spike cannot achieve acceptable precision, revisit the analysis architecture before building the full MVP.
