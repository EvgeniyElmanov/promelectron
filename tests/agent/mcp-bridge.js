/**
 * MCP Bridge — реальное подключение к Playwright MCP серверу через stdio
 * Использует @modelcontextprotocol/sdk Client + StdioClientTransport
 */

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MCP_SERVER_PATH = join(__dirname, '../../node_modules/.bin/playwright-mcp');
const MCP_SERVER_COMMAND = process.platform === 'win32' ? 'node' : MCP_SERVER_PATH;
const MCP_SERVER_ARGS = process.platform === 'win32'
  ? [MCP_SERVER_PATH, '--headless', '--browser', 'chromium']
  : ['--headless', '--browser', 'chromium'];

// Playwright MCP tool names (не playwright_navigate, а browser_navigate!)
const TOOLS = {
  navigate: 'browser_navigate',
  click: 'browser_click',
  fill: 'browser_type',
  selectOption: 'browser_select_option',
  hover: 'browser_hover',
  screenshot: 'browser_take_screenshot',
  evaluate: 'browser_evaluate',
  consoleMessages: 'browser_console_messages',
  waitFor: 'browser_wait_for',
  close: 'browser_close',
  resize: 'browser_resize',
  snapshot: 'browser_snapshot',
  tabs: 'browser_tabs',
  pressKey: 'browser_press_key',
  drag: 'browser_drag',
  drop: 'browser_drop',
  fileUpload: 'browser_file_upload',
  fillForm: 'browser_fill_form',
  networkRequests: 'browser_network_requests',
  handleDialog: 'browser_handle_dialog',
  runCode: 'browser_run_code_unsafe',
};

export class MCPBridge {
  constructor(options = {}) {
    this.client = null;
    this.transport = null;
    this.tools = new Map();
    this.connected = false;
    this.headless = options.headless !== false;
    this.debug = options.debug || false;
    this.screenshots = [];
  }

  async connect() {
    if (this.connected) return;

    this.transport = new StdioClientTransport({
      command: MCP_SERVER_COMMAND,
      args: this.headless ? MCP_SERVER_ARGS : ['@playwright/mcp@latest'],
      env: {
        PLAYWRIGHT_HEADLESS: this.headless ? 'true' : 'false',
      },
    });

    this.client = new Client({ name: 'autonomous-tester', version: '1.0.0' });
    await this.client.connect(this.transport);
    this.connected = true;

    // Кэшируем список инструментов
    const toolsList = await this.client.listTools();
    for (const tool of toolsList.tools || []) {
      this.tools.set(tool.name, tool);
    }

    if (this.debug) {
      console.log(`[MCP] Connected. ${this.tools.size} tools available.`);
    }
  }

  async disconnect() {
    if (!this.connected) return;
    try {
      await this.callTool(TOOLS.close, {});
    } catch {
      // ignore
    }
    await this.client.close();
    this.connected = false;
    this.client = null;
    this.transport = null;
    this.tools.clear();
  }

  _extractText(raw) {
    if (typeof raw === 'string') return raw;
    if (raw && typeof raw.text === 'string') return raw.text;
    if (raw && Array.isArray(raw.content)) {
      return raw.content.map((item) => (item.type === 'text' ? item.text || '' : '')).join('');
    }
    return '';
  }

  async callTool(name, args = {}) {
    if (!this.connected) throw new Error('MCP not connected');
    if (this.debug) {
      console.log(`[MCP] callTool(${name})`, JSON.stringify(args).slice(0, 200));
    }

    const rawResult = await this.client.callTool({ name, arguments: args });

    // Извлекаем контент из результата (robust для разных версий MCP)
    const text = this._extractText(rawResult);
    let image = null;
    if (rawResult.content) {
      for (const item of rawResult.content) {
        if (item.type === 'image') image = item;
      }
    }

    const wrapped = { result: rawResult, text, image };
    if (this.debug) {
      console.log(`[MCP] callTool(${name}) text length:`, text.length, 'result keys:', Object.keys(rawResult).join(','));
    }
    if (rawResult.isError) {
      const errText = text.replace(/^### Error\n?/, '').trim() || 'Unknown MCP error';
      throw new Error(`MCP tool ${name} failed: ${errText}`);
    }
    return wrapped;
  }

  // ═══════════════════════════════════════
  // Playwright helpers
  // ═══════════════════════════════════════

  async navigate(url) {
    return this.callTool(TOOLS.navigate, { url });
  }

  async click(selector, options = {}) {
    return this.callTool(TOOLS.click, { target: selector, element: selector, ...options });
  }

  async fill(selector, value, options = {}) {
    return this.callTool(TOOLS.fill, { target: selector, element: selector, text: value, ...options });
  }

  async selectOption(selector, value) {
    return this.callTool(TOOLS.selectOption, { target: selector, element: selector, value });
  }

  async hover(selector) {
    return this.callTool(TOOLS.hover, { target: selector, element: selector });
  }

  async screenshot({ name = 'screenshot', saveAs = null, fullPage = false, width = null, height = null } = {}) {
    const args = {};
    if (saveAs) args.save_as = saveAs;
    if (fullPage) args.fullPage = true;
    if (width && height) {
      args.width = width;
      args.height = height;
    }

    const result = await this.callTool(TOOLS.screenshot, args);
    if (result.image) {
      this.screenshots.push({ name, data: result.image.data, mimeType: result.image.mimeType });
    }
    return result;
  }

  async getUrl() {
    // Method 1: try snapshot
    const r = await this.callTool(TOOLS.snapshot, {});
    let text = r.text || '';
    if (!text && r.result) {
      text = this._extractText(r.result);
    }
    const match = text.match(/Page URL:\s*(.+)/m);
    if (match) return match[1].trim();

    // Method 2: fallback to evaluate
    try {
      const r2 = await this.evaluate("() => window.location.href");
      if (typeof r2.result === 'string') return r2.result;
      if (typeof r2.result === 'number') return String(r2.result);
      return String(r2.result || '');
    } catch {
      return '';
    }
  }

  async getPageContent() {
    const r = await this.callTool(TOOLS.snapshot, {});
    return r.text || this._extractText(r.result) || '';
  }

  async evaluate(code) {
    const r = await this.callTool(TOOLS.evaluate, { function: code });
    // Парсим результат из текстового ответа Playwright MCP
    let text = r.text || '';

    // Fallback: если text пустой, попробуем извлечь из raw result
    if (!text && r.result) {
      text = this._extractText(r.result);
    }

    if (this.debug) {
      console.log(`[MCP] evaluate text length:`, text.length, 'first 100:', text.slice(0, 100));
    }

    // Ищем блок между "### Result" и "### Ran Playwright code"
    const resultMatch = text.match(/### Result\n([\s\S]*?)(?:\n### Ran Playwright code|$)/);
    if (resultMatch) {
      const raw = resultMatch[1].trim();

      // Пытаемся распарсить как JSON
      if (raw.startsWith('{') || raw.startsWith('[')) {
        try {
          r.result = JSON.parse(raw);
        } catch {
          r.result = raw;
        }
      } else if (raw.startsWith('"') && raw.endsWith('"')) {
        try {
          r.result = JSON.parse(raw);
        } catch {
          r.result = raw.slice(1, -1);
        }
      } else if (raw === 'true') {
        r.result = true;
      } else if (raw === 'false') {
        r.result = false;
      } else if (raw === 'null') {
        r.result = null;
      } else if (!isNaN(Number(raw)) && raw !== '') {
        r.result = Number(raw);
      } else if (raw.startsWith('undefined')) {
        r.result = undefined;
      } else {
        r.result = raw;
      }
    } else {
      // Fallback: простое значение в одну строку
      const simpleMatch = text.match(/### Result\s*\n(.+)/);
      if (simpleMatch) {
        const raw = simpleMatch[1].trim();
        if (raw === 'true') r.result = true;
        else if (raw === 'false') r.result = false;
        else if (!isNaN(Number(raw))) r.result = Number(raw);
        else r.result = raw;
      } else if (text) {
        // No "### Result" header but some text — maybe plain JSON
        const trimmed = text.trim();
        if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
          try { r.result = JSON.parse(trimmed); } catch { r.result = trimmed; }
        } else if (trimmed.startsWith('"') && trimmed.endsWith('"')) {
          try { r.result = JSON.parse(trimmed); } catch { r.result = trimmed.slice(1, -1); }
        } else {
          r.result = trimmed;
        }
      }
    }
    return r;
  }

  async getConsoleLogs() {
    try {
      const r = await this.callTool(TOOLS.consoleMessages, {});
      return r.text || this._extractText(r.result) || '';
    } catch {
      return '';
    }
  }

  async pressKey(key) {
    return this.callTool(TOOLS.pressKey, { key });
  }

  async waitForSelector(selector, timeout = 5000) {
    return this.callTool(TOOLS.waitFor, { target: selector, element: selector, timeout, action: 'selector' });
  }

  async waitForLoadState(state = 'networkidle') {
    // browser_wait_for не поддерживает load state напрямую,
    // используем evaluate с ожиданием document.readyState
    const script = `
      new Promise(resolve => {
        if (document.readyState === 'complete') resolve('complete');
        else window.addEventListener('load', () => resolve('complete'));
      })
    `;
    return this.evaluate(script);
  }

  async setViewport(width, height) {
    return this.callTool(TOOLS.resize, { width, height });
  }

  async closeBrowser() {
    try {
      return this.callTool(TOOLS.close, {});
    } catch {
      // ignore
    }
  }

  async getAccessibilityTree() {
    try {
      const r = await this.callTool(TOOLS.snapshot, {});
      return r.text || this._extractText(r.result) || '';
    } catch {
      return '';
    }
  }

  async findElementByText(text, options = {}) {
    const script = `
      (function() {
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        const results = [];
        while (walker.nextNode()) {
          const node = walker.currentNode;
          if (node.textContent.trim().includes('${text.replace(/'/g, "\\'")}')) {
            const el = node.parentElement;
            const tag = el.tagName.toLowerCase();
            const id = el.id ? '#' + el.id : '';
            const cls = el.className && typeof el.className === 'string' ? '.' + el.className.split(' ').slice(0,2).join('.') : '';
            const clickable = ['button','a','input','select','textarea','label'].includes(tag) || el.onclick !== null;
            results.push({ tag, id, cls, clickable, text: el.textContent.trim().slice(0,100) });
          }
        }
        return results.slice(0, 10);
      })()
    `;
    const r = await this.evaluate(script);
    return r.result || [];
  }

  async isElementVisible(selector) {
    try {
      const r = await this.evaluate(`
        const el = document.querySelector('${selector.replace(/'/g, "\\'")}');
        el && el.offsetParent !== null && getComputedStyle(el).display !== 'none' && getComputedStyle(el).visibility !== 'hidden'
      `);
      return r.result === true;
    } catch {
      return false;
    }
  }
}
