# AutoVD MVP Task Checklist

Source: `tasks/plan.md`

## Gate A — Prove the AI/MCP assumption first

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
  - [ ] Create a small human-labeled clean/anomaly corpus.
  - [ ] Score cut precision separately from recall.
  - [ ] Verify uncertain/clean footage is normally kept.
  - [ ] Run the fixed set through the real ChatGPT/MCP workflow.
  - [ ] **GO only if cut precision meets the approved threshold (initial target >= 90%).**

> If Gate A fails: stop the broader MVP build and revise the analysis architecture/spec/ADR before proceeding.

## Gate B — Deterministic editing core

- [ ] **Task 4 — Safe media ingestion + job workspace**
  - [ ] Validate file/media/count/size/duration boundaries.
  - [ ] Create isolated randomized ephemeral workspaces.
  - [ ] Preserve trusted upload order metadata.
  - [ ] Add focused boundary/integration tests.

- [ ] **Task 5 — Frame sampling + motion detection**
  - [ ] Support coarse and dense timestamped sampling.
  - [ ] Implement deterministic motion scoring.
  - [ ] Extract sustained low-motion regions.
  - [ ] Keep thresholds/min duration/speed factor configurable.
  - [ ] Add static/moving synthetic tests.

- [ ] **Task 6 — Edit-plan + timeline engine**
  - [ ] Define strict typed CUT contracts.
  - [ ] Enforce `certainty == clear` for final CUT.
  - [ ] Validate timestamps/enums/ranges.
  - [ ] Sort/merge intervals deterministically.
  - [ ] Resolve CUT vs speed-up conflicts.
  - [ ] Add RED→GREEN unit tests for edge cases.

> Gate B passes only when Tasks 4–6 have stable contracts and focused tests passing.

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
