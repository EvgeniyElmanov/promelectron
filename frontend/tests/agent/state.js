/**
 * State Machine — память агента между запусками
 * Сохраняет аккаунты, токены, созданные сущности, баги
 */

import { promises as fs } from 'fs';
import { createRequire } from 'module';

const STATE_FILE = process.env.AGENT_STATE_FILE || './tests/agent/agent-state.json';

export class AgentState {
  constructor(options = {}) {
    this.file = options.stateFile || STATE_FILE;
    this.data = {
      version: 1,
      accounts: {},        // { user: {email, password, token, role}, admin: {...}, supplier: {...} }
      entities: {},        // { products: [], categories: [], orders: [] }
      bugs: [],            // найденные баги
      sessions: [],        // история сессий
      learnings: {},       // что агент уже знает о сайте
      lastRun: null,
    };
    this.dirty = false;
  }

  async load() {
    try {
      const raw = await fs.readFile(this.file, 'utf-8');
      const loaded = JSON.parse(raw);
      this.data = { ...this.data, ...loaded };
    } catch (e) {
      // Файла нет — начинаем с чистого состояния
    }
  }

  async save() {
    if (!this.dirty) return;
    try {
      await fs.mkdir(this.file.split('/').slice(0, -1).join('/'), { recursive: true });
      await fs.writeFile(this.file, JSON.stringify(this.data, null, 2));
      this.dirty = false;
    } catch (e) {
      console.error('[State] Failed to save:', e.message);
    }
  }

  // ═══════════════════════════════════════
  // Account management
  // ═══════════════════════════════════════

  getAccount(role) {
    return this.data.accounts[role] || null;
  }

  setAccount(role, account) {
    this.data.accounts[role] = { ...this.data.accounts[role], ...account, role };
    this.dirty = true;
  }

  hasAccount(role) {
    return !!this.data.accounts[role]?.email;
  }

  getAllAccounts() {
    return this.data.accounts;
  }

  // ═══════════════════════════════════════
  // Entity tracking
  // ═══════════════════════════════════════

  addEntity(type, entity) {
    if (!this.data.entities[type]) this.data.entities[type] = [];
    this.data.entities[type].push({ ...entity, createdAt: new Date().toISOString() });
    this.dirty = true;
  }

  getEntities(type) {
    return this.data.entities[type] || [];
  }

  removeEntity(type, predicate) {
    if (!this.data.entities[type]) return;
    this.data.entities[type] = this.data.entities[type].filter(e => !predicate(e));
    this.dirty = true;
  }

  // ═══════════════════════════════════════
  // Bug tracking
  // ═══════════════════════════════════════

  addBug(bug) {
    // Дедупликация по message + url
    const exists = this.data.bugs.some(
      b => b.message === bug.message && b.url === bug.url
    );
    if (!exists) {
      this.data.bugs.push({
        ...bug,
        id: `bug-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        timestamp: new Date().toISOString(),
      });
      this.dirty = true;
    }
  }

  getBugs(filters = {}) {
    let bugs = this.data.bugs;
    if (filters.severity) bugs = bugs.filter(b => b.severity === filters.severity);
    if (filters.persona) bugs = bugs.filter(b => b.persona === filters.persona);
    if (filters.status) bugs = bugs.filter(b => b.status === filters.status);
    return bugs;
  }

  updateBug(id, updates) {
    const bug = this.data.bugs.find(b => b.id === id);
    if (bug) {
      Object.assign(bug, updates);
      this.dirty = true;
    }
  }

  // ═══════════════════════════════════════
  // Session tracking
  // ═══════════════════════════════════════

  startSession(persona, scenario) {
    const session = {
      id: `sess-${Date.now()}`,
      persona,
      scenario,
      startTime: new Date().toISOString(),
      endTime: null,
      steps: [],
      passed: true,
    };
    this.data.sessions.push(session);
    this.dirty = true;
    return session;
  }

  endSession(sessionId, result) {
    const session = this.data.sessions.find(s => s.id === sessionId);
    if (session) {
      session.endTime = new Date().toISOString();
      session.passed = result.passed;
      session.errors = result.errors || [];
      this.dirty = true;
    }
  }

  // ═══════════════════════════════════════
  // Learnings — что агент узнал о сайте
  // ═══════════════════════════════════════

  learn(key, value) {
    this.data.learnings[key] = value;
    this.dirty = true;
  }

  getLearning(key) {
    return this.data.learnings[key];
  }

  hasLearning(key) {
    return key in this.data.learnings;
  }

  // ═══════════════════════════════════════
  // Reporting
  // ═══════════════════════════════════════

  getStats() {
    const sessions = this.data.sessions;
    return {
      totalSessions: sessions.length,
      passed: sessions.filter(s => s.passed).length,
      failed: sessions.filter(s => !s.passed).length,
      totalBugs: this.data.bugs.length,
      bugsBySeverity: this.data.bugs.reduce((acc, b) => {
        acc[b.severity] = (acc[b.severity] || 0) + 1;
        return acc;
      }, {}),
      accounts: Object.keys(this.data.accounts),
      entities: Object.fromEntries(
        Object.entries(this.data.entities).map(([k, v]) => [k, v.length])
      ),
      lastRun: this.data.lastRun,
    };
  }

  async markRunComplete() {
    this.data.lastRun = new Date().toISOString();
    this.dirty = true;
    await this.save();
  }
}
