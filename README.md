# AutoVD

AutoVD is a full-auto cleanup pipeline for AI-generated video clips.

The MVP is designed to run inside ChatGPT: the user uploads one or more AI-generated clips, ChatGPT identifies only clear visual generation failures, and the AutoVD MCP backend validates the edit plan, speeds up sustained low-motion regions, removes source audio, adds one curated music track, and renders one final video.

## MVP workflow

```text
Upload 1..N clips in ChatGPT
        ↓
prepare_video_analysis
        ↓
validated isolated job + clip metadata
        ↓
get_analysis_chunk
        ↓
timestamped bounded frame evidence
        ↓
ChatGPT emits conservative CUT candidates
        ↓
backend validates CUTs + detects low motion
        ↓
CUT / speed-up / preserve upload order
        ↓
remove source audio + add one music track
        ↓
render H.264/AAC MP4
        ↓
return MCP output resource
```

## Product rules

- Full auto: no mandatory timeline review in the MVP.
- Precision over recall: uncertain visual regions are kept.
- ChatGPT decides **what** looks visually broken; deterministic backend code decides **how** edits are executed.
- Low-motion pacing is deterministic and non-semantic.
- Upload order is the final clip order.
- All source audio is removed.
- Exactly one track from the server-owned curated music library supplies output audio.
- No standalone frontend, accounts, database, persistent media storage, semantic story editing, or scene reordering in the MVP.

## Current implementation status

### Backend: implemented and runtime-verified

The deterministic/backend path is implemented through the MVP hardening slice:

- safe staged-media ingestion with `ffprobe` validation, configured count/size/duration limits, randomized internal paths, and isolated workspaces;
- bounded sparse/dense timestamped PNG sampling for visual analysis;
- deterministic FFmpeg-only grayscale motion scoring and sustained low-motion detection;
- strict typed CUT contracts with `certainty == clear`, timestamp validation, overlap merge, and CUT precedence over speed-up;
- deterministic timeline generation;
- FFmpeg render pipeline with normalization, cuts, speed-ups, upload-order concatenation, complete source-audio removal, one curated music track, and H.264/AAC MP4 output;
- production MCP tools: `prepare_video_analysis`, `get_analysis_chunk`, and `render_video`;
- current ChatGPT file-parameter metadata on the upload tool;
- MCP output resource/`ResourceLink` for the rendered MP4;
- HTTPS/public-address/redirect/stream-size controls for temporary uploaded-file downloads;
- bounded active jobs, lazy TTL cleanup, and rendered-output byte limits;
- model-safe errors for implemented external boundaries;
- CI gates for Ruff, format, strict mypy, pytest, FFmpeg integration tests, and MCP Inspector transport checks.

### Still pending: real ChatGPT Gate A

The backend and MCP protocol transport are proven, but **Gate A is deferred, not passed**. The following still require a real ChatGPT Developer Mode session and representative AI-generated footage:

1. connect AutoVD to ChatGPT;
2. confirm ChatGPT receives/interprets timestamp + image ordering as intended;
3. obtain structured anomaly intervals from real model analysis;
4. run the fixed human-labeled anomaly corpus;
5. confirm cut precision meets the approved target before claiming MVP completion.

Do not interpret backend/Inspector success as evidence that ChatGPT visual anomaly quality is sufficient.

## Toolchain

Locked/current repository tooling includes:

- Python project contract: `>=3.12,<3.15`; CI currently runs Python 3.13;
- `mcp[cli] == 2.0.0`;
- `pydantic == 2.13.4`;
- `pytest == 9.1.1`;
- `ruff == 0.16.3`;
- `mypy == 2.3.0`;
- `uv == 0.12.5` in CI;
- MCP Inspector `2.2.0` in CI;
- FFmpeg supplied by the runtime/OS.

Motion analysis intentionally uses FFmpeg only; OpenCV is not required by the current MVP implementation.

## Canonical commands

```bash
uv sync --all-groups --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest -q
uv run autovd-mcp
```

The local MCP endpoint is exposed at `http://127.0.0.1:8000/mcp` by the current entrypoint.

For the legacy temporal spike tool only, a server operator may configure:

```bash
AUTOVD_SPIKE_VIDEO=/absolute/path/to/short-test-video.mp4 uv run autovd-mcp
```

Models/users cannot supply that filesystem path through the spike tool.

## MVP runtime configuration

Current server-owned defaults are configurable through environment variables. Important resource bounds include:

- `AUTOVD_MAX_ACTIVE_JOBS=8`
- `AUTOVD_JOB_TTL_SECONDS=1800`
- `AUTOVD_MAX_OUTPUT_BYTES=536870912`
- `AUTOVD_MAX_CLIPS=8`
- `AUTOVD_MAX_FILE_BYTES=268435456`
- `AUTOVD_MAX_CLIP_DURATION_MS=120000`
- `AUTOVD_RENDER_TIMEOUT_SECONDS=180`
- `AUTOVD_MUSIC_DIR=music/library`

These are operational defaults, not promises about future product limits.

## Documentation

- [MVP specification](docs/specs/mvp.md)
- [Architecture and workflow](docs/architecture.md)
- [ADR 0001 — ChatGPT + MCP architecture](docs/adr/0001-chatgpt-mcp.md)
- [Implementation plan](tasks/plan.md)
- [Task checklist](tasks/todo.md)
- [Agent/project rules](AGENTS.md)

## Safety boundary

Uploads, temporary download URLs, model edit plans, MCP arguments, media metadata, and process output are untrusted. AutoVD validates those boundaries before privileged media work and never accepts model-generated shell/FFmpeg command text or model-controlled server paths.

The current repository is **backend-ready for the deferred ChatGPT integration/evaluation gate**, not production-shipped and not yet an evidence-backed completed MVP.
