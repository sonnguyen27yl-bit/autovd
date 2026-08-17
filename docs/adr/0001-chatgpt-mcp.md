# ADR 0001: Use ChatGPT Web + MCP as the MVP interaction architecture

- **Status:** Accepted
- **Date:** 2026-08-18

## Context

AutoVD needs an AI component that can inspect temporal visual evidence from AI-generated clips and decide which regions are clearly broken. The confirmed product direction is that users should work entirely inside ChatGPT Web rather than opening a separate AutoVD frontend.

The project also needs deterministic, auditable video operations for cutting, speed changes, concatenation, audio removal, music insertion, and rendering.

Combining all responsibilities inside an unconstrained model agent would create avoidable correctness and security risk. Building a standalone web application for the MVP would add UI/auth/storage/product scope before the core analysis assumption is proven.

## Decision

Use this MVP architecture:

```text
ChatGPT Web
   ↓ MCP
AutoVD MCP server
   ↓
Deterministic media backend
```

ChatGPT is the AI reasoning/orchestration layer. It determines **what visual intervals are clear AI-generation failures** from timestamped temporal evidence.

The AutoVD backend owns **how media is processed**. It validates every model/tool input and performs media operations through constrained deterministic code.

The MVP will not build a standalone web frontend.

The MCP surface should be small and capability-oriented, initially centered on preparing analysis data, retrieving temporal analysis chunks, and rendering a validated structured edit plan.

The model must never be given authority to submit arbitrary FFmpeg/shell commands for execution.

## Alternatives considered

### 1. Standalone web application + direct model API

**Rejected for MVP.**

It provides more UI control but adds frontend, upload UX, auth/storage considerations, API orchestration, and deployment surface before the core question—whether temporal anomaly analysis works well enough—has been proven.

It may become appropriate after the MVP is validated.

### 2. Backend-only automatic computer-vision rules with no multimodal model

**Rejected as the primary anomaly detector.**

Deterministic rules are appropriate for motion scoring and media operations, but obvious AI-generation failures include semantic/visual inconsistencies such as anatomy deformation, identity changes, and object mutations that are not well captured by simple motion/frame-difference heuristics.

### 3. Let the model directly generate FFmpeg commands

**Rejected.**

This unnecessarily mixes reasoning with privileged execution, weakens validation boundaries, makes behavior harder to test, and increases command-injection/path-manipulation risk.

### 4. Add another external AI provider for video analysis

**Deferred.**

The confirmed MVP specifically uses ChatGPT Web. Adding a second AI provider increases cost, privacy/integration scope, and operational complexity. It remains an explicit ask-first decision if the ChatGPT/MCP temporal-analysis spike fails.

## Consequences

### Positive

- smallest user-facing product surface;
- directly matches the desired ChatGPT-native workflow;
- clear separation between AI judgment and media execution;
- deterministic editing logic can be unit/integration tested independently;
- avoids premature standalone UI work;
- allows the riskiest assumption to be tested first.

### Negative / risks

- product feasibility depends on how effectively ChatGPT can consume timestamped temporal visual evidence through the MCP workflow;
- file/tool capabilities and model-visible content are platform-dependent and must be verified against current official OpenAI documentation during implementation;
- long videos require chunking/adaptive sampling rather than one large context;
- the system needs careful validation because model output remains untrusted.

## Required follow-up

The first implementation spike must verify the end-to-end temporal analysis handoff:

```text
short AI clip
→ extract timestamped frame sequence
→ expose through MCP
→ ChatGPT identifies clear anomaly interval
→ compare with human label
```

If this does not achieve acceptable cut precision, the project must revisit the analysis architecture before expanding the renderer or infrastructure.
