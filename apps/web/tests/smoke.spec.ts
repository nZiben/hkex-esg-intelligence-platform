import { test, expect } from '@playwright/test';

test('dashboard page loads', async ({ page }) => {
  await page.goto('/dashboard');
  await expect(page.getByText(/Dashboard|Portfolio dashboard/)).toBeVisible();
});

test('chat page loads', async ({ page }) => {
  await page.goto('/chat');
  await expect(page.getByText('Analyst chat')).toBeVisible();
});

test('compare page loads', async ({ page }) => {
  await page.goto('/compare');
  await expect(page.getByText('Comparison studio')).toBeVisible();
});

test('predictions page loads', async ({ page }) => {
  await page.goto('/predictions');
  await expect(page.getByText('Model predictions')).toBeVisible();
});
