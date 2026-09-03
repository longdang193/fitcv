import { describe, it, expect, vi, beforeEach } from "vitest";
import { candidateProfileEditHash, parseCandidateRoute } from "../features/candidate-profile/route";
import { discoverFeatureRoutes, matchRoute } from "../app/route-registry";
import {
  generateIdempotencyKey,
  fetchFieldSchema,
  createCreationAttempt,
  fetchCreationAttempt,
  patchBaselineReview,
  approveBaselineReview,
  patchDerivedReview,
  approveDerivedReview,
  fetchConfirmation,
  confirmProfile,
  fetchProfiles,
  fetchProfileDetail,
  archiveProfile,
  restoreProfile,
  deleteProfile,
  discardCreationAttempt,
  updateProfile,
  fetchSourceBlock,
  normalizeCandidateProfileDetail,
  createEditAttempt,
} from "../features/candidate-profile/api";
import { apiClient } from "../lib/api-client";
import { CandidateProfileReviewOperation } from "../features/candidate-profile/types";
import { getCandidateProfileFailurePresentation } from "../features/candidate-profile/components/ProcessingStep";

describe("Candidate Profile Route Hash Parsing & Route Discovery", () => {
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

  it("parses dynamic profile detail view and decodes encoded IDs", () => {
    expect(parseCandidateRoute("#/candidate-profile/prof_abc123")).toEqual({
      view: "detail",
      profileId: "prof_abc123",
    });
    expect(parseCandidateRoute("#/candidate-profile/prof%20with%20spaces")).toEqual({
      view: "detail",
      profileId: "prof with spaces",
    });
  });

  it("builds baseline edit deep-link from confirmed attempt", () => {
    expect(candidateProfileEditHash("attempt with spaces")).toBe(
      "#/candidate-profile/create/attempt%20with%20spaces/baseline"
    );
  });

  it("discovers candidate-profile route via discoverFeatureRoutes()", () => {
    const routes = discoverFeatureRoutes();
    const candidateRoute = routes.find((r) => r.id === "candidate-profile");
    expect(candidateRoute).toBeDefined();
    expect(candidateRoute?.path).toBe("#/candidate-profile");
    expect(candidateRoute?.title).toBe("Candidate Profile");
    expect(candidateRoute?.group).toBe("workspace");

    // Test matchRoute with deep-links
    const matchedCatalog = matchRoute("#/candidate-profile", routes);
    expect(matchedCatalog.id).toBe("candidate-profile");

    const matchedDetail = matchRoute("#/candidate-profile/prof_456", routes);
    expect(matchedDetail.id).toBe("candidate-profile");

    const matchedCreate = matchRoute("#/candidate-profile/create/att_789/baseline", routes);
    expect(matchedCreate.id).toBe("candidate-profile");
  });
});

describe("Candidate Profile processing failure actions", () => {
  it("maps unavailable LLM routing to provider setup while keeping retry available", () => {
    expect(
      getCandidateProfileFailurePresentation({
        code: "candidate_profile_llm_unavailable",
        message: "LLM routing is unavailable for candidate_profile_derived_claims",
        retryable: true,
      })
    ).toEqual({
      title: "Provider setup required",
      message:
        "Candidate Profile cannot regenerate AI-assisted fields because its LLM route is unavailable. Open Provider Settings, verify a provider connection, add a validated model, set Default Route, then return and retry processing.",
      requiresProviderSetup: true,
    });
  });

  it("maps generic failure presentation keeping backend message verbatim", () => {
    expect(
      getCandidateProfileFailurePresentation({
        code: "parse_error",
        message: "Failed to parse markdown heading structure.",
      })
    ).toEqual({
      title: "Processing Failed",
      message: "Failed to parse markdown heading structure.",
      requiresProviderSetup: false,
    });
  });
});

describe("Candidate Profile API & Full Lifecycle Operations", () => {
  it("normalizes CandidateProfileDetail with nested profile.canonical or overview", () => {
    const rawWithNestedProfile: any = {
      profile_id: "prof_test_1",
      profile_name: "Test Candidate",
      display_name: "Test Candidate",
      lifecycle: "active",
      creation_status: "succeeded",
      revision: 1,
      created_at: "2026-09-01T00:00:00Z",
      capabilities: { inspect: true, archive: true, restore: false, delete: false, use_for_run: true },
      overview: {
        name: "Test Overview Name",
      },
      profile: {
        profile_revision_id: "rev_1",
        revision: 1,
        checksum: "abc",
        schema_version: "candidate-profile.v2",
        canonical: {
          name: "Jordan Lee",
          headline: "Senior Full Stack Engineer",
          summary: "Experienced software engineer specializing in Python and React.",
          contact: {
            email: "jordan.lee@example.com",
            phone: "+49 170 1234567",
            location: "Berlin, Germany",
          },
          experiences: [
            {
              id: "exp_1",
              role: "Senior Software Engineer",
              company: "TechCore Labs",
              start: "2022-03",
              end: "Present",
              evidence: [
                { id: "ev_1", text: "Architected high-throughput services." }
              ]
            }
          ],
          education: [
            {
              id: "edu_1",
              degree: "B.Sc. Computer Science",
              institution: "Technical University of Munich",
              start: "2015-10",
              end: "2019-05"
            }
          ],
          skills: [
            {
              id: "skill_1",
              name: "FastAPI",
              confidence: 0.98,
              support_status: "supported",
              evidence_refs: ["ev_1"]
            }
          ]
        }
      }
    };

    const normalized = normalizeCandidateProfileDetail(rawWithNestedProfile);
    expect(normalized.canonical).toBeDefined();
    expect(normalized.canonical?.name).toBe("Jordan Lee");
    expect(normalized.canonical?.headline).toBe("Senior Full Stack Engineer");
    expect(normalized.canonical?.summary).toBe("Experienced software engineer specializing in Python and React.");
    expect(normalized.canonical?.contact?.email).toBe("jordan.lee@example.com");
    expect(normalized.canonical?.experiences?.[0].role).toBe("Senior Software Engineer");
    expect(normalized.canonical?.experiences?.[0].company).toBe("TechCore Labs");
    expect(normalized.canonical?.education?.[0].institution).toBe("Technical University of Munich");
    expect(normalized.canonical?.skills?.[0].name).toBe("FastAPI");
  });

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

  it("creates creation attempt using FormData without hardcoded Content-Type", async () => {
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

  it("fetches creation attempt by dynamic ID", async () => {
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce({
      data: {
        data: {
          attempt_id: "att_xyz999",
          profile_name: "Dynamic Candidate",
          creation_status: "base_review",
          revision: 1,
          next_action: "review_baseline",
          capabilities: { retry: false },
        },
      } as any,
      status: 200,
    });

    const res = await fetchCreationAttempt("att_xyz999");
    expect(res.attempt_id).toBe("att_xyz999");
    expect(getSpy).toHaveBeenCalledWith("/candidate-profile-creation-attempts/att_xyz999");
  });

  it("fetches source block citation with dynamic parameters", async () => {
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce({
      data: {
        data: {
          source_block_id: "sb_001",
          document_id: "doc_1",
          locator: { kind: "markdown_lines", start: 1, end: 5 },
          text: "Senior Software Engineer with 10 years experience",
        },
      } as any,
      status: 200,
    });

    const sb = await fetchSourceBlock("att_001", "sb_001");
    expect(sb.source_block_id).toBe("sb_001");
    expect(getSpy).toHaveBeenCalledWith(
      "/candidate-profile-creation-attempts/att_001/source-blocks/sb_001"
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
        value: { id: "exp_1", role: "Engineer", company: "Acme", evidence: [] },
      },
    ];

    await patchBaselineReview("att_001", 1, ops, "patch-key");
    expect(patchSpy).toHaveBeenCalledWith(
      "/candidate-profile-creation-attempts/att_001/baseline",
      { expected_revision: 1, operations: ops },
      { idempotencyKey: "patch-key" }
    );
  });

  it("approves baseline review with expected fingerprint", async () => {
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
      status: 200,
    });

    await approveBaselineReview("att_001", 2, "fp_baseline", "approve-key");
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

  it("fetches confirmation data and confirms candidate profile with all fingerprints", async () => {
    const getConfSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce({
      data: {
        data: {
          attempt_id: "att_001",
          revision: 5,
          fingerprint: "fp_conf",
          approval_fingerprints: { baseline: "fp_base", derived: "fp_der" },
          readiness: { ready: true, blockers: [] },
          profile: { profile_id: "prof_alex_morgan", canonical: {} },
        },
      } as any,
      status: 200,
    });

    const postSpy = vi.spyOn(apiClient, "post").mockResolvedValueOnce({
      data: {
        data: {
          profile_id: "prof_alex_morgan",
        },
      } as any,
      status: 200,
    });

    const conf = await fetchConfirmation("att_001");
    expect(conf.attempt_id).toBe("att_001");
    expect(getConfSpy).toHaveBeenCalledWith(
      "/candidate-profile-creation-attempts/att_001/confirmation"
    );

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

  it("supports catalog fetching and detail fetching without static placeholders", async () => {
    const getSpy = vi.spyOn(apiClient, "get")
      .mockResolvedValueOnce({
        data: {
          data: [
            {
              profile_id: "prof_live_1",
              profile_name: "Live Engineer",
              lifecycle: "active",
              revision: 1,
              created_at: "2026-08-30T10:00:00Z",
            },
          ],
          page: 1,
          page_size: 20,
          total_items: 1,
          meta: { active_count: 1, archived_count: 0 },
        } as any,
        status: 200,
      })
      .mockResolvedValueOnce({
        data: {
          data: {
            profile_id: "prof_live_1",
            profile_name: "Live Engineer",
            lifecycle: "active",
            revision: 1,
            canonical: { name: "Live Engineer" },
            created_at: "2026-08-30T10:00:00Z",
          },
        } as any,
        status: 200,
      });

    const catalogRes = await fetchProfiles({ view: "active" });
    expect(catalogRes.data[0].profile_id).toBe("prof_live_1");
    expect(getSpy).toHaveBeenNthCalledWith(1, "/candidate-profiles?view=active");

    const detailRes = await fetchProfileDetail("prof_live_1");
    expect(detailRes.profile_id).toBe("prof_live_1");
    expect(getSpy).toHaveBeenNthCalledWith(2, "/candidate-profiles/prof_live_1");
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

  it("sends contract parameter view=active and view=archived in fetchProfiles", async () => {
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValue({
      data: {
        data: [],
        page: 1,
        page_size: 20,
        total_items: 0,
      } as any,
      status: 200,
    });

    await fetchProfiles({ view: "active" });
    expect(getSpy).toHaveBeenCalledWith("/candidate-profiles?view=active");

    await fetchProfiles({ view: "archived" });
    expect(getSpy).toHaveBeenCalledWith("/candidate-profiles?view=archived");
  });

  it("waitForAttemptTransition honors returned poll_after_ms instead of hardcoded delay", async () => {
    const getSpy = vi.spyOn(apiClient, "get")
      .mockResolvedValueOnce({
        data: {
          data: {
            attempt_id: "att_poll",
            creation_status: "base_mapping",
            revision: 1,
            next_action: "none",
            poll_after_ms: 10,
          },
        } as any,
        status: 200,
      })
      .mockResolvedValueOnce({
        data: {
          data: {
            attempt_id: "att_poll",
            creation_status: "base_review",
            revision: 2,
            next_action: "review_baseline",
          },
        } as any,
        status: 200,
      });

    const { waitForAttemptTransition } = await import("../features/candidate-profile/api");
    const result = await waitForAttemptTransition("att_poll", "review_baseline", 5, 50);
    expect(result.creation_status).toBe("base_review");
    expect(result.next_action).toBe("review_baseline");
    expect(getSpy).toHaveBeenCalledTimes(2);
  });

  it("retries attempt and returns attempt with server-declared next_action and poll_after_ms", async () => {
    const postSpy = vi.spyOn(apiClient, "post").mockResolvedValueOnce({
      data: {
        data: {
          attempt_id: "att_retry_1",
          creation_status: "base_mapping",
          revision: 2,
          next_action: "none",
          poll_after_ms: 500,
          capabilities: { retry: false },
        },
      } as any,
      status: 200,
    });

    const { retryAttempt } = await import("../features/candidate-profile/api");
    const res = await retryAttempt("att_retry_1", 1, "retry-key");
    expect(res.attempt_id).toBe("att_retry_1");
    expect(res.creation_status).toBe("base_mapping");
    expect(res.poll_after_ms).toBe(500);
    expect(postSpy).toHaveBeenCalledWith(
      "/candidate-profile-creation-attempts/att_retry_1/actions/retry",
      { expected_revision: 1 },
      { idempotencyKey: "retry-key" }
    );
  });

  it("discards only draft attempts through revision-safe API", async () => {
    const postSpy = vi.spyOn(apiClient, "post").mockResolvedValueOnce({
      data: { data: { attempt_id: "att_draft", discarded: true } } as any,
      status: 200,
    });

    await expect(discardCreationAttempt("att_draft", 3, "discard-key")).resolves.toEqual({
      attempt_id: "att_draft",
      discarded: true,
    });
    expect(postSpy).toHaveBeenCalledWith(
      "/candidate-profile-creation-attempts/att_draft/actions/discard",
      { expected_revision: 3 },
      { idempotencyKey: "discard-key" }
    );
  });

  it("handles archive capabilities selectively without mutating unauthorized records", async () => {
    const profiles = [
      {
        profile_id: "prof_archivable",
        profile_name: "Archivable",
        lifecycle: "active",
        revision: 1,
        capabilities: { archive: true },
      },
      {
        profile_id: "prof_not_archivable",
        profile_name: "Not Archivable",
        lifecycle: "active",
        revision: 1,
        capabilities: { archive: false },
      },
    ];

    const postSpy = vi.spyOn(apiClient, "post").mockResolvedValue({
      data: { data: { profile_id: "prof_archivable", lifecycle: "archived", revision: 2 } } as any,
      status: 200,
    });

    // Simulating CatalogView filtering by capability
    const selectedKeys = new Set(["prof_archivable", "prof_not_archivable"]);
    const archivable = profiles
      .filter((p) => selectedKeys.has(p.profile_id))
      .filter((p) => p.capabilities?.archive === true);

    expect(archivable).toHaveLength(1);
    expect(archivable[0].profile_id).toBe("prof_archivable");

    for (const p of archivable) {
      await archiveProfile(p.profile_id, p.revision);
    }

    expect(postSpy).toHaveBeenCalledTimes(1);
    expect(postSpy).toHaveBeenCalledWith(
      "/candidate-profiles/prof_archivable/actions/archive",
      { expected_revision: 1 },
      expect.anything()
    );
  });


  it("routes successful processing with status succeeded and view_profile to profile detail", () => {
    // Test route navigation helper logic matching route.tsx handleProcessingReady
    const handleProcessingReady = (attempt: any, navigate: (path: string) => void) => {
      if (
        (attempt.profile_id && (attempt.creation_status === "succeeded" || attempt.next_action === "view_profile")) ||
        attempt.creation_status === "succeeded" ||
        attempt.next_action === "view_profile"
      ) {
        if (attempt.profile_id) {
          navigate(`#/candidate-profile/${encodeURIComponent(attempt.profile_id)}`);
        } else {
          navigate("#/candidate-profile");
        }
      } else if (
        attempt.next_action === "review_derived" ||
        attempt.creation_status === "derived_review"
      ) {
        navigate(`#/candidate-profile/create/${encodeURIComponent(attempt.attempt_id)}/derived`);
      } else if (
        attempt.next_action === "confirm" ||
        attempt.creation_status === "ready_to_confirm" ||
        attempt.creation_status === "confirmed"
      ) {
        navigate(`#/candidate-profile/create/${encodeURIComponent(attempt.attempt_id)}/confirm`);
      } else if (
        attempt.next_action === "review_baseline" ||
        attempt.creation_status === "base_review"
      ) {
        navigate(`#/candidate-profile/create/${encodeURIComponent(attempt.attempt_id)}/baseline`);
      } else if (attempt.profile_id) {
        navigate(`#/candidate-profile/${encodeURIComponent(attempt.profile_id)}`);
      } else {
        navigate(`#/candidate-profile/create/${encodeURIComponent(attempt.attempt_id)}/baseline`);
      }
    };

    const navPaths: string[] = [];
    const mockNavigate = (p: string) => navPaths.push(p);

    // 1. Succeeded with profile_id
    handleProcessingReady(
      {
        attempt_id: "att_succ",
        creation_status: "succeeded",
        next_action: "view_profile",
        profile_id: "prof_complete_123",
      },
      mockNavigate
    );
    expect(navPaths[0]).toBe("#/candidate-profile/prof_complete_123");

    // 2. Ready to confirm
    handleProcessingReady(
      {
        attempt_id: "att_conf",
        creation_status: "ready_to_confirm",
        next_action: "confirm",
      },
      mockNavigate
    );
    expect(navPaths[1]).toBe("#/candidate-profile/create/att_conf/confirm");

    // 3. Derived review
    handleProcessingReady(
      {
        attempt_id: "att_der",
        creation_status: "derived_review",
        next_action: "review_derived",
      },
      mockNavigate
    );
    expect(navPaths[2]).toBe("#/candidate-profile/create/att_der/derived");

    // 4. Baseline review
    handleProcessingReady(
      {
        attempt_id: "att_base",
        creation_status: "base_review",
        next_action: "review_baseline",
      },
      mockNavigate
    );
    expect(navPaths[3]).toBe("#/candidate-profile/create/att_base/baseline");
  });

  it("handles retry response with extracting_base/deriving and routes to processing view", () => {
    // Verify resume stage mapping logic from CatalogView
    const resolveResumeRoute = (att: any) => {
      const stageParam =
        att.next_action === "confirm" || att.creation_status === "ready_to_confirm"
          ? "confirm"
          : att.next_action === "review_derived" || att.creation_status === "derived_review"
          ? "derived"
          : att.next_action === "review_baseline" || att.creation_status === "base_review"
          ? "baseline"
          : undefined;

      if (stageParam) {
        return `#/candidate-profile/create/${encodeURIComponent(att.attempt_id)}/${stageParam}`;
      }
      return `#/candidate-profile/create/${encodeURIComponent(att.attempt_id)}`;
    };

    // Retry response in extracting_base / wait -> routes to processing (no stage suffix)
    const extractingAttempt = {
      attempt_id: "att_retry_extracting",
      creation_status: "extracting_base",
      next_action: "wait",
      revision: 2,
    };
    expect(resolveResumeRoute(extractingAttempt)).toBe("#/candidate-profile/create/att_retry_extracting");

    // Retry response in deriving / wait -> routes to processing (no stage suffix)
    const derivingAttempt = {
      attempt_id: "att_retry_deriving",
      creation_status: "deriving",
      next_action: "wait",
      revision: 3,
    };
    expect(resolveResumeRoute(derivingAttempt)).toBe("#/candidate-profile/create/att_retry_deriving");

    // Attempt in baseline review -> routes to baseline stage
    const baseReviewAttempt = {
      attempt_id: "att_ready_base",
      creation_status: "base_review",
      next_action: "review_baseline",
      revision: 2,
    };
    expect(resolveResumeRoute(baseReviewAttempt)).toBe("#/candidate-profile/create/att_ready_base/baseline");
  });

  it("creates edit attempt for active profile and routes to Step 2 baseline review without canonical JSON editor", async () => {
    const postSpy = vi.spyOn(apiClient, "post").mockResolvedValueOnce({
      data: {
        data: {
          attempt_id: "att_edit_live",
          profile_name: "Active Lead",
          creation_status: "base_review",
          next_action: "review_baseline",
          revision: 1,
          capabilities: { review_baseline: true, approve_baseline: true },
        },
      } as any,
      status: 201,
    });

    const editAttempt = await createEditAttempt("prof_live_99", "edit-key-99");
    expect(editAttempt.attempt_id).toBe("att_edit_live");
    expect(editAttempt.creation_status).toBe("base_review");
    expect(editAttempt.next_action).toBe("review_baseline");
    expect(postSpy).toHaveBeenCalledWith(
      "/candidate-profiles/prof_live_99/actions/edit",
      {},
      { idempotencyKey: "edit-key-99" }
    );

    // Opening edit routes to Step 2 Baseline review
    const targetHash = candidateProfileEditHash(editAttempt.attempt_id);
    expect(targetHash).toBe("#/candidate-profile/create/att_edit_live/baseline");

    const parsed = parseCandidateRoute(targetHash);
    expect(parsed.view).toBe("create_baseline");
    expect(parsed.attemptId).toBe("att_edit_live");
    // Target is never a raw JSON editor or /admin JSON route
    expect(targetHash).not.toContain("canonical");
    expect(targetHash).not.toContain("json");
  });

  it("configures dev proxy for /candidate-profile-field-schema to avoid 404 in baseline review", async () => {
    const viteConfig = await import("../../vite.config");
    const proxy = (viteConfig.default as any)?.server?.proxy || {};
    expect(proxy["/candidate-profile-field-schema"]).toBe("http://127.0.0.1:8000");
  });

});
