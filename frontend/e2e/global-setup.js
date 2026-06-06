import { request } from '@playwright/test';

const SEED_SECRET = 'promelectron-test-seed-2024';

export default async function globalSetup() {
  const apiUrl = process.env.API_URL || 'http://127.0.0.1:8000';
  const context = await request.newContext({ baseURL: apiUrl });

  const res = await context.post('/api/v1/seed', {
    headers: { 'x-seed-secret': SEED_SECRET },
  });

  if (!res.ok()) {
    const body = await res.text();
    throw new Error(`Seed failed (${res.status()}): ${body}`);
  }

  await context.dispose();
}
