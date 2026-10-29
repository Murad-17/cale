/* Settings regression: node tests/ui_gradients.cjs (Playwright).
 * Uses the disposable local backend; does not call paid AI providers.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawn} = require('node:child_process');
const {chromium} = require(process.env.ORION_PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const server = spawn(process.env.ORION_UI_PYTHON || 'python', [path.join(__dirname, 'ui_server.py')]);
  const artifacts = process.env.ORION_UI_ARTIFACTS || fs.mkdtempSync(path.join(os.tmpdir(), 'orion-gradients-'));
  fs.mkdirSync(artifacts, {recursive: true});
  const errors = [], consoleErrors = [], httpErrors = [], passed = [];
  let browser;
  try {
    const base = await new Promise((resolve, reject) => {
      let output = '', stderr = '';
      const timer = setTimeout(() => reject(Error('UI server did not start: ' + stderr)), 20000);
      server.stderr.on('data', chunk => { stderr = (stderr + chunk).slice(-4000); });
      server.stdout.on('data', chunk => {
        output += chunk;
        const address = output.match(/http:\/\/127\.0\.0\.1:\d+/);
        if (address) { clearTimeout(timer); resolve(address[0]); }
      });
      server.once('error', error => { clearTimeout(timer); reject(error); });
      server.once('exit', code => { clearTimeout(timer); reject(Error('UI server exited (' + code + '): ' + stderr)); });
    });
    browser = await chromium.launch({
      headless: true,
      ...(process.env.ORION_UI_CHROMIUM ? {executablePath: process.env.ORION_UI_CHROMIUM} : {}),
      args: JSON.parse(process.env.ORION_UI_BROWSER_ARGS || '[]')
    });
    const context = await browser.newContext({viewport: {width: 1440, height: 900}, reducedMotion: 'reduce'});
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') consoleErrors.push({text: message.text(), location: message.location()}); });
    page.on('response', response => {
      if (response.status() >= 400) httpErrors.push({url: response.url(), method: response.request().method(), status: response.status()});
    });
    await page.goto(base);
    // The supplied application has no favicon route. Verify that baseline
    // response before allowing only its browser-generated resource warning.
    const missingFavicon = (await page.request.get(base + '/favicon.ico')).status() === 404;
    await page.request.post(base + '/api/updates/preferences', {data: {consent: false, automatic: false}});
    await page.evaluate(() => localStorage.setItem('orion.entry.v1', '1'));
    await page.reload();
    await page.waitForFunction(() => window.ORIONBig && document.body.classList.contains('premium-ui'));
    await page.evaluate(() => document.fonts.ready);
    const openSettings = async () => {
      await page.evaluate(() => { window.OrionOS.navigate('settings'); setSettingsSection('themesSection'); });
      await page.locator('#settingsDialog').waitFor({state: 'visible'});
    };
    const choices = page.locator('#gradientThemeChoices .theme-choice, #themeChoices .theme-choice');
    const selected = page.locator('#gradientThemeChoices .theme-choice[aria-pressed="true"], #themeChoices .theme-choice[aria-pressed="true"]');
    await openSettings();
    assert.equal(await choices.count(), 17);
    assert.equal(await page.locator('#gradientThemeChoices .theme-choice').count(), 5);
    assert.equal(await page.locator('#themeChoices .theme-choice').count(), 12);
    passed.push('Five luminous palettes and all twelve existing palettes are available');

    const palettes = {
      prism: '#80e8d5', cobalt: '#6b9eff', ember: '#ffac80', lagoon: '#6de0ee', auroraglow: '#9bc5ff'
    };
    for (const [id, accent] of Object.entries(palettes)) {
      await page.locator('#gradientThemeChoices [data-theme-choice="' + id + '"]').click();
      await page.mouse.move(0, 0);
      assert.equal(await page.evaluate(() => orionSettings.theme), id);
      assert.equal(await selected.count(), 1);
      assert.equal(await selected.getAttribute('data-theme-choice'), id);
      assert.equal(await page.evaluate(() => JSON.parse(localStorage.getItem(SETTINGS_KEY)).theme), id);
      assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()), accent);
      await page.waitForFunction(async expected => {
        const response = await fetch('/api/panel/appearance');
        return response.ok && (await response.json()).theme === expected;
      }, id, {timeout: 5000});
      await page.reload();
      await page.waitForFunction(() => window.ORIONBig && document.body.classList.contains('premium-ui'));
      await openSettings();
      assert.equal(await page.evaluate(() => orionSettings.theme), id);
      assert.equal(await page.locator('html').getAttribute('data-theme'), id);
      assert.equal(await selected.count(), 1);
      assert.equal(await selected.getAttribute('data-theme-choice'), id);
      assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()), accent);
    }
    passed.push('Every new palette is selectable, updates the effective accent and detached-panel appearance, and survives reload');

    const stored = await page.evaluate(() => localStorage.getItem(SETTINGS_KEY));
    const preview = page.locator('#gradientThemeChoices [data-theme-choice="cobalt"]');
    await preview.hover();
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'cobalt');
    assert.equal(await page.evaluate(() => localStorage.getItem(SETTINGS_KEY)), stored);
    assert.equal(await selected.getAttribute('data-theme-choice'), 'auroraglow');
    await page.mouse.move(0, 0);
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'auroraglow');
    await preview.focus();
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'cobalt');
    assert.equal(await page.evaluate(() => localStorage.getItem(SETTINGS_KEY)), stored);
    await page.locator('#settingsSearch').focus();
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'auroraglow');
    passed.push('Pointer and keyboard previews restore the saved palette without committing changes');

    await page.locator('#settingsSearch').fill('zzzzzzzzzz');
    await page.locator('#settingsEmptySearch').waitFor({state: 'visible'});
    assert.equal(await page.locator('#themesSection').isVisible(), false);
    await page.locator('#settingsSearch').fill('');
    await page.locator('#gradientThemeChoices').waitFor({state: 'visible'});
    assert.equal(await choices.count(), 17);
    assert.equal(await page.locator('#settingsEmptySearch').isVisible(), false);
    passed.push('Empty search results and clearing the search preserve the palette controls');

    await page.locator('.settings-nav-link[data-section="generalSection"]').click();
    assert.equal(await page.locator('#appearanceMode').isVisible(), true);
    await page.locator('#appearanceMode').selectOption('neon');
    await page.locator('.settings-nav-link[data-section="audioSection"]').click();
    assert.equal(await page.locator('#audioInput').isVisible(), true);
    assert.equal(await page.locator('#audioOutput').isVisible(), true);
    await page.locator('.settings-nav-link[data-section="aboutSection"]').click();
    assert.equal(await page.locator('#updateCurrent').isVisible(), true);
    assert.equal(await page.locator('#updateAutomatic').isVisible(), true);
    await page.waitForFunction(() => document.getElementById('updateCurrent').textContent === '0.6.0');
    assert.equal(await page.locator('#updateCurrentName').textContent(), 'Premium UI');
    await page.locator('#updateNotesButton').click();
    const releaseNotes = await page.locator('#updateNotes').textContent();
    for (const text of ['ORION 0.6.0', 'İşıq kolleksiyası', 'İnci işığı', 'Kobalt işığı', 'Mərcan alovu', 'Mavi laqun', 'Qütb parıltısı']) {
      assert.ok(releaseNotes.includes(text), 'Release notes include ' + text);
    }
    passed.push('About shows version 0.6.0, Premium UI, and the actual five-palette release notes');
    await page.locator('.settings-nav-link[data-section="generalSection"]').click();
    assert.equal(await page.locator('#appearanceMode').inputValue(), 'neon');
    await page.locator('#appearanceMode').selectOption('dark');
    passed.push('General, audio, and about navigation retain the existing fields and their state');

    await page.locator('.settings-nav-link[data-section="themesSection"]').click();
    for (const width of [1440, 1024, 768, 390, 360]) {
      await page.setViewportSize({width, height: 900});
      // The visualViewport listener updates dialog dimensions on the next
      // animation frame; wait for those dimensions before measuring the grid.
      await page.waitForFunction(expectedWidth => {
        const r = document.getElementById('settingsDialog').getBoundingClientRect();
        return innerWidth === expectedWidth && r.left >= -1 && r.right <= expectedWidth + 1 && r.top >= -1 && r.bottom <= 901;
      }, width, {timeout: 5000});
      await page.evaluate(() => { document.getElementById('settingsContent').scrollTop = 0; });
      const layout = await page.evaluate(() => {
        const dialog = document.getElementById('settingsDialog').getBoundingClientRect();
        const content = document.getElementById('settingsContent');
        const cards = [...document.querySelectorAll('#gradientThemeChoices .theme-choice, #themeChoices .theme-choice')]
          .filter(card => card.checkVisibility())
          .map(card => { const r = card.getBoundingClientRect(); return {id: card.dataset.themeChoice, left: r.left, right: r.right, width: r.width}; });
        return {
          dialog: {left: dialog.left, right: dialog.right, top: dialog.top, bottom: dialog.bottom},
          contentOverflow: content.scrollWidth - content.clientWidth,
          pageOverflow: document.documentElement.scrollWidth - innerWidth,
          cards
        };
      });
      assert.ok(layout.dialog.left >= -1 && layout.dialog.right <= width + 1, 'Dialog horizontal bounds at ' + width);
      assert.ok(layout.dialog.top >= -1 && layout.dialog.bottom <= 901, 'Dialog vertical bounds at ' + width);
      assert.ok(layout.contentOverflow <= 2, 'Settings content overflow at ' + width + ': ' + layout.contentOverflow);
      assert.ok(layout.pageOverflow <= 2, 'Document overflow at ' + width);
      assert.equal(layout.cards.length, 17);
      for (const card of layout.cards) {
        assert.ok(card.width > 0 && card.left >= -1 && card.right <= width + 1, card.id + ' bounds at ' + width);
      }
      await page.screenshot({path: path.join(artifacts, 'settings-gradients-' + width + '.png')});
    }
    passed.push('Dialog and all palette cards fit five desktop and mobile viewport widths without horizontal overflow');

    await page.locator('#saveSettings').click();
    await page.waitForFunction(() => !document.getElementById('saveSettings').disabled && /saxlanıldı/.test(document.getElementById('saveResult').textContent));
    assert.equal(await page.evaluate(() => JSON.parse(localStorage.getItem(SETTINGS_KEY)).theme), 'auroraglow');
    await page.keyboard.press('Escape');
    await page.locator('#settingsDialog').waitFor({state: 'hidden'});
    assert.equal(await page.locator('body').evaluate(body => body.classList.contains('settings-open')), false);
    passed.push('Save retains the selected palette and Escape closes settings cleanly');
    assert.deepEqual(errors, []);
    const baselineFaviconWarning = error => missingFavicon && error.location.url === base + '/favicon.ico'
      && error.text === 'Failed to load resource: the server responded with a status of 404 (Not Found)';
    assert.deepEqual(consoleErrors.filter(error => !baselineFaviconWarning(error)), []);
    assert.deepEqual(httpErrors.filter(error => !(missingFavicon && error.url === base + '/favicon.ico' && error.status === 404)), []);
    console.log(JSON.stringify({passed, errors, consoleErrors, httpErrors, baselineMissingFavicon: missingFavicon, artifacts}, null, 2));
  } catch (error) {
    console.error(JSON.stringify({errors, consoleErrors, httpErrors, artifacts}));
    throw error;
  } finally {
    await browser?.close();
    server.kill();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
