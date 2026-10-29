/* Optional browser regression: node tests/ui_mini_update.cjs (Playwright). */
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {spawn}=require('node:child_process');
const {chromium}=require(process.env.ORION_PLAYWRIGHT_MODULE||'playwright');

(async()=>{
 const server=spawn(process.env.ORION_UI_PYTHON||'python',[path.join(__dirname,'ui_server.py')]);
 const artifacts=fs.mkdtempSync(path.join(os.tmpdir(),'orion-mini-'));
 let browser;const errors=[],passed=[];
 try{
  const base=await new Promise((resolve,reject)=>{server.stdout.once('data',data=>resolve(String(data).trim()));server.once('error',reject);});
  const launch=()=>chromium.launch({headless:true,...(process.env.ORION_UI_CHROMIUM?{executablePath:process.env.ORION_UI_CHROMIUM}:{}),args:JSON.parse(process.env.ORION_UI_BROWSER_ARGS||'[]')});
  browser=await launch();
  const context=await browser.newContext({viewport:{width:1380,height:900}}),page=await context.newPage();
  page.on('pageerror',e=>errors.push(e.message));
  await page.request.post(base+'/api/updates/preferences',{data:{consent:false,automatic:false}});
  await page.goto(base);await page.waitForFunction(()=>window.ORIONBig&&document.querySelector('#bigEntryPasswordMeter[data-enhanced]'));
  const meter=page.locator('#bigEntryPasswordMeter'),input=page.locator('#bigEntryPassword'),eye=meter.locator('.vs-password-meter-eye');
  await page.waitForFunction(()=>document.getElementById('bigEntry').open);
  await page.evaluate(()=>document.fonts.ready);
  assert.match(await meter.locator('label').evaluate(e=>getComputedStyle(e).fontFamily),/Euclid Circular A/);
  assert.equal(await meter.locator('label').getAttribute('for'),'bigEntryPassword');
  assert.equal(await page.evaluate(async()=>(await document.fonts.load('400 16px "JetBrains Mono"','ƏəĞğŞşİı')).length>0),true);
  assert.equal(await input.getAttribute('autocomplete'),'new-password');
  await input.fill('Password123!');
  assert.equal(await meter.locator('[data-rule="common"]').evaluate(e=>e.classList.contains('is-met')),false);
  assert.match(await meter.locator('.vs-password-meter-word').textContent(),/Çox yayılmış/);
  await input.fill('ƏəĞğ1234');
  assert.equal(await meter.locator('[data-rule="case"]').evaluate(e=>e.classList.contains('is-met')),true);
  assert.equal(await meter.locator('[data-rule="symbol"]').evaluate(e=>e.classList.contains('is-met')),false);
  await input.fill('Q7!mZ2@xR9#vL4$pT8&k');
  await page.waitForFunction(()=>document.querySelector('#bigEntryPasswordMeter .vs-password-meter-word').textContent.includes('Çox güclü'));
  assert.equal(await meter.locator('.vs-password-meter-rules li.is-met').count(),5);
  await input.focus();await input.evaluate(e=>e.setSelectionRange(3,8));await eye.click();
  assert.equal(await input.getAttribute('type'),'text');assert.equal(await eye.getAttribute('aria-pressed'),'true');
  assert.deepEqual(await input.evaluate(e=>[document.activeElement===e,e.selectionStart,e.selectionEnd]),[true,3,8]);
  await page.waitForFunction(()=>[...document.querySelectorAll('#bigEntryPasswordMeter .vs-password-meter-ch b')].map(n=>n.textContent).join('')===document.getElementById('bigEntryPassword').value);
  await eye.click();assert.equal(await input.getAttribute('type'),'password');
  await input.evaluate(e=>e.dispatchEvent(new KeyboardEvent('keydown',{key:'CapsLock',modifierCapsLock:true,bubbles:true})));
  assert.equal(await meter.evaluate(e=>e.classList.contains('is-caps')),true);
  await input.blur();assert.equal(await meter.evaluate(e=>e.classList.contains('is-caps')),false);
  await page.waitForFunction(()=>{const root=document.getElementById('bigEntryPasswordMeter'),chars=root.querySelectorAll('.vs-password-meter-ch');return chars.length===root.value.length&&[...chars].every(c=>Number(getComputedStyle(c.querySelector('i')).opacity)>.99);});
  await page.screenshot({path:path.join(artifacts,'entry-register-desktop.png')});
  passed.push('Supplied password meter recognizes common passwords and Azerbaijani letters, animates reveal, retains caret and detects Caps Lock');

  for(const width of [390,360]){
   await page.setViewportSize({width,height:900});await input.fill('Q7!mZ2@xR9#vL4$pT8&k');await input.scrollIntoViewIfNeeded();
   const layout=await meter.evaluate(root=>{const box=root.getBoundingClientRect();return {fits:box.left>=0&&box.right<=innerWidth,overflow:root.scrollWidth>root.clientWidth+1,fieldHeight:root.querySelector('.vs-password-meter-field').getBoundingClientRect().height,inputHeight:root.querySelector('input').getBoundingClientRect().height};});
   assert.equal(layout.fits,true);assert.equal(layout.overflow,false);assert.equal(layout.fieldHeight,layout.inputHeight);
   assert.equal(await page.locator('#bigEntry').evaluate(e=>e.scrollWidth>e.clientWidth+1),false);
   await page.screenshot({path:path.join(artifacts,'entry-register-'+width+'.png')});
  }
  await page.setViewportSize({width:1380,height:900});
  await page.locator('[data-entry-kind="login"]').click();
  assert.equal(await input.getAttribute('autocomplete'),'current-password');
  assert.equal(await meter.locator('.vs-password-meter-rules').isVisible(),false);
  assert.equal(await meter.locator('.vs-password-meter-status').isVisible(),false);
  await page.screenshot({path:path.join(artifacts,'entry-login.png')});
  await page.locator('[data-entry-kind="register"]').click();
  await page.locator('#bigEntryName').fill('Mini QA');await page.locator('#bigEntryEmail').fill('mini.qa@example.test');
  await input.fill('password123');await eye.click();await page.locator('#bigEntrySubmit').click();
  await page.waitForFunction(()=>!document.getElementById('bigEntry').open);
  assert.equal(await input.inputValue(),'');assert.equal(await input.getAttribute('type'),'password');
  assert.equal(await meter.locator('.vs-password-meter-ch').count(),0);
  assert.equal(await page.evaluate(()=>JSON.stringify(localStorage).includes('password123')),false);
  await page.evaluate(()=>window.OrionOS.actions.get('logout')());
  await page.waitForFunction(()=>document.getElementById('bigEntry').open);
  assert.equal(await meter.getAttribute('data-mode'),'login');
  await input.fill('wrong-password');await page.locator('#bigEntrySubmit').click();
  await page.waitForFunction(()=>document.getElementById('bigEntryError').textContent.includes('düzgün deyil'));
  assert.equal(await input.inputValue(),'wrong-password');
  await input.fill('password123');await page.locator('#bigEntrySubmit').click();
  await page.waitForFunction(()=>!document.getElementById('bigEntry').open);
  assert.equal(await meter.locator('.vs-password-meter-ch').count(),0);
  passed.push('Real registration, failed login and successful login preserve existing validation and clear the field, reveal state and mirror on success');

  const panel=await context.newPage();panel.on('pageerror',e=>errors.push(e.message));
  await panel.setViewportSize({width:560,height:900});await panel.goto(base+'/panel');await panel.waitForFunction(()=>window.ORIONPanel);
  await panel.locator('.quick-grid [data-mode="chat"]').click();
  for(const name of ['emerald','purple','aurora']){
   const appearance=await page.evaluate(name=>{chooseTheme(name);const t=THEMES[name];return {theme:name,name:t.name,light:false,accent:t.accent,secondary:t.secondary,background:t.bg,surface:t.surface,raised:t.raised,muted:t.muted,text:t.light};},name),accent=appearance.accent;
   await page.request.post(base+'/api/panel/appearance',{data:appearance});await panel.evaluate(()=>window.ORIONPanel.refresh());
   const border=await panel.locator('#panel').evaluate(e=>({line:getComputedStyle(e,'::before').backgroundImage,glow:getComputedStyle(e,'::after').backgroundImage,radius:getComputedStyle(e).borderTopLeftRadius}));
   assert.equal(border.radius,'26px');
   const rgb=accent.match(/\w\w/g).map(v=>parseInt(v,16)).join(', ');
   assert.ok(border.line.includes(rgb));assert.ok(border.glow.includes(rgb));
   await panel.screenshot({path:path.join(artifacts,'chat-'+name+'.png')});
   await panel.locator('#closeChatButton').click();await panel.setViewportSize({width:300,height:56});
   const shape=await panel.locator('#panel').evaluate(e=>{const s=getComputedStyle(e);return [s.borderTopLeftRadius,s.borderTopRightRadius,s.borderBottomLeftRadius,s.borderBottomRightRadius];});
   assert.deepEqual(shape,['28px','28px','28px','28px']);
   assert.equal(await panel.locator('#peekStatus').evaluate(e=>e.scrollWidth>e.clientWidth+1),false);
   assert.ok((await panel.locator('#panel').evaluate(e=>getComputedStyle(e,'::after').backgroundImage)).includes(rgb));
   for(const b of await panel.locator('.peek button').all()){
    const box=await b.boundingBox();assert.ok(box.x>=0&&box.y>=0&&box.x+box.width<=300&&box.y+box.height<=56);
   }
   await panel.screenshot({path:path.join(artifacts,'peek-'+name+'.png')});
   await panel.locator('#expandButton').click();await panel.setViewportSize({width:560,height:900});
  }
  passed.push('Open and collapsed panels follow three selected accent colors; all capsule corners are rounded and controls/status fit');
  await browser.close();browser=await launch();
  const reduced=await browser.newContext({viewport:{width:390,height:850},reducedMotion:'reduce',hasTouch:true}),quiet=await reduced.newPage();quiet.on('pageerror',e=>errors.push(e.message));
  await quiet.request.post(base+'/api/workspace/logout',{data:{}});await quiet.goto(base);await quiet.waitForFunction(()=>document.getElementById('bigEntry')?.open);
  await quiet.locator('#bigEntryPassword').fill('password123');await quiet.locator('.vs-password-meter-eye').tap();
  assert.equal(await quiet.locator('#bigEntryPassword').getAttribute('type'),'text');
  assert.ok(await quiet.locator('.vs-password-meter-eye').evaluate(e=>parseFloat(getComputedStyle(e).transitionDuration)<=.01));
  assert.equal(await quiet.locator('.vs-password-meter-ch.is-scr').count(),0);
  passed.push('Touch reveal and reduced-motion mode both work');
  assert.deepEqual(errors,[]);console.log(JSON.stringify({passed,errors,artifacts},null,2));
 }catch(error){console.error(JSON.stringify({errors,artifacts}));throw error;}finally{await browser?.close();server.kill();}
})().catch(error=>{console.error(error);process.exitCode=1;});
