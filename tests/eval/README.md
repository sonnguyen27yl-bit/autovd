# AutoVD anomaly evaluation

This directory documents the small human-labeled evaluation set used to decide whether the ChatGPT temporal-analysis approach is precise enough for full-auto cutting.

## Status

The deterministic scoring harness exists, but the real AI-generated labeled corpus and real ChatGPT/MCP results are still pending. No Gate A pass is implied by this directory.

The user explicitly approved deferring that real-model gate so deterministic backend work may continue. Before the MVP is declared complete, the fixed corpus must still be run through the real ChatGPT Developer Mode workflow.

## Human label shape

Each labeled interval records:

```json
{
  "clip_id": "clip_001",
  "start_ms": 1200,
  "end_ms": 1900,
  "should_cut": true,
  "category": "ANATOMY_DEFORMATION"
}
```

The corpus must contain both clear anomalies (`should_cut=true`) and clean/ambiguous footage (`should_cut=false`). Real evaluation media should not be committed if licensing/privacy does not permit it.

## Prediction shape used by the scorer

Only model-selected CUT intervals are passed to the precision scorer:

```json
{
  "clip_id": "clip_001",
  "start_ms": 1250,
  "end_ms": 1800
}
```

A predicted CUT is counted as correct when it overlaps at least one human `should_cut=true` interval in the same clip. Recall counts human anomaly intervals overlapped by at least one predicted CUT.

If there are zero predicted cuts, cut precision is reported as undefined (`None`) rather than as an artificial perfect score. The same rule applies to recall when the labeled set contains zero anomalies.

## Primary gate

Cut precision is the primary metric. The product spec currently uses an initial target of at least 90% on the small fixed labeled set; recall is secondary.
