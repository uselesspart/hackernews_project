import { createBrowserRouter, type RouteObject } from "react-router-dom";

import { Layout } from "./components/Layout";
import { HomePage } from "./pages/HomePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { TechPage } from "./pages/TechPage";

export const routes: RouteObject[] = [
  {
    element: <Layout />,
    children: [
      { path: "/", element: <HomePage /> },
      { path: "/tech/:key", element: <TechPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];

// Поведение v7 включено заранее: переход на v7 не изменит работу приложения
export const futureFlags = {
  v7_relativeSplatPath: true,
  v7_fetcherPersist: true,
  v7_normalizeFormMethod: true,
  v7_partialHydration: true,
  v7_skipActionErrorRevalidation: true,
} as const;

export const router = createBrowserRouter(routes, { future: futureFlags });
