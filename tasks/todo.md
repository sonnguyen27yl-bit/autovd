# AutoVD MVP Task Checklist

Source: `tasks/plan.md`

## Gate A — Prove the AI/MCP assumption first

> **Execution note (2026-08-18):** the user explicitly approved deferring the remaining real ChatGPT Developer Mode/evaluation checks so deterministic backend work may continue. Gate A is **deferred, not passed**. Any real ChatGPT interpretation, cut-precision claim, production readiness claim, or MVP-complete claim still requires the pending Gate A evidence below.

- [x] **Task 1 — Minimal Python/MCP scaffold**
  - [x] Pin current Python/MCP dependencies from authoritative docs.
  - [x] Establish canonical dev/test/lint/type commands.
  - [x] Start one minimal MCP server/tool.
  - [x] Verify initialization/list/call with MCP Inspector.

- [ ] **Task 2 — ChatGPT temporal-vision spike**
  - [x] Extract ordered timestamped frames from one short fixture clip.
  - [x] Expose temporal timestamp/image evidence through the real MCP protocol.
  - [ ] Connect the real server in ChatGPT Developer Mode.
  - [ ] Obtain a structured anomaly interval from ChatGPT.
  - [ ] Confirm and document that ChatGPT actually receives/interprets the timestamp + image ordering as intended.

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

- [x] **Task 5 — Frame sampling + motion detection**
  - [x] Support configurable sparse/dense timestamped sampling intervals.
  - [x] Implement deterministic motion scoring.
  - [x] Extract sustained low-motion regions.
  - [x] Keep thresholds/min duration/speed factor configurable.
  - [x] Add static/moving synthetic tests.

- [x] **Task 6 — Edit-plan + timeline engine**
  - [x] Define strict typed CUT contracts.
  - [x] Enforce `certainty == clear` for final CUT.
  - [x] Validate timestamps/enums/ranges.
  - [x] Sort/merge intervals deterministically.
  - [x] Resolve CUT vs speed-up conflicts.
  - [x] Add RED→GREEN unit tests for edge cases.

> **Gate B passes:** Tasks 4–6 have stable deterministic contracts with focused runtime tests. This does not change the deferred status of Gate A.

## Gate C — Complete product path

- [x] **Task 7 — FFmpeg renderer vertical slice**
  - [x] Normalize retained segments into one configured output profile.
  - [x] Remove CUT intervals by rendering only retained timeline segments.
  - [x] Apply configured speed-ups.
  - [x] Preserve trusted clip upload order.
  - [x] Remove all source audio from the output graph.
  - [x] Select one curated music track and record its ID.
  - [x] Render/probe one playable MP4.
  - [x] Add integration tests with tiny fixture videos.

- [ ] **Task 8 — Production MCP tools**
  - [x] Implement `prepare_video_analysis` with the current ChatGPT file-parameter contract.
  - [x] Implement `get_analysis_chunk` with bounded subrange/dense re-sampling support.
  - [x] Implement `render_video` with structured edit-plan input only.
  - [x] Keep MCP handlers thin and core behavior in testable services/modules.
  - [x] Return rendered MP4 through an MCP resource template/`ResourceLink` instead of embedding the file in a tool result.
  - [x] Verify production tool names, file-parameter metadata/schema, workflow results, and existing tools through pytest + MCP Inspector on 2026-08-18.
  - [ ] Verify expected tool selection, temporal interpretation, and output UX in real ChatGPT Developer Mode.

  Backend/protocol side is implemented and verified. The final ChatGPT-side check remains part of the deferred human gate and is not claimed as passed.

- [ ] **Task 9 — Security/resource hardening**
  - [ ] Bound remaining job/output lifetime and size risks.
  - [x] Prevent arbitrary model paths and shell/FFmpeg command execution in implemented core.
  - [x] Apply HTTPS/public-host/redirect/streaming size controls to server-side ChatGPT file fetching.
  - [x] Keep normal tool errors model-safe and avoid logging raw media/signed file URLs.
  - [ ] Add bounded fallback cleanup/expiry for active job media.
  - [ ] Add focused abuse/security regression tests.

- [ ] **Task 10 — E2E, CI, docs, Definition of Done**
  - [ ] Run the complete real ChatGPT → MCP → render flow.
  - [x] Run the complete backend workflow with synthetic uploaded-media adapter → analysis chunk → render → output resource.
  - [x] Verify final media streams/order/duration behavior with FFmpeg integration tests.
  - [ ] Rerun anomaly evaluation against real ChatGPT and confirm cut precision remains acceptable.
  - [x] Maintain CI gates using actual repository commands.
  - [ ] Update README/spec/architecture/AGENTS with exact final backend state and deferred human gates.
  - [ ] Review security/integration/documentation/review evidence against project Definition of Done.

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
- [ ] Full real ChatGPT integration/evaluation evidence is complete.
