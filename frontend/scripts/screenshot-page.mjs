#!/usr/bin/env node

import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const HELP = `
页面截图脚本

用法：
  npm run screenshot -- --url http://127.0.0.1:5173/graph --out ../outputs/screenshots/graph.png

常用参数：
  --url <url>                 要打开的页面 URL，必填
  --out <path>                PNG 输出路径，默认 ../outputs/screenshots/page.png
  --selector <css>            只截取某个区域，例如 ".graph-shell"；不填则截整页
  --width <number>            视口宽度，默认 1920
  --height <number>           视口高度，默认 1080
  --wait <ms>                 页面打开后额外等待时间，默认 2500
  --full-page                 截整页；指定 selector 时无效
  --local-storage k=v         写入 localStorage，可重复；例如 active_case_id=case_xxx
  --click <text>              按文本点击按钮/链接，可重复；例如 --click 原始图谱层 --click 邻域扩展
  --hide <css>                截图前隐藏元素，可重复；例如 --hide ".topbar"
  --drag <dx,dy>              截图前拖动画布，可重复；例如 --drag 180,220

示例：
  npm run screenshot -- --url http://127.0.0.1:5173/graph --selector ".graph-shell" --out ../outputs/screenshots/graph-shell.png --wait 5000
  npm run screenshot -- --url http://127.0.0.1:5173/graph --local-storage active_case_id=case_xxx --click 原始图谱层 --click 邻域扩展 --out ../outputs/screenshots/neighborhood.png

首次使用如果提示缺少浏览器：
  npm i -D playwright
  npx playwright install chromium
`;

function parseArgs(argv) {
  const args = {
    url: '',
    out: '../outputs/screenshots/page.png',
    selector: '',
    width: 1920,
    height: 1080,
    wait: 2500,
  fullPage: false,
  localStorage: [],
  click: [],
  hide: [],
  drag: [],
  };

  for (let index = 0; index < argv.length; index += 1) {
    const item = argv[index];
    const next = argv[index + 1];
    if (item === '--help' || item === '-h') {
      console.log(HELP);
      process.exit(0);
    }
    if (item === '--full-page') {
      args.fullPage = true;
      continue;
    }
    if (item === '--url') {
      args.url = next || '';
      index += 1;
      continue;
    }
    if (item === '--out') {
      args.out = next || args.out;
      index += 1;
      continue;
    }
    if (item === '--selector') {
      args.selector = next || '';
      index += 1;
      continue;
    }
    if (item === '--width') {
      args.width = Number(next || args.width);
      index += 1;
      continue;
    }
    if (item === '--height') {
      args.height = Number(next || args.height);
      index += 1;
      continue;
    }
    if (item === '--wait') {
      args.wait = Number(next || args.wait);
      index += 1;
      continue;
    }
    if (item === '--local-storage') {
      args.localStorage.push(next || '');
      index += 1;
      continue;
    }
    if (item === '--click') {
      args.click.push(next || '');
      index += 1;
      continue;
    }
    if (item === '--hide') {
      args.hide.push(next || '');
      index += 1;
      continue;
    }
    if (item === '--drag') {
      args.drag.push(next || '');
      index += 1;
      continue;
    }
    throw new Error(`未知参数：${item}\n${HELP}`);
  }

  if (!args.url) throw new Error(`缺少 --url。\n${HELP}`);
  if (!Number.isFinite(args.width) || args.width <= 0) throw new Error('--width 必须是正数。');
  if (!Number.isFinite(args.height) || args.height <= 0) throw new Error('--height 必须是正数。');
  if (!Number.isFinite(args.wait) || args.wait < 0) throw new Error('--wait 必须是非负数。');
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

function localStoragePairs(items) {
  return items
    .filter(Boolean)
    .map((item) => {
      const equalIndex = item.indexOf('=');
      if (equalIndex < 1) throw new Error(`--local-storage 参数格式应为 key=value，收到：${item}`);
      return [item.slice(0, equalIndex), item.slice(equalIndex + 1)];
    });
}

async function clickByText(page, text) {
  if (!text) return;
  const locator = page.getByText(text, { exact: true }).first();
  await locator.waitFor({ state: 'visible', timeout: 8000 });
  await locator.click();
}

async function hideElements(page, selectors) {
  const cleanSelectors = selectors.filter(Boolean);
  if (!cleanSelectors.length) return;
  await page.addStyleTag({
    content: cleanSelectors.map((selector) => `${selector}{visibility:hidden!important;}`).join('\n'),
  });
}

function parseDrag(value) {
  const [dxRaw, dyRaw] = String(value || '').split(',');
  const dx = Number(dxRaw);
  const dy = Number(dyRaw);
  if (!Number.isFinite(dx) || !Number.isFinite(dy)) {
    throw new Error(`--drag 参数格式应为 dx,dy，收到：${value}`);
  }
  return { dx, dy };
}

async function dragCanvas(page, selector, dragValue) {
  const { dx, dy } = parseDrag(dragValue);
  const box = selector
    ? await page.locator(selector).first().boundingBox()
    : { x: 0, y: 0, width: page.viewportSize()?.width || 1920, height: page.viewportSize()?.height || 1080 };
  if (!box) throw new Error(`无法找到拖动区域：${selector || '页面'}`);
  const startX = box.x + box.width * 0.55;
  const startY = box.y + box.height * 0.55;
  await page.mouse.move(startX, startY);
  await page.mouse.down();
  await page.mouse.move(startX + dx, startY + dy, { steps: 16 });
  await page.mouse.up();
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const { chromium } = await loadPlaywright();
  const outPath = path.resolve(process.cwd(), args.out);
  await fs.mkdir(path.dirname(outPath), { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: args.width, height: args.height },
    deviceScaleFactor: 1,
    locale: 'zh-CN',
  });

  const pairs = localStoragePairs(args.localStorage);
  if (pairs.length) {
    await context.addInitScript((entries) => {
      for (const [key, value] of entries) window.localStorage.setItem(key, value);
    }, pairs);
  }

  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  await page.goto(args.url, { waitUntil: 'networkidle' });
  for (const text of args.click) {
    await clickByText(page, text);
    await page.waitForTimeout(600);
  }
  if (args.wait > 0) await page.waitForTimeout(args.wait);
  for (const dragValue of args.drag) {
    await dragCanvas(page, args.selector, dragValue);
    await page.waitForTimeout(350);
  }
  await hideElements(page, args.hide);

  if (args.selector) {
    const target = page.locator(args.selector).first();
    await target.waitFor({ state: 'visible', timeout: 15000 });
    await target.screenshot({ path: outPath });
  } else {
    await page.screenshot({ path: outPath, fullPage: args.fullPage });
  }

  await browser.close();
  console.log(`截图已保存：${outPath}`);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
