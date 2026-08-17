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

## Current implementation status

Gate A is in progress.

Implemented and runtime-verified so far:

- Python project scaffold with `uv.lock`;
- MCP Python SDK v2 server using Streamable HTTP;
- typed `health` diagnostic tool;
- deterministic FFmpeg timestamped PNG frame sampler;
- `get_temporal_analysis_demo` spike tool;
- temporal MCP results represented as ordered timestamp `TextContent` + PNG `ImageContent` blocks;
- unit/integration tests for diagnostic, frame extraction, multimodal evidence, and in-memory MCP calls;
- GitHub Actions gates for lint, format, strict mypy, pytest, and MCP Inspector;
- MCP Inspector verification of tool listing, `health`, and temporal image-result transport.

Not yet proven: ChatGPT itself consuming the temporal image sequence through a real Developer Mode app and returning an anomaly interval. That is the next Gate A step.

## Toolchain

Locked/bootstrap versions currently include:

- Python 3.13 in CI (`>=3.12,<3.15` supported by project metadata)
- `mcp[cli] == 2.0.0`
- `pydantic == 2.13.4`
- `pytest == 9.1.1`
- `ruff == 0.16.3`
- `mypy == 2.3.0`
- `uv == 0.12.5` in CI
- MCP Inspector `2.2.0` in CI
- FFmpeg supplied by the runtime/OS

OpenCV is still only a proposed dependency for later motion scoring and has not been added yet.

## Canonical commands

Install locked dependencies:

```bash
uv sync --all-groups --locked
```

Run the MCP server locally:

```bash
uv run autovd-mcp
```

Run tests:

```bash
uv run pytest -q
```

Lint:

```bash
uv run ruff check .
```

Format check:

```bash
uv run ruff format --check .
```

Type check:

```bash
uv run mypy src
```

Inspect a running local MCP endpoint:

```bash
npx --yes @modelcontextprotocol/inspector@2.2.0 --cli \
  http://127.0.0.1:8000/mcp --transport http --method tools/list
```

The temporal spike reads a server-operator-controlled fixture path from `AUTOVD_SPIKE_VIDEO`. Models/users cannot submit arbitrary filesystem paths through that tool.

Example local spike setup:

```bash
AUTOVD_SPIKE_VIDEO=/absolute/path/to/short-test-video.mp4 uv run autovd-mcp
```

## Documentation

- [MVP specification](docs/specs/mvp.md)
- [Architecture and workflow](docs/architecture.md)
- [ADR 0001 — ChatGPT + MCP architecture](docs/adr/0001-chatgpt-mcp.md)
- [Implementation plan](tasks/plan.md)
- [Task checklist](tasks/todo.md)
- [Agent/project rules](AGENTS.md)

## Safety boundary

The current temporal spike intentionally accepts only a fixture path configured by the server operator. User-upload ingestion, path isolation, media limits, and production job workspaces are later tasks and must be implemented before AutoVD handles arbitrary uploads.
