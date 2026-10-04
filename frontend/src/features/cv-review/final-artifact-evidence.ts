import { CvQualityWarningsEnvelope } from "./types";

export function hasVerifiedNativeOnePageRender(
  evidence: CvQualityWarningsEnvelope | null | undefined
): boolean {
  if (!evidence || evidence.evidence_state !== "passed") return false;
  const proof = evidence.render_proof;
  const pageCount = evidence.page_count ?? proof?.page_count;
  const pageFitStatus = evidence.page_fit_status ?? proof?.page_fit_status;
  const renderAcceptance = evidence.render_acceptance ?? proof?.render_acceptance;
  const artifactChecksum = evidence.artifact_checksum ?? proof?.artifact_checksum;
  return pageCount === 1
    && ["pass", "passed"].includes(String(pageFitStatus || "").toLowerCase())
    && ["true", "pass", "passed", "accepted"].includes(String(renderAcceptance || "").toLowerCase())
    && /^[0-9a-f]{64}$/i.test(String(artifactChecksum || ""));
}
