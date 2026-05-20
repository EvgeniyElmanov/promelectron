/**
 * Autonomous Agent — интеллектуальный execution loop v2
 * 
 * Агент может:
 * 1. Самостоятельно определять что делать на странице
 * 2. Адаптироваться к изменениям UI (fallback селекторы)
 * 3. Комбинировать UI + API проверки
 * 4. Запоминать и учиться от запуска к запуску
 * 5. Генерировать fuzz данные
 * 6. Запускать cross-role сценарии
 * 7. Измерять performance метрики
 * 8. Проверять accessibility
 * 9. Тестировать responsive layout
 */

import { personas, generateCredentials, generateFuzzData, generateCrossRoleCredentials } from './personas.js';
import { scenarios, getScenariosForPersona } from './scenarios.js';
import { MCPBridge } from './mcp-bridge.js';
import { VisionAnalyzer } from './vision.js';
import { AgentState } from './state.js';
import { ApiClient } from './api-client.js';

const BASE_URL = process.env.TEST_BASE_URL || 'https://promelectron-test.aidrivencode.ru';

/**
 * Fallback селекторы — если data-testid не найден, ищем по тексту
 */
const FALLBACK_SELECTORS = {
  'register-name': ['text=Имя'],
  'register-email': ['text=Email'],
  'register-password': ['text=Пароль'],
  'register-password-confirm': ['text=Подтвердите пароль'],
  'register-submit': ['text=Зарегистрироваться'],
  'login-email': ['text=Email'],
  'login-password': ['text=Пароль'],
  'login-submit': ['text=Войти'],
  'add-to-cart-button': ['text=В корзину'],
  'cart-link': ['text=Корзина'],
  'favorite-button': ['text=Избранное'],
  'checkout-button': ['text=Оформить заказ'],
  'product-card': ['text=Подробнее'],
  'search-bar': ['input[type="search"]'],
  'sort-select': ['text=Сортировка'],
  'category-chip': ['text=Категории'],
};

export class AutonomousAgent {
  constructor(options = {}) {
    this.mcp = new MCPBridge({ headless: options.headless !== false, debug: options.debug });
    this.vision = new VisionAnalyzer(options);
    this.state = new AgentState(options);
    this.api = new ApiClient(options);
    this.debug = options.debug || false;
    this.maxRetries = options.maxRetries || 3;
    this.stepDelay = options.stepDelay || 500;
    this.bugs = [];
    this.report = null;
    this.context = {}; // Для cross-role сценариев
  }

  async init() {
    await this.state.load();
    await this.vision.init();
    await this.mcp.connect();
    console.log('[Agent] Initialized and connected to MCP');
  }

  async cleanup() {
    await this.mcp.disconnect();
    await this.state.save();
  }

  // ═══════════════════════════════════════
  // Core execution
  // ═══════════════════════════════════════

  async runScenario(scenarioName, personaKey = 'user') {
    const persona = personas[personaKey];
    const scenario = scenarios[scenarioName];
    if (!scenario) throw new Error(`Unknown scenario: ${scenarioName}`);

    const session = this.state.startSession(personaKey, scenarioName);
    this.report = {
      id: session.id,
      scenario: scenarioName,
      persona: personaKey,
      startTime: new Date().toISOString(),
      steps: [],
      apiChecks: [],
      bugs: [],
      passed: true,
      performance: {},
    };

    console.log(`\n🚀 [${personaKey}] Running: ${scenarioName} (${scenario.length} steps)`);

    // Генерируем или получаем креды
    let credentials;
    if (scenarioName === 'endToEndPurchase' || scenarioName.startsWith('cross')) {
      credentials = generateCrossRoleCredentials();
      // Загружаем существующие admin креды
      const adminAccount = this.state.getAccount('admin');
      if (adminAccount) {
        credentials.admin_email = adminAccount.email;
        credentials.admin_password = adminAccount.password;
      }
    } else if (persona?.defaultCredentials) {
      credentials = persona.defaultCredentials;
    } else if (this.state.hasAccount(personaKey)) {
      credentials = this.state.getAccount(personaKey);
    } else {
      credentials = generateCredentials(persona || personas.user);
      this.state.setAccount(personaKey, credentials);
    }

    // Генерируем fuzz данные если нужно
    const fuzzData = generateFuzzData();

    let stepIndex = 0;
    for (const step of scenario) {
      stepIndex++;
      const result = await this.executeStep(step, { stepIndex, personaKey, credentials, fuzzData, scenarioName });
      this.report.steps.push({ step: stepIndex, action: step.action, result });

      if (!result.ok) {
        this.report.passed = false;
        const bug = {
          severity: step.action === 'api' ? 'critical' : 'major',
          message: result.error,
          step: stepIndex,
          action: step.action,
          url: await this.safeGetUrl(),
          persona: personaKey,
          scenario: scenarioName,
        };
        this.report.bugs.push(bug);
        this.state.addBug(bug);
        console.log(`   ❌ Step ${stepIndex} FAILED: ${result.error}`);
        break;
      } else {
        console.log(`   ✅ Step ${stepIndex} ${step.action}`);
      }

      if (this.stepDelay > 0) {
        await new Promise(r => setTimeout(r, this.stepDelay));
      }
    }

    // API проверки
    if (!scenarioName.startsWith('api')) {
      await this.runApiValidation(personaKey, scenarioName);
    }

    this.report.endTime = new Date().toISOString();
    this.state.endSession(session.id, { passed: this.report.passed, errors: this.report.bugs });

    return this.report;
  }

  async executeStep(step, context) {
    const { action } = step;
    const maxAttempts = this.maxRetries;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        const result = await this.tryExecuteAction(step, context);
        if (result.ok) return result;
        if (attempt === maxAttempts) return result;
        console.log(`   ⚠️ Retry ${attempt}/${maxAttempts} for ${action}`);
        await new Promise(r => setTimeout(r, 500));
      } catch (err) {
        if (attempt === maxAttempts) return { ok: false, error: err.message };
      }
    }

    return { ok: false, error: `Max retries exceeded for ${action}` };
  }

  async tryExecuteAction(step, context) {
    const { credentials, fuzzData, personaKey } = context;
    const { action, selector, value, target, expected, ms, script, name, type, method, path, body, as, storeToken, storeResult } = step;

    switch (action) {
      case 'navigate': {
        const url = target.startsWith('http') ? target : `${BASE_URL}${target}`;
        await this.mcp.navigate(url);
        await this.mcp.waitForLoadState('networkidle').catch(() => {});
        return { ok: true, url };
      }

      case 'click': {
        const sel = this.interpolate(selector, credentials, fuzzData);
        const resolved = await this.resolveSelector(sel, 'click');
        await this.mcp.click(resolved);
        return { ok: true, selector: resolved };
      }

      case 'fill': {
        const sel = this.interpolate(selector, credentials, fuzzData);
        const val = this.interpolate(value, credentials, fuzzData);
        const resolved = await this.resolveSelector(sel, 'fill');
        await this.mcp.fill(resolved, val);
        return { ok: true, selector: resolved, value: val };
      }

      case 'select': {
        const sel = this.interpolate(selector, credentials, fuzzData);
        const val = this.interpolate(value, credentials, fuzzData);
        const resolved = await this.resolveSelector(sel, 'select');
        await this.mcp.selectOption(resolved, val);
        return { ok: true, selector: resolved, value: val };
      }

      case 'wait': {
        await new Promise(r => setTimeout(r, ms || 1000));
        return { ok: true, ms };
      }

      case 'screenshot': {
        const fname = `${this.report.id}-step-${context.stepIndex}-${name || 'screenshot'}.png`;
        const result = await this.mcp.screenshot({ name: fname, saveAs: fname });
        return { ok: true, file: fname };
      }

      case 'evaluate': {
        let code = script;
        if (!code.trim().startsWith('()') && !code.trim().startsWith('function')) {
          code = `() => { ${code} }`;
        }
        const r = await this.mcp.evaluate(code);
        if (step.assert) {
          const val = r.result;
          if (step.assert.min !== undefined && val < step.assert.min) {
            return { ok: false, error: `Evaluate result ${val} < min ${step.assert.min}` };
          }
          if (step.assert.max !== undefined && val > step.assert.max) {
            return { ok: false, error: `Evaluate result ${val} > max ${step.assert.max}` };
          }
        }
        return { ok: true, result: r.result };
      }

      case 'login': {
        const p = personas[step.persona || personaKey];
        const creds = p?.defaultCredentials || credentials;
        await this.mcp.navigate(`${BASE_URL}/login`);
        await this.mcp.waitForLoadState('networkidle').catch(() => {});
        
        const emailSel = await this.resolveSelector('[data-testid="login-email"]', 'fill');
        const passSel = await this.resolveSelector('[data-testid="login-password"]', 'fill');
        const submitSel = await this.resolveSelector('[data-testid="login-submit"]', 'click');
        
        await this.mcp.fill(emailSel, creds.email);
        await this.mcp.fill(passSel, creds.password);
        await this.mcp.click(submitSel);
        await new Promise(r => setTimeout(r, 1000));
        
        const url = await this.safeGetUrl();
        if (url.includes('/login')) {
          return { ok: false, error: 'Login failed — still on login page' };
        }
        
        const apiResult = await this.api.login(creds);
        if (apiResult.ok) {
          this.state.setAccount(step.persona || personaKey, {
            ...creds,
            token: apiResult.data.access_token,
          });
        }
        
        return { ok: true, email: creds.email };
      }

      case 'assert': {
        return this.executeAssertion({ type, selector, expected }, credentials, fuzzData);
      }

      case 'api': {
        const apiPath = this.interpolate(path, credentials, fuzzData);
        const apiBody = body ? JSON.parse(this.interpolate(JSON.stringify(body), credentials, fuzzData)) : undefined;
        const role = as || 'anonymous';
        
        const result = await this.api.request(method, apiPath, { body: apiBody, as: role });
        
        // Сохраняем токен
        if (storeToken && result.ok && result.data?.access_token) {
          this.api.setToken(storeToken, result.data.access_token);
          this.context[`${storeToken}_token`] = result.data.access_token;
        }
        
        // Сохраняем результат
        if (storeResult) {
          this.context[storeResult] = result.data;
        }
        
        // Подставляем context переменные в path для следующих шагов
        if (result.data?.id) {
          this.context[`${storeResult}_id`] = result.data.id;
        }
        
        // Валидация
        if (expected) {
          if (expected.status) {
            const allowedStatuses = Array.isArray(expected.status) ? expected.status : [expected.status];
            if (!allowedStatuses.includes(result.status)) {
              return { ok: false, error: `API ${method} ${apiPath}: expected ${allowedStatuses.join('|')}, got ${result.status}` };
            }
          }
          if (expected.duration?.max && result.duration > expected.duration.max) {
            return { ok: false, error: `API ${method} ${apiPath}: duration ${result.duration}ms > max ${expected.duration.max}ms` };
          }
          if (expected.arrayMinLength !== undefined) {
            const arr = Array.isArray(result.data) ? result.data : result.data?.items || [];
            if (!arr || arr.length < expected.arrayMinLength) {
              return { ok: false, error: `API ${method} ${apiPath}: array length ${arr?.length || 0} < min ${expected.arrayMinLength}` };
            }
          }
        }
        
        return { ok: true, status: result.status, duration: result.duration, data: result.data };
      }

      default:
        return { ok: false, error: `Unknown action: ${action}` };
    }
  }

  // ═══════════════════════════════════════
  // Selector resolution with fallback
  // ═══════════════════════════════════════

  async resolveSelector(selector, actionType) {
    if (!selector) return selector;
    if (selector.includes('data-testid')) {
      const testId = selector.match(/data-testid="([^"]+)"/)?.[1];
      if (testId && FALLBACK_SELECTORS[testId]) {
        const visible = await this.mcp.isElementVisible(selector);
        if (!visible) {
          for (const fallback of FALLBACK_SELECTORS[testId]) {
            const isVis = await this.mcp.isElementVisible(fallback);
            if (isVis) {
              if (this.debug) console.log(`   [Selector] Fallback: ${selector} → ${fallback}`);
              return fallback;
            }
          }
          const byText = await this.vision.findSelector(this.mcp, testId);
          if (byText && byText.length > 0 && byText[0].selector) {
            return byText[0].selector;
          }
        }
      }
    }
    return selector;
  }

  // ═══════════════════════════════════════
  // Assertion engine
  // ═══════════════════════════════════════

  async executeAssertion({ type, selector, expected }, credentials, fuzzData) {
    switch (type) {
      case 'url': {
        const url = await this.safeGetUrl();
        if (expected.startsWith('http')) {
          if (url !== expected) return { ok: false, error: `URL mismatch: ${url} !== ${expected}` };
        } else if (!url.includes(expected)) {
          return { ok: false, error: `URL mismatch: ${url} does not include ${expected}` };
        }
        return { ok: true, url };
      }

      case 'element': {
        const sel = this.interpolate(selector, credentials, fuzzData);
        const resolved = await this.resolveSelector(sel, 'assert');
        const visible = await this.mcp.isElementVisible(resolved);
        if (!visible) {
          return { ok: false, error: `Element not visible: ${resolved}` };
        }
        return { ok: true, selector: resolved };
      }

      case 'text': {
        const sel = selector === 'body' ? 'body' : this.interpolate(selector, credentials, fuzzData);
        const r = await this.mcp.evaluate(`() => {
          const el = document.querySelector('${sel.replace(/'/g, "\\'")}');
          return (el ? el.innerText : document.body.innerText) || '';
        }`);
        const text = (r.result || '').toLowerCase();
        if (!text.includes(expected.toLowerCase())) {
          return { ok: false, error: `Text "${expected}" not found in ${sel}` };
        }
        return { ok: true, found: true };
      }

      case 'toast': {
        await new Promise(r => setTimeout(r, 500));
        const r = await this.mcp.evaluate(`() => {
          return document.body.innerText.includes('${expected.replace(/'/g, "\\'")}');
        }`);
        if (!r.result) {
          return { ok: false, error: `Toast "${expected}" not found` };
        }
        return { ok: true, found: true };
      }

      case 'evaluate': {
        const r = await this.mcp.evaluate(`() => { return ${expected}; }`);
        if (!r.result) {
          return { ok: false, error: `Evaluate assertion failed` };
        }
        return { ok: true, result: r.result };
      }

      default:
        return { ok: false, error: `Unknown assertion type: ${type}` };
    }
  }

  // ═══════════════════════════════════════
  // API validation at scenario end
  // ═══════════════════════════════════════

  async runApiValidation(personaKey, scenarioName) {
    const checks = [];

    const health = await this.api.health();
    checks.push({ name: 'health', ...health });

    if (scenarioName === 'fullPurchaseFlow' || scenarioName === 'searchAndFilter') {
      const products = await this.api.getProducts({ skip: 0, limit: 10 });
      checks.push({ name: 'products_list', ...products });
    }

    if (scenarioName === 'supplierAddProduct' || scenarioName === 'supplierEditProduct') {
      const me = await this.api.getMe('supplier');
      checks.push({ name: 'supplier_me', ...me });
    }

    if (scenarioName === 'adminCategoryManagement') {
      const cats = await this.api.getCategories();
      checks.push({ name: 'categories', ...cats });
    }

    if (scenarioName === 'userProfileFlow') {
      const me = await this.api.getMe('user');
      checks.push({ name: 'user_me', ...me });
    }

    if (scenarioName === 'userOrdersFlow') {
      const orders = await this.api.getOrders('user');
      checks.push({ name: 'user_orders', ...orders });
    }

    if (scenarioName === 'adminOrderManagement') {
      const orders = await this.api.getAdminOrders('admin');
      checks.push({ name: 'admin_orders', ...orders });
    }

    if (scenarioName === 'adminDashboardStats') {
      const stats = await this.api.getAdminStats('admin');
      checks.push({ name: 'admin_stats', ...stats });
    }

    for (const check of checks) {
      const validation = this.validateApiCheck(check);
      this.report.apiChecks.push({ ...check, validation });
      if (!validation.valid) {
        const bug = {
          severity: check.status >= 500 ? 'critical' : 'major',
          message: `API ${check.name}: ${validation.issues.join(', ')}`,
          step: 'api_validation',
          action: 'api_check',
          url: check.name,
          persona: personaKey,
          scenario: scenarioName,
        };
        this.report.bugs.push(bug);
        this.state.addBug(bug);
      }
    }
  }

  validateApiCheck(check) {
    const issues = [];
    if (!check.ok && check.status !== 0) {
      issues.push(`HTTP ${check.status} ${check.statusText || ''}`);
    }
    if (check.status === 0) {
      issues.push(`Network error: ${check.error}`);
    }
    return { valid: issues.length === 0, issues };
  }

  // ═══════════════════════════════════════
  // Autonomous discovery mode
  // ═══════════════════════════════════════

  async discover(personaKey = 'user', maxSteps = 20) {
    const session = this.state.startSession(personaKey, 'discover');
    this.report = {
      id: session.id,
      scenario: 'discover',
      persona: personaKey,
      startTime: new Date().toISOString(),
      steps: [],
      bugs: [],
      passed: true,
      performance: {},
    };

    console.log(`\n🔍 [${personaKey}] Discovery mode — ${maxSteps} steps`);

    await this.mcp.navigate(BASE_URL);
    await this.mcp.waitForLoadState('networkidle').catch(() => {});

    const visitedUrls = new Set();

    for (let i = 0; i < maxSteps; i++) {
      const analysis = await this.vision.analyzePage(this.mcp);
      console.log(`   Step ${i + 1}: ${analysis.pageType} | ${analysis.url || ''}`);

      // Проверяем консольные ошибки
      const logs = await this.mcp.getConsoleLogs();
      if (logs && logs.includes('error')) {
        const bug = {
          severity: 'minor',
          message: `Console error detected on ${analysis.pageType}`,
          step: i + 1,
          action: 'discover',
          url: analysis.url,
          persona: personaKey,
          scenario: 'discover',
        };
        this.report.bugs.push(bug);
        this.state.addBug(bug);
      }

      if (analysis.pageType === 'error') {
        const bug = {
          severity: 'critical',
          message: `Error page detected: ${analysis.url}`,
          step: i + 1,
          action: 'discover',
          url: analysis.url,
          persona: personaKey,
          scenario: 'discover',
        };
        this.report.bugs.push(bug);
        this.state.addBug(bug);
      }

      // Performance snapshot
      if (i === 0) {
        try {
          const perf = await this.mcp.evaluate(`() => {
            const nav = performance.getEntriesByType('navigation')[0];
            return { loadTime: nav?.loadEventEnd || 0, fcp: nav?.domContentLoadedEventEnd || 0 };
          }`);
          if (perf.result) {
            this.report.performance = { ...this.report.performance, ...perf.result };
          }
        } catch {
          // ignore
        }
      }

      const elements = Array.isArray(analysis.elements) ? analysis.elements : [];
      const links = elements.filter(e => e.tag === 'a' && e.href && !e.href.includes('#') && !visitedUrls.has(e.href));
      
      if (links.length > 0) {
        const random = links[Math.floor(Math.random() * links.length)];
        visitedUrls.add(random.href);
        try {
          await this.mcp.click(random.selector || random.tag || 'a');
          await new Promise(r => setTimeout(r, 1000));
        } catch {
          break;
        }
      } else {
        break;
      }
    }

    this.report.endTime = new Date().toISOString();
    this.state.endSession(session.id, { passed: this.report.bugs.length === 0, errors: this.report.bugs });
    return this.report;
  }

  // ═══════════════════════════════════════
  // Performance testing
  // ═══════════════════════════════════════

  async measurePerformance(url) {
    const startTime = Date.now();
    await this.mcp.navigate(url);
    const navigationTime = Date.now() - startTime;
    
    await this.mcp.waitForLoadState('networkidle').catch(() => {});
    const loadTime = Date.now() - startTime;
    
    // Ждём немного для стабилизации метрик
    await new Promise(r => setTimeout(r, 1000));

    const metrics = await this.mcp.evaluate(`() => {
      try {
        const timing = performance.timing;
        const now = performance.now();
        const navStart = timing.navigationStart || 0;
        
        // Базовые метрики из timing API
        const ttfb = timing.responseStart ? timing.responseStart - navStart : 0;
        const domContentLoaded = timing.domContentLoadedEventEnd ? timing.domContentLoadedEventEnd - navStart : 0;
        const loadComplete = timing.loadEventEnd ? timing.loadEventEnd - navStart : 0;
        
        // Paint метрики
        const paintEntries = performance.getEntriesByType('paint');
        const fcpEntry = paintEntries.find(e => e.name === 'first-contentful-paint');
        const fcp = fcpEntry ? Math.round(fcpEntry.startTime) : 0;
        
        // LCP из PerformanceObserver (если доступен)
        let lcp = 0;
        try {
          const lcpEntries = performance.getEntriesByType('largest-contentful-paint');
          if (lcpEntries.length > 0) {
            lcp = Math.round(lcpEntries[lcpEntries.length - 1].startTime);
          }
        } catch(e) { /* ignore */ }
        
        // CLS
        let cls = 0;
        try {
          const layoutShifts = performance.getEntriesByType('layout-shift').filter(e => !e.hadRecentInput);
          cls = Math.round(layoutShifts.reduce((sum, e) => sum + e.value, 0) * 1000) / 1000;
        } catch(e) { /* ignore */ }
        
        // Resource count
        const resources = performance.getEntriesByType('resource');
        
        return {
          url: window.location.href,
          ttfb,
          fcp,
          lcp,
          cls,
          domContentLoaded,
          loadComplete,
          resourceCount: resources.length,
          totalSize: Math.round(resources.reduce((sum, r) => sum + (r.transferSize || 0), 0) / 1024),
        };
      } catch(e) {
        return { error: e.message, url: window.location.href };
      }
    }`);

    return metrics.result || { url, navigationTime, loadTime };
  }

  // ═══════════════════════════════════════
  // Accessibility testing
  // ═══════════════════════════════════════

  async checkAccessibility(url) {
    await this.mcp.navigate(url);
    await this.mcp.waitForLoadState('networkidle').catch(() => {});

    const checks = await this.mcp.evaluate(`() => {
      const results = {
        imagesWithoutAlt: 0,
        missingAriaLabels: 0,
        lowContrastElements: 0,
        missingFormLabels: 0,
        focusableWithoutOutline: 0,
        headings: { h1: 0, h2: 0, h3: 0, h4: 0 },
        landmarks: { main: 0, nav: 0, aside: 0, footer: 0, header: 0 },
        totalImages: 0,
        totalLinks: 0,
        totalButtons: 0,
        lang: document.documentElement.lang || 'missing',
        title: document.title || 'missing',
      };

      // Images
      document.querySelectorAll('img').forEach(img => {
        results.totalImages++;
        if (!img.alt && !img.ariaLabel) results.imagesWithoutAlt++;
      });

      // Headings
      document.querySelectorAll('h1, h2, h3, h4').forEach(h => {
        results.headings[h.tagName.toLowerCase()]++;
      });

      // Landmarks
      document.querySelectorAll('main, nav, aside, footer, header, [role="main"], [role="navigation"]').forEach(el => {
        const role = el.getAttribute('role') || el.tagName.toLowerCase();
        if (results.landmarks[role] !== undefined) results.landmarks[role]++;
      });

      // Form labels
      document.querySelectorAll('input, select, textarea').forEach(input => {
        const id = input.id;
        const ariaLabel = input.getAttribute('aria-label');
        const ariaLabelledBy = input.getAttribute('aria-labelledby');
        const hasLabel = id && document.querySelector('label[for="' + id + '"]');
        const placeholder = input.placeholder;
        if (!hasLabel && !ariaLabel && !ariaLabelledBy && !placeholder) {
          results.missingFormLabels++;
        }
      });

      // Focusable elements
      document.querySelectorAll('a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])').forEach(el => {
        const style = window.getComputedStyle(el);
        if (style.outlineStyle === 'none' && style.boxShadow === 'none') {
          results.focusableWithoutOutline++;
        }
      });

      // Links and buttons
      results.totalLinks = document.querySelectorAll('a').length;
      results.totalButtons = document.querySelectorAll('button').length;

      return results;
    }`);

    return checks.result || {};
  }

  // ═══════════════════════════════════════
  // Responsive testing
  // ═══════════════════════════════════════

  async testResponsive(url) {
    const viewports = [
      { name: 'mobile', width: 375, height: 812 },
      { name: 'tablet', width: 768, height: 1024 },
      { name: 'desktop', width: 1440, height: 900 },
    ];

    const results = [];
    for (const vp of viewports) {
      await this.mcp.setViewport(vp.width, vp.height);
      await this.mcp.navigate(url);
      await this.mcp.waitForLoadState('networkidle').catch(() => {});
      await new Promise(r => setTimeout(r, 1000));

      const screenshot = await this.mcp.screenshot({ name: `responsive-${vp.name}`, saveAs: `responsive-${vp.name}.png` });
      
      const scrollCheck = await this.mcp.evaluate(`() => {
        return {
          hasHorizontalScroll: document.documentElement.scrollWidth > window.innerWidth,
          hasVerticalScroll: document.documentElement.scrollHeight > window.innerHeight,
          viewportWidth: window.innerWidth,
          viewportHeight: window.innerHeight,
        };
      }`);

      results.push({
        viewport: vp.name,
        dimensions: `${vp.width}x${vp.height}`,
        hasHorizontalScroll: scrollCheck.result?.hasHorizontalScroll,
        screenshot: screenshot.text,
      });
    }

    return results;
  }

  // ═══════════════════════════════════════
  // Utilities
  // ═══════════════════════════════════════

  interpolate(value, credentials, fuzzData) {
    if (typeof value !== 'string') return value;
    let result = value;
    
    // Стандартные переменные
    if (credentials) {
      result = result
        .replace(/\{\{email\}\}/g, credentials.email || '')
        .replace(/\{\{password\}\}/g, credentials.password || '')
        .replace(/\{\{name\}\}/g, credentials.name || '')
        .replace(/\{\{admin_email\}\}/g, credentials.admin_email || '')
        .replace(/\{\{admin_password\}\}/g, credentials.admin_password || '')
        .replace(/\{\{supplier_email\}\}/g, credentials.supplier_email || '')
        .replace(/\{\{user_email\}\}/g, credentials.user_email || '');
    }
    
    // Fuzz данные
    if (fuzzData) {
      for (const [key, val] of Object.entries(fuzzData)) {
        result = result.replace(new RegExp(`\\{\\{${key}\\}\\}`, 'g'), val);
      }
    }
    
    // Context переменные (из cross-role сценариев)
    for (const [key, val] of Object.entries(this.context)) {
      if (typeof val === 'string' || typeof val === 'number') {
        result = result.replace(new RegExp(`\\{\\{${key}\\}\\}`, 'g'), String(val));
      }
    }
    
    // Random
    result = result.replace(/\{\{random\}\}/g, Date.now().toString());
    
    return result;
  }

  async safeGetUrl() {
    try {
      return await this.mcp.getUrl();
    } catch {
      return '';
    }
  }
}
