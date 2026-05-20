/**
 * Vision Layer — анализ UI через скриншоты + LLM Vision API
 * 
 * При наличии OPENAI_API_KEY или ANTHROPIC_API_KEY использует vision model.
 * Иначе — эвристический анализ через accessibility tree + DOM evaluation.
 */

import { promises as fs } from 'fs';
import { createRequire } from 'module';

const require = createRequire(import.meta.url);

export class VisionAnalyzer {
  constructor(options = {}) {
    this.provider = options.provider || process.env.VISION_PROVIDER || 'heuristic';
    this.model = options.model || process.env.VISION_MODEL || 'gpt-4o';
    this.apiKey = options.apiKey || process.env.OPENAI_API_KEY || process.env.ANTHROPIC_API_KEY;
    this.debug = options.debug || false;
    this.llm = null;
  }

  async init() {
    if (this.provider === 'openai' && this.apiKey) {
      try {
        const { OpenAI } = require('openai');
        this.llm = new OpenAI({ apiKey: this.apiKey });
      } catch (e) {
        console.warn('[Vision] OpenAI SDK not available, falling back to heuristic');
        this.provider = 'heuristic';
      }
    }
  }

  /**
   * Анализ скриншота — найти элементы, понять состояние страницы
   */
  async analyzePage(mcpBridge, prompt = 'What do you see on this page? List all interactive elements.') {
    // Делаем скриншот
    const screenshot = await mcpBridge.screenshot({ name: 'analysis' });
    const imageBase64 = screenshot.image?.data;

    if (!imageBase64) {
      // Fallback: accessibility tree
      return this.analyzeViaAccessibility(mcpBridge);
    }

    if (this.provider === 'openai' && this.llm) {
      return this.analyzeWithOpenAI(imageBase64, prompt);
    }

    // Heuristic analysis
    return this.analyzeViaHeuristics(mcpBridge, imageBase64);
  }

  async analyzeWithOpenAI(imageBase64, prompt) {
    const response = await this.llm.chat.completions.create({
      model: this.model,
      messages: [
        {
          role: 'system',
          content: `You are a QA automation engineer analyzing a web page screenshot.
Respond with a structured JSON object containing:
- pageType: (login|register|homepage|product_list|product_detail|cart|checkout|admin_dashboard|error|other)
- title: page title or heading
- elements: array of interactive elements { type, text, approximate_location, confidence }
- issues: array of potential UI issues
- nextActions: array of possible next actions
Respond ONLY with valid JSON.`,
        },
        {
          role: 'user',
          content: [
            { type: 'text', text: prompt },
            { type: 'image_url', image_url: { url: `data:image/png;base64,${imageBase64}` } },
          ],
        },
      ],
      max_tokens: 2000,
    });

    const text = response.choices[0].message.content;
    return this.parseJSONResponse(text);
  }

  async analyzeViaAccessibility(mcpBridge) {
    const snapshot = await mcpBridge.getPageContent();
    const url = await mcpBridge.getUrl();

    return {
      pageType: this.guessPageType(url, snapshot),
      url,
      elements: this.extractElementsFromSnapshot(snapshot),
      text: snapshot.slice(0, 2000),
      source: 'accessibility',
    };
  }

  async analyzeViaHeuristics(mcpBridge, imageBase64) {
    // Комбинируем DOM analysis + snapshot
    const [snapshot, url, interactive] = await Promise.all([
      mcpBridge.getPageContent(),
      mcpBridge.getUrl(),
      mcpBridge.evaluate(`
        Array.from(document.querySelectorAll('button, a, input, select, textarea, [role="button"], [onclick]'))
          .filter(el => el.offsetParent !== null)
          .map(el => ({
            tag: el.tagName.toLowerCase(),
            text: (el.innerText || el.value || el.placeholder || el.title || '').trim().slice(0,50),
            id: el.id,
            class: el.className?.slice(0,50),
            type: el.type,
            href: el.href,
            rect: el.getBoundingClientRect ? { x: el.getBoundingClientRect().x, y: el.getBoundingClientRect().y, w: el.getBoundingClientRect().width, h: el.getBoundingClientRect().height } : null
          }))
          .slice(0, 50)
      `),
    ]);

    return {
      pageType: this.guessPageType(url, snapshot),
      url,
      elements: interactive.result || [],
      text: snapshot.slice(0, 2000),
      source: 'heuristic',
    };
  }

  guessPageType(url, snapshot) {
    const lower = (url + ' ' + snapshot).toLowerCase();
    if (lower.includes('login') || lower.includes('вход') || lower.includes('sign in')) return 'login';
    if (lower.includes('register') || lower.includes('регистрация') || lower.includes('sign up')) return 'register';
    if (lower.includes('/admin')) return 'admin_dashboard';
    if (lower.includes('/product/') || lower.includes('товар') || lower.includes('product detail')) return 'product_detail';
    if (lower.includes('/cart') || lower.includes('корзина')) return 'cart';
    if (lower.includes('/checkout') || lower.includes('оформление')) return 'checkout';
    if (lower.includes('/orders') || lower.includes('заказы')) return 'orders';
    if (lower.includes('/my-products') || lower.includes('мои товары')) return 'supplier_dashboard';
    if (lower.includes('популярные товары') || lower.includes('catalog') || (lower.includes('/products') && !lower.includes('/product/'))) return 'product_list';
    if (lower.includes('error') || lower.includes('ошибка') || lower.includes('404') || lower.includes('500')) return 'error';
    return 'other';
  }

  extractElementsFromSnapshot(snapshot) {
    const elements = [];
    const lines = snapshot.split('\n');
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      // Пытаемся распознать элементы из accessibility tree
      const match = trimmed.match(/^(\[?\w+\]?\s*)+(.*)/);
      if (match) {
        elements.push({ text: trimmed, type: 'unknown' });
      }
    }
    return elements;
  }

  parseJSONResponse(text) {
    try {
      // Убираем markdown code blocks
      const clean = text.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
      return JSON.parse(clean);
    } catch (e) {
      return {
        pageType: 'unknown',
        error: 'Failed to parse vision response',
        raw: text,
      };
    }
  }

  /**
   * Найти CSS селектор для элемента по тексту
   */
  async findSelector(mcpBridge, text) {
    const r = await mcpBridge.evaluate(`
      (function() {
        const keywords = ['${text.toLowerCase().replace(/'/g, "\\'")}'];
        const results = [];
        for (const keyword of keywords) {
          // Ищем по точному совпадению
          let els = Array.from(document.querySelectorAll('button, a, input[type="submit"], [role="button"], label'));
          for (const el of els) {
            const txt = (el.innerText || el.value || el.placeholder || el.title || '').toLowerCase().trim();
            if (txt.includes(keyword)) {
              const selector = el.id ? '#' + el.id : 
                el.className ? el.tagName.toLowerCase() + '.' + el.className.split(' ').join('.') :
                el.tagName.toLowerCase();
              results.push({ selector, text: txt, tag: el.tagName.toLowerCase(), exact: txt === keyword });
            }
          }
          // Ищем по data-testid
          els = document.querySelectorAll('[data-testid*="' + keyword.replace(/"/g, '\\"') + '"]');
          for (const el of els) {
            results.push({ selector: '[data-testid="' + el.getAttribute('data-testid') + '"]', text: keyword, tag: el.tagName.toLowerCase(), exact: true });
          }
        }
        // Сортируем: exact match first, then by tag priority
        const priority = { button: 1, a: 2, input: 3, label: 4 };
        results.sort((a, b) => {
          if (a.exact !== b.exact) return a.exact ? -1 : 1;
          return (priority[a.tag] || 99) - (priority[b.tag] || 99);
        });
        return results.slice(0, 5);
      })()
    `);
    return r.result || [];
  }

  /**
   * Определить следующее действие на основе анализа страницы
   */
  async decideNextAction(mcpBridge, goal, previousActions = []) {
    const analysis = await this.analyzePage(mcpBridge, `Goal: ${goal}. What should I do next?`);

    // Простой rule-based decision engine
    const pageType = analysis.pageType;
    const elements = analysis.elements || [];

    // Если цель — залогиниться и мы на login page
    if (goal.toLowerCase().includes('login') && pageType === 'login') {
      return { action: 'fill_credentials', fields: { email: '[data-testid="login-email"]', password: '[data-testid="login-password"]' } };
    }

    // Если цель — зарегистрироваться и мы на register page
    if (goal.toLowerCase().includes('register') && pageType === 'register') {
      return { action: 'fill_registration' };
    }

    // Если цель — добавить в корзину и мы на product page
    if (goal.toLowerCase().includes('cart') && pageType === 'product_detail') {
      const btn = elements.find(e => e.text?.toLowerCase().includes('корзин') || e.text?.toLowerCase().includes('cart'));
      if (btn) return { action: 'click', selector: btn.selector || `[data-testid="add-to-cart-button"]` };
    }

    // Если цель — купить и мы на cart page
    if (goal.toLowerCase().includes('checkout') && pageType === 'cart') {
      const btn = elements.find(e => e.text?.toLowerCase().includes('оформ') || e.text?.toLowerCase().includes('checkout'));
      if (btn) return { action: 'click', selector: btn.selector || `[data-testid="checkout-button"]` };
    }

    // Generic: ищем кнопку/ссылку которая приближает нас к цели
    const goalKeywords = goal.toLowerCase().split(' ');
    for (const el of elements) {
      const txt = (el.text || '').toLowerCase();
      if (goalKeywords.some(k => txt.includes(k))) {
        return { action: 'click', selector: el.selector || el.tag || 'body' };
      }
    }

    return { action: 'analyze', pageType, analysis };
  }
}
