# AutoVD Architecture & Workflow

## Purpose

This document explains the MVP architecture in an operational form so future implementation sessions do not have to reconstruct decisions from chat history.

## System overview

```text
User in ChatGPT Web
│
├─ uploads 1..N AI-generated clips
└─ asks AutoVD to edit them
        ↓
ChatGPT
│
├─ orchestrates MCP tool calls
├─ inspects timestamped temporal visual evidence
├─ classifies obvious AI-generation anomalies
└─ emits conservative structured CUT decisions
        ↓
AutoVD MCP server
│
├─ validates file/tool inputs
├─ manages isolated job workspace
├─ probes media
├─ extracts timestamped analysis frames
├─ computes motion metadata
├─ validates edit plan
└─ delegates deterministic media work
        ↓
Media pipeline
│
├─ remove CUT intervals
├─ detect sustained low-motion intervals
├─ apply speed-up to low-motion intervals
├─ normalize media as needed
├─ concatenate clips in upload order
├─ remove all input audio
├─ choose one random curated music track
└─ render final video
        ↓
Playable output returned to ChatGPT
```

## Responsibility split

### ChatGPT owns

- visual anomaly reasoning;
- anomaly taxonomy classification;
- approximate temporal localization;
- deciding whether evidence is clear enough for CUT;
- requesting denser evidence when coarse sampling is insufficient.

### Backend owns

- media validation;
- frame extraction;
- motion scoring;
- job state/workspaces;
- timestamp validation;
- cut interval merge/clamp;
- speed-up calculation;
- FFmpeg invocation;
- clip normalization/concatenation;
- source-audio removal;
- music selection;
- final render validation.

This boundary is deliberate: the model expresses intent; deterministic code executes media transformations.

## Visual anomaly analysis

### Rule

The model is not asked to "make the video better." It is asked to identify **clear visual generation failures only**.

The analysis instruction should enforce:

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
Chunk
 │
 ├─ Coarse timestamped frame sampling
 │       ↓
 │   suspicious region?
 │      /       \
 │    no         yes
 │    ↓           ↓
 │   KEEP     Dense re-sampling
 │                ↓
 │          clear anomaly?
 │             /      \
 │           no        yes
 │           ↓          ↓
 │          KEEP     CUT candidate
 │                       ↓
 │                schema validation
 │                       ↓
 └────────────────── final edit plan
```

Dense verification is important because the product is fully automatic and prioritizes false-cut avoidance.

## Motion/pacing workflow

Motion-based pacing is separate from model anomaly analysis.

```text
video frames
    ↓
deterministic motion score
    ↓
sustained low-motion region?
    ├─ no  → no pacing change
    └─ yes → apply configured speed-up
```

The MVP does not ask ChatGPT whether a scene is narratively slow or boring.

## Proposed MCP tools

### `prepare_video_analysis`

Input concept:

```text
videos: uploaded file array
```

Produces a job with stable identifiers, media metadata, analysis chunks, and motion metadata.

### `get_analysis_chunk`

Returns model-consumable timestamped visual evidence for one chunk and should support a denser sampling request around a suspicious interval.

### `render_video`

Accepts only a structured validated edit plan. It must not accept arbitrary FFmpeg or shell syntax.

Conceptual input:

```json
{
  "job_id": "job_123",
  "clips": [
    {
      "clip_id": "clip_01",
      "cuts": [
        {
          "start_ms": 4200,
          "end_ms": 5100,
          "category": "ANATOMY_DEFORMATION",
          "certainty": "clear"
        }
      ]
    }
  ]
}
```

## Timeline safety rules

Before rendering:

1. validate schema and allowed enums;
2. reject invalid/non-finite/negative timestamps;
3. reject `start >= end`;
4. clamp only according to explicit policy;
5. sort intervals;
6. merge overlaps/adjacent intervals as configured;
7. ensure low-motion speed-up intervals do not conflict incorrectly with removed ranges;
8. calculate final timeline deterministically.

## Data/trust boundaries

```text
ChatGPT upload/file reference   = untrusted
MCP tool arguments              = untrusted
model analysis/edit plan        = untrusted
server-side downloaded bytes    = untrusted
curated internal music library  = trusted only after ingestion validation
internal typed timeline state   = trusted after validation boundary
```

No prompt instruction is considered a security boundary.

## Job workspace

Each request should use an isolated temporary workspace such as:

```text
/jobs/<random-job-id>/
  input/
  analysis/
  render/
```

Exact storage implementation is not locked yet.

Requirements:

- randomized non-user-controlled paths;
- bounded lifetime/TTL;
- cleanup on success/failure where practical;
- no sensitive temporary URLs in normal logs;
- no arbitrary path access through MCP arguments.

## First technical spike

Do not begin by building the complete renderer.

The first vertical slice must prove:

```text
short AI video
→ AutoVD prepares timestamped frames
→ ChatGPT can inspect the sequence through MCP
→ ChatGPT returns structured anomaly interval(s)
→ result is compared with human labels
```

### Spike pass condition

The exact evaluation corpus will be defined during planning, but the spike must demonstrate that clear anomalies can be located with precision compatible with the product's conservative full-auto policy.

### If the spike fails

Revisit how temporal visual evidence is exposed to the model before investing in broader backend features. Do not mask a failed analysis assumption by adding more renderer infrastructure.

## Post-MVP direction

The architecture may later expand from cleanup to creative editing:

```text
CUT / KEEP
    ↓
CUT / KEEP / TRIM / SPEED_UP / SLOW_DOWN / REORDER / SELECT_BEST_TAKE
```

That expansion is explicitly out of scope until the MVP cleanup loop is proven.
