import { test, expect } from '@playwright/test';

test('dashboard page loads', async ({ page }) => {
  await page.goto('/dashboard');
  await expect(page.getByText('ESG Dashboard Overview')).toBeVisible();
});

test('chat page loads', async ({ page }) => {
  await page.goto('/chat');
  await expect(page.getByText('ESG Analyst Chat')).toBeVisible();
});

test('compare page loads', async ({ page }) => {
  await page.goto('/compare');
  await expect(page.getByText('Company Comparison')).toBeVisible();
});
