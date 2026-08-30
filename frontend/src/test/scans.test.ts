import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  fetchScans,
  createScan,
  verifyTrackedCompany,
  createTrackedCompany,
  cancelScan,
  runScanAgain,
  archiveScans,
  unarchiveScans,
  previewDeleteScans,
  deleteScans,
  fetchScanEvents,
  fetchScanJobs,
  fetchScanOutputJson,
  buildRunSourcesHash,
} from "../features/scans/api";
import { apiClient } from "../lib/api-client";
import { discoverFeatureRoutes, matchRoute } from "../app/route-registry";

describe("scans feature route and api slice", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("registers and matches scans feature route", () => {
    const routes = discoverFeatureRoutes();
    const scanRoute = routes.find((r) => r.id === "scans");
    expect(scanRoute).toBeDefined();
    expect(scanRoute?.path).toBe("#/scans");
    expect(scanRoute?.group).toBe("workspace");

    const matched = matchRoute("#/scans?lifecycle=archived", routes);
    expect(matched.id).toBe("scans");
  });

  it("fetches scans collection with query parameters", async () => {
    const mockResponse = {
      data: {
        data: [
          {
            scan_id: "scan-1",
            scan_name: "Test Scan",
            execution_status: "succeeded",
            lifecycle: "active",
            row_revision: 1,
            created_at: "2026-08-30T12:00:00Z",
            company_count: 1,
            capabilities: {
              inspect: true,
              cancel: false,
              run_again: true,
              download: true,
              archive: true,
              unarchive: false,
              delete: false,
              use_for_run: true,
            },
            warnings: [],
          },
        ],
        page: 1,
        page_size: 20,
        total_items: 1,
        meta: { active_count: 1, archived_count: 0 },
      },
      status: 200,
    };

    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockResponse as any);

    const result = await fetchScans({
      lifecycle: "active",
      page: 1,
      page_size: 20,
    });

    expect(getSpy).toHaveBeenCalledWith("/scans?lifecycle=active&page=1&page_size=20");
    expect(result.data.length).toBe(1);
    expect(result.data[0].scan_id).toBe("scan-1");
  });

  it("verifies and creates tracked company", async () => {
    const verifySpy = vi.spyOn(apiClient, "post").mockResolvedValueOnce({
      data: {
        data: {
          company_name: "Acme",
          careers_url: "https://careers.acme.com",
          provider_id: "greenhouse",
          provider_label: "Greenhouse",
        },
      },
      status: 200,
    } as any);

    const verified = await verifyTrackedCompany({
      company_name: "Acme",
      careers_url: "https://careers.acme.com",
    });
    expect(verifySpy).toHaveBeenCalledWith("/tracked-companies/actions/verify", {
      company_name: "Acme",
      careers_url: "https://careers.acme.com",
    });
    expect(verified.provider_id).toBe("greenhouse");

    const createSpy = vi.spyOn(apiClient, "post").mockResolvedValueOnce({
      data: {
        data: {
          company_id: "comp-1",
          company_name: "Acme",
          careers_url: "https://careers.acme.com",
          provider_id: "greenhouse",
          row_revision: 1,
          created_at: "2026-08-30T12:00:00Z",
          updated_at: "2026-08-30T12:00:00Z",
        },
      },
      status: 201,
    } as any);

    const created = await createTrackedCompany(
      { company_name: "Acme", careers_url: "https://careers.acme.com" },
      "idemp-1"
    );
    expect(createSpy).toHaveBeenCalledWith(
      "/tracked-companies",
      { company_name: "Acme", careers_url: "https://careers.acme.com" },
      { idempotencyKey: "idemp-1" }
    );
    expect(created.company_id).toBe("comp-1");
  });

  it("supports scan lifecycle actions: create, cancel, run-again, archive, unarchive, delete preview & delete", async () => {
    const postSpy = vi.spyOn(apiClient, "post");

    // Create Scan
    postSpy.mockResolvedValueOnce({
      data: { data: { scan_id: "scan-created", execution_status: "queued" } },
      status: 201,
    } as any);
    const createdScan = await createScan(
      { company_ids: ["comp-1"], published_window: "past_24_hours" },
      "idemp-scan-1"
    );
    expect(postSpy).toHaveBeenCalledWith(
      "/scans",
      { company_ids: ["comp-1"], published_window: "past_24_hours" },
      { idempotencyKey: "idemp-scan-1" }
    );
    expect(createdScan.scan_id).toBe("scan-created");

    // Cancel Scan
    postSpy.mockResolvedValueOnce({
      data: { data: { scan_id: "scan-created", execution_status: "cancelling" } },
      status: 202,
    } as any);
    const cancelled = await cancelScan("scan-created", 1, "idemp-cancel");
    expect(postSpy).toHaveBeenCalledWith(
      "/scans/scan-created/actions/cancel",
      { scan_id: "scan-created", expected_revision: 1 },
      { idempotencyKey: "idemp-cancel" }
    );
    expect(cancelled.execution_status).toBe("cancelling");

    // Run Again
    postSpy.mockResolvedValueOnce({
      data: { data: { scan_id: "scan-rerun", execution_status: "queued" } },
      status: 201,
    } as any);
    const rerun = await runScanAgain("scan-created", "Rerun 1", 2, "idemp-rerun");
    expect(postSpy).toHaveBeenCalledWith(
      "/scans/scan-created/actions/run-again",
      { scan_id: "scan-created", scan_name: "Rerun 1", expected_revision: 2 },
      { idempotencyKey: "idemp-rerun" }
    );
    expect(rerun.scan_id).toBe("scan-rerun");

    // Archive
    postSpy.mockResolvedValueOnce({ data: { updated: 1 }, status: 200 } as any);
    await archiveScans([{ scan_id: "scan-1", expected_revision: 1 }], "idemp-archive");
    expect(postSpy).toHaveBeenCalledWith(
      "/scans/actions/archive",
      { items: [{ scan_id: "scan-1", expected_revision: 1 }] },
      { idempotencyKey: "idemp-archive" }
    );

    // Unarchive
    postSpy.mockResolvedValueOnce({ data: { updated: 1 }, status: 200 } as any);
    await unarchiveScans([{ scan_id: "scan-1", expected_revision: 2 }], "idemp-unarchive");
    expect(postSpy).toHaveBeenCalledWith(
      "/scans/actions/unarchive",
      { items: [{ scan_id: "scan-1", expected_revision: 2 }] },
      { idempotencyKey: "idemp-unarchive" }
    );

    // Delete Preview
    postSpy.mockResolvedValueOnce({
      data: {
        data: {
          eligible_scan_ids: ["scan-1"],
          referenced_scan_ids: [],
          invalid_scan_ids: [],
          missing_scan_ids: [],
          preview_revision: "prev-rev-1",
          row_revisions: { "scan-1": 2 },
        },
      },
      status: 200,
    } as any);
    const preview = await previewDeleteScans(["scan-1"]);
    expect(postSpy).toHaveBeenCalledWith("/scans/actions/delete-archived/preview", {
      scan_ids: ["scan-1"],
    });
    expect(preview.preview_revision).toBe("prev-rev-1");

    // Delete Commit
    postSpy.mockResolvedValueOnce({ data: { deleted_count: 1 }, status: 200 } as any);
    await deleteScans(["scan-1"], "prev-rev-1", "idemp-delete");
    expect(postSpy).toHaveBeenCalledWith(
      "/scans/actions/delete-archived",
      { scan_ids: ["scan-1"], preview_revision: "prev-rev-1" },
      { idempotencyKey: "idemp-delete" }
    );
  });

  it("fetches scan events and output jobs", async () => {
    const getSpy = vi.spyOn(apiClient, "get");

    getSpy.mockResolvedValueOnce({
      data: {
        data: {
          events: [
            {
              event_id: "evt-1",
              event_seq: 1,
              process_type: "scan",
              process_id: "scan-1",
              stage_name: "acquire",
              event_type: "started",
              event_level: "info",
              payload: { message: "Acquiring jobs" },
              recorded_at: "2026-08-30T12:00:01Z",
            },
          ],
          has_more: false,
        },
      },
      status: 200,
    } as any);

    const eventsPage = await fetchScanEvents("scan-1");
    expect(getSpy).toHaveBeenCalledWith("/scans/scan-1/events?limit=200");
    expect(eventsPage.events.length).toBe(1);

    getSpy.mockResolvedValueOnce({
      data: {
        data: [{ title: "Frontend Engineer", company: "Acme" }],
        page: 1,
        page_size: 20,
        total_items: 1,
      },
      status: 200,
    } as any);

    const jobsRes = await fetchScanJobs("scan-1", 1, 20);
    expect(getSpy).toHaveBeenCalledWith("/scans/scan-1/jobs?page=1&page_size=20");
    expect(jobsRes.data.length).toBe(1);
    expect(jobsRes.data[0].title).toBe("Frontend Engineer");
  });

  it("preserves output bytes for preview and encodes Run source handoff", async () => {
    const previewSpy = vi.spyOn(apiClient, "previewText").mockResolvedValueOnce('[{"title":"Exact"}]');

    await expect(fetchScanOutputJson("scan/1")).resolves.toBe('[{"title":"Exact"}]');
    expect(previewSpy).toHaveBeenCalledWith("/scans/scan%2F1/output");
    expect(buildRunSourcesHash(["scan-1", "scan/2"])).toBe("#/runs?scan_ids=scan-1&scan_ids=scan%2F2");
  });
});
