import { describe, expect, it } from "vitest";
import { hasVerifiedNativeOnePageRender } from "./final-artifact-evidence";

describe("final artifact evidence", () => {
  it("rejects legacy passed evidence without native one-page proof", () => {
    expect(hasVerifiedNativeOnePageRender({ evidence_state: "passed" })).toBe(false);
  });

  it("accepts complete native one-page proof", () => {
    expect(hasVerifiedNativeOnePageRender({
      evidence_state: "passed",
      artifact_version_id: "cv-1",
      content_checksum: "b".repeat(64),
      page_count: 1,
      page_fit_status: "pass",
      artifact_checksum: "a".repeat(64),
      render_proof: {
        render_status: "pass",
        page_count: 1,
        page_fit_status: "pass",
        artifact_checksum: "a".repeat(64),
        content_sha256: "b".repeat(64),
        template_sha256: "c".repeat(64),
        render_config_fingerprint: "d".repeat(64),
        renderer_contract_version: "fitcv_native_render_v1",
      },
    })).toBe(true);
  });

  it("rejects passed evidence without PDF artifact checksum", () => {
    expect(hasVerifiedNativeOnePageRender({
      evidence_state: "passed",
      artifact_version_id: "cv-1",
      content_checksum: "b".repeat(64),
      page_count: 1,
      page_fit_status: "pass",
      render_proof: {
        render_status: "pass",
        page_count: 1,
        page_fit_status: "pass",
        content_sha256: "b".repeat(64),
        template_sha256: "c".repeat(64),
        render_config_fingerprint: "d".repeat(64),
        renderer_contract_version: "fitcv_native_render_v1",
      },
    })).toBe(false);
  });

  it("rejects proof bound to another version or content checksum", () => {
    const evidence = {
      evidence_state: "passed" as const,
      artifact_version_id: "cv-1",
      content_checksum: "b".repeat(64),
      render_proof: {
        render_status: "pass",
        page_count: 1,
        page_fit_status: "pass",
        artifact_checksum: "a".repeat(64),
        content_sha256: "b".repeat(64),
        template_sha256: "c".repeat(64),
        render_config_fingerprint: "d".repeat(64),
        renderer_contract_version: "fitcv_native_render_v1",
      },
    };
    expect(hasVerifiedNativeOnePageRender(evidence, { artifactVersionId: "cv-2" })).toBe(false);
    expect(hasVerifiedNativeOnePageRender({ ...evidence, content_checksum: "e".repeat(64) })).toBe(false);
  });
});
