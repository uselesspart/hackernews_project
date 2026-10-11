// Типы ответов берутся из src/api/schema.d.ts (npm run gen:api), а не пишутся вручную
import type { components } from "./schema";

type S = components["schemas"];

export type DatasetMeta = S["DatasetMeta"];
export type Suggestion = S["Suggestion"];
export type TechListItem = S["TechListItem"];
export type TechProfile = S["TechProfile"];
export type Sentiment = S["Sentiment"];
export type SentimentShares = S["SentimentShares"];
export type CommentExample = S["CommentExample"];
export type IrrBrief = S["IrrBrief"];
export type StoriesPage = S["StoriesPage"];
export type StoryOut = S["StoryOut"];
export type Timeline = S["Timeline"];

export type StorySort = "score" | "comments" | "time";
export type TechSort = "stories" | "comments" | "sentiment" | "irr" | "name";
export type TimelineBucket = "day" | "week" | "month";
