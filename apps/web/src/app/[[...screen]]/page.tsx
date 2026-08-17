import { redirect } from "next/navigation";

const screenByRoute: Record<string, number> = {
  "": 1,
  start: 2,
  chat: 3,
  recipe: 6,
  search: 13,
  profile: 14,
  sessions: 17,
  b2b: 5,
  "b2b/recipes": 7,
  "b2b/guests": 10,
  "b2b/guests/profile": 8,
  "b2b/recipes/editor": 9,
  "b2b/menu": 11,
  "b2b/transactions": 12,
  "b2b/recommendations": 15,
  "b2b/copilot": 16,
  "b2b/bespoke": 18,
  "b2b/privacy": 19,
  "menu-builder": 9,
};

export default async function StitchScreen({
  params,
}: {
  params: Promise<{ screen?: string[] }>;
}) {
  const { screen = [] } = await params;
  const route = screen.join("/");
  const number = screenByRoute[route] ?? 1;

  redirect(`/stitch/screen-${number}.html`);
}
