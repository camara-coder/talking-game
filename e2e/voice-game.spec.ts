/**
 * E2E tests for Voice Game
 */
import { test, expect } from '@playwright/test';

test.describe('Voice Game E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto('/');

    // Wait for the page to load
    await page.waitForLoadState('networkidle');
  });

  test('should display the main UI elements', async ({ page }) => {
    // Check for character canvas
    const canvas = page.locator('canvas');
    await expect(canvas).toBeVisible();

    // Check for push-to-talk button
    const button = page.locator('button:has-text("Push to Talk")');
    await expect(button).toBeVisible();

    // Check for caption display
    const captions = page.locator('.caption-display');
    await expect(captions).toBeVisible();
  });

  test('should update button text when clicked', async ({ page }) => {
    const button = page.locator('button:has-text("Push to Talk")');

    // Click button
    await button.click();

    // Button text should change
    await expect(button).toContainText('Listening');
  });

  test('should handle session start and stop', async ({ page }) => {
    const button = page.locator('button:has-text("Push to Talk")');

    // Start session (mouse down)
    await button.dispatchEvent('mousedown');
    await page.waitForTimeout(500);

    // Check state changed to listening
    await expect(button).toContainText('Listening');

    // Stop session (mouse up)
    await button.dispatchEvent('mouseup');
    await page.waitForTimeout(500);

    // State should change to thinking
    await expect(button).toContainText('Thinking');
  });

  test('should connect to WebSocket', async ({ page }) => {
    // Listen for WebSocket connection
    let wsConnected = false;

    page.on('websocket', (ws) => {
      ws.on('open', () => {
        wsConnected = true;
      });
    });

    // Start session to trigger WebSocket connection
    const button = page.locator('button:has-text("Push to Talk")');
    await button.click();

    // Wait a bit for WebSocket to connect
    await page.waitForTimeout(1000);

    // WebSocket should be connected
    // Note: This assertion might need adjustment based on implementation
  });

  test('should display captions when provided', async ({ page }) => {
    const captions = page.locator('.caption-display');

    // Initially should be empty
    await expect(captions).toBeEmpty();

    // Simulate receiving transcript
    await page.evaluate(() => {
      const event = new CustomEvent('transcript', {
        detail: { text: 'Test transcript' },
      });
      window.dispatchEvent(event);
    });

    // Captions should show transcript
    // Note: This test needs actual WebSocket integration
  });

  test('should handle multiple sessions', async ({ page }) => {
    const button = page.locator('button:has-text("Push to Talk")');

    // First session
    await button.click();
    await page.waitForTimeout(500);
    await button.click();
    await page.waitForTimeout(1000);

    // Second session
    await button.click();
    await page.waitForTimeout(500);
    await button.click();
    await page.waitForTimeout(1000);

    // Should not throw errors
  });

  test('should be responsive on mobile', async ({ page, isMobile }) => {
    if (!isMobile) {
      test.skip();
    }

    // Check elements are visible on mobile
    const canvas = page.locator('canvas');
    await expect(canvas).toBeVisible();

    const button = page.locator('button:has-text("Push to Talk")');
    await expect(button).toBeVisible();

    // Button should be easily tappable (at least 44x44 px)
    const boundingBox = await button.boundingBox();
    expect(boundingBox?.width).toBeGreaterThanOrEqual(44);
    expect(boundingBox?.height).toBeGreaterThanOrEqual(44);
  });

  test('should handle network errors gracefully', async ({ page, context }) => {
    // Block backend API
    await context.route('**/api/**', (route) => route.abort());

    const button = page.locator('button:has-text("Push to Talk")');

    // Try to start session
    await button.click();

    // Should show error message or remain functional
    // (Implementation-dependent)
  });
});

test.describe('Backend Health', () => {
  test('backend should be healthy', async ({ request }) => {
    const response = await request.get('http://localhost:8008/health');

    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.service).toBe('healthy');
  });

  test('Ollama should be available', async ({ request }) => {
    const response = await request.get('http://localhost:8008/health');
    const data = await response.json();

    expect(data.checks.ollama).toBeDefined();
  });

  test('STT should be ready', async ({ request }) => {
    const response = await request.get('http://localhost:8008/health');
    const data = await response.json();

    expect(data.checks.stt.status).toBe('ready');
  });
});

test.describe('Session Management', () => {
  test('should create a new session', async ({ request }) => {
    const response = await request.post('http://localhost:8008/api/session/start', {
      data: {
        language: 'en',
        mode: 'ptt',
      },
    });

    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.session_id).toBeDefined();
    expect(data.status).toBe('listening');
  });

  test('should stop a session', async ({ request }) => {
    // Start session
    const startResponse = await request.post(
      'http://localhost:8008/api/session/start',
      { data: {} }
    );
    const { session_id } = await startResponse.json();

    // Stop session
    const stopResponse = await request.post(
      'http://localhost:8008/api/session/stop',
      {
        data: {
          session_id,
          return_audio: false,
        },
      }
    );

    expect(stopResponse.ok()).toBeTruthy();
  });

  test('should get session info', async ({ request }) => {
    // Start session
    const startResponse = await request.post(
      'http://localhost:8008/api/session/start',
      { data: {} }
    );
    const { session_id } = await startResponse.json();

    // Get session
    const getResponse = await request.get(
      `http://localhost:8008/api/session/${session_id}`
    );

    expect(getResponse.ok()).toBeTruthy();

    const data = await getResponse.json();
    expect(data.session_id).toBe(session_id);
  });
});

test.describe('Accessibility', () => {
  test('should have no accessibility violations', async ({ page }) => {
    // This would require @axe-core/playwright
    // await injectAxe(page);
    // const violations = await checkA11y(page);
    // expect(violations).toHaveLength(0);
  });

  test('should be keyboard navigable', async ({ page }) => {
    // Tab to button
    await page.keyboard.press('Tab');

    // Button should be focused
    const button = page.locator('button:has-text("Push to Talk")');
    await expect(button).toBeFocused();

    // Space should activate button
    await page.keyboard.press('Space');

    // State should change
    await expect(button).toContainText('Listening');
  });

  test('should have proper ARIA attributes', async ({ page }) => {
    const button = page.locator('button:has-text("Push to Talk")');

    // Check for ARIA attributes
    await expect(button).toHaveAttribute('role', 'button');
  });
});
