/**
 * src/lib/sseClient.ts
 * Fetch-based Server-Sent Events client supporting POST requests and JSON streaming.
 */

import { Block } from '@/components/sdui/types';

export interface LocationContext {
  lat: number;
  lng: number;
}

export interface ChatContext {
  current_location?: LocationContext;
}

export interface ChatPayload {
  session_id: string;
  content: string;
  context?: ChatContext;
}

export interface SSEClientCallbacks {
  /** Triggered when a new token chunk is streamed (supports typing indicators) */
  onToken: (token: string) => void;
  /** Triggered when the final payload with complete UI blocks and quick replies arrives */
  onBlocks: (ui_blocks: Block[], quick_replies: string[]) => void;
  /** Triggered when the stream successfully terminates or completes */
  onComplete: () => void;
  /** Triggered on HTTP errors, parser errors, or explicit backend errors */
  onError: (error: Error) => void;
}

export interface RawVenueItem {
  id?: string;
  name?: string;
  vibe?: string;
  image_url?: string;
  district?: string;
  city?: string;
  rationale?: string;
  vibe_tags?: string[];
}

export interface RawCocktailItem {
  id?: string;
  name?: string;
  vibe?: string;
  image_url?: string;
  rationale?: string;
  vibe_tags?: string[];
  alcoholic_type?: string;
  base_liquor?: string;
}

export interface RawBlock {
  type: string;
  items?: (RawVenueItem | RawCocktailItem)[];
  replies?: string[];
  content?: string;
  [key: string]: unknown;
}

/**
 * Helper to normalize backend block models to match frontend expected types.
 */
export function normalizeUIBlocks(blocks: RawBlock[]): Block[] {
  return blocks.map((block) => {
    // 1. Map 'items' from backend to 'data' for carousels
    if (block.type === 'carousel_venues' || block.type === 'carousel_cocktails') {
      const items = block.items || [];
      return {
        type: block.type,
        data: items.map((item, idx: number) => {
          const isVenue = block.type === 'carousel_venues';
          const venueItem = item as RawVenueItem;
          const cocktailItem = item as RawCocktailItem;
          
          if (isVenue) {
            return {
              id: venueItem.id || `${block.type}-${idx}`,
              name: venueItem.name || 'Unknown',
              vibe: venueItem.vibe || 'Friendly',
              image_url: venueItem.image_url,
              vibe_tags: venueItem.vibe_tags || (venueItem.district ? [venueItem.district, venueItem.city].filter((x): x is string => !!x) : []),
              rationale: venueItem.rationale,
            };
          } else {
            return {
              id: cocktailItem.id || `${block.type}-${idx}`,
              name: cocktailItem.name || 'Unknown',
              vibe: cocktailItem.vibe || 'Friendly',
              image_url: cocktailItem.image_url,
              vibe_tags: cocktailItem.vibe_tags || [],
              rationale: cocktailItem.rationale,
              alcoholic_type: cocktailItem.alcoholic_type,
              base_liquor: cocktailItem.base_liquor,
            };
          }
        }),
      } as Block;
    }

    // 2. Map quick replies 'replies' field to 'actions'
    if (block.type === 'quick_replies') {
      return {
        type: 'quick_replies',
        actions: block.replies || [],
      } as Block;
    }

    return block as unknown as Block;
  });
}

/**
 * Initiates an SSE chat request and processes the streamed response.
 */
export async function connectSSEChat(
  url: string,
  payload: ChatPayload,
  callbacks: SSEClientCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const { onToken, onBlocks, onComplete, onError } = callbacks;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify(payload),
      signal,
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => 'No error detail provided');
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    if (!response.body) {
      throw new Error('Response body stream is not available');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }

      // Decode the current chunk and append to buffer
      buffer += decoder.decode(value, { stream: true });

      // SSE items are separated by double newlines (\n\n)
      let boundaryIndex: number;
      while ((boundaryIndex = buffer.indexOf('\n\n')) !== -1) {
        const rawEvent = buffer.substring(0, boundaryIndex);
        buffer = buffer.substring(boundaryIndex + 2);

        // Process line-by-line in the event block
        const lines = rawEvent.split('\n');
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;

          // Check for standard SSE prefix 'data:'
          if (trimmed.startsWith('data:')) {
            const dataContent = trimmed.substring(trimmed.indexOf(':') + 1).trim();
            if (!dataContent) continue;

            try {
              const parsed = JSON.parse(dataContent);

              // 1. Check for backend error payload
              if (parsed.error) {
                onError(new Error(parsed.error));
                return; // Terminate execution on explicit error
              }

              // 2. Stream individual tokens
              if (typeof parsed.token === 'string') {
                onToken(parsed.token);
              }

              // 3. Capture the final SDUI payload
              if (parsed.done === true) {
                // To resolve backend/frontend misalignments during client-side parsing:
                const normalizedBlocks = normalizeUIBlocks(parsed.ui_blocks || []);
                onBlocks(normalizedBlocks, parsed.quick_replies || []);
              }
            } catch (e) {
              onError(new Error(`Failed to parse SSE JSON: ${e instanceof Error ? e.message : String(e)}`));
              return;
            }
          }
        }
      }
    }

    // Flush any leftover buffer content that did not terminate in \n\n
    if (buffer.trim()) {
      const trimmed = buffer.trim();
      if (trimmed.startsWith('data:')) {
        const dataContent = trimmed.substring(trimmed.indexOf(':') + 1).trim();
        try {
          const parsed = JSON.parse(dataContent);
          if (parsed.error) {
            onError(new Error(parsed.error));
            return;
          }
          if (typeof parsed.token === 'string') {
            onToken(parsed.token);
          }
          if (parsed.done === true) {
            const normalizedBlocks = normalizeUIBlocks(parsed.ui_blocks || []);
            onBlocks(normalizedBlocks, parsed.quick_replies || []);
          }
        } catch {
          // Ignore trailing malformed buffer contents
        }
      }
    }

    onComplete();
  } catch (error) {
    if (signal?.aborted || (error instanceof Error && error.name === 'AbortError')) {
      // Graceful cancellation on user action (e.g. stop generation)
      onComplete();
    } else {
      onError(error instanceof Error ? error : new Error(String(error)));
    }
  }
}

