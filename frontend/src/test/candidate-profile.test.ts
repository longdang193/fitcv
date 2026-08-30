import { describe, it, expect, vi, beforeEach } from "vitest";
import { parseCandidateRoute } from "../features/candidate-profile/route";
import {
  generateIdempotencyKey,
  fetchFieldSchema,
  createCreationAttempt,
  patchBaselineReview,
  approveBaselineReview,
  patchDerivedReview,
  approveDerivedReview,
  confirmProfile,
  archiveProfile,
  restoreProfile,
  deleteProfile,
  updateProfile,
} from "../features/candidate-profile/api";
import { apiClient } from "../lib/api-client";
import { CandidateProfileReviewOperation } from "../features/candidate-profile/types";

describe("Candidate Profile Route Hash Parsing", () => {
  it("parses catalog view", () => {
    expect(parseCandidateRoute("#/candidate-profile")).toEqual({ view: "catalog" });
    expect(parseCandidateRoute("candidate-profile")).toEqual({ view: "catalog" });
    expect(parseCandidateRoute("")).toEqual({ view: "catalog" });
  });

  it("parses upload creation view", () => {
    expect(parseCandidateRoute("#/candidate-profile/create")).toEqual({ view: "create_upload" });
  });

  it("parses creation processing view", () => {
    expect(parseCandidateRoute("#/candidate-profile/create/att_123")).toEqual({
      view: "create_processing",
      attemptId: "att_123",
    });
  });

  it("parses baseline review stage", () => {
    expect(parseCandidateRoute("#/candidate-profile/create/att_123/baseline")).toEqual({
      view: "create_baseline",
      attemptId: "att_123",
    });
  });

  it("parses derived review stage", () => {
    expect(parseCandidateRoute("#/candidate-profile/create/att_123/derived")).toEqual({
      view: "create_derived",
      attemptId: "att_123",
    });
  });

  it("parses confirmation stage", () => {
    expect(parseCandidateRoute("#/candidate-profile/create/att_123/confirm")).toEqual({
      view: "create_confirm",
      attemptId: "att_123",
    });
  });

  it("parses detail view", () => {
    expect(parseCandidateRoute("#/candidate-profile/prof_abc123")).toEqual({
      view: "detail",
      profileId: "prof_abc123",
    });
  });
});

describe("Candidate Profile API & Operations", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("generates unique idempotency keys", () => {
    const key1 = generateIdempotencyKey();
    const key2 = generateIdempotencyKey();
    expect(key1).toBeTruthy();
    expect(key2).toBeTruthy();
    expect(key1).not.toEqual(key2);
  });

  it("fetches field schema and caches it", async () => {
    const mockSchema = {
      schema_version: "candidate-profile-fields.v1",
      schema_revision: 1,
      checksum: "abc12345",
      date_grammar: { format: "YYYY-MM", present_value: "Present", optional: true },
      evidence_kinds: ["work_experience", "education", "project"],
      sections: [],
    };

    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce({
      data: { data: mockSchema } as any,
      status: 200,
      etag: '"abc12345"',
    });

    const schema1 = await fetchFieldSchema(true);
    expect(schema1.schema_version).toBe("candidate-profile-fields.v1");
    expect(getSpy).toHaveBeenCalledTimes(1);

    const schema2 = await fetchFieldSchema();
    expect(schema2.checksum).toBe("abc12345");
    expect(getSpy).toHaveBeenCalledTimes(1);
  });

  it("creates creation attempt using FormData and Idempotency-Key", async () => {
    const postSpy = vi.spyOn(apiClient, "post").mockResolvedValueOnce({
      data: {
        data: {
          attempt_id: "att_001",
          profile_name: "Test Candidate",
          creation_status: "base_mapping",
          revision: 1,
          next_action: "review_baseline",
          capabilities: {},
        },
      } as any,
      status: 202,
    });

    const file = new File(["# Test Candidate\n"], "candidate.md", { type: "text/markdown" });
    const attempt = await createCreationAttempt("Test Candidate", file, "test-idem-key");

    expect(attempt.attempt_id).toBe("att_001");
    expect(postSpy).toHaveBeenCalledWith(
      "/candidate-profile-creation-attempts",
      expect.any(FormData),
      { idempotencyKey: "test-idem-key" }
    );
  });

  it("patches baseline review with ordered ID-addressed operations", async () => {
    const patchSpy = vi.spyOn(apiClient, "patch").mockResolvedValueOnce({
      data: {
        data: {
          attempt_id: "att_001",
          stage: "baseline",
          revision: 2,
          fingerprint: "fp_222",
          document: {},
          annotations: {},
          validation: { valid: true, errors: [] },
          capabilities: {},
        },
      } as any,
      status: 200,
    });

    const ops: CandidateProfileReviewOperation[] = [
      { operation: "replace", path: "/name", value: "Alex Morgan" },
      {
        operation: "add",
        path: "/experiences",
        value: { id: "exp_1", role: "Engineer", company: "Acme" },
      },
      { operation: "remove", path: "/projects/proj_old" },
    ];

    const res = await patchBaselineReview("att_001", 1, ops, "patch-key");
    expect(res.revision).toBe(2);
    expect(patchSpy).toHaveBeenCalledWith(
      "/candidate-profile-creation-attempts/att_001/baseline",
      {
        expected_revision: 1,
        operations: ops,
      },
      { idempotencyKey: "patch-key" }
    );
  });

  it("approves baseline review with expected revision and fingerprint", async () => {
    const postSpy = vi.spyOn(apiClient, "post").mockResolvedValueOnce({
      data: {
        data: {
          attempt_id: "att_001",
          profile_name: "Alex",
          creation_status: "derived_claims",
          revision: 3,
          next_action: "review_derived",
          capabilities: {},
        },
      } as any,
      status: 202,
    });

    const res = await approveBaselineReview("att_001", 2, "fp_baseline", "approve-key");
    expect(res.creation_status).toBe("derived_claims");
    expect(postSpy).toHaveBeenCalledWith(
      "/candidate-profile-creation-attempts/att_001/baseline/actions/approve",
      {
        expected_revision: 2,
        expected_fingerprint: "fp_baseline",
      },
      { idempotencyKey: "approve-key" }
    );
  });

  it("patches derived review and approves with baseline fingerprint", async () => {
    const patchSpy = vi.spyOn(apiClient, "patch").mockResolvedValueOnce({
      data: {
        data: {
          attempt_id: "att_001",
          stage: "derived",
          revision: 4,
          fingerprint: "fp_derived",
          document: {},
          annotations: {},
          validation: { valid: true, errors: [] },
          capabilities: {},
        },
      } as any,
      status: 200,
    });

    const approveSpy = vi.spyOn(apiClient, "post").mockResolvedValueOnce({
      data: {
        data: {
          attempt_id: "att_001",
          profile_name: "Alex",
          creation_status: "confirmed",
          revision: 5,
          next_action: "confirm",
          capabilities: {},
        },
      } as any,
      status: 200,
    });

    const ops: CandidateProfileReviewOperation[] = [
      { operation: "replace", path: "/skills/skill_1/confidence", value: 0.95 },
      { operation: "replace", path: "/skills/skill_1/evidence_refs", value: ["ev_exp_1_0"] },
    ];

    await patchDerivedReview("att_001", 3, ops, "patch-derived-key");
    expect(patchSpy).toHaveBeenCalledWith(
      "/candidate-profile-creation-attempts/att_001/derived",
      { expected_revision: 3, operations: ops },
      { idempotencyKey: "patch-derived-key" }
    );

    await approveDerivedReview("att_001", 4, "fp_derived", "fp_approved_baseline", "approve-derived-key");
    expect(approveSpy).toHaveBeenCalledWith(
      "/candidate-profile-creation-attempts/att_001/derived/actions/approve",
      {
        expected_revision: 4,
        expected_fingerprint: "fp_derived",
        expected_baseline_fingerprint: "fp_approved_baseline",
      },
      { idempotencyKey: "approve-derived-key" }
    );
  });

  it("confirms candidate profile with all fingerprints", async () => {
    const postSpy = vi.spyOn(apiClient, "post").mockResolvedValueOnce({
      data: {
        data: {
          profile_id: "prof_alex_morgan",
        },
      } as any,
      status: 200,
    });

    const result = await confirmProfile(
      "att_001",
      5,
      "fp_base",
      "fp_der",
      "fp_conf",
      "confirm-key"
    );

    expect(result.profile_id).toBe("prof_alex_morgan");
    expect(postSpy).toHaveBeenCalledWith(
      "/candidate-profile-creation-attempts/att_001/actions/confirm",
      {
        expected_revision: 5,
        expected_baseline_fingerprint: "fp_base",
        expected_derived_fingerprint: "fp_der",
        expected_confirmation_fingerprint: "fp_conf",
      },
      { idempotencyKey: "confirm-key" }
    );
  });

  it("supports lifecycle transitions: archive, restore, delete, update", async () => {
    const postSpy = vi
      .spyOn(apiClient, "post")
      .mockResolvedValueOnce({
        data: {
          data: {
            profile_id: "prof_1",
            lifecycle: "archived",
            revision: 2,
          },
        } as any,
        status: 200,
      })
      .mockResolvedValueOnce({
        data: {
          data: {
            profile_id: "prof_1",
            lifecycle: "active",
            revision: 3,
          },
        } as any,
        status: 200,
      })
      .mockResolvedValueOnce({
        data: {
          data: {
            profile_id: "prof_1",
            deleted: true,
          },
        } as any,
        status: 200,
      });

    const putSpy = vi.spyOn(apiClient, "put").mockResolvedValueOnce({
      data: {
        data: {
          profile_id: "prof_1",
          profile_name: "Updated Name",
          revision: 4,
        },
      } as any,
      status: 200,
    });

    await archiveProfile("prof_1", 1, "arch-key");
    expect(postSpy).toHaveBeenNthCalledWith(
      1,
      "/candidate-profiles/prof_1/actions/archive",
      { expected_revision: 1 },
      { idempotencyKey: "arch-key" }
    );

    await restoreProfile("prof_1", 2, "rest-key");
    expect(postSpy).toHaveBeenNthCalledWith(
      2,
      "/candidate-profiles/prof_1/actions/restore",
      { expected_revision: 2 },
      { idempotencyKey: "rest-key" }
    );

    await deleteProfile("prof_1", 3, "del-key");
    expect(postSpy).toHaveBeenNthCalledWith(
      3,
      "/candidate-profiles/prof_1/actions/delete",
      { expected_revision: 3 },
      { idempotencyKey: "del-key" }
    );

    await updateProfile("prof_1", 3, "Updated Name", { schema_version: "candidate-profile.v2" }, "update-key");
    expect(putSpy).toHaveBeenCalledWith(
      "/candidate-profiles/prof_1",
      {
        expected_revision: 3,
        profile_name: "Updated Name",
        canonical: { schema_version: "candidate-profile.v2" },
      },
      { idempotencyKey: "update-key" }
    );
  });
});
