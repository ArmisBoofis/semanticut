export type VideoListItem = {
  id: string;
  label: string;
  ingestion_status: string;
  ingestion_phase: string | null;
  ingestion_progress_percent: number | null;
  created_at: string;
};

export function isVideoListPayload(data: unknown): data is VideoListItem[] {
  if (!Array.isArray(data)) return false;
  return data.every(
    (row) =>
      row !== null &&
      typeof row === "object" &&
      "id" in row &&
      "label" in row &&
      "ingestion_status" in row &&
      "created_at" in row,
  );
}

export function filterCompletedVideos(items: VideoListItem[]): VideoListItem[] {
  return items.filter((item) => item.ingestion_status === "completed");
}
