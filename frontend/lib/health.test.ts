import { describe, expect, it } from "vitest";
import { isBackendHealthyPayload } from "./health";

describe("isBackendHealthyPayload", () => {
  it("returns true for ok health response", () => {
    expect(isBackendHealthyPayload({ status: "ok", database: "ok" })).toBe(
      true,
    );
  });

  it("returns false for 503-style body", () => {
    expect(
      isBackendHealthyPayload({ status: "unavailable", database: "error" }),
    ).toBe(false);
  });

  it("returns false for invalid input", () => {
    expect(isBackendHealthyPayload(null)).toBe(false);
    expect(isBackendHealthyPayload("x")).toBe(false);
  });
});
