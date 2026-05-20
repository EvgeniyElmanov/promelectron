#!/usr/bin/env node
/**
 * Autonomous Tester Agent — Entry Point v2
 * 
 * Полностью автономный агент для тестирования e-commerce приложения.
 * 
 * Запуск:
 *   # Сценарии
 *   node tests/agent/agent.js --persona=user --scenario=fullPurchaseFlow
 *   node tests/agent/agent.js --persona=admin
 *   node tests/agent/agent.js --persona=all --report=all
 * 
 *   # Discovery mode
 *   node tests/agent/agent.js --persona=user --discover
 * 
 *   # Performance testing
 *   node tests/agent/agent.js --performance --report=all
 * 
 *   # Accessibility testing
 *   node tests/agent/agent.js --accessibility --report=all
 * 
 *   # Responsive testing
 *   node tests/agent/agent.js --responsive --report=all
 * 
 *   # Security testing
 *   node tests/agent/agent.js --persona=security --report=all
 * 
 *   # Fuzz testing
 *   node tests/agent/agent.js --persona=fuzz --report=all
 * 
 *   # Cross-role testing
 *   node tests/agent/agent.js --persona=crossrole --report=all
 * 
 *   # Отладка
 *   node tests/agent/agent.js --persona=user --headed --debug
 * 
 *   # Свой URL
 *   node tests/agent/agent.js --persona=user --base-url=http://localhost:5173 --api-url=http://localhost:8000
 * 
 * Окружение:
 *   TEST_BASE_URL     — URL фронтенда
 *   TEST_API_URL      — URL API
 *   OPENAI_API_KEY    — для vision model (optional)
 *   VISION_PROVIDER   — heuristic | openai (default: heuristic)
 *   AGENT_STATE_FILE  — путь к state файлу
 */

import { TestRunner } from './runner.js';

async function main() {
  const args = process.argv.slice(2);

  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
Autonomous Tester Agent v2
==========================

Usage:
  node tests/agent/agent.js [options]

Options:
  --persona=<role>         Роль: user | admin | supplier | security | performance | crossrole | fuzz | accessibility | responsive | all
  --scenario=<name>        Конкретный сценарий
  --discover               Режим исследования сайта
  --performance            Performance testing (LCP, CLS, FCP, TTFB)
  --accessibility          Accessibility testing (a11y checks)
  --responsive             Responsive testing (mobile/tablet/desktop)
  --headed                 Показывать браузер
  --debug                  Подробный вывод
  --report=<format>        console | json | html | markdown | all
  --base-url=<url>         URL фронтенда
  --api-url=<url>          URL API
  --help, -h               Эта справка

Examples:
  # Полное тестирование
  npm run agent:all

  # Performance
  node tests/agent/agent.js --performance --report=all

  # Accessibility
  node tests/agent/agent.js --accessibility --report=all

  # Security
  node tests/agent/agent.js --persona=security --report=all

  # Fuzz
  node tests/agent/agent.js --persona=fuzz --report=all
`);
    process.exit(0);
  }

  const runner = new TestRunner();
  const exitCode = await runner.run(args);
  process.exit(exitCode);
}

main().catch((err) => {
  console.error('Agent crashed:', err);
  process.exit(1);
});
