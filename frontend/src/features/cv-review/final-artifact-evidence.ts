import { CvQualityWarningsEnvelope } from "./types";

export function hasVerifiedNativeOnePageRender(
  evidence: CvQualityWarningsEnvelope | null | undefined,
  identity?: { artifactVersionId?: string | null; contentChecksum?: string | null }
): boolean {
  if (!evidence || evidence.evidence_state !== "passed") return false;
  if (!evidence.artifact_version_id || !/^[0-9a-f]{64}$/i.test(String(evidence.content_checksum || ""))) return false;
  if (identity?.artifactVersionId && evidence.artifact_version_id !== identity.artifactVersionId) return false;
  if (identity?.contentChecksum && evidence.content_checksum !== identity.contentChecksum) return false;
  const proof = evidence.render_proof;
  const pageCount = evidence.page_count ?? proof?.page_count;
  const pageFitStatus = evidence.page_fit_status ?? proof?.page_fit_status;
  const artifactChecksum = evidence.artifact_checksum ?? proof?.artifact_checksum;
  const proofContentChecksum = String(proof?.content_sha256 || "").toLowerCase();
  return pageCount === 1
    && ["pass", "passed"].includes(String(pageFitStatus || "").toLowerCase())
    && String(proof?.render_status || "").toLowerCase() === "pass"
    && proofContentChecksum === String(evidence.content_checksum).toLowerCase()
    && /^[0-9a-f]{64}$/i.test(String(artifactChecksum || ""))
    && /^[0-9a-f]{64}$/i.test(String(proof?.template_sha256 || ""))
    && /^[0-9a-f]{64}$/i.test(String(proof?.render_config_fingerprint || ""))
    && Boolean(proof?.renderer_contract_version);
}
