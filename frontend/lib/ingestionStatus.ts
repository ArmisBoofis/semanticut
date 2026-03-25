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

/**
 * Phase label for the admin list, with "truthful determinism" for states where
 * `ingestion_phase` can be null (e.g. pending/completed).
 */
export function frenchIngestionPhaseLabelForStatus(
  ingestion_status: string,
  phase: string | null,
): string {
  if (ingestion_status === "pending") {
    return PHASE_LABELS.extracting_audio;
  }
  if (ingestion_status === "completed") {
    // Backend sets `phase=None` on completion; keep the UI unambiguous.
    return "Terminé";
  }
  if (ingestion_status === "failed") {
    const phaseLabel = frenchIngestionPhaseLabel(phase);
    if (phaseLabel === "—") return STATUS_LABELS.failed;
    return `${STATUS_LABELS.failed} — ${phaseLabel}`;
  }
  return frenchIngestionPhaseLabel(phase);
}

const ERROR_CODE_SUMMARIES: Record<string, string> = {
  TRANSCRIPTION_FAILED:
    "Transcription impossible. Vérifiez le fichier et réessayez.",
  FILE_NOT_FOUND: "Fichier vidéo introuvable. Vérifiez le chemin du fichier.",
};

const ERROR_CODE_FALLBACK = "Échec de l’ingestion. Consultez les logs serveur.";

/**
 * Demo-operator-friendly French error summary.
 * Never rely on `error_message` (may be non-French/too technical); use `error_code` only.
 */
export function frenchIngestionFailedErrorSummary(
  error_code: string | null | undefined,
): string {
  if (!error_code) return ERROR_CODE_FALLBACK;
  return ERROR_CODE_SUMMARIES[error_code] ?? ERROR_CODE_FALLBACK;
}
