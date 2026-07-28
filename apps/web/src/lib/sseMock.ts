/**
 * src/lib/sseMock.ts
 * Mock stream generator for Playwright and local development offline testing.
 */

export interface MockStreamOptions {
  tokens: string[];
  tokenDelayMs?: number;
  finalBlocks: unknown[];
  quickReplies?: string[];
  errorPayload?: string;
}

/**
 * Creates a standard mock Response object containing a timed SSE stream.
 */
export function createMockSSEStreamResponse(options: MockStreamOptions): Response {
  const { tokens, tokenDelayMs = 30, finalBlocks, quickReplies = [], errorPayload } = options;
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      try {
        // 1. Stream tokens
        for (const token of tokens) {
          if (tokenDelayMs > 0) {
            await new Promise((resolve) => setTimeout(resolve, tokenDelayMs));
          }
          const chunk = `data: ${JSON.stringify({ token })}\n\n`;
          controller.enqueue(encoder.encode(chunk));
        }

        // 2. Optional: Stream error payload
        if (errorPayload) {
          if (tokenDelayMs > 0) {
            await new Promise((resolve) => setTimeout(resolve, tokenDelayMs));
          }
          const errorChunk = `data: ${JSON.stringify({ error: errorPayload })}\n\n`;
          controller.enqueue(encoder.encode(errorChunk));
          controller.close();
          return;
        }

        // 3. Stream final SDUI event payload
        if (tokenDelayMs > 0) {
          await new Promise((resolve) => setTimeout(resolve, tokenDelayMs));
        }
        const finalPayload = {
          ui_blocks: finalBlocks,
          quick_replies: quickReplies,
          done: true,
        };
        const finalChunk = `data: ${JSON.stringify(finalPayload)}\n\n`;
        controller.enqueue(encoder.encode(finalChunk));
        controller.close();
      } catch (err) {
        controller.error(err);
      }
    },
  });

  return new Response(stream, {
    status: 200,
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}
