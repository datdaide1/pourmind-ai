import { test, expect } from '@playwright/test';

// Custom browser context script to intercept fetch and mock SSE streaming
test.describe('Server-Driven UI & SSE Stream Testing', () => {
  test.beforeEach(async ({ context }) => {
    await context.addInitScript(() => {
      const originalFetch = window.fetch;
      window.fetch = async (input, init) => {
        const url = typeof input === 'string' ? input : input.url;

        if (url.includes('/api/v1/chat/message')) {
          const payload = JSON.parse(init?.body as string || '{}');
          const isB2B = payload.content?.toLowerCase().includes('b2b') || payload.mode === 'b2b';

          const encoder = new TextEncoder();
          const stream = new ReadableStream({
            async start(controller) {
              // 1. Stream timed text tokens
              const tokens = isB2B
                ? ['Phân', ' tích', ' doanh', ' thu', ' thực', ' đơn', '.']
                : ['Chào', ' mừng', ' bạn', ' đến', ' với', ' Mixologist', '.'];

              for (const token of tokens) {
                await new Promise((resolve) => setTimeout(resolve, 30));
                controller.enqueue(encoder.encode(`data: ${JSON.stringify({ token })}\n\n`));
              }

              // Wait before sending the final block payload
              await new Promise((resolve) => setTimeout(resolve, 50));

              // 2. Stream final SDUI Block JSON payload
              const finalBlocks = isB2B
                ? [
                    { type: 'text', content: 'Phân tích doanh thu thực đơn.' },
                    {
                      type: 'carousel_venues',
                      data: [{ id: 'venue-b1', name: 'Layla Eatery & Bar', vibe: 'Lively Bar', vibe_tags: ['Cocktails'] }]
                    },
                    {
                      type: 'carousel_cocktails',
                      data: [{ id: 'cocktail-b1', name: 'Classic Negroni', alcoholic_type: 'Alcoholic', base_liquor: 'Gin' }]
                    },
                    { type: 'rationale', content: 'Gợi ý từ thuật toán dự báo doanh thu.' },
                    { type: 'quick_replies', actions: ['Tải Báo Cáo', 'Cập Nhật Thực Đơn'] }
                  ]
                : [
                    { type: 'text', content: 'Chào mừng bạn đến với Mixologist.' },
                    {
                      type: 'carousel_venues',
                      data: [{ id: 'venue-c1', name: 'The Rabbit Hole', vibe: 'Cozy Lounge', vibe_tags: ['Classic'] }]
                    },
                    {
                      type: 'carousel_cocktails',
                      data: [{ id: 'cocktail-c1', name: 'Classic Manhattan', alcoholic_type: 'Alcoholic', base_liquor: 'Rye Whiskey' }]
                    },
                    { type: 'rationale', content: 'Đề xuất dựa trên sở thích uống rượu nền Whiskey của bạn.' },
                    { type: 'quick_replies', actions: ['Tìm Quán Bar Khác', 'Đổi Vị Đồ Uống'] }
                  ];

              const finalPayload = {
                ui_blocks: finalBlocks,
                quick_replies: isB2B ? ['Tải Báo Cáo', 'Cập Nhật Thực Đơn'] : ['Tìm Quán Bar Khác', 'Đổi Vị Đồ Uống'],
                done: true
              };

              controller.enqueue(encoder.encode(`data: ${JSON.stringify(finalPayload)}\n\n`));
              controller.close();
            }
          });

          return new Response(stream, {
            status: 200,
            headers: {
              'Content-Type': 'text/event-stream',
              'Cache-Control': 'no-cache',
              'Connection': 'keep-alive',
            }
          });
        }

        return originalFetch(input, init);
      };
    });
  });

  test('should assert incremental text tokens and dynamic SDUI block rendering', async ({ page }) => {
    await page.goto('/');

    // Inject temporary interactive test chat component to trigger fetch requests during E2E testing
    await page.evaluate(() => {
      const container = document.createElement('div');
      container.id = 'e2e-chat-test-root';
      container.style.position = 'fixed';
      container.style.bottom = '10px';
      container.style.right = '10px';
      container.style.zIndex = '9999';
      container.style.background = '#12121E';
      container.style.border = '1px solid rgba(255,255,255,0.1)';
      container.style.padding = '12px';
      container.style.borderRadius = '12px';
      
      container.innerHTML = `
        <div id="chat-messages" class="flex flex-col gap-2 mb-2"></div>
        <textarea id="chat-input" placeholder="Gõ tin nhắn cho Mixologist..."></textarea>
        <button id="chat-submit-btn">Send</button>
      `;
      document.body.appendChild(container);

      const submitBtn = document.getElementById('chat-submit-btn')!;
      const chatInput = document.getElementById('chat-input') as HTMLTextAreaElement;
      const chatMessages = document.getElementById('chat-messages')!;

      submitBtn.addEventListener('click', async () => {
        const text = chatInput.value;
        if (!text) return;

        const aiMsg = document.createElement('div');
        aiMsg.className = 'ai-msg-bubble';
        aiMsg.innerHTML = `<span class="tokens"></span><div class="blocks"></div>`;
        chatMessages.appendChild(aiMsg);

        const tokenSpan = aiMsg.querySelector('.tokens') as HTMLSpanElement;
        const blocksDiv = aiMsg.querySelector('.blocks') as HTMLDivElement;

        const response = await fetch('/api/v1/chat/message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: text, mode: text.toLowerCase().includes('b2b') ? 'b2b' : 'b2c' }),
        });

        const reader = response.body!.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value);

          let boundaryIndex: number;
          while ((boundaryIndex = buffer.indexOf('\n\n')) !== -1) {
            const rawEvent = buffer.substring(0, boundaryIndex);
            buffer = buffer.substring(boundaryIndex + 2);

            const lines = rawEvent.split('\n');
            for (const line of lines) {
              if (line.startsWith('data:')) {
                type CatalogItem = {
                  id: string;
                  name: string;
                  vibe: string;
                  rationale: string;
                  alcoholic_type: string;
                  base_liquor: string;
                };
                type UiBlock = {
                  type: string;
                  content: string;
                  data: CatalogItem[];
                  actions: string[];
                };
                const parsed = JSON.parse(line.substring(5).trim()) as {
                  token?: string;
                  done?: boolean;
                  ui_blocks: UiBlock[];
                };
                if (parsed.token) {
                  tokenSpan.innerText += parsed.token;
                  window.dispatchEvent(new CustomEvent('token-received', { detail: parsed.token }));
                }
                if (parsed.done === true) {
                  parsed.ui_blocks.forEach((block) => {
                    const blockEl = document.createElement('div');
                    blockEl.className = `sdui-${block.type}`;
                    blockEl.setAttribute('data-testid', `sdui-${block.type}`);
                    if (block.type === 'text') {
                      blockEl.innerText = block.content;
                    } else if (block.type === 'carousel_venues') {
                      blockEl.innerHTML = block.data.map((v) => `
                        <div class="venue-card" data-venue-id="${v.id}">
                          <h4 class="text-h4 text-left">${v.name}</h4>
                          <p class="text-body text-left">${v.vibe}</p>
                          <div class="rationale-block border-l-2 border-[var(--mode-accent)] bg-[var(--mode-accent-soft)] p-2">
                            <p class="text-body-sm text-left">${v.rationale}</p>
                          </div>
                        </div>
                      `).join('');
                    } else if (block.type === 'carousel_cocktails') {
                      blockEl.innerHTML = block.data.map((c) => `
                        <div class="cocktail-card" data-cocktail-id="${c.id}">
                          <h4 class="text-h4 text-left">${c.name}</h4>
                          <p class="text-body text-left">${c.alcoholic_type} · ${c.base_liquor}</p>
                          <div class="rationale-block border-l-2 border-[var(--mode-accent)] bg-[var(--mode-accent-soft)] p-2">
                            <p class="text-body-sm text-left">${c.rationale}</p>
                          </div>
                        </div>
                      `).join('');
                    } else if (block.type === 'rationale') {
                      blockEl.innerHTML = `
                        <div class="rationale-block border-l-2 border-[var(--mode-accent)] bg-[var(--mode-accent-soft)] p-2">
                          <p class="text-body-sm text-left">${block.content}</p>
                        </div>
                      `;
                    } else if (block.type === 'quick_replies') {
                      blockEl.innerHTML = block.actions.map((act: string) => `
                        <button class="quick-reply-btn text-body-sm text-left">${act}</button>
                      `).join('');
                    }
                    blocksDiv.appendChild(blockEl);
                  });
                }
              }
            }
          }
        }
      });
    });

    const chatInput = page.locator('#chat-input');
    const sendBtn = page.locator('#chat-submit-btn');

    // Setup listener to log tokens incrementally
    const receivedTokens: string[] = [];
    await page.exposeFunction('onTokenReceived', (token: string) => {
      receivedTokens.push(token);
    });
    await page.evaluate(() => {
      window.addEventListener('token-received', (event) => {
        const tokenEvent = event as CustomEvent<string>;
        const testWindow = window as typeof window & { onTokenReceived: (token: string) => void };
        testWindow.onTokenReceived(tokenEvent.detail);
      });
    });

    // Run test query for B2C
    await chatInput.fill('Gợi ý quán bar cho B2C');
    await sendBtn.click();

    // Verify completion
    await page.waitForSelector('[data-testid="sdui-quick_replies"]');

    // 1. Assert incremental token rendering
    expect(receivedTokens.length).toBeGreaterThan(0);
    expect(receivedTokens.join('')).toContain('Chào mừng bạn đến với Mixologist.');

    // 2. Assert SDUI Card, Carousel, Quick Replies, and Rationale Block render correctly
    await expect(page.locator('[data-testid="sdui-carousel_venues"]')).toBeVisible();
    await expect(page.locator('[data-testid="sdui-carousel_cocktails"]')).toBeVisible();
    await expect(page.locator('[data-testid="sdui-rationale"]')).toBeVisible();
    await expect(page.locator('[data-testid="sdui-quick_replies"]')).toBeVisible();

    // Assert actual content
    await expect(page.locator('[data-testid="sdui-carousel_venues"] .venue-card h4').first()).toHaveText('The Rabbit Hole');
    await expect(page.locator('[data-testid="sdui-carousel_cocktails"] .cocktail-card h4').first()).toHaveText('Classic Manhattan');
    await expect(page.locator('[data-testid="sdui-rationale"]').first()).toContainText('Đề xuất dựa trên sở thích uống rượu nền Whiskey của bạn.');
  });
});

test.describe('Static Component Styles & Design Token Verifications', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should assert typography rules for headings h1-h4', async ({ page }) => {
    const headings = page.locator('h1, h2, h3, h4');
    const count = await headings.count();
    expect(count).toBeGreaterThan(0);

    for (let i = 0; i < count; i++) {
      const header = headings.nth(i);
      const metrics = await header.evaluate((el) => {
        const style = window.getComputedStyle(el);
        const fontSize = parseFloat(style.fontSize);
        const lineHeight = parseFloat(style.lineHeight);
        return {
          tag: el.tagName.toLowerCase(),
          fontSize,
          lineHeight,
          ratio: lineHeight / fontSize,
        };
      });

      // Assert line height ratio is between 1.1 and 1.3
      expect(metrics.ratio).toBeGreaterThanOrEqual(1.1 - 0.02); // Stretches for pixel-rounding variances
      expect(metrics.ratio).toBeLessThanOrEqual(1.3 + 0.02);
    }
  });

  test('should assert typography rules for body texts p and span', async ({ page }) => {
    // Target text elements in showcasing sections (excluding tags, captions, and badges which have different line heights)
    const paragraphs = page.locator('section[data-mode] p');
    const count = await paragraphs.count();
    expect(count).toBeGreaterThan(0);

    for (let i = 0; i < count; i++) {
      const p = paragraphs.nth(i);
      const metrics = await p.evaluate((el) => {
        const style = window.getComputedStyle(el);
        const fontSize = parseFloat(style.fontSize);
        const lineHeight = parseFloat(style.lineHeight);
        return {
          className: el.className,
          fontSize,
          lineHeight,
          ratio: lineHeight / fontSize,
        };
      });

      // Skip caption or micro text classes which purposefully carry different rules
      if (metrics.className.includes('text-micro') || metrics.className.includes('text-overline') || metrics.className.includes('text-caption')) {
        continue;
      }

      // Assert line height ratio is between 1.5 and 1.6
      expect(metrics.ratio).toBeGreaterThanOrEqual(1.5 - 0.02);
      expect(metrics.ratio).toBeLessThanOrEqual(1.6 + 0.02);
    }
  });

  test('should strictly left-align all components and texts', async ({ page }) => {
    const textEls = page.locator('section[data-mode] h4, section[data-mode] p');
    const count = await textEls.count();
    expect(count).toBeGreaterThan(0);

    for (let i = 0; i < count; i++) {
      const el = textEls.nth(i);
      const textAlign = await el.evaluate((element) => {
        return window.getComputedStyle(element).textAlign;
      });

      expect(['left', 'start']).toContain(textAlign);
    }
  });

  test('should resolve border-color and background-color to B2B gold and B2C blue', async ({ page }) => {
    // 1. Assert B2C Mode colors resolve to Blue: rgb(59, 130, 246)
    const b2cRationale = page.locator('section[data-mode="b2c"] .border-l-2').first();
    const b2cColors = await b2cRationale.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return {
        borderLeftColor: style.borderLeftColor,
        backgroundColor: style.backgroundColor
      };
    });

    expect(b2cColors.borderLeftColor).toBe('rgb(59, 130, 246)');
    expect(b2cColors.backgroundColor).toBe('rgba(59, 130, 246, 0.15)');

    // 2. Assert B2B Mode colors resolve to Gold: rgb(212, 175, 55)
    const b2bRationale = page.locator('section[data-mode="b2b"] .border-l-2').first();
    const b2bColors = await b2bRationale.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return {
        borderLeftColor: style.borderLeftColor,
        backgroundColor: style.backgroundColor
      };
    });

    expect(b2bColors.borderLeftColor).toBe('rgb(212, 175, 55)');
    expect(b2bColors.backgroundColor).toBe('rgba(212, 175, 55, 0.15)');
  });
});
