# AutoVD MVP Task Checklist

Source: `tasks/plan.md`

## Gate A — Prove the AI/MCP assumption first

> **Execution note (2026-08-18):** the user explicitly approved deferring the remaining real ChatGPT Developer Mode/evaluation checks so deterministic backend work may continue. Gate A is **deferred, not passed**. Any real ChatGPT interpretation, cut-precision claim, production readiness claim, or MVP-complete claim still requires the pending Gate A evidence below.

- [x] **Task 1 — Minimal Python/MCP scaffold**
  - [x] Pin current Python/MCP dependencies from authoritative docs.
  - [x] Establish canonical dev/test/lint/type commands.
  - [x] Start one minimal MCP server/tool.
  - [x] Verify initialization/list/call with MCP Inspector.

  Verified in GitHub Actions on 2026-08-18: dependency install, Ruff lint/format, strict mypy, pytest, Streamable HTTP MCP startup, Inspector `tools/list`, `health`, and temporal image-result tool call all passed.

- [ ] **Task 2 — ChatGPT temporal-vision spike**
  - [x] Extract ordered timestamped frames from one short fixture clip.
  - [x] Expose temporal timestamp/image evidence through the real MCP protocol.
  - [ ] Connect the real server in ChatGPT Developer Mode.
  - [ ] Obtain a structured anomaly interval from ChatGPT.
  - [ ] Confirm and document that ChatGPT actually receives/interprets the timestamp + image ordering as intended.

  Current stop point: MCP-side transport is proven; the remaining checks require a real ChatGPT Developer Mode app/session and therefore user/workspace participation.

- [ ] **Task 3 — Evaluation harness + go/no-go**
  - [ ] Create a small human-labeled clean/anomaly corpus using real representative AI-generated footage.
  - [x] Define the human-label and predicted-CUT scoring contract.
  - [x] Score cut precision separately from recall.
  - [ ] Verify uncertain/clean footage is normally kept by the real ChatGPT workflow.
  - [ ] Run the fixed set through the real ChatGPT/MCP workflow.
  - [ ] **GO only if cut precision meets the approved threshold (initial target >= 90%).**

> If real Gate A evidence fails, stop and revisit the analysis architecture/spec/ADR. The current deferral only authorizes deterministic backend implementation; it does not convert unknown AI quality into a pass.

## Gate B — Deterministic editing core

- [x] **Task 4 — Safe media ingestion + job workspace**
  - [x] Validate staged file/media/count/size/duration boundaries.
  - [x] Create isolated randomized ephemeral workspaces.
  - [x] Preserve trusted input order metadata.
  - [x] Add focused boundary/integration tests.

  Verified on the staged-media core boundary: `ffprobe` validates actual video content, user filenames are not reused internally, limits are caller-configured, symlink/non-file inputs are rejected, and workspace cleanup occurs on context exit. ChatGPT file-download/handoff remains a Task 8 adapter concern.

- [x] **Task 5 — Frame sampling + motion detection**
  - [x] Support configurable sparse/dense timestamped sampling intervals.
  - [x] Implement deterministic motion scoring.
  - [x] Extract sustained low-motion regions.
  - [x] Keep thresholds/min duration/speed factor configurable.
  - [x] Add static/moving synthetic tests.

  Verified in GitHub Actions on 2026-08-18: bounded 32×32 grayscale FFmpeg sampling distinguishes static synthetic footage from moving `testsrc2`; sustained low-motion runs are grouped deterministically and short low-motion runs are not accelerated. No OpenCV or semantic pacing dependency is used.

- [x] **Task 6 — Edit-plan + timeline engine**
  - [x] Define strict typed CUT contracts.
  - [x] Enforce `certainty == clear` for final CUT.
  - [x] Validate timestamps/enums/ranges.
  - [x] Sort/merge intervals deterministically.
  - [x] Resolve CUT vs speed-up conflicts.
  - [x] Add RED→GREEN unit tests for edge cases.

  Verified in GitHub Actions on 2026-08-18: unknown anomaly categories/invalid ranges are rejected by schema; every candidate is clip/timestamp validated before uncertain candidates are kept; clear touching/overlapping CUTs merge deterministically; CUT takes precedence over overlapping speed-up regions; fully cut clips yield no render segments. Runtime tests also caught and fixed an adjacent-boundary iteration bug before merge.

> **Gate B passes:** Tasks 4–6 now have stable deterministic contracts with focused runtime tests. This does not change the deferred status of Gate A.

## Gate C — Complete product path

- [ ] **Task 7 — FFmpeg renderer vertical slice**
  - [ ] Normalize incompatible inputs.
  - [ ] Remove CUT intervals.
  - [ ] Apply configured speed-ups.
  - [ ] Preserve clip upload order.
  - [ ] Remove all source audio.
  - [ ] Select one curated music track and record its ID.
  - [ ] Render/probe one playable MP4.
  - [ ] Add integration tests with tiny fixture videos.

- [ ] **Task 8 — Production MCP tools**
  - [ ] Implement `prepare_video_analysis`.
  - [ ] Implement `get_analysis_chunk` with dense re-sampling support.
  - [ ] Implement `render_video` with structured edit-plan input only.
  - [ ] Keep MCP handlers thin.
  - [ ] Verify schemas/results with MCP Inspector.
  - [ ] Verify expected tool selection in ChatGPT Developer Mode.

- [ ] **Task 9 — Security/resource hardening**
  - [ ] Bound expensive media/render operations.
  - [ ] Prevent arbitrary paths/shell/FFmpeg text execution.
  - [ ] Add SSRF controls if server-side URL fetching exists.
  - [ ] Ensure logs exclude raw media/secrets/temporary credentials.
  - [ ] Clean job media on terminal states + bounded fallback TTL.
  - [ ] Add abuse/security tests.
  - [ ] Review dependency/lockfile security.

- [ ] **Task 10 — E2E, CI, docs, Definition of Done**
  - [ ] Run the complete ChatGPT → MCP → render flow.
  - [ ] Verify final media streams/order/duration behavior.
  - [ ] Rerun anomaly evaluation and confirm cut precision remains acceptable.
  - [ ] Add CI quality gates using actual repository commands.
  - [ ] Update README/spec/architecture with exact current truth and limits.
  - [ ] Review security/integration/documentation/review evidence against project Definition of Done.

## MVP finish line

- [ ] User uploads 1..N AI-generated clips in ChatGPT.
- [ ] Obvious AI-generation failures are removed with high cut precision.
- [ ] Ambiguous footage is kept by default.
- [ ] Sustained low-motion regions are sped up deterministically.
- [ ] Upload order is preserved.
- [ ] Original audio is absent.
- [ ] Exactly one permitted music track supplies output audio.
- [ ] Final output is one playable video.
- [ ] Model/tool/file inputs are validated before privileged execution.
- [ ] Full relevant tests/checks and runtime verification have actually been executed.
