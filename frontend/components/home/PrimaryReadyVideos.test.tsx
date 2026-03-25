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

const completedVideoB = {
  id: "660e8400-e29b-41d4-a716-446655440001",
  label: "Vidéo B",
  ingestion_status: "completed",
  ingestion_phase: null,
  ingestion_progress_percent: null,
  created_at: "2026-03-23T00:00:00Z",
};

/** Opens the dropdown for the first video in the list (player + search). */
async function expandFirstVideoPanel(
  user: ReturnType<typeof userEvent.setup>,
) {
  const toggle = await screen.findByRole("button", {
    name: /Afficher le lecteur pour/,
  });
  await user.click(toggle);
}

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
    delete window.__SEMANTICUT_SEARCH_TIMEOUT_MS__;
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("disables submit when query is empty", async () => {
    vi.stubGlobal("fetch", setupFetch());

    const user = userEvent.setup();
    render(<PrimaryReadyVideos />);

    await expandFirstVideoPanel(user);

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

    await expandFirstVideoPanel(user);

    await waitFor(() => {
      expect(screen.getByLabelText(fr.homeSearchQueryLabel)).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText(fr.homeSearchQueryLabel), "bonjour");
    await user.click(screen.getByRole("button", { name: fr.homeSearchSubmit }));

    await waitFor(() => {
      expect(screen.getByText(/contexte oral/)).toBeInTheDocument();
    });

    expect(screen.getByText(fr.homeSearchSeeking)).toBeInTheDocument();
    expect(screen.queryByText(/Lecture à partir de 00:12/)).not.toBeInTheDocument();
    const video = document.querySelector("video");
    expect(video).not.toBeNull();
    video?.dispatchEvent(new Event("seeked"));
    await waitFor(() => {
      expect(screen.getByText(/Lecture à partir de 00:12/)).toBeInTheDocument();
      expect(screen.queryByText(fr.homeSearchSeeking)).not.toBeInTheDocument();
    });
  });

  it("handles repeated searches without stale seek completion feedback", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async (url: string | URL, init?: RequestInit): Promise<Response> => {
          const u = typeof url === "string" ? url : url.toString();

          if (u.includes("/api/videos") && !u.includes("search")) {
            return {
              ok: true,
              status: 200,
              json: async () => [completedVideo],
            } as Response;
          }

          if (u.includes("/search")) {
            const body =
              typeof init?.body === "string"
                ? (JSON.parse(init.body) as { query?: string })
                : {};
            const q = body.query ?? "";

            if (q === "A") {
              return {
                ok: true,
                status: 200,
                json: async () => ({
                  start_ts: 1,
                  end_ts: 2,
                  text: "extrait A",
                  confidence: 0.9,
                  macro_context_text: "contexte oral A",
                  match_start_offset: 0,
                  match_end_offset: 8,
                  match_quality: "strong",
                }),
              } as Response;
            }

            return {
              ok: true,
              status: 200,
              json: async () => ({
                start_ts: 12,
                end_ts: 20,
                text: "extrait B",
                confidence: 0.85,
                macro_context_text: "contexte oral B",
                match_start_offset: 0,
                match_end_offset: 8,
                match_quality: "partial",
              }),
            } as Response;
          }

          throw new Error(`unexpected fetch: ${u}`);
        },
      ),
    );

    const user = userEvent.setup();
    render(<PrimaryReadyVideos />);

    await expandFirstVideoPanel(user);

    const input = await waitFor(() =>
      screen.getByLabelText(fr.homeSearchQueryLabel),
    );

    await user.type(input, "A");
    await user.click(screen.getByRole("button", { name: fr.homeSearchSubmit }));

    await waitFor(() => {
      expect(screen.getByText(/oral A/)).toBeInTheDocument();
    });
    expect(screen.getByText(fr.homeSearchSeeking)).toBeInTheDocument();

    await user.clear(input);
    await user.type(input, "B");
    await user.click(screen.getByRole("button", { name: fr.homeSearchSubmit }));

    await waitFor(() => {
      expect(screen.getByText(/oral B/)).toBeInTheDocument();
    });
    expect(screen.getByText(fr.homeSearchSeeking)).toBeInTheDocument();

    const video = document.querySelector("video");
    expect(video).not.toBeNull();
    // Give `SemanticVideoPlayer` effects time to attach the latest `seeked` handler.
    await new Promise((r) => setTimeout(r, 0));
    video?.dispatchEvent(new Event("seeked"));

    await waitFor(() => {
      expect(screen.getByText(/Lecture à partir de 00:12/)).toBeInTheDocument();
      expect(screen.queryByText(/Lecture à partir de 00:01/)).not.toBeInTheDocument();
      expect(screen.queryByText(fr.homeSearchSeeking)).not.toBeInTheDocument();
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

    await expandFirstVideoPanel(user);

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

    await expandFirstVideoPanel(user);

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

    await expandFirstVideoPanel(user);

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

  it("prevents duplicate submits while a search is in flight", async () => {
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
        if (u.includes("/search")) return pending;
        throw new Error(u);
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    const user = userEvent.setup();
    render(<PrimaryReadyVideos />);

    await expandFirstVideoPanel(user);

    await waitFor(() => {
      expect(screen.getByLabelText(fr.homeSearchQueryLabel)).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText(fr.homeSearchQueryLabel), "q");
    await user.click(screen.getByRole("button", { name: fr.homeSearchSubmit }));
    await user.click(screen.getByRole("button", { name: fr.homeSearchSubmitting }));

    expect(
      fetchMock.mock.calls.filter((call) =>
        String(call[0]).includes("/search"),
      ),
    ).toHaveLength(1);

    resolveSearch({
      ok: true,
      status: 200,
      json: async () => ({
        start_ts: 1,
        end_ts: 2,
        text: "ok",
        confidence: 1,
        macro_context_text: "ok",
        match_start_offset: 0,
        match_end_offset: 2,
        match_quality: "strong",
      }),
    } as Response);

    await waitFor(() => {
      expect(screen.getByText(fr.homeSearchSeeking)).toBeInTheDocument();
    });
    // Give `SemanticVideoPlayer` effects time to attach the latest `seeked` handler.
    await new Promise((r) => setTimeout(r, 0));

    const video = document.querySelector("video");
    expect(video).not.toBeNull();
    video?.dispatchEvent(new Event("loadedmetadata"));
    video?.dispatchEvent(new Event("seeked"));
    await waitFor(() => {
      expect(screen.getByText(/Lecture à partir de 00:01/)).toBeInTheDocument();
    });
  });

  it("shows timeout message and supports retry", async () => {
    window.__SEMANTICUT_SEARCH_TIMEOUT_MS__ = 5;

    let searchCalls = 0;
    const fetchMock = vi.fn(
      async (url: string | URL, init?: RequestInit): Promise<Response> => {
        const u = typeof url === "string" ? url : url.toString();
        if (u.includes("/api/videos") && !u.includes("search")) {
          return {
            ok: true,
            status: 200,
            json: async () => [completedVideo],
          } as Response;
        }
        if (u.includes("/search")) {
          searchCalls += 1;
          if (searchCalls === 1) {
            return new Promise<Response>((_, reject) => {
              init?.signal?.addEventListener("abort", () => {
                reject(new DOMException("Aborted", "AbortError"));
              });
            });
          }
          return {
            ok: true,
            status: 200,
            json: async () => ({
              start_ts: 8,
              end_ts: 9,
              text: "ok",
              confidence: 1,
              macro_context_text: "ok",
              match_start_offset: 0,
              match_end_offset: 2,
              match_quality: "strong",
            }),
          } as Response;
        }
        throw new Error(u);
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    const user = userEvent.setup();
    render(<PrimaryReadyVideos />);

    await expandFirstVideoPanel(user);

    await waitFor(() => {
      expect(screen.getByLabelText(fr.homeSearchQueryLabel)).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText(fr.homeSearchQueryLabel), "q");
    await user.click(screen.getByRole("button", { name: fr.homeSearchSubmit }));

    await waitFor(() => {
      expect(screen.getByText(fr.homeSearchTimeoutError)).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: fr.homeSearchRetry }),
      ).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: fr.homeSearchRetry }));

    const video = document.querySelector("video");
    expect(video).not.toBeNull();
    video?.dispatchEvent(new Event("seeked"));
    await waitFor(() => {
      expect(screen.getByText(/Lecture à partir de 00:08/)).toBeInTheDocument();
    });

  });

  it("renders trusted snippet without highlight when offsets are absent", async () => {
    vi.stubGlobal(
      "fetch",
      setupFetch(async () => ({
        ok: true,
        status: 200,
        json: async () => ({
          start_ts: 10,
          end_ts: 13,
          text: "extrait sans offset",
          confidence: 0.8,
          macro_context_text: "contexte sans offset",
          match_quality: "partial",
        }),
      })),
    );

    const user = userEvent.setup();
    render(<PrimaryReadyVideos />);
    await expandFirstVideoPanel(user);
    await waitFor(() => {
      expect(screen.getByLabelText(fr.homeSearchQueryLabel)).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText(fr.homeSearchQueryLabel), "bonjour");
    await user.click(screen.getByRole("button", { name: fr.homeSearchSubmit }));

    await waitFor(() => {
      expect(screen.getByText("contexte sans offset")).toBeInTheDocument();
    });
    expect(
      screen.queryByLabelText(fr.homeSearchPassageHighlightAria),
    ).not.toBeInTheDocument();
  });

  it("shows unplayable result error when start_ts is invalid", async () => {
    vi.stubGlobal(
      "fetch",
      setupFetch(async () => ({
        ok: true,
        status: 200,
        json: async () => ({
          start_ts: -1,
          end_ts: 3,
          text: "extrait trouvé",
          confidence: 0.85,
          macro_context_text: "contexte oral extrait trouvé fin",
          match_start_offset: 13,
          match_end_offset: 27,
          match_quality: "partial",
        }),
      })),
    );

    const user = userEvent.setup();
    render(<PrimaryReadyVideos />);
    await expandFirstVideoPanel(user);
    await waitFor(() => {
      expect(screen.getByLabelText(fr.homeSearchQueryLabel)).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText(fr.homeSearchQueryLabel), "bonjour");
    await user.click(screen.getByRole("button", { name: fr.homeSearchSubmit }));

    await waitFor(() => {
      expect(screen.getByText(fr.homeSearchUnplayableResult)).toBeInTheDocument();
    });
    expect(screen.queryByText(/Lecture à partir de/)).not.toBeInTheDocument();
  });

  it("keeps draft search query per video when switching dropdowns", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async (url: string | URL): Promise<Response> => {
          const u = typeof url === "string" ? url : url.toString();
          if (u.includes("/api/videos") && !u.includes("search")) {
            return {
              ok: true,
              status: 200,
              json: async () => [completedVideo, completedVideoB],
            } as Response;
          }
          throw new Error(`unexpected fetch: ${u}`);
        },
      ),
    );

    const user = userEvent.setup();
    render(<PrimaryReadyVideos />);

    const toggleA = await screen.findByRole("button", {
      name: `Afficher le lecteur pour "${completedVideo.label}"`,
    });
    await user.click(toggleA);
    const inputA = await screen.findByLabelText(fr.homeSearchQueryLabel);
    await user.type(inputA, "draft A");

    await user.click(
      screen.getByRole("button", {
        name: `Afficher le lecteur pour "${completedVideoB.label}"`,
      }),
    );
    const inputB = await screen.findByLabelText(fr.homeSearchQueryLabel);
    expect(inputB).toHaveValue("");
    await user.type(inputB, "draft B");

    await user.click(
      screen.getByRole("button", {
        name: `Afficher le lecteur pour "${completedVideo.label}"`,
      }),
    );
    const inputAAgain = await screen.findByLabelText(fr.homeSearchQueryLabel);
    expect(inputAAgain).toHaveValue("draft A");
  });

  it("renders empty state and no-video guidance when /api/videos returns []", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string | URL): Promise<Response> => {
        const u = typeof url === "string" ? url : url.toString();
        if (u.includes("/api/videos") && !u.includes("search")) {
          return {
            ok: true,
            status: 200,
            json: async () => [],
          } as Response;
        }
        throw new Error(`unexpected fetch: ${u}`);
      }),
    );

    render(<PrimaryReadyVideos />);

    await waitFor(() => {
      expect(screen.getByText(fr.homeReadyVideosEmpty)).toBeInTheDocument();
      expect(screen.getByText(fr.homeSearchNoVideoSelected)).toBeInTheDocument();
    });

    expect(screen.queryByLabelText(fr.homeSearchQueryLabel)).not.toBeInTheDocument();
    expect(document.querySelector("video")).toBeNull();
  });

  it("shows friendly service-unavailable message when /api/videos fetch throws", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      }),
    );

    render(<PrimaryReadyVideos />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(fr.homeReadyVideosError);
  });

  it("extracts error.message from structured non-OK /api/videos responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async (url: string | URL): Promise<Response> => {
          const u = typeof url === "string" ? url : url.toString();
          if (u.includes("/api/videos") && !u.includes("search")) {
            return {
              ok: false,
              status: 503,
              json: async () => ({
                error: { code: "UPSTREAM_DOWN", message: "service indisponible" },
              }),
            } as Response;
          }
          throw new Error(`unexpected fetch: ${u}`);
        },
      ),
    );

    render(<PrimaryReadyVideos />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("service indisponible");
    });
    expect(screen.queryByText("UPSTREAM_DOWN")).not.toBeInTheDocument();
  });

  it("falls back to generic error when non-OK /api/videos response lacks error.message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string | URL): Promise<Response> => {
        const u = typeof url === "string" ? url : url.toString();
        if (u.includes("/api/videos") && !u.includes("search")) {
          return {
            ok: false,
            status: 500,
            json: async () => ({
              error: { code: "UPSTREAM_DOWN" },
            }),
          } as Response;
        }
        throw new Error(`unexpected fetch: ${u}`);
      }),
    );

    render(<PrimaryReadyVideos />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(fr.homeReadyVideosError);
  });
});
