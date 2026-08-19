# AutoVD MVP Task Checklist

Source: `tasks/plan.md`

## Gate A — Real ChatGPT temporal-analysis proof

> **Execution note (2026-08-18):** the user explicitly approved deferring the remaining real ChatGPT integration/evaluation checks so deterministic backend work could continue. Gate A is **deferred, not passed**. Backend completion does not convert unknown model quality into a pass.

- [x] **Task 1 — Minimal Python/MCP scaffold**
  - [x] Pin current Python/MCP dependencies from authoritative docs.
  - [x] Establish canonical dev/test/lint/type commands.
  - [x] Start one minimal MCP server/tool.
  - [x] Verify initialization/list/call with MCP Inspector.

- [ ] **Task 2 — ChatGPT temporal-vision spike**
  - [x] Extract ordered timestamped frames from one short fixture clip.
  - [x] Expose timestamp/image evidence through the real MCP protocol.
  - [x] Prepare the MCP server for remote server-URL deployment with configurable bind settings, hostname allowlisting, health checks, and a verified container image.
  - [ ] Connect the real server as an internal ChatGPT plugin/app using the remote MCP URL.
  - [ ] Obtain a structured anomaly interval from real ChatGPT.
  - [ ] Confirm ChatGPT interprets timestamp + image ordering as intended.

- [ ] **Task 3 — Evaluation harness + go/no-go**
  - [ ] Create/finalize a small human-labeled clean/anomaly corpus using representative AI-generated footage.
  - [x] Define the human-label and predicted-CUT scoring contract.
  - [x] Score cut precision separately from recall.
  - [ ] Verify uncertain/clean footage is normally kept by the real ChatGPT workflow.
  - [ ] Run the fixed set through the real ChatGPT/MCP workflow.
  - [ ] **GO only if cut precision meets the approved initial target >= 90%.**

> If real Gate A evidence fails, revisit the analysis representation/prompt/spec before claiming the MVP works. The deterministic backend is intentionally isolated so it remains reusable.

## Gate B — Deterministic editing core

- [x] **Task 4 — Safe media ingestion + job workspace**
  - [x] Validate staged file/media/count/size/duration boundaries.
  - [x] Create isolated randomized ephemeral workspaces.
  - [x] Preserve trusted input order metadata.
  - [x] Add focused boundary/integration tests.

- [x] **Task 5 — Frame sampling + motion detection**
  - [x] Support configurable sparse/dense timestamped sampling intervals.
  - [x] Implement deterministic FFmpeg-only motion scoring.
  - [x] Extract sustained low-motion regions.
  - [x] Keep thresholds/min duration/speed factor configurable.
  - [x] Add static/moving synthetic tests.

- [x] **Task 6 — Edit-plan + timeline engine**
  - [x] Define strict typed CUT contracts.
  - [x] Enforce `certainty == clear` for final CUT.
  - [x] Validate timestamps/enums/ranges/clip identity.
  - [x] Sort/merge intervals deterministically.
  - [x] Resolve CUT vs speed-up conflicts with CUT precedence.
  - [x] Add RED→GREEN unit tests for edge cases.

> **Gate B passes:** deterministic ingestion, motion, edit-plan, and timeline contracts have focused runtime evidence.

## Gate C — Backend product path

- [x] **Task 7 — FFmpeg renderer vertical slice**
  - [x] Normalize retained segments into one configured output profile.
  - [x] Remove CUT intervals by rendering only retained timeline segments.
  - [x] Apply configured speed-ups.
  - [x] Preserve trusted clip upload order.
  - [x] Remove all source audio from the output graph.
  - [x] Select one curated music track and record its ID.
  - [x] Render/probe one playable H.264/AAC MP4.
  - [x] Add real FFmpeg integration tests with tiny synthetic videos.

- [ ] **Task 8 — Production MCP tools**
  - [x] Implement `prepare_video_analysis` with the current ChatGPT file-parameter contract.
  - [x] Implement `get_analysis_chunk` with bounded subrange/dense re-sampling support.
  - [x] Implement `render_video` with structured edit-plan input only.
  - [x] Keep MCP handlers thin and core behavior in testable services/modules.
  - [x] Return rendered MP4 through an MCP resource template/`ResourceLink`.
  - [x] Verify production tool names, file-parameter metadata/schema, workflow results, and existing tools through pytest + MCP Inspector.
  - [ ] Verify expected tool selection, temporal interpretation, and output UX in a real ChatGPT internal plugin/app session.

  Backend/protocol implementation is complete. The final ChatGPT-side behavior belongs to deferred Gate A and is not claimed as passed.

- [x] **Task 9 — MVP security/resource hardening**
  - [x] Bound active job count, inactivity TTL, input resources, render timeout, frame payloads, and output resource bytes.
  - [x] Prevent arbitrary model paths and model-generated shell/FFmpeg execution.
  - [x] Apply HTTPS/public-address/redirect/timeout/stream-size controls to server-side ChatGPT file fetching.
  - [x] Ignore untrusted filenames for staged paths.
  - [x] Keep implemented tool/media errors model-safe and avoid normal logging of raw media/signed URLs.
  - [x] Add lazy job expiry/cleanup before reuse of active-job capacity.
  - [x] Add focused abuse/security regression tests.
  - [x] Keep hardening MVP-scoped: no auth/database/background scheduler/rate-limit service added.

  Verified on PR #8 exact head: locked dependency install, Ruff lint, format check, strict mypy, full pytest including hardening/media tests, and MCP Inspector all passed before merge.

- [ ] **Task 10 — E2E, CI, docs, Definition of Done**
  - [ ] Run the complete **real ChatGPT → MCP → render → returned output** flow.
  - [x] Run the complete backend workflow with synthetic uploaded-media adapter → analysis chunk → render → output resource.
  - [x] Verify final media streams/order/duration/cut/speed/audio behavior with FFmpeg integration tests.
  - [ ] Rerun anomaly evaluation against real ChatGPT and confirm cut precision remains acceptable.
  - [x] Maintain CI gates using actual repository commands and pinned Action SHAs.
  - [x] Keep FFmpeg CI setup bounded/retryable rather than allowing an indefinite dependency-install stall.
  - [x] Build and smoke-test a deployment container exposing the MCP server and `/health` endpoint.
  - [x] Document the remote HTTPS server-URL deployment path and required public Host allowlist.
  - [x] Update README/spec/architecture/AGENTS with exact current backend state and deferred human gates.
  - [x] Review backend correctness/security/integration/documentation evidence against the project Definition of Done.

  **Backend completion point:** everything that can be verified without a real ChatGPT internal plugin/app session and representative human-labeled AI footage is implemented or explicitly documented. Task 10 remains open only because the real-model evidence items above are part of MVP success, not because deterministic backend/deployment packaging is missing.

## Backend Definition of Done evidence

- [x] Task acceptance criteria for deterministic backend slices are implemented.
- [x] New deterministic behavior has regression/integration tests.
- [x] Existing full pytest suite passes on the relevant merged/PR heads.
- [x] Ruff lint and format checks pass.
- [x] Strict mypy passes.
- [x] Real FFmpeg integration behavior is exercised in CI.
- [x] Running MCP Streamable HTTP endpoint is exercised with MCP Inspector.
- [x] Deployment Docker image builds and its published-port health endpoint is smoke-tested in CI.
- [x] Model/file/tool inputs are validated before privileged media operations.
- [x] No model-controlled shell commands or filesystem paths are accepted.
- [x] Resource bounds and temporary-job cleanup policy are implemented.
- [x] Current docs describe implemented backend truth and explicitly preserve the unresolved Gate A.
- [ ] Real ChatGPT visual-analysis quality is verified.
- [ ] Real ChatGPT end-to-end UX/output handoff is verified.

## MVP finish line

- [ ] User uploads 1..N AI-generated clips in real ChatGPT and receives the final result end-to-end.
- [ ] Obvious AI-generation failures are removed with high cut precision on the real evaluation set.
- [x] Ambiguous/uncertain edit candidates are kept by backend policy.
- [x] Sustained low-motion regions are sped up deterministically.
- [x] Upload order is preserved by the trusted core contract.
- [x] Original source audio is absent from rendered output.
- [x] Exactly one permitted music track supplies output audio in the renderer core.
- [x] Final backend render is one playable H.264/AAC MP4.
- [x] Implemented model/tool/file inputs are validated before privileged execution.
- [x] Deterministic backend checks and runtime verification have been executed.
- [ ] Full real ChatGPT integration/evaluation evidence is complete.
