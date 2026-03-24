import { describe, expect, it } from "vitest";

import {
  buildSearchRequestBody,
  extractApiErrorMessage,
  formatSecondsToClock,
  isNoMatchError,
  parseSearchSuccess,
  splitMacroHighlight,
} from "./videoSearch";

describe("buildSearchRequestBody", () => {
  it("trims query", () => {
    expect(buildSearchRequestBody("  hello  ")).toEqual({ query: "hello" });
  });
});

describe("parseSearchSuccess", () => {
  it("parses valid payload", () => {
    expect(
      parseSearchSuccess({
        start_ts: 12.5,
        end_ts: 20,
        text: "bonjour",
        confidence: 0.87,
        macro_context_text: "un deux bonjour trois",
        match_start_offset: 8,
        match_end_offset: 15,
        match_quality: "strong",
      }),
    ).toEqual({
      start_ts: 12.5,
      end_ts: 20,
      text: "bonjour",
      confidence: 0.87,
      macro_context_text: "un deux bonjour trois",
      match_start_offset: 8,
      match_end_offset: 15,
      match_quality: "strong",
    });
  });

  it("returns null for malformed payload", () => {
    expect(parseSearchSuccess({})).toBe(null);
    expect(parseSearchSuccess(null)).toBe(null);
    expect(
      parseSearchSuccess({
        start_ts: "x",
        end_ts: 1,
        text: "a",
        confidence: 1,
      }),
    ).toBe(null);
  });

  it("accepts payload without macro context and offsets", () => {
    expect(
      parseSearchSuccess({
        start_ts: 12,
        end_ts: 20,
        text: "bonjour",
        confidence: 0.87,
        match_quality: "partial",
      }),
    ).toEqual({
      start_ts: 12,
      end_ts: 20,
      text: "bonjour",
      confidence: 0.87,
      macro_context_text: null,
      match_start_offset: null,
      match_end_offset: null,
      match_quality: "partial",
    });
  });
});

describe("extractApiErrorMessage", () => {
  it("reads nested message", () => {
    expect(
      extractApiErrorMessage(
        { error: { code: "X", message: "msg" } },
        "fallback",
      ),
    ).toBe("msg");
  });

  it("uses fallback when missing", () => {
    expect(extractApiErrorMessage({}, "fallback")).toBe("fallback");
  });

  it("uses fallback when message looks like internal code", () => {
    expect(
      extractApiErrorMessage(
        { error: { code: "UPSTREAM_ERROR", message: "UPSTREAM_TIMEOUT" } },
        "fallback",
      ),
    ).toBe("fallback");
  });
});

describe("isNoMatchError", () => {
  it("detects NO_MATCH", () => {
    expect(isNoMatchError({ error: { code: "NO_MATCH" } })).toBe(true);
    expect(isNoMatchError({ error: { code: "NOT_FOUND" } })).toBe(false);
  });
});

describe("formatSecondsToClock", () => {
  it("formats MM:SS", () => {
    expect(formatSecondsToClock(65)).toBe("01:05");
    expect(formatSecondsToClock(0)).toBe("00:00");
  });
});

describe("splitMacroHighlight", () => {
  it("splits using offsets and clamps to length", () => {
    expect(
      splitMacroHighlight("aa bb cc", 3, 5),
    ).toEqual({ before: "aa ", mid: "bb", after: " cc" });
    expect(splitMacroHighlight("x", 0, 99)).toEqual({
      before: "",
      mid: "x",
      after: "",
    });
  });
});
