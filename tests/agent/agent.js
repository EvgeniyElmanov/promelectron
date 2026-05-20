#!/usr/bin/env node
/**
 * Autonomous Tester Agent
 * 
 * Запуск:
 *   node tests/agent/agent.js --persona=user --scenario=fullPurchaseFlow
 *   node tests/agent/agent.js --persona=all --report=json
 * 
 * Требует:
 *   - Playwright MCP сервер (npx @playwright/mcp@latest)
 *   - Доступный сайт (по умолчанию https://promelectron-test.aidrivencode.ru)
 */

import { personas, generateCredentials } from './personas.js';
import { scenarios, getScenariosForPersona } from './scenarios.js';

const BASE_URL = process.env.TEST_BASE_URL || 'https://promelectron-test.aidrivencode.ru';
const REPORT_DIR = process.env.TEST_REPORT_DIR || './tests/agent/reports';

// ═══════════════════════════════════════
// MCP Client (Playwright bridge)
// ═══════════════════════════════════════

class PlaywrightMCPClient {
  constructor() {
    this.sessionId = null;
    this.page = null;
  }

  async call(method, params = {}) {
    // MCP вызов через stdio или HTTP
    // В реальном агенте — через @modelcontextprotocol/sdk Client
    // Здесь — stub для демонстрации архитектуры
    console.log(`  [MCP] ${method}`, params);
    return { success: true };
  }

  async navigate(url) {
    return this.call('playwright_navigate', { url });
  }

  async click(selector) {
    return this.call('playwright_click', { selector });
  }

  async fill(selector, value) {
    return this.call('playwright_fill', { selector, value });
  }

  async selectOption(selector, value) {
    return this.call('playwright_select_option', { selector, value });
  }

  async screenshot(name) {
    return this.call('playwright_screenshot', { name });
  }

  async evaluate(script) {
    return this.call('playwright_evaluate', { script });
  }

  async getUrl() {
    const r = await this.call('playwright_evaluate', { script: 'window.location.href' });
    return r.result;
  }

  async getConsoleLogs() {
    return this.call('browser_console_logs');
  }
}

// ═══════════════════════════════════════
// Step Executor
// ═══════════════════════════════════════

class StepExecutor {
  constructor(mcp, persona, credentials, report) {
    this.mcp = mcp;
    this.persona = persona;
    this.credentials = credentials;
    this.report = report;
    this.stepNumber = 0;
  }

  interpolate(value) {
    if (typeof value !== 'string') return value;
    return value
      .replace(/\{\{email\}\}/g, this.credentials.email)
      .replace(/\{\{password\}\}/g, this.credentials.password)
      .replace(/\{\{name\}\}/g, this.credentials.name)
      .replace(/\{\{random\}\}/g, Date.now().toString());
  }

  async execute(step) {
    this.stepNumber = step.step || this.stepNumber + 1;
    const { action, selector, value, target, expected, ms, script, name, type } = step;

    try {
      switch (action) {
        case 'navigate': {
          const url = target.startsWith('http') ? target : `${BASE_URL}${target}`;
          await this.mcp.navigate(url);
          return { ok: true, url };
        }

        case 'click': {
          const sel = this.interpolate(selector);
          await this.mcp.click(sel);
          return { ok: true, selector: sel };
        }

        case 'fill': {
          const sel = this.interpolate(selector);
          const val = this.interpolate(value);
          await this.mcp.fill(sel, val);
          return { ok: true, selector: sel, value: val };
        }

        case 'select': {
          const sel = this.interpolate(selector);
          const val = this.interpolate(value);
          await this.mcp.selectOption(sel, val);
          return { ok: true, selector: sel, value: val };
        }

        case 'wait': {
          await new Promise((r) => setTimeout(r, ms || 1000));
          return { ok: true, ms };
        }

        case 'screenshot': {
          const fname = `${this.report.id}-${this.stepNumber}-${name || 'screenshot'}.png`;
          await this.mcp.screenshot(fname);
          this.report.screenshots.push(fname);
          return { ok: true, file: fname };
        }

        case 'evaluate': {
          const result = await this.mcp.evaluate(script);
          // Если есть assert для evaluate
          if (step.assert) {
            const val = result.result || result;
            if (step.assert.min !== undefined && val < step.assert.min) {
              throw new Error(`Evaluate result ${val} < min ${step.assert.min}`);
            }
            if (step.assert.max !== undefined && val > step.assert.max) {
              throw new Error(`Evaluate result ${val} > max ${step.assert.max}`);
            }
          }
          return { ok: true, result };
        }

        case 'login': {
          const p = personas[step.persona || this.persona.key];
          const creds = p.defaultCredentials || this.credentials;
          await this.mcp.navigate(`${BASE_URL}/login`);
          await this.mcp.fill('[data-testid="login-email"]', creds.email);
          await this.mcp.fill('[data-testid="login-password"]', creds.password);
          await this.mcp.click('[data-testid="login-submit"]');
          await new Promise((r) => setTimeout(r, 1000));
          return { ok: true, email: creds.email };
        }

        case 'assert': {
          const result = await this.executeAssertion({ type, selector, expected });
          return { ok: true, assertion: result };
        }

        default:
          return { ok: false, error: `Unknown action: ${action}` };
      }
    } catch (err) {
      return {
        ok: false,
        error: err.message,
        step,
        screenshot: await this.captureError(),
      };
    }
  }

  async executeAssertion({ type, selector, expected }) {
    switch (type) {
      case 'url': {
        const url = await this.mcp.getUrl();
        if (expected.startsWith('http')) {
          if (url !== expected) throw new Error(`URL mismatch: ${url} !== ${expected}`);
        } else if (!url.includes(expected)) {
          throw new Error(`URL mismatch: ${url} does not include ${expected}`);
        }
        return { url };
      }

      case 'element': {
        const sel = this.interpolate(selector);
        const result = await this.mcp.evaluate(`
          const el = document.querySelector('${sel.replace(/'/g, "\\'")}');
          el ? { visible: el.offsetParent !== null, text: el.textContent?.slice(0, 100) } : null
        `);
        if (!result.result) throw new Error(`Element not found: ${sel}`);
        if (expected === 'visible' && !result.result.visible) {
          throw new Error(`Element not visible: ${sel}`);
        }
        return result.result;
      }

      case 'text': {
        const sel = this.interpolate(selector);
        const result = await this.mcp.evaluate(`
          const el = document.querySelector('${sel.replace(/'/g, "\\'")}');
          el ? el.textContent : document.body.textContent
        `);
        const text = result.result || '';
        if (!text.includes(expected)) {
          throw new Error(`Text "${expected}" not found in ${sel}`);
        }
        return { found: true };
      }

      case 'toast': {
        // Ждём toast в DOM
        await new Promise((r) => setTimeout(r, 500));
        const result = await this.mcp.evaluate(`
          document.body.textContent.includes('${expected.replace(/'/g, "\\'")}')
        `);
        if (!result.result) throw new Error(`Toast "${expected}" not found`);
        return { found: true };
      }

      default:
        throw new Error(`Unknown assertion type: ${type}`);
    }
  }

  async captureError() {
    try {
      const fname = `${this.report.id}-error-step-${this.stepNumber}.png`;
      await this.mcp.screenshot(fname);
      this.report.screenshots.push(fname);
      return fname;
    } catch {
      return null;
    }
  }
}

// ═══════════════════════════════════════
// Scenario Runner
// ═══════════════════════════════════════

class ScenarioRunner {
  constructor(mcp) {
    this.mcp = mcp;
  }

  async run(scenarioName, personaKey) {
    const persona = personas[personaKey];
    const credentials = persona.defaultCredentials || generateCredentials(persona);
    const steps = scenarios[scenarioName];

    const report = {
      id: `test-${Date.now()}`,
      scenario: scenarioName,
      persona: personaKey,
      credentials: { email: credentials.email, name: credentials.name },
      startTime: new Date().toISOString(),
      endTime: null,
      steps: [],
      screenshots: [],
      consoleErrors: [],
      passed: true,
      errors: [],
    };

    console.log(`\n🚀 [${personaKey}] ${scenarioName} — ${steps.length} шагов`);
    console.log(`   Email: ${credentials.email}`);

    const executor = new StepExecutor(this.mcp, persona, credentials, report);

    for (const step of steps) {
      const result = await executor.execute(step);
      report.steps.push({ step: executor.stepNumber, action: step.action, result });

      if (!result.ok) {
        report.passed = false;
        report.errors.push({
          step: executor.stepNumber,
          action: step.action,
          error: result.error,
          screenshot: result.screenshot,
        });
        console.log(`   ❌ Step ${executor.stepNumber} FAILED: ${result.error}`);
        break;
      } else {
        console.log(`   ✅ Step ${executor.stepNumber} ${step.action}`);
      }
    }

    // Собираем логи консоли
    try {
      const logs = await this.mcp.getConsoleLogs();
      report.consoleErrors = (logs.errors || []).filter(
        (e) => !e.message?.includes('favicon') && !e.message?.includes('[Vue Router warn]')
      );
    } catch {
      // ignore
    }

    report.endTime = new Date().toISOString();
    return report;
  }
}

// ═══════════════════════════════════════
// Main
// ═══════════════════════════════════════

async function main() {
  const args = process.argv.slice(2);
  const personaArg = args.find((a) => a.startsWith('--persona='))?.split('=')[1] || 'user';
  const scenarioArg = args.find((a) => a.startsWith('--scenario='))?.split('=')[1];
  const reportFormat = args.find((a) => a.startsWith('--report='))?.split('=')[1] || 'console';

  const mcp = new PlaywrightMCPClient();
  const runner = new ScenarioRunner(mcp);

  let scenarioList;
  if (scenarioArg) {
    scenarioList = [{ name: scenarioArg, steps: scenarios[scenarioArg] }];
  } else {
    scenarioList = getScenariosForPersona(personaArg);
  }

  const allReports = [];

  for (const { name } of scenarioList) {
    const report = await runner.run(name, personaArg === 'all' ? 'user' : personaArg);
    allReports.push(report);
  }

  // Итог
  const passed = allReports.filter((r) => r.passed).length;
  const failed = allReports.filter((r) => !r.passed).length;

  console.log(`\n${'='.repeat(50)}`);
  console.log(`📊 Results: ${passed} passed, ${failed} failed / ${allReports.length} total`);

  if (reportFormat === 'json') {
    const fs = await import('fs');
    const path = await import('path');
    const reportPath = path.join(REPORT_DIR, `report-${Date.now()}.json`);
    fs.mkdirSync(REPORT_DIR, { recursive: true });
    fs.writeFileSync(reportPath, JSON.stringify(allReports, null, 2));
    console.log(`📝 Report saved: ${reportPath}`);
  }

  for (const r of allReports.filter((r) => !r.passed)) {
    console.log(`\n🔴 FAILED: [${r.persona}] ${r.scenario}`);
    for (const e of r.errors) {
      console.log(`   Step ${e.step}: ${e.error}`);
      if (e.screenshot) console.log(`   📸 ${e.screenshot}`);
    }
  }

  process.exit(failed > 0 ? 1 : 0);
}

main().catch((err) => {
  console.error('Agent crashed:', err);
  process.exit(1);
});
