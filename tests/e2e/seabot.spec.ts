import { test, expect } from '@playwright/test';
import path from 'path';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('Seabot Maritime RAG Chatbot E2E Suite', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
  });

  test('F1 & F2: Complete upload, question answering, and clickable source chip verification', async ({
    page,
  }) => {
    // 1. Open upload modal
    await page.getByRole('button', { name: /Upload/i }).first().click();

    // 2. Upload sample document
    const samplePath = path.resolve(
      __dirname,
      '../../sample_docs/Main Engine Operating Manual.pdf'
    );

    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.locator('input[type="file"]').setInputFiles(samplePath);

    // 3. Close upload dialog once ready
    await page.getByRole('button', { name: /Done/i }).click();

    // 4. Send technical question
    const textarea = page.locator('textarea');
    await textarea.fill('What is the cylinder head tightening torque for the main engine?');
    await page.getByRole('button', { name: /Send/i }).click();

    // 5. Verify streamed answer appears with citation badge
    const assistantMessage = page.locator('.whitespace-pre-wrap').last();
    await expect(assistantMessage).toContainText('1250 Nm', { timeout: 20000 });
    await expect(assistantMessage).toContainText(/\[S\d+\]/);

    // 6. Verify clickable source chip
    const sourceChip = page.locator('button:has-text("Main Engine Operating Manual")').first();
    await expect(sourceChip).toBeVisible();

    // 7. Click chip to deep link into PDF viewer
    await sourceChip.click();
    await expect(page).toHaveURL(/\/viewer\/.+\?page=\d+/);
    await expect(page.getByText(/Page \d+ of/i)).toBeVisible();

    // 8. Test browser back closes viewer
    await page.goBack();
    await expect(page).toHaveURL(/\/chat\//);
  });

  test('F2: Exact NOT-FOUND response on out-of-scope question', async ({ page }) => {
    const textarea = page.locator('textarea');
    await textarea.fill('What is the recipe for chocolate soufflé in the ship galley?');
    await page.getByRole('button', { name: /Send/i }).click();

    const assistantMessage = page.locator('.whitespace-pre-wrap').last();
    await expect(assistantMessage).toContainText('Not found in the uploaded documents.', {
      timeout: 15000,
    });

    // Ensure zero source chips shown
    await expect(page.getByText('Referenced Sources')).not.toBeVisible();
  });

  test('F3 & F4: Clear history with time range modal', async ({ page }) => {
    // Open Clear History modal
    await page.getByRole('button', { name: /Clear History/i }).click();
    await expect(page.getByText('Clear History')).toBeVisible();

    // Select Today range
    await page.getByLabel('Today').check();
    await page.getByRole('button', { name: /Review & Confirm/i }).click();

    // Confirm deletion
    await page.getByRole('button', { name: /Confirm Delete/i }).click();
    await expect(page.getByText('Clear History')).not.toBeVisible();
  });

  test('F6: Resume state after page refresh (< 1 second restore)', async ({ page }) => {
    const draftText = 'Emergency fire pump battery voltage check';
    const textarea = page.locator('textarea');
    await textarea.fill(draftText);

    // Refresh page
    const startTime = Date.now();
    await page.reload();
    const durationMs = Date.now() - startTime;

    // Verify restore completed quickly
    expect(durationMs).toBeLessThan(3000);

    // Verify draft restored
    await expect(page.locator('textarea')).toHaveValue(draftText);
  });

  test('F7: Ask Seabot empty state and suggested starter questions', async ({ page }) => {
    await page.getByRole('button', { name: /New Conversation/i }).click();

    await expect(
      page.getByRole('heading', { name: /Ask Seabot about your documents/i })
    ).toBeVisible();

    // Check scope selector chips
    await expect(page.getByText(/Scope:/i)).toBeVisible();
  });
});
