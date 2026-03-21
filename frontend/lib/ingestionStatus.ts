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

export function frenchIngestionStatusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}
