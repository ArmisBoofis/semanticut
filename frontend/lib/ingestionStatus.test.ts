import { describe, expect, it } from "vitest";
import {
  frenchIngestionFailedErrorSummary,
  frenchIngestionPhaseLabelForStatus,
  frenchIngestionStatusLabel,
} from "./ingestionStatus";

describe("frenchIngestionStatusLabel", () => {
  it("maps known API statuses to French", () => {
    expect(frenchIngestionStatusLabel("pending")).toBe("En attente");
    expect(frenchIngestionStatusLabel("running")).toBe("En cours");
    expect(frenchIngestionStatusLabel("completed")).toBe("Terminé");
    expect(frenchIngestionStatusLabel("failed")).toBe("Échec");
    expect(frenchIngestionStatusLabel("unknown")).toBe("Inconnu");
  });

  it("passes through unknown future values for transparency", () => {
    expect(frenchIngestionStatusLabel("queued")).toBe("queued");
  });
});

describe("frenchIngestionPhaseLabelForStatus", () => {
  it("returns queued/first-phase label for pending when phase is missing", () => {
    expect(frenchIngestionPhaseLabelForStatus("pending", null)).toBe(
      "Extraction audio",
    );
  });

  it("returns phase label for running/failed when phase is present", () => {
    expect(frenchIngestionPhaseLabelForStatus("running", "transcribing")).toBe(
      "Transcription",
    );
    expect(
      frenchIngestionPhaseLabelForStatus("failed", "transcribing"),
    ).toBe("Échec — Transcription");
  });

  it("returns a non-blank completed label when phase is missing", () => {
    expect(frenchIngestionPhaseLabelForStatus("completed", null)).toBe(
      "Terminé",
    );
  });
});

describe("frenchIngestionFailedErrorSummary", () => {
  it("maps known error codes to French, demo-operator-friendly summaries", () => {
    expect(frenchIngestionFailedErrorSummary("TRANSCRIPTION_FAILED")).toBe(
      "Transcription impossible. Vérifiez le fichier et réessayez.",
    );
    expect(frenchIngestionFailedErrorSummary("FILE_NOT_FOUND")).toBe(
      "Fichier vidéo introuvable. Vérifiez le chemin du fichier.",
    );
  });

  it("falls back for unknown or missing error codes", () => {
    expect(frenchIngestionFailedErrorSummary(null)).toBe(
      "Échec de l’ingestion. Consultez les logs serveur.",
    );
    expect(frenchIngestionFailedErrorSummary("SOME_UNKNOWN_CODE")).toBe(
      "Échec de l’ingestion. Consultez les logs serveur.",
    );
  });
});
