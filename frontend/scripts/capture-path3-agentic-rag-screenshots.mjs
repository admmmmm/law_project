#!/usr/bin/env node

import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const DEFAULT_TASK =
  '@行为画像分析 请围绕杨承泽，结合案件证据图谱、人物关系、资金往来和通话记录，分析其在案件中的行为方式、可疑信息和后续核查方向，并要求每个结论关联证据来源。';

const HELP = `
主路径三截图脚本

用法：
  node frontend/scripts/capture-path3-agentic-rag-screenshots.mjs --base-url http://127.0.0.1:5173 --case-id case_632371a3a613

参数：
  --base-url <url>      前端地址，默认 http://127.0.0.1:5173
  --case-id <id>        演示案件 ID，默认 case_632371a3a613
  --out-dir <path>      输出目录，默认 outputs/screenshots
  --timeout <ms>        等待分析生成的最长时间，默认 180000
  --help               显示帮助
`;

function parseArgs(argv) {
  const args = {
    baseUrl: 'http://127.0.0.1:5173',
    caseId: 'case_632371a3a613',
    outDir: '../outputs/screenshots',
    timeout: 180000,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const item = argv[index];
    const next = argv[index + 1];
    if (item === '--help' || item === '-h') {
      console.log(HELP);
      process.exit(0);
    }
    if (item === '--base-url') {
      args.baseUrl = next || args.baseUrl;
      index += 1;
      continue;
    }
    if (item === '--case-id') {
      args.caseId = next || args.caseId;
      index += 1;
      continue;
    }
    if (item === '--out-dir') {
      args.outDir = next || args.outDir;
      index += 1;
      continue;
    }
    if (item === '--timeout') {
      args.timeout = Number(next || args.timeout);
      index += 1;
      continue;
    }
    throw new Error(`未知参数：${item}\n${HELP}`);
  }

  if (!Number.isFinite(args.timeout) || args.timeout <= 0) throw new Error('--timeout 必须是正数。');
  return args;
}

async function loadPlaywright() {
  try {
    return await import('playwright');
  } catch (error) {
    throw new Error(
      `当前 frontend 未安装 Playwright。请先执行：\n\n` +
        `  cd frontend\n` +
        `  npm i -D playwright\n` +
        `  npx playwright install chromium\n\n` +
        `原始错误：${error instanceof Error ? error.message : String(error)}`,
    );
  }
}

function appUrl(baseUrl, route) {
  const normalizedBase = baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`;
  const cleanRoute = route.replace(/^\//, '');
  return new URL(cleanRoute, normalizedBase).toString();
}

async function screenshot(locator, outPath) {
  await locator.waitFor({ state: 'visible', timeout: 30000 });
  await locator.screenshot({ path: outPath });
  console.log(`截图已保存：${outPath}`);
}

async function ensureAnalysisThread(page, timeout) {
  const threadCards = page.getByTestId('analysis-thread-card');
  const count = await threadCards.count();
  if (count > 0) {
    await threadCards.first().click();
    await page.getByTestId('analysis-result').waitFor({ state: 'visible', timeout: 30000 });
    return;
  }

  await page.getByTestId('send-analysis').click();
  await page.getByTestId('evidence-citation').first().waitFor({ state: 'visible', timeout });
}

async function openRetrievalDetails(page) {
  const retrieval = page.getByTestId('retrieval-session').first();
  await retrieval.waitFor({ state: 'visible', timeout: 60000 });
  const isOpen = await retrieval.evaluate((node) => Boolean(node.open));
  if (!isOpen) await retrieval.locator('summary').click();
  await retrieval.locator('.tool-call, .retrieval-step, .retrieval-body').first().waitFor({ state: 'visible', timeout: 60000 });
}

async function ensurePortraitFacts(page, timeout) {
  const citation = page.getByTestId('evidence-citation').first();
  try {
    await citation.waitFor({ state: 'visible', timeout: 20000 });
  } catch {
    await page.getByRole('button', { name: /重新生成事实画像|生成事实画像|检索中/ }).first().click();
    await citation.waitFor({ state: 'visible', timeout });
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const outDir = path.resolve(process.cwd(), args.outDir);
  await fs.mkdir(outDir, { recursive: true });
  const { chromium } = await loadPlaywright();

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1600, height: 900 },
    deviceScaleFactor: 1,
    locale: 'zh-CN',
  });
  await context.addInitScript((caseId) => {
    window.localStorage.setItem('active_case_id', caseId);
  }, args.caseId);

  const page = await context.newPage();
  page.setDefaultTimeout(30000);

  await page.goto(appUrl(args.baseUrl, '/intelligence'), { waitUntil: 'networkidle' });
  await page.getByTestId('analysis-page').waitFor({ state: 'visible' });
  await page.getByTestId('hypothesis-tab').click();
  const newThreadButton = page.getByTestId('new-analysis-thread');
  if (!(await page.getByTestId('analysis-input').isVisible().catch(() => false))) {
    await newThreadButton.click();
  }
  await page.getByTestId('analysis-input').fill(DEFAULT_TASK);
  await screenshot(page.getByTestId('analysis-page'), path.join(outDir, 'path3-01-task-input-skills.png'));

  await ensureAnalysisThread(page, args.timeout);
  await openRetrievalDetails(page);
  await screenshot(page.getByTestId('retrieval-session').first(), path.join(outDir, 'path3-02-agentic-rag-trace.png'));
  await screenshot(page.getByTestId('analysis-result'), path.join(outDir, 'path3-03-analysis-result.png'));

  await page.goto(appUrl(args.baseUrl, '/portrait'), { waitUntil: 'networkidle' });
  await page.getByTestId('portrait-page').waitFor({ state: 'visible' });
  await ensurePortraitFacts(page, args.timeout);
  await screenshot(page.getByTestId('portrait-report'), path.join(outDir, 'path3-04-portrait-report.png'));

  const portraitCitation = page.getByTestId('evidence-citation').first();
  try {
    await portraitCitation.click();
    await screenshot(page.getByTestId('provenance-modal').first(), path.join(outDir, 'path3-05-evidence-provenance.png'));
  } catch (error) {
    console.warn(`证据溯源截图跳过：${error instanceof Error ? error.message : String(error)}`);
  }

  await browser.close();
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
