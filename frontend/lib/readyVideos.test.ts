import { describe, expect, it } from "vitest";

import {
  filterCompletedVideos,
  isVideoListPayload,
  type VideoListItem,
} from "./readyVideos";

const video = (overrides: Partial<VideoListItem>): VideoListItem => ({
  id: "id-1",
  label: "Video 1",
  ingestion_status: "pending",
  ingestion_phase: null,
  ingestion_progress_percent: null,
  created_at: "2026-03-23T00:00:00Z",
  ...overrides,
});

describe("isVideoListPayload", () => {
  it("returns true for array of video items", () => {
    const data = [video({ id: "a" }), video({ id: "b", ingestion_status: "completed" })];
    expect(isVideoListPayload(data)).toBe(true);
  });

  it("returns false for invalid payload", () => {
    expect(isVideoListPayload(null)).toBe(false);
    expect(isVideoListPayload([{}])).toBe(false);
  });
});

describe("filterCompletedVideos", () => {
  it("returns only videos with completed status", () => {
    const data = [
      video({ id: "pending", ingestion_status: "pending" }),
      video({ id: "running", ingestion_status: "running" }),
      video({ id: "completed-1", ingestion_status: "completed" }),
      video({ id: "failed", ingestion_status: "failed" }),
      video({ id: "completed-2", ingestion_status: "completed" }),
    ];

    expect(filterCompletedVideos(data).map((item) => item.id)).toEqual([
      "completed-1",
      "completed-2",
    ]);
  });

  it("supports transition after refresh by reevaluating new payload", () => {
    const before = [
      video({ id: "v1", ingestion_status: "running" }),
      video({ id: "v2", ingestion_status: "pending" }),
    ];
    expect(filterCompletedVideos(before)).toEqual([]);

    const after = [
      video({ id: "v1", ingestion_status: "completed" }),
      video({ id: "v2", ingestion_status: "pending" }),
    ];
    expect(filterCompletedVideos(after).map((item) => item.id)).toEqual(["v1"]);
  });

  it("returns empty list when no completed videos exist", () => {
    const data = [
      video({ id: "pending", ingestion_status: "pending" }),
      video({ id: "running", ingestion_status: "running" }),
    ];
    expect(filterCompletedVideos(data)).toEqual([]);
  });
});
