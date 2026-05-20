/**
 * CLI Runner — запуск автономного агента из командной строки
 * Поддерживает все режимы: scenarios, discovery, performance, accessibility, responsive
 */

import { promises as fs } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { AutonomousAgent } from './autonomous-agent.js';
import { getScenariosForPersona } from './scenarios.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPORT_DIR = process.env.TEST_REPORT_DIR || join(__dirname, 'reports');

export class TestRunner {
  constructor(options = {}) {
    this.options = options;
    this.reports = [];
  }

  async run(args) {
    const personaArg = args.find((a) => a.startsWith('--persona='))?.split('=')[1] || 'user';
    const scenarioArg = args.find((a) => a.startsWith('--scenario='))?.split('=')[1];
    const reportFormat = args.find((a) => a.startsWith('--report='))?.split('=')[1] || 'console';
    const discoverMode = args.includes('--discover');
    const perfMode = args.includes('--performance');
    const a11yMode = args.includes('--accessibility');
    const responsiveMode = args.includes('--responsive');
    const headless = !args.includes('--headed');
    const debug = args.includes('--debug');
    const baseUrl = args.find((a) => a.startsWith('--base-url='))?.split('=')[1];
    const apiUrl = args.find((a) => a.startsWith('--api-url='))?.split('=')[1];

    if (baseUrl) process.env.TEST_BASE_URL = baseUrl;
    if (apiUrl) process.env.TEST_API_URL = apiUrl;

    const agent = new AutonomousAgent({ headless, debug });
    await agent.init();

    try {
      if (discoverMode) {
        const report = await agent.discover(personaArg, 20);
        this.reports.push(report);
      } else if (perfMode) {
        await this.runPerformanceTests(agent);
      } else if (a11yMode) {
        await this.runAccessibilityTests(agent);
      } else if (responsiveMode) {
        await this.runResponsiveTests(agent);
      } else {
        // Scenario mode
        let scenarioList;
        if (scenarioArg) {
          scenarioList = [{ name: scenarioArg }];
        } else {
          scenarioList = getScenariosForPersona(personaArg);
        }

        for (const { name } of scenarioList) {
          const effectivePersona = personaArg === 'all' ? this.inferPersonaFromScenario(name) : personaArg;
          try {
            const report = await agent.runScenario(name, effectivePersona);
            this.reports.push(report);
          } catch (err) {
            console.error(`   💥 Scenario ${name} crashed:`, err.message);
            this.reports.push({
              scenario: name,
              persona: effectivePersona,
              passed: false,
              bugs: [{ severity: 'critical', message: err.message }],
            });
          }
        }
      }
    } finally {
      await agent.cleanup();
    }

    // Сохраняем отчёт
    await this.saveReport(reportFormat);

    // Итог
    const passed = this.reports.filter((r) => r.passed).length;
    const failed = this.reports.filter((r) => !r.passed).length;
    const totalBugs = this.reports.reduce((sum, r) => sum + (r.bugs?.length || 0), 0);

    console.log(`\n${'='.repeat(60)}`);
    console.log(`📊 RESULTS: ${passed} passed, ${failed} failed / ${this.reports.length} scenarios`);
    console.log(`🐛 BUGS: ${totalBugs} total`);

    if (failed > 0) {
      console.log(`\n🔴 FAILED SCENARIOS:`);
      for (const r of this.reports.filter((r) => !r.passed)) {
        console.log(`   [${r.persona}] ${r.scenario}`);
        for (const b of r.bugs) {
          console.log(`      → ${b.severity}: ${b.message}`);
        }
      }
    }

    // Статистика из state
    const stats = agent.state.getStats();
    console.log(`\n📈 HISTORICAL STATS:`);
    console.log(`   Total sessions: ${stats.totalSessions}`);
    console.log(`   Total bugs found: ${stats.totalBugs}`);
    console.log(`   Bugs by severity: ${JSON.stringify(stats.bugsBySeverity)}`);
    console.log(`   Accounts: ${stats.accounts.join(', ')}`);

    return failed === 0 ? 0 : 1;
  }

  async runPerformanceTests(agent) {
    console.log('\n⚡ Performance Testing Mode');
    const urls = [
      'https://promelectron-test.aidrivencode.ru/',
      'https://promelectron-test.aidrivencode.ru/login',
      'https://promelectron-test.aidrivencode.ru/register',
      'https://promelectron-test.aidrivencode.ru/cart',
    ];

    for (const url of urls) {
      console.log(`\n   Testing: ${url}`);
      const metrics = await agent.measurePerformance(url);
      this.reports.push({
        scenario: `perf_${url.replace(/[^a-z0-9]/gi, '_')}`,
        persona: 'performance',
        passed: true,
        performance: metrics,
        bugs: [],
      });
      console.log(`      TTFB: ${metrics.ttfb}ms`);
      console.log(`      FCP: ${metrics.fcp}ms`);
      console.log(`      LCP: ${metrics.lcp}ms`);
      console.log(`      CLS: ${metrics.cls}`);
      console.log(`      Load: ${metrics.loadComplete}ms`);
    }
  }

  async runAccessibilityTests(agent) {
    console.log('\n♿ Accessibility Testing Mode');
    const urls = [
      'https://promelectron-test.aidrivencode.ru/',
      'https://promelectron-test.aidrivencode.ru/login',
      'https://promelectron-test.aidrivencode.ru/register',
      'https://promelectron-test.aidrivencode.ru/cart',
    ];

    for (const url of urls) {
      console.log(`\n   Testing: ${url}`);
      const checks = await agent.checkAccessibility(url);
      const bugs = [];
      
      if (checks.imagesWithoutAlt > 0) {
        bugs.push({ severity: 'minor', message: `${checks.imagesWithoutAlt} images without alt text` });
      }
      if (checks.missingFormLabels > 0) {
        bugs.push({ severity: 'major', message: `${checks.missingFormLabels} form inputs without labels` });
      }
      if (checks.headings?.h1 === 0) {
        bugs.push({ severity: 'major', message: 'No H1 heading found' });
      }
      if (checks.lang === 'missing') {
        bugs.push({ severity: 'minor', message: 'Missing lang attribute on html element' });
      }

      this.reports.push({
        scenario: `a11y_${url.replace(/[^a-z0-9]/gi, '_')}`,
        persona: 'accessibility',
        passed: bugs.length === 0,
        accessibility: checks,
        bugs,
      });

      console.log(`      Images without alt: ${checks.imagesWithoutAlt}/${checks.totalImages}`);
      console.log(`      Missing form labels: ${checks.missingFormLabels}`);
      console.log(`      Headings: H1=${checks.headings?.h1 || 0}`);
    }
  }

  async runResponsiveTests(agent) {
    console.log('\n📱 Responsive Testing Mode');
    const url = 'https://promelectron-test.aidrivencode.ru/';
    const results = await agent.testResponsive(url);
    
    for (const result of results) {
      const bugs = [];
      if (result.hasHorizontalScroll) {
        bugs.push({ severity: 'major', message: `Horizontal scroll detected at ${result.dimensions}` });
      }
      this.reports.push({
        scenario: `responsive_${result.viewport}`,
        persona: 'responsive',
        passed: bugs.length === 0,
        responsive: result,
        bugs,
      });
      console.log(`   ${result.viewport} (${result.dimensions}): ${result.hasHorizontalScroll ? '❌ horizontal scroll' : '✅ OK'}`);
    }
  }

  inferPersonaFromScenario(scenarioName) {
    if (scenarioName.startsWith('admin')) return 'admin';
    if (scenarioName.startsWith('supplier')) return 'supplier';
    if (scenarioName.startsWith('user')) return 'user';
    if (scenarioName.startsWith('security')) return 'security';
    if (scenarioName.startsWith('perf')) return 'performance';
    if (scenarioName.startsWith('cross')) return 'crossrole';
    if (scenarioName.startsWith('fuzz')) return 'user';
    if (scenarioName.startsWith('a11y')) return 'accessibility';
    if (scenarioName.startsWith('responsive')) return 'responsive';
    return 'user';
  }

  async saveReport(format) {
    await fs.mkdir(REPORT_DIR, { recursive: true });
    const timestamp = Date.now();

    if (format === 'json' || format === 'all') {
      const path = join(REPORT_DIR, `report-${timestamp}.json`);
      await fs.writeFile(path, JSON.stringify(this.reports, null, 2));
      console.log(`\n📝 JSON report: ${path}`);
    }

    if (format === 'html' || format === 'all') {
      const path = join(REPORT_DIR, `report-${timestamp}.html`);
      const html = this.generateHtmlReport();
      await fs.writeFile(path, html);
      console.log(`📝 HTML report: ${path}`);
    }

    if (format === 'markdown' || format === 'all') {
      const path = join(REPORT_DIR, `report-${timestamp}.md`);
      const md = this.generateMarkdownReport();
      await fs.writeFile(path, md);
      console.log(`📝 Markdown report: ${path}`);
    }
  }

  generateHtmlReport() {
    const rows = this.reports.map(r => {
      const status = r.passed ? '✅ PASS' : '❌ FAIL';
      const bugs = r.bugs?.map(b => `<li><strong>${b.severity}</strong>: ${b.message}</li>`).join('') || '<li>None</li>';
      const steps = r.steps?.map(s => `<li>${s.step}. ${s.action} — ${s.result?.ok ? 'OK' : 'FAIL'}</li>`).join('') || '';
      
      let extra = '';
      if (r.performance) {
        extra = `<pre>${JSON.stringify(r.performance, null, 2)}</pre>`;
      }
      if (r.accessibility) {
        extra = `<pre>${JSON.stringify(r.accessibility, null, 2)}</pre>`;
      }
      if (r.responsive) {
        extra = `<pre>${JSON.stringify(r.responsive, null, 2)}</pre>`;
      }

      return `
        <tr>
          <td>${status}</td>
          <td>${r.persona}</td>
          <td>${r.scenario}</td>
          <td>${r.steps?.length || 0}</td>
          <td><ul>${bugs}</ul></td>
          <td>${extra}<ol>${steps}</ol></td>
        </tr>
      `;
    }).join('');

    return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Autonomous Agent Report</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 1400px; margin: 2rem auto; padding: 0 1rem; }
    h1 { color: #333; }
    table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
    th, td { border: 1px solid #ddd; padding: 0.5rem; text-align: left; vertical-align: top; }
    th { background: #f5f5f5; }
    tr:nth-child(even) { background: #fafafa; }
    .fail { color: #d32f2f; }
    .pass { color: #388e3c; }
    ul, ol { margin: 0; padding-left: 1.2rem; }
    pre { background: #f5f5f5; padding: 0.5rem; overflow-x: auto; font-size: 0.85rem; }
  </style>
</head>
<body>
  <h1>🤖 Autonomous Tester Report</h1>
  <p>Generated: ${new Date().toISOString()}</p>
  <table>
    <thead>
      <tr><th>Status</th><th>Persona</th><th>Scenario</th><th>Steps</th><th>Bugs</th><th>Details</th></tr>
    </thead>
    <tbody>${rows}</tbody>
  </table>
</body>
</html>`;
  }

  generateMarkdownReport() {
    const lines = [
      '# 🤖 Autonomous Tester Report',
      `\nGenerated: ${new Date().toISOString()}`,
      `\n## Summary`,
      `- Total scenarios: ${this.reports.length}`,
      `- Passed: ${this.reports.filter(r => r.passed).length}`,
      `- Failed: ${this.reports.filter(r => !r.passed).length}`,
      `- Total bugs: ${this.reports.reduce((s, r) => s + (r.bugs?.length || 0), 0)}`,
      `\n## Results`,
    ];

    for (const r of this.reports) {
      lines.push(`\n### ${r.passed ? '✅' : '❌'} ${r.persona} — ${r.scenario}`);
      lines.push(`- Duration: ${r.startTime || 'N/A'} → ${r.endTime || 'N/A'}`);
      lines.push(`- Steps: ${r.steps?.length || 0}`);
      
      if (r.performance) {
        lines.push(`- Performance:`);
        lines.push(`  - TTFB: ${r.performance.ttfb}ms`);
        lines.push(`  - FCP: ${r.performance.fcp}ms`);
        lines.push(`  - LCP: ${r.performance.lcp}ms`);
        lines.push(`  - CLS: ${r.performance.cls}`);
      }
      
      if (r.accessibility) {
        lines.push(`- Accessibility:`);
        lines.push(`  - Images without alt: ${r.accessibility.imagesWithoutAlt}/${r.accessibility.totalImages}`);
        lines.push(`  - Missing form labels: ${r.accessibility.missingFormLabels}`);
        lines.push(`  - Headings: H1=${r.accessibility.headings?.h1 || 0}`);
      }
      
      if (r.responsive) {
        lines.push(`- Responsive: ${r.responsive.viewport} (${r.responsive.dimensions})`);
      }
      
      if (r.bugs?.length) {
        lines.push(`- Bugs:`);
        for (const b of r.bugs) {
          lines.push(`  - **${b.severity}**: ${b.message} (step ${b.step})`);
        }
      }
      if (r.apiChecks?.length) {
        lines.push(`- API Checks:`);
        for (const c of r.apiChecks) {
          lines.push(`  - ${c.name}: HTTP ${c.status} ${c.validation?.valid ? '✅' : '❌'}`);
        }
      }
    }

    return lines.join('\n');
  }
}
