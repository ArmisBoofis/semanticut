import React from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PrimaryReadyVideos } from "./PrimaryReadyVideos";
import { fr } from "@/lib/strings";

const completedVideo = {
  id: "550e8400-e29b-41d4-a716-446655440000",
  label: "Vidéo test",
  ingestion_status: "completed",
  ingestion_phase: null,
  ingestion_progress_percent: null,
  created_at: "2026-03-23T00:00:00Z",
};

function setupFetch(
  searchHandler?: (url: string) => Promise<{
    ok: boolean;
    status: number;
    json: () => Promise<unknown>;
  }>,
) {
  return vi.fn(
    async (url: string | URL): Promise<Response> => {
      const u = typeof url === "string" ? url : url.toString();
      if (u.includes("/api/videos") && !u.includes("search")) {
        return {
          ok: true,
          status: 200,
          json: async () => [completedVideo],
        } as Response;
      }
      if (u.includes("/search")) {
        if (searchHandler) return searchHandler(u) as Response;
        return {
          ok: true,
          status: 200,
          json: async () => ({
            start_ts: 12,
            end_ts: 20,
            text: "extrait trouvé",
            confidence: 0.85,
            macro_context_text: "contexte oral extrait trouvé fin",
            match_start_offset: 13,
            match_end_offset: 27,
            match_quality: "partial",
          }),
        } as Response;
      }
      throw new Error(`unexpected fetch: ${u}`);
    },
  );
}

describe("PrimaryReadyVideos", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("disables submit when query is empty", async () => {
    vi.stubGlobal("fetch", setupFetch());

    render(<PrimaryReadyVideos />);

    await waitFor(() => {
      expect(screen.getByLabelText(fr.homeSearchQueryLabel)).toBeInTheDocument();
    });

    expect(
      screen.getByRole("button", { name: fr.homeSearchSubmit }),
    ).toBeDisabled();
  });

  it("renders snippet and timestamp after successful search", async () => {
    vi.stubGlobal("fetch", setupFetch());

    const user = userEvent.setup();
    render(<PrimaryReadyVideos />);

    await waitFor(() => {
      expect(screen.getByLabelText(fr.homeSearchQueryLabel)).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText(fr.homeSearchQueryLabel), "bonjour");
    await user.click(screen.getByRole("button", { name: fr.homeSearchSubmit }));

    await waitFor(() => {
      expect(screen.getByText(/contexte oral/)).toBeInTheDocument();
      expect(
        screen.getByText(/Lecture à partir de 00:12/),
      ).toBeInTheDocument();
    });
  });

  it("shows no-match guidance for NO_MATCH", async () => {
    vi.stubGlobal(
      "fetch",
      setupFetch(async () => ({
        ok: false,
        status: 404,
        json: async () => ({
          error: { code: "NO_MATCH", message: "aucun" },
        }),
      })),
    );

    const user = userEvent.setup();
    render(<PrimaryReadyVideos />);

    await waitFor(() => {
      expect(screen.getByLabelText(fr.homeSearchQueryLabel)).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText(fr.homeSearchQueryLabel), "test");
    await user.click(screen.getByRole("button", { name: fr.homeSearchSubmit }));

    await waitFor(() => {
      expect(screen.getByText(fr.homeSearchNoMatch)).toBeInTheDocument();
    });
  });

  it("shows API error message for structured failure", async () => {
    vi.stubGlobal(
      "fetch",
      setupFetch(async () => ({
        ok: false,
        status: 502,
        json: async () => ({
          error: { code: "UPSTREAM_ERROR", message: "erreur test" },
        }),
      })),
    );

    const user = userEvent.setup();
    render(<PrimaryReadyVideos />);

    await waitFor(() => {
      expect(screen.getByLabelText(fr.homeSearchQueryLabel)).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText(fr.homeSearchQueryLabel), "x");
    await user.click(screen.getByRole("button", { name: fr.homeSearchSubmit }));

    await waitFor(() => {
      expect(screen.getByText("erreur test")).toBeInTheDocument();
    });
  });

  it("disables submit while a search request is in flight", async () => {
    let resolveSearch!: (v: Response) => void;
    const pending = new Promise<Response>((r) => {
      resolveSearch = r;
    });

    const fetchMock = vi.fn(
      async (url: string | URL): Promise<Response> => {
        const u = typeof url === "string" ? url : url.toString();
        if (u.includes("/api/videos") && !u.includes("search")) {
          return {
            ok: true,
            status: 200,
            json: async () => [completedVideo],
          } as Response;
        }
        if (u.includes("/search")) {
          return pending;
        }
        throw new Error(u);
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    const user = userEvent.setup();
    render(<PrimaryReadyVideos />);

    await waitFor(() => {
      expect(screen.getByLabelText(fr.homeSearchQueryLabel)).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText(fr.homeSearchQueryLabel), "q");
    await user.click(screen.getByRole("button", { name: fr.homeSearchSubmit }));

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: fr.homeSearchSubmitting }),
      ).toBeDisabled();
    });

    resolveSearch({
      ok: true,
      status: 200,
      json: async () => ({
        start_ts: 0,
        end_ts: 1,
        text: "done",
        confidence: 1,
        macro_context_text: "done",
        match_start_offset: 0,
        match_end_offset: 4,
        match_quality: "strong",
      }),
    } as Response);

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: fr.homeSearchSubmit }),
      ).not.toBeDisabled();
    });
  });
});
