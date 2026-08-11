import { request } from '@playwright/test';

// F006/S001: секрет только из env (GitHub Secret SEED_SECRET в CI) — без хардкода.
const SEED_SECRET = process.env.SEED_SECRET;

export default async function globalSetup() {
  if (!SEED_SECRET) {
    throw new Error(
      'SEED_SECRET не задан: экспортируйте переменную окружения SEED_SECRET ' +
        '(значение — тестовая фикстура из GitHub Secrets / helm test values).',
    );
  }
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
