/**
 * Maps API ingestion status values to French labels for display.
 */
const STATUS_LABELS: Record<string, string> = {
  pending: "En attente",
  running: "En cours",
  completed: "Terminé",
  failed: "Échec",
  unknown: "Inconnu",
};

/** API phase codes from `ingestion_jobs.phase` (Story 2.4). */
const PHASE_LABELS: Record<string, string> = {
  extracting_audio: "Extraction audio",
  transcribing: "Transcription",
  chunking: "Découpage",
  embedding: "Embeddings",
  indexing: "Indexation",
};

export function frenchIngestionStatusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

export function frenchIngestionPhaseLabel(phase: string | null): string {
  if (phase === null || phase === "") {
    return "—";
  }
  return PHASE_LABELS[phase] ?? phase;
}
