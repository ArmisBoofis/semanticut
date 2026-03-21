import { describe, expect, it } from "vitest";
import { frenchIngestionStatusLabel } from "./ingestionStatus";

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
