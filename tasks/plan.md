# AutoVD MVP Implementation Plan

- **Status:** Ready for human review
- **Date:** 2026-08-18
- **Source spec:** `docs/specs/mvp.md`
- **Architecture:** `docs/architecture.md`
- **ADR:** `docs/adr/0001-chatgpt-mcp.md`

## Goal

Implement the smallest full-auto AutoVD MVP that can be used from ChatGPT Web through MCP:

```text
AI-generated clips
→ timestamped temporal analysis
→ conservative AI anomaly CUT decisions
→ deterministic low-motion speed-up
→ deterministic render
→ remove source audio
→ add random curated music
→ return one playable video
```

The plan is deliberately **risk-first**. The project must prove the ChatGPT + MCP temporal-vision handoff before investing heavily in rendering/infrastructure.

## Planning assumptions

These are implementation assumptions, not new product requirements:

1. Python remains the preferred backend language unless the spike exposes a concrete blocker.
2. FFmpeg remains the media execution engine; OpenCV or an equivalently simple library handles frame sampling/motion scoring.
3. ChatGPT does visual anomaly reasoning; AutoVD backend does not call a second AI provider in the MVP.
4. No standalone frontend, auth system, database, or persistent user-video storage is introduced.
5. Exact dependency versions, file-upload handoff details, and model-visible MCP image/frame representation are **not considered proven until Task 1/2 verification**.
6. All uploaded media and model/tool output remain untrusted and are validated before privileged operations.

## Current OpenAI integration facts to design around

Verified against current official OpenAI documentation on 2026-08-18:

- ChatGPT Developer Mode provides MCP client support for read and write tools.
- A remote MCP server can be connected to ChatGPT Developer Mode.
- OpenAI's plugin/MCP testing guidance recommends validating the server directly with MCP Inspector before testing it in ChatGPT.
- For remote development, the MCP endpoint must be reachable through supported transport (public HTTPS/streamable HTTP or supported secure tunnel path).
- Current OpenAI models support image input, but AutoVD must still runtime-prove the exact **timestamped multi-frame MCP → ChatGPT context** mechanism needed for this product.

Official references:

- https://developers.openai.com/api/docs/guides/developer-mode
- https://developers.openai.com/plugins/deploy/connect-chatgpt
- https://developers.openai.com/api/docs/models

## Dependency graph

```text
Task 1  Minimal project scaffold + current MCP contract proof
   ↓
Task 2  Temporal-vision vertical spike in ChatGPT
   ↓
Task 3  Evaluation harness + go/no-go decision
   │
   ├── FAIL → revisit ADR/analysis representation; STOP broader MVP build
   │
   └── PASS
        ↓
Task 4  Safe media ingestion + job workspace
        ↓
Task 5  Frame sampling + deterministic motion analysis
        ↓
Task 6  Typed edit-plan/timeline engine
        ↓
Task 7  Deterministic FFmpeg render vertical slice
        ↓
Task 8  Production MCP tool surface integration
        ↓
Task 9  Security/resource hardening + cleanup
        ↓
Task 10 End-to-end verification + CI/docs readiness
```

Tasks 4–6 may partially proceed in parallel **only after Task 3 passes**, because they share contracts that should be locked by the spike first.

---

## Task 1: Create the minimal Python/MCP scaffold and prove the transport contract

**Description:** Create only enough project structure to run a tiny MCP server locally/remotely and validate the exact current SDK/tool contract. Pin current dependency versions from authoritative sources at implementation time. Do not add video-processing architecture yet.

**Acceptance criteria:**

- [ ] Repository has a minimal Python project/lockfile and one canonical package namespace (`autovd`).
- [ ] A minimal MCP server starts and exposes one harmless diagnostic tool with explicit input/output schema.
- [ ] MCP Inspector can initialize the server, list the tool, call it, and observe a model-readable result.

**Verification:**

- [ ] Run the repository's newly established install/dev/test/lint/type commands and record them in README/spec.
- [ ] Run `npx @modelcontextprotocol/inspector@latest` against the server and capture the actual initialization/tool-call result.
- [ ] Verify the chosen MCP SDK/API pattern against current official OpenAI/MCP documentation; do not rely on remembered signatures.

**Dependencies:** None.

**Files likely touched:**

- `pyproject.toml`
- lockfile
- `src/autovd/mcp_server.py`
- `tests/test_mcp_server.py`
- `README.md`

**Estimated scope:** Medium (3–5 source/config files plus lockfile).

---

## Task 2: Prove the ChatGPT temporal-vision handoff

**Description:** Build the narrowest end-to-end spike for the project's highest-risk assumption. Take one short fixture clip, extract timestamped representative frames, expose them through MCP in a model-consumable form, connect the server to ChatGPT Developer Mode, and verify that ChatGPT can inspect the ordered temporal evidence and return a structured anomaly interval.

**Acceptance criteria:**

- [ ] One short clip can be transformed into an ordered timestamped frame sequence.
- [ ] ChatGPT can access the frame evidence through the actual MCP connection, not through a manually pasted substitute.
- [ ] ChatGPT returns a parseable structured decision containing clip ID, interval, category, certainty, and evidence.

**Verification:**

- [ ] MCP Inspector verifies the analysis tool's schema and representative result.
- [ ] ChatGPT Developer Mode invokes the real tool successfully in a fresh conversation.
- [ ] Record exactly what representation ChatGPT received (for example image/file references + timestamps) and update `docs/architecture.md` if the actual mechanism differs from the current hypothesis.

**Dependencies:** Task 1.

**Files likely touched:**

- `src/autovd/tools/analysis_spike.py`
- `src/autovd/media/frame_sampler.py`
- `src/autovd/contracts/analysis.py`
- `tests/test_analysis_spike.py`
- `docs/architecture.md`

**Estimated scope:** Medium.

---

## Task 3: Build the anomaly evaluation harness and enforce a go/no-go gate

**Description:** Turn the spike into evidence rather than a demo. Create a tiny human-labeled corpus with clean and obviously broken AI-generated intervals, a repeatable prompt/rubric, and a scorer focused on cut precision.

**Acceptance criteria:**

- [ ] Evaluation data includes clean footage plus at least several distinct MVP anomaly categories.
- [ ] Labels contain clip ID, start/end interval, `should_cut`, and category.
- [ ] The evaluation produces cut precision and anomaly recall separately; precision is the primary metric.

**Verification:**

- [ ] Run the fixed evaluation set through the real ChatGPT/MCP workflow and preserve results in a non-sensitive report.
- [ ] Confirm ambiguous/clean examples are normally kept.
- [ ] **GO condition:** observed cut precision is compatible with the spec target (initially >= 90% on the small labeled set). If not, mark the spike failed and stop Tasks 4–10 until the analysis architecture/spec/ADR is revisited.

**Dependencies:** Task 2.

**Files likely touched:**

- `tests/eval/labels.json`
- `tests/eval/README.md`
- `tests/eval/score.py`
- `docs/evals/temporal-spike.md`

**Estimated scope:** Medium.

### Checkpoint A — Analysis architecture gate

Do not continue the full MVP build unless Task 3 passes or the user explicitly approves a revised architecture after reviewing the evidence.

---

## Task 4: Implement safe media ingestion and isolated job workspaces

**Description:** Implement validated ingestion for 1..N uploaded clips and isolated temporary job state. Keep storage ephemeral for the MVP.

**Acceptance criteria:**

- [ ] Supported media is validated by content/probe results and bounded by configured count/size/duration limits.
- [ ] Each job uses randomized internal identifiers/paths not controlled by the model/user.
- [ ] Clip upload order is persisted in trusted internal job metadata.

**Verification:**

- [ ] Unit tests reject invalid media metadata, invalid counts, unsafe identifiers/paths, and configured limit violations.
- [ ] Integration fixture with multiple clips preserves input order.
- [ ] Temporary credentials/raw media/path values are absent from normal logs.

**Dependencies:** Task 3 PASS.

**Files likely touched:**

- `src/autovd/media/ingest.py`
- `src/autovd/media/probe.py`
- `src/autovd/jobs/workspace.py`
- `src/autovd/config.py`
- `tests/unit/test_ingest.py`

**Estimated scope:** Medium.

---

## Task 5: Implement frame sampling and deterministic low-motion detection

**Description:** Generalize the spike's frame sampler and add the MVP pacing heuristic. Keep motion logic deterministic and config-driven; do not introduce semantic pacing.

**Acceptance criteria:**

- [ ] Coarse and dense sampling produce ordered frames with stable timestamps.
- [ ] Motion scoring detects sustained low-motion regions according to configured threshold/minimum duration.
- [ ] Speed factor and all motion thresholds are config-driven with safe bounds.

**Verification:**

- [ ] Unit tests use synthetic/static/moving frames to prove score and region extraction behavior.
- [ ] A generated low-motion fixture yields the expected speed-up interval.
- [ ] Normal-motion fixture does not receive an unintended speed-up interval.

**Dependencies:** Task 3 PASS; may be developed alongside Task 4 after shared contracts are agreed.

**Files likely touched:**

- `src/autovd/media/frame_sampler.py`
- `src/autovd/media/motion.py`
- `src/autovd/contracts/analysis.py`
- `src/autovd/config.py`
- `tests/unit/test_motion.py`

**Estimated scope:** Medium.

---

## Task 6: Implement the typed edit-plan and timeline engine

**Description:** Define the trusted boundary between model judgment and deterministic execution. Validate model-produced CUT decisions and compute a conflict-free final timeline.

**Acceptance criteria:**

- [ ] CUT schema restricts decisions/categories/certainty and validates finite integer timestamps.
- [ ] Only `certainty == clear` CUT decisions can enter the render plan; uncertain decisions are kept.
- [ ] Timeline logic sorts/merges intervals and resolves removed ranges vs. speed-up ranges deterministically.

**Verification:**

- [ ] RED→GREEN unit tests cover negative timestamps, `start >= end`, out-of-range intervals, overlap merge, adjacency policy, malformed enums, and speed/cut conflicts.
- [ ] Property/parameterized tests cover interval ordering and non-overlap invariants where practical.
- [ ] No test requires executing FFmpeg; timeline logic remains pure/testable.

**Dependencies:** Task 3 PASS.

**Files likely touched:**

- `src/autovd/contracts/edit_plan.py`
- `src/autovd/media/timeline.py`
- `tests/unit/test_edit_plan.py`
- `tests/unit/test_timeline.py`

**Estimated scope:** Medium.

### Checkpoint B — Deterministic core gate

Before renderer work, Tasks 4–6 must have focused tests passing and a stable typed contract for job metadata, frame timestamps, CUT intervals, and speed-up intervals.

---

## Task 7: Implement one deterministic FFmpeg render vertical slice

**Description:** Build the smallest complete media-output path using argument arrays, never model-generated command text. It must apply cuts and speed-ups, preserve clip order, remove all original audio, attach one selected curated track, and produce a probeable output.

**Acceptance criteria:**

- [ ] Multiple normalized clips are rendered in upload order with requested CUT ranges absent.
- [ ] Configured low-motion regions are accelerated and original source audio is absent.
- [ ] Exactly one selected library music track supplies output audio and its stable ID is recorded.

**Verification:**

- [ ] Integration tests use tiny generated/checked-in-safe fixture videos and probe output duration/streams.
- [ ] Test proves a known CUT interval is absent within defined timestamp tolerance.
- [ ] FFmpeg invocation uses a structured argument list and cannot execute arbitrary model/user shell text.

**Dependencies:** Tasks 4, 5, 6.

**Files likely touched:**

- `src/autovd/media/renderer.py`
- `src/autovd/media/music.py`
- `tests/integration/test_renderer.py`
- `tests/fixtures/README.md`
- `music/library/README.md`

**Estimated scope:** Medium.

---

## Task 8: Integrate the production MCP tool surface

**Description:** Replace spike-only behavior with the three small capability-oriented tools from the spec: `prepare_video_analysis`, `get_analysis_chunk`, and `render_video`. MCP handlers remain thin adapters over typed core modules.

**Acceptance criteria:**

- [ ] The three tool schemas match the spec or the spec is updated first for any necessary contract change.
- [ ] `get_analysis_chunk` supports coarse and denser temporal evidence without exposing server paths.
- [ ] `render_video` accepts only validated structured edit plans and returns structured output metadata/file reference.

**Verification:**

- [ ] MCP contract tests cover valid, invalid, missing, and boundary arguments.
- [ ] MCP Inspector can list/call all tools and structured results match declared schemas.
- [ ] ChatGPT Developer Mode selects expected tools for direct/follow-up requests and avoids tools for unsupported requests.

**Dependencies:** Task 7.

**Files likely touched:**

- `src/autovd/mcp_server.py`
- `src/autovd/tools/prepare_video_analysis.py`
- `src/autovd/tools/get_analysis_chunk.py`
- `src/autovd/tools/render_video.py`
- `tests/integration/test_mcp_tools.py`

**Estimated scope:** Medium.

---

## Task 9: Add security/resource hardening and deterministic cleanup

**Description:** Harden every untrusted boundary now that the full path exists. Focus on file/media validation, URL-fetch safety if applicable, subprocess/path safety, resource bounds, and temporary data deletion.

**Acceptance criteria:**

- [ ] Count/size/duration/frame/render limits are bounded and centrally configured.
- [ ] No model/user-controlled path or shell syntax reaches privileged media execution.
- [ ] Job temp data is cleaned on successful completion and has a bounded fallback TTL/failure cleanup strategy.

**Verification:**

- [ ] Security/abuse tests cover malformed edit plans, path traversal attempts, oversized/overlong inputs, unsupported media, and unsafe remote URL behavior if remote fetching is present.
- [ ] Secret/private URL/raw media logging review finds no forbidden fields in normal logs.
- [ ] Dependency/lockfile review is performed using the ecosystem's current audit tooling; findings are triaged rather than auto-force-upgraded.

**Dependencies:** Task 8.

**Files likely touched:**

- `src/autovd/config.py`
- `src/autovd/jobs/cleanup.py`
- `src/autovd/media/ingest.py`
- `tests/security/test_boundaries.py`
- `.gitignore`

**Estimated scope:** Medium.

---

## Task 10: End-to-end verification, CI, and documentation readiness

**Description:** Prove the complete user journey and establish repeatable merge gates. This task does not add product features.

**Acceptance criteria:**

- [ ] A representative ChatGPT request can traverse upload/analysis/dense verification/render and return one playable final video.
- [ ] Required repository checks are automated in CI in cheap-to-expensive order (format/lint/type/unit/integration/security as appropriate).
- [ ] README/spec/architecture/ADR accurately describe the implemented current truth, including exact setup/test commands and known limits.

**Verification:**

- [ ] Full repository test/lint/type suite passes.
- [ ] End-to-end ChatGPT Developer Mode scenario is executed and recorded, including tool selection/results and final media probe.
- [ ] Human-labeled anomaly evaluation is rerun; cut precision remains at/above the approved threshold.
- [ ] Definition of Done is reviewed before declaring MVP complete.

**Dependencies:** Task 9.

**Files likely touched:**

- `.github/workflows/ci.yml`
- `README.md`
- `docs/specs/mvp.md`
- `docs/architecture.md`
- `docs/evals/mvp.md`

**Estimated scope:** Medium.

### Checkpoint C — MVP completion gate

MVP is not complete merely because rendering works. Completion requires both task acceptance criteria and the project-wide Definition of Done: correctness, actual runtime verification, security, integration, documentation, and review evidence.

---

## Vertical slices

The implementation sequence intentionally creates usable evidence at each stage:

1. **Transport slice:** MCP server can be inspected/called.
2. **AI feasibility slice:** ChatGPT sees real timestamped temporal evidence and emits a structured anomaly interval.
3. **Evaluation slice:** AI behavior is scored; architecture either passes or stops.
4. **Deterministic core slice:** trusted job/timeline/motion contracts work without FFmpeg.
5. **Renderer slice:** known deterministic edit plan produces known output.
6. **ChatGPT product slice:** ChatGPT drives the real MCP tools end-to-end.
7. **Hardening/ship slice:** boundary abuse, cleanup, CI, docs, and DoD are verified.

## Risks and mitigations

### R1 — ChatGPT cannot reliably consume temporal evidence through MCP

**Impact:** Kills the current primary architecture.

**Mitigation:** Tasks 1–3 come first; no broad backend build before the evaluation gate.

### R2 — High false-positive CUT rate

**Impact:** Full-auto tool destroys good footage.

**Mitigation:** conservative rubric, coarse→dense verification, `certainty == clear` boundary, precision-first evaluation.

### R3 — Sparse frame sampling misses short glitches

**Impact:** Recall is poor.

**Mitigation:** configurable coarse sampling and targeted dense re-sampling; optimize recall only after precision is safe.

### R4 — Heterogeneous codecs/FPS/resolution break concatenation

**Impact:** Render failures/non-deterministic timelines.

**Mitigation:** media probe + canonical normalization before concatenation; integration fixtures with mismatched input properties.

### R5 — Untrusted media/model output reaches privileged execution

**Impact:** command/path injection, SSRF, resource exhaustion, data leakage.

**Mitigation:** typed schemas, argument-array subprocess calls, isolated workspaces, SSRF controls where needed, resource caps, no model-controlled paths.

### R6 — Temporary media accumulates

**Impact:** privacy/storage/availability issue.

**Mitigation:** ephemeral workspaces, cleanup on terminal states, bounded TTL and operational visibility.

## Parallelization guidance

**Safe after Checkpoint A:**

- Task 4 media ingestion and Task 5 motion logic can proceed in parallel once shared identifiers/config conventions are fixed.
- Task 6 pure timeline contracts can proceed independently once the edit-plan schema is agreed.

**Must remain sequential:**

- Tasks 1 → 2 → 3 (feasibility chain).
- Task 7 waits for deterministic contracts from Tasks 4–6.
- Task 8 waits for a working renderer/core.
- Security/ship verification follows the assembled path, though security rules apply from the first code change.

## Explicitly not planned for MVP

- standalone frontend/dashboard;
- user accounts/auth/database;
- persistent media library/storage;
- second external AI provider;
- semantic storytelling/pacing;
- automatic scene reordering;
- captions/subtitles;
- voice/audio preservation;
- advanced transitions/color/VFX;
- AI-generated music or semantic/beat music matching.

Any addition above requires a spec change before implementation.
