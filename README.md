# AutoVD

AutoVD is a full-auto AI video cleanup tool for AI-generated clips.

The MVP runs entirely inside ChatGPT: the user uploads one or more AI-generated video clips, ChatGPT analyzes obvious visual generation failures, and an MCP-backed deterministic video backend applies the edit plan and returns one rendered video.

## MVP goal

Turn raw AI-generated clips into a cleaner final video with no mandatory manual review.

```text
Upload clips in ChatGPT
        ↓
ChatGPT + AutoVD MCP
        ↓
Prepare temporal visual analysis
        ↓
Detect obvious AI visual anomalies
        ↓
CUT only high-certainty bad regions
        ↓
Detect sustained low-motion regions
        ↓
Speed up slow regions
        ↓
Preserve upload order and concatenate clips
        ↓
Remove all source audio
        ↓
Add one random track from the curated music library
        ↓
Render and return one final video
```

## Product principles

- Full auto: no mandatory timeline review in the MVP.
- Conservative cuts: prefer keeping an uncertain region over deleting good footage.
- Precision over recall for AI-error removal.
- ChatGPT decides **what** looks broken; the backend decides **how** to perform the edit safely.
- Motion-based pacing only in the MVP; semantic/story pacing is post-MVP.
- Upload order is the final clip order.
- Original input audio is always removed.
- No standalone frontend in the MVP.

## Documentation

- [MVP specification](docs/specs/mvp.md)
- [Architecture and workflow](docs/architecture.md)
- [ADR 0001 — ChatGPT + MCP architecture](docs/adr/0001-chatgpt-mcp.md)
- [Agent/project rules](AGENTS.md)

## Current status

Documentation-first initialization. No production implementation exists yet.

The next engineering phase is planning. The first planned technical spike should prove the highest-risk assumption: whether a ChatGPT + MCP workflow can inspect a timestamped temporal frame sequence accurately enough to locate obvious AI-generation anomalies with high cut precision.

## Proposed implementation stack

Not yet dependency-locked:

- Python
- Model Context Protocol (MCP) server
- FFmpeg for deterministic media editing/rendering
- OpenCV for frame sampling and motion scoring
- Pydantic or equivalent schema validation for boundaries

Exact versions and commands must be verified against the repository once the project scaffold is created.
