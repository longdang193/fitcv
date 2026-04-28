# Project Charter

FitCV LangGraph exists to upgrade the existing FitCV end-to-end pipeline with selective agentic AI while preserving the original pipeline's semantics, stage boundaries, and deterministic acceptance discipline.

The project is anchored to the original FitCV runtime and control flow, not to a parallel replay-first product story.

The upgrade promise is:

- keep the original FitCV pipeline meaning authoritative
- preserve stage order, checkpoint meaning, and operator-facing run truth
- introduce agentic behavior only in bounded seams where it improves quality or efficiency
- keep deterministic validation and acceptance as the final gate
- make new agentic outputs explainable through stage-owned artifacts and clear hold, accept, and reject reasons

The project should feel like FitCV with stronger late-stage intelligence, not like a separate system that happens to process the same inputs.
