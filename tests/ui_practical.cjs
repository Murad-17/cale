/* Optional browser regression checks: node tests/ui_practical.cjs (Playwright). */
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {spawn}=require('node:child_process');
const {chromium}=require(process.env.ORION_PLAYWRIGHT_MODULE||'playwright');

(async()=>{
 const server=spawn(process.env.ORION_UI_PYTHON||'python',[path.join(__dirname,'ui_server.py')]);
 const artifacts=fs.mkdtempSync(path.join(os.tmpdir(),'orion-060-'));
 let browser;const errors=[],passed=[];
 try{
  const base=await new Promise((resolve,reject)=>{server.stdout.once('data',data=>resolve(String(data).trim()));server.once('error',reject);});
  browser=await chromium.launch({headless:true,...(process.env.ORION_UI_CHROMIUM?{executablePath:process.env.ORION_UI_CHROMIUM}:{}),args:JSON.parse(process.env.ORION_UI_BROWSER_ARGS||'[]')});
  const context=await browser.newContext({viewport:{width:1380,height:900},reducedMotion:'no-preference'});
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base);await page.request.post(base+'/api/updates/preferences',{data:{consent:false,automatic:false}});
  await page.evaluate(()=>localStorage.setItem('orion.entry.v1','1'));await page.reload();
  await page.waitForFunction(()=>window.ORIONBig);await page.evaluate(()=>document.fonts.ready);
  assert.equal(await page.locator('#mainTitle').isVisible(),true);
  assert.ok((await page.locator('#orionGreetingAccessible').textContent()).trim().length>0);
  for(const weight of [300,400,500,600,700]){
   assert.equal(await page.evaluate(async weight=>(await document.fonts.load(weight+' 16px "Euclid Circular A"','Əə')).length>0,weight),true);
   assert.equal(await page.evaluate(async weight=>(await document.fonts.load('italic '+weight+' 16px "Euclid Circular A"','Əə')).length>0,weight),true);
  }
  assert.match(await page.locator('body').evaluate(e=>getComputedStyle(e).fontFamily),/Euclid Circular A/);passed.push('All ten supplied font faces load, including Azerbaijani glyphs');
  await page.evaluate(()=>{const O=window.OrionOS;O.state.notes=[{id:'completed',title:'Tamamlandı',text:'',checklist:[],tag:'',column:'done',priority:'normal',color:'green',date:O.today()}];O.touch();chooseTheme('emerald');});
  for(const width of [1380,1024,768,390,360]){
   await page.setViewportSize({width,height:900});await page.evaluate(()=>window.OrionOS.navigate('home'));
   await page.locator('#overview').scrollIntoViewIfNeeded();await page.waitForFunction(()=>Number(getComputedStyle(document.getElementById('overview')).opacity)>.99);
   await page.mouse.move(0,0);
   await page.waitForFunction(()=>Array.from(document.querySelectorAll('#overview .metric-card')).every(card=>getComputedStyle(card).transform==='none'));
   const metrics=await page.locator('#overview .metric-card').evaluateAll(cards=>cards.map(card=>{
    const r=selector=>card.querySelector(selector).getBoundingClientRect(),label=r('.metric-label'),chart=r('svg'),number=r('.metric-number'),note=r('p');
    return {cardTop:card.getBoundingClientRect().top,labelEnd:label.bottom,chartStart:chart.top,chartEnd:chart.bottom,numberStart:number.top,numberEnd:number.bottom,noteStart:note.top};
   }));
   for(const m of metrics){assert.ok(m.labelEnd<=m.chartStart+1);assert.ok(m.chartEnd<m.numberStart);assert.ok(m.numberEnd<=m.noteStart+1);}
   if(width>760)assert.ok(Math.max(...metrics.map(m=>m.numberStart-m.cardTop))-Math.min(...metrics.map(m=>m.numberStart-m.cardTop))<2,JSON.stringify({width,metrics}));
   if(width===1380||width===390)await page.screenshot({path:path.join(artifacts,'metrics-'+width+'.png')});
   await page.evaluate(()=>window.OrionOS.navigate('studio'));await page.evaluate(()=>document.fonts.ready);
   await page.waitForFunction(()=>Array.from(document.querySelectorAll('#bigStudio .big-node-number')).every(badge=>Math.abs(badge.getBoundingClientRect().width-parseFloat(getComputedStyle(badge).width))<.05));
   const badges=await page.locator('#bigStudio .big-node-number').evaluateAll(nodes=>nodes.map(node=>{
    const range=document.createRange();range.selectNodeContents(node);const text=range.getBoundingClientRect(),box=node.getBoundingClientRect();
    return {delta:Math.abs((text.left+text.right-box.left-box.right)/2),padding:getComputedStyle(node).paddingRight,width:box.width};
   }));for(const b of badges){assert.ok(b.delta<2);assert.equal(b.padding,'0px');assert.ok(Math.abs(b.width-30)<.05);}
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2),false);
   if(width===1380||width===390)await page.screenshot({path:path.join(artifacts,'studio-'+width+'.png')});
  }
  passed.push('Metric values and studio badges align at five viewport widths');
  await page.setViewportSize({width:1380,height:900});
  await page.evaluate(()=>{window.OrionOS.navigate('settings');setSettingsSection('aboutSection');});
  await page.waitForFunction(()=>document.getElementById('updateCurrent').textContent==='0.6.0');
  assert.equal(await page.locator('#updateCurrentName').textContent(),'Premium UI');
  await page.locator('#updateNotesButton').click();assert.match(await page.locator('#updateNotes').textContent(),/0\.6\.0 — Premium UI/);passed.push('Updates displays version 0.6.0 and its actual release name and notes');

  const panel=await context.newPage();panel.on('pageerror',e=>errors.push(e.message));
  await panel.setViewportSize({width:740,height:260});await panel.goto(base+'/panel');await panel.waitForFunction(()=>window.ORIONPanel&&window.ORIONRobot);
  await panel.waitForFunction(()=>!document.getElementById('draft').disabled);await panel.evaluate(()=>document.fonts.ready);
  assert.match(await panel.locator('body').evaluate(e=>getComputedStyle(e).fontFamily),/Euclid Circular A/);
  const pose=await panel.locator('#homeMascot .robot-pose').evaluate(e=>getComputedStyle(e).transform);
  await panel.waitForFunction(before=>getComputedStyle(document.querySelector('#homeMascot .robot-pose')).transform!==before,pose);
  await panel.screenshot({path:path.join(artifacts,'panel-home.png')});
  await panel.locator('.quick-grid [data-mode="chat"]').click();await panel.setViewportSize({width:560,height:900});
  await panel.locator('#draft').fill('Qaralamam saxlanılır — 0.5.9');
  const border=await panel.locator('#panel').evaluate(el=>{const p=getComputedStyle(el,'::after');return {background:p.backgroundImage,events:p.pointerEvents,padding:parseFloat(p.paddingTop),filter:p.filter,mask:p.maskComposite};});
  assert.match(border.background,/linear-gradient/);assert.equal(border.events,'none');assert.ok(Math.abs(border.padding-1.4)<.05);assert.equal(border.filter,'none');assert.ok(border.mask.split(',').every(value=>value.trim()==='exclude'));
  await panel.screenshot({path:path.join(artifacts,'panel-chat.png')});
  await panel.locator('#closeChatButton').click();assert.equal(await panel.locator('body').getAttribute('data-mode'),'home');
  await panel.locator('#collapseButton').click();await panel.setViewportSize({width:300,height:56});
  assert.equal(await panel.locator('body').getAttribute('data-mode'),'peek');
  const controls=await panel.locator('.peek button').evaluateAll(nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight;}));assert.ok(controls.every(Boolean));
  await panel.screenshot({path:path.join(artifacts,'panel-peek.png')});
  await panel.locator('#expandButton').click();await panel.setViewportSize({width:560,height:900});
  assert.equal(await panel.locator('body').getAttribute('data-mode'),'home');await panel.locator('#chatButton').click();assert.equal(await panel.locator('body').getAttribute('data-mode'),'chat');assert.equal(await panel.locator('#draft').inputValue(),'Qaralamam saxlanılır — 0.5.9');passed.push('Chat returns home, the home panel collapses to its capsule, and reopening chat preserves its draft');
  await panel.route('**/api/jobs?thread=*',route=>route.fulfill({json:{jobs:[{id:'qa-thinking',kind:'chat',status:'running',label:'Offline QA'}]}}));
  await panel.evaluate(()=>window.ORIONPanel.refresh());
  assert.equal(await panel.evaluate(()=>window.ORIONRobot.state().activity),'thinking');passed.push('Robot movement and thinking state track the actual panel job status');
  const reduced=await browser.newContext({viewport:{width:740,height:260},reducedMotion:'reduce'}),quiet=await reduced.newPage();await quiet.goto(base+'/panel');
  await quiet.waitForFunction(()=>window.ORIONRobot);assert.equal(await quiet.locator('#homeMascot .robot-pose').evaluate(e=>getComputedStyle(e).transform),'none');
  assert.equal(await quiet.locator('#panel').evaluate(e=>getComputedStyle(e,'::after').animationName),'none');passed.push('Reduced-motion preference disables robot and edge movement');
  assert.deepEqual(errors,[]);console.log(JSON.stringify({passed,errors,artifacts},null,2));
 }finally{await browser?.close();server.kill();}
})().catch(error=>{console.error(error);process.exitCode=1;});
