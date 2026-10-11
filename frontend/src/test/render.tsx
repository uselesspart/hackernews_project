import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { vi } from "vitest";

import { futureFlags, routes } from "../router";
import meta from "./fixtures/meta.json";
import fossil from "./fixtures/profile-fossil.json";
import rust from "./fixtures/profile-rust.json";
import storiesRust from "./fixtures/stories-rust.json";
import suggestEmpty from "./fixtures/suggest-empty.json";
import suggestGolang from "./fixtures/suggest-golang.json";
import techs from "./fixtures/techs.json";

type Handler = (url: URL) => { status?: number; body: unknown } | undefined;

/** Ответы по умолчанию — реальные ответы API на базе run_small (src/test/fixtures). */
export const defaultApi: Handler = (url) => {
  const p = url.pathname;
  if (p === "/api/meta") return { body: meta };
  if (p === "/api/techs") return { body: techs };
  if (p === "/api/techs/suggest") {
    const q = url.searchParams.get("q") ?? "";
    if (q === "") return { body: suggestEmpty };
    if ("golang".startsWith(q)) return { body: suggestGolang };
    return { body: [] };
  }
  if (p === "/api/techs/rust") return { body: rust };
  if (p === "/api/techs/fossil") return { body: fossil };
  if (p === "/api/techs/rust/stories") return { body: storiesRust };
  if (p.startsWith("/api/techs/") && !p.includes("/", "/api/techs/".length)) {
    return { status: 404, body: { detail: "Технология не отслеживается" } };
  }
  return undefined;
};

export function mockApi(...handlers: Handler[]) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), "http://localhost");
    for (const h of [...handlers, defaultApi]) {
      const r = h(url);
      if (r) {
        return new Response(JSON.stringify(r.body), {
          status: r.status ?? 200,
          headers: { "Content-Type": "application/json" },
        });
      }
    }
    return new Response("{}", { status: 500 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export function renderRoute(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(routes, { initialEntries: [path], future: futureFlags });
  const result = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} future={{ v7_startTransition: true }} />
    </QueryClientProvider>,
  );
  return { ...result, router };
}
