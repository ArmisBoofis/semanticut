import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AdminVideoList } from "./AdminVideoList";
import { fr } from "@/lib/strings";

describe("AdminVideoList", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("renders empty state when /api/videos returns []", async () => {
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

    render(<AdminVideoList />);

    const empty = await screen.findByText(fr.adminEmpty);
    expect(empty).toBeInTheDocument();
    expect(screen.queryByText(fr.adminColStatus)).not.toBeInTheDocument();
  });

  it("renders friendly load error when /api/videos fetch throws", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      }),
    );

    render(<AdminVideoList />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(fr.adminLoadError);
    expect(screen.queryByText(fr.adminEmpty)).not.toBeInTheDocument();
  });
});

