import { keepPreviousData, useInfiniteQuery, useQuery } from "@tanstack/react-query";

import { getJson } from "./client";
import type {
  DatasetMeta,
  StoriesPage,
  StorySort,
  Suggestion,
  TechListItem,
  TechProfile,
  TechSort,
  Timeline,
  TimelineBucket,
} from "./types";

export const STORIES_PAGE_SIZE = 10;

export function useMeta() {
  return useQuery({
    queryKey: ["meta"],
    queryFn: ({ signal }) => getJson<DatasetMeta>("/meta", {}, signal),
    // Данные меняются только после precompute
    staleTime: 10 * 60_000,
  });
}

export function useSuggest(q: string, enabled: boolean, limit = 8) {
  return useQuery({
    queryKey: ["suggest", q, limit],
    // signal отменяет устаревший запрос, когда пользователь печатает дальше
    queryFn: ({ signal }) => getJson<Suggestion[]>("/techs/suggest", { q, limit }, signal),
    enabled,
    placeholderData: keepPreviousData,
    staleTime: 10 * 60_000,
  });
}

export function useTechList(sort: TechSort = "stories", minStories = 1) {
  return useQuery({
    queryKey: ["techs", sort, minStories],
    queryFn: ({ signal }) =>
      getJson<TechListItem[]>("/techs", { sort, min_stories: minStories, limit: 500 }, signal),
    staleTime: 10 * 60_000,
  });
}

export function useTechProfile(key: string) {
  return useQuery({
    queryKey: ["tech", key],
    queryFn: ({ signal }) => getJson<TechProfile>(`/techs/${encodeURIComponent(key)}`, { words_limit: 30 }, signal),
    staleTime: 10 * 60_000,
  });
}

export function useTechStories(key: string, sort: StorySort) {
  return useInfiniteQuery({
    queryKey: ["stories", key, sort],
    queryFn: ({ pageParam, signal }) =>
      getJson<StoriesPage>(
        `/techs/${encodeURIComponent(key)}/stories`,
        { sort, limit: STORIES_PAGE_SIZE, offset: pageParam },
        signal,
      ),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => {
      const loaded = pages.reduce((n, p) => n + p.items.length, 0);
      return loaded < last.total ? loaded : undefined;
    },
    // При смене сортировки держим старый список (приглушённым), а не мигаем скелетоном
    placeholderData: keepPreviousData,
    staleTime: 10 * 60_000,
  });
}

export function useTechTimeline(key: string, bucket: TimelineBucket, enabled: boolean) {
  return useQuery({
    queryKey: ["timeline", key, bucket],
    queryFn: ({ signal }) =>
      getJson<Timeline>(`/techs/${encodeURIComponent(key)}/timeline`, { bucket }, signal),
    enabled,
    staleTime: 10 * 60_000,
  });
}
