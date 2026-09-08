// Optional real-browser smoke. No browser dependency is required by the product.
// VEMO_PLAYWRIGHT_MODULE=/absolute/path/to/playwright node tests/test_setup_browser.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {spawn, execFileSync} = require('node:child_process');
const {chromium} = require(process.env.VEMO_PLAYWRIGHT_MODULE || 'playwright');
const parent = path.resolve(__dirname, '..');
const root = path.basename(parent) === 'eval' ? path.dirname(parent) : parent;
const output = path.join(root, '.vemo', 'run');
fs.mkdirSync(output, {recursive: true});
const project = fs.mkdtempSync(path.join(output, 'browser-中文 项目-'));
execFileSync('git', ['init', '-q', project]);
const child = spawn(process.env.VEMO_TEST_PYTHON || 'python3', ['bin/vemo', 'ui', '--no-browser'], {cwd: root});

async function until(predicate) {
  const deadline = Date.now() + 30000;
  while (!(await predicate())) {
    if (Date.now() > deadline) throw new Error('UI condition timeout');
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
}

async function main() {
  let browser;
  try {
    const url = await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('server start timeout')), 10000);
      child.stdout.on('data', (data) => {
        const match = data.toString().match(/http:\/\/127\.0\.0\.1:\d+\/#token=[\w-]+/);
        if (match) { clearTimeout(timer); resolve(match[0]); }
      });
      child.once('error', reject);
      child.once('exit', (code) => { if (code) reject(new Error(`server exit ${code}`)); });
    });
    browser = await chromium.launch({executablePath: process.env.VEMO_TEST_CHROME || '/usr/bin/google-chrome', headless: false, args: ['--headless=new', '--no-sandbox']});
    const page = await browser.newPage({viewport: {width: 1440, height: 1080}});
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto(url);
    await until(async () => (await page.locator('#version').textContent()) !== '—');
    await page.screenshot({path: path.join(output, 'setup-desktop.png'), fullPage: true});
    await page.locator('#target').fill('relative/path');
    await page.locator('#preview').click();
    await until(async () => (await page.locator('#notice').textContent()).includes('绝对路径'));
    await page.locator('#target').fill(project);
    await page.locator('#preset').selectOption('docs');
    await page.locator('#preview').click();
    await until(async () => !(await page.locator('#apply').isDisabled()));
    assert.equal(fs.existsSync(path.join(project, 'bin', 'vemo')), false, 'preview must be read-only');
    await page.locator('#apply').click();
    await until(async () => (await page.locator('#result-title').textContent()).includes('安装完成'));
    assert.equal(fs.existsSync(path.join(project, '.vemo', 'install.json')), true);
    const receipt = JSON.parse(fs.readFileSync(path.join(project, '.vemo', 'install.json')));
    assert.ok(receipt.verification.every((row) => row.ok));
    await page.screenshot({path: path.join(output, 'setup-installed.png'), fullPage: true});
    // Reload verifies the token is retained in this browser session without remaining in the URL.
    await page.reload();
    await until(async () => (await page.locator('#version').textContent()) !== '—');
    await page.locator('[data-view="maintain"]').click();
    await page.locator('#target').fill(project);
    await page.locator('#target').press('Enter');
    await until(async () => (await page.locator('#result-title').textContent()).includes('安装检查通过'));
    assert.equal(await page.locator('#preview-panel').isVisible(), false, 'maintenance Enter must not start an install preview');
    await page.locator('#uninstall-preview').click();
    await until(async () => !(await page.locator('#apply').isDisabled()));
    await page.locator('#apply').click();
    await until(async () => (await page.locator('#result-title').textContent()).includes('卸载完成'));
    assert.equal(fs.existsSync(path.join(project, 'bin', 'vemo')), false);
    await page.locator('[data-view="install"]').click();
    await page.setViewportSize({width: 390, height: 844});
    await page.screenshot({path: path.join(output, 'setup-mobile.png'), fullPage: true});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'mobile layout overflows');
    for (const filename of ['install', 'usage', 'design']) {
      const response = await page.goto(new URL(`/help/${filename}.html`, url).href);
      assert.equal(response.status(), 200);
      assert.equal(await page.locator('h1').count(), 1);
    }
    assert.deepEqual(errors, []);
    const report = {status: 'pass', browser: await browser.version(), checks: ['invalid input', 'read-only preview', 'Unicode install', 'receipt verification', 'reload auth', 'diagnostics', 'uninstall', '390px layout', 'offline help', 'no page errors']};
    fs.writeFileSync(path.join(output, 'setup-browser.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
  } finally {
    if (browser) await browser.close();
    child.kill('SIGTERM');
  }
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
