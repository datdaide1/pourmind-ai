import { readFile } from "node:fs/promises";
import { join } from "node:path";

const sourceScreen = /^screen-(?:[1-9]|1[0-9])\.html$/;

/** Serves the supplied Stitch document byte-for-byte as the product UI. */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ screen: string }> },
) {
  const { screen } = await params;

  if (!sourceScreen.test(screen)) {
    return new Response("Not found", { status: 404 });
  }

  const source = await readFile(join(process.cwd(), "public", "stitch", screen));
  return new Response(source, {
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "public, max-age=0, must-revalidate",
    },
  });
}
