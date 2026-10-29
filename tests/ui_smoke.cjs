const fs=require('node:fs');
const assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const {chromium:pw}=require(process.env.ORION_PLAYWRIGHT_MODULE||'playwright');
const path=require('node:path'),os=require('node:os');
const root=path.resolve(__dirname,'..');
const artifacts=fs.mkdtempSync(path.join(os.tmpdir(),'orion-ui-results-'));
let base;

(async()=>{
 const server=spawn(process.env.ORION_UI_PYTHON||'python',[path.join(__dirname,'ui_server.py')]);let browser;
 const passed=[],errors=[];
 try {
  await new Promise((resolve,reject)=>{server.stdout.once('data',chunk=>{base=String(chunk).trim();resolve();});server.once('error',reject);server.once('exit',code=>reject(Error('Test server exited: '+code)));});
  browser=await pw.launch({headless:true,...(process.env.ORION_UI_CHROMIUM?{executablePath:process.env.ORION_UI_CHROMIUM}:{}),args:JSON.parse(process.env.ORION_UI_BROWSER_ARGS||'[]')});
  const context=await browser.newContext({viewport:{width:1380,height:900},reducedMotion:'reduce',acceptDownloads:true});
  const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));
  await page.goto(base);
  await page.request.post(base+'/api/updates/preferences',{data:{consent:false,automatic:false}});
  await page.evaluate(()=>localStorage.setItem('orion.entry.v1','1'));
  await page.reload();await page.waitForFunction(()=>window.ORIONBig&&document.querySelector('.big-card-menu'));
  const actualStatus=await (await page.request.get(base+'/api/status')).json();
  const expectedNodes=['blender','roblox','forge'].filter(key=>['hazır','qoşuldu'].includes(actualStatus.nodes?.[key]?.status)).length;
  await page.evaluate(()=>pollStatus(true));
  await page.waitForFunction(expected=>document.getElementById('statNodes').textContent===String(expected),expectedNodes);
  assert.equal(await page.locator('#nodeCount').textContent(),String(expectedNodes));
  assert.equal(await page.locator('#statNodes').textContent(),String(expectedNodes));passed.push('Node counts reflect the actual available services');

  let nodeStates={blender:{status:'qoşulmayıb'},roblox:{status:'qoşulmadı'},forge:{status:'qoşulmayıb'}};
  await page.route('**/api/status',route=>route.fulfill({json:{nodes:nodeStates}}));
  await page.evaluate(()=>pollStatus(true));
  await page.waitForFunction(()=>document.getElementById('statNodes').textContent==='0');
  assert.equal(await page.locator('#nodeCount').textContent(),'0');
  for(const id of ['blenderBridgeStatus','robloxApiStatus'])assert.equal(await page.locator('#'+id).evaluate(el=>el.classList.contains('online')),false);
  nodeStates={blender:{status:'hazır'},roblox:{status:'qoşuldu'},forge:{status:'qoşulmayıb'}};
  await page.evaluate(()=>pollStatus(true));
  await page.waitForFunction(()=>document.getElementById('statNodes').textContent==='2');
  assert.equal(await page.locator('#nodeCount').textContent(),'2');
  for(const id of ['blenderBridgeStatus','robloxApiStatus'])assert.equal(await page.locator('#'+id).evaluate(el=>el.classList.contains('online')),true);
  await page.unroute('**/api/status');await page.evaluate(()=>pollStatus(true));
  await page.waitForFunction(expected=>document.getElementById('statNodes').textContent===String(expected),expectedNodes);
  passed.push('Azerbaijani disconnected statuses stay offline while ready and connected nodes count correctly');

  await page.evaluate(()=>{
   const O=window.OrionOS,s=O.state,m=O.monthKey();s.profile.name='Murad';
   s.notes=[{id:'qa-note',title:'UI audit',text:'Button placement and mobile review',tag:'Dizayn',column:'new',priority:'high',color:'green',date:m+'-15',updated:new Date().toISOString(),checklist:[{done:false,text:'Review menus'}]},{id:'qa-done',title:'Tamamlanmış tapşırıq',text:'',tag:'',column:'done',priority:'normal',color:'blue',date:m+'-12',updated:new Date().toISOString(),checklist:[]}];
   s.transactions=[{id:'qa-income',date:m+'-05',type:'income',signed:true,amount:1200,currency:'AZN',status:'completed',account:'cash',category:'Dizayn',note:'Poster layihəsi'},{id:'qa-expense',date:m+'-07',type:'expense',signed:true,amount:-200,currency:'AZN',status:'completed',account:'card',category:'Abunəlik',note:'Creative tools'},{id:'qa-pending',date:m+'-09',type:'income',signed:true,amount:450,currency:'AZN',status:'pending',account:'card',category:'Motion',note:'Animasiya ödənişi'}];
   s.properties=[{id:'qa-property-a',name:'Ocean View',city:'Bakı',units:12,occupied:9,income:800,currency:'AZN',rating:4.8,color:'green',kind:'tower'},{id:'qa-property-b',name:'Cedar Heights',city:'Sumqayıt',units:8,occupied:7,income:600,currency:'AZN',rating:4.7,color:'blue',kind:'tower'}];
   O.touch();
  });
  await page.evaluate(()=>window.ORIONBig.whenSaved());
  await page.waitForTimeout(160);
  assert.equal(await page.locator('#completionRate').textContent(),'50%');
  await page.locator('#refreshOverview').click();
  assert.equal(await page.locator('#completionRate').textContent(),'50%');passed.push('Note completion remains consistent after server polling');

  await page.locator('.os-navigation [data-route="finance"]').click();
  await page.screenshot({path:artifacts+'/after-finance.png',fullPage:true});
  assert.equal(await page.locator('#osTransactions tbody tr').count(),3);
  await page.locator('#osTransactionAccount').selectOption('card');
  assert.equal(await page.locator('#osTransactions tbody tr').count(),2);
  await page.locator('#osTransactionFilter').selectOption('pending');
  assert.equal(await page.locator('#osTransactions tbody tr').count(),1);
  assert.match(await page.locator('#osTransactionSummary').textContent(),/1 gözlənilən/);
  assert.ok((await page.locator('#osTransactionSummary strong.income').textContent()).includes('0'));
  await page.locator('#osTransactionReset').click();
  await page.locator('#osTransactionSort').selectOption('largest');
  assert.match(await page.locator('#osTransactions tbody tr').first().textContent(),/Poster/);
  const csvPromise=page.waitForEvent('download');await page.locator('#osTransactionExport').click();
  const csv=await csvPromise;await csv.saveAs(artifacts+'/qa-ledger.csv');
  const text=fs.readFileSync(artifacts+'/qa-ledger.csv','utf8');assert.ok(text.includes('Creative tools'));assert.ok(text.includes('-200'));
  passed.push('Finance filtering, sorting, pending totals and CSV export');

  await page.locator('#osAccounts [data-action="finance-inline"]').first().click();
  await page.locator('[data-inline-amount]').fill('1500,50');await page.locator('[data-inline-amount]').press('Enter');
  const total=await page.locator('#osAccountsTotalValue').getAttribute('data-total');assert.equal(Number(total),1300.5);
  await page.locator('#osFinance .os-toolbar [data-action="income-new"]').click();
  await page.locator('#osEditor [name="amount"]').fill('125');
  await page.locator('#osEditor [name="category"]').fill('UI işi');
  await page.locator('#osEditor [type="submit"]').click();
  assert.equal(Number(await page.locator('#osAccountsTotalValue').getAttribute('data-total')),1425.5);
  passed.push('Manual account balance plus new transaction updates the total');

  await page.locator('#bigSearchButton').click();
  await page.locator('#bigSearchInput').fill('UI audit');
  assert.equal(await page.locator('[data-search-result]').count(),1);
  await page.locator('#bigSearchInput').press('Enter');
  assert.equal(await page.locator('#osEditor [name="title"]').inputValue(),'UI audit');
  await page.locator('#osEditor [data-close-editor]').first().click();passed.push('Search opens the actual matching record');

  await page.locator('.os-navigation [data-route="notes"]').click();await page.waitForTimeout(180);
  await page.locator('[data-note-id="qa-note"] [data-action="check-toggle"]').click();
  assert.equal(await page.locator('#osEditor').evaluate(e=>e.open),false);
  await page.locator('[data-note-id="qa-note"] .big-card-menu summary').click();
  assert.equal(await page.locator('#osEditor').evaluate(e=>e.open),false);
  assert.equal(await page.locator('#bigCardPopover').evaluate(e=>e.matches(':popover-open')),true);
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('#bigCardPopover').isVisible(),false);passed.push('Note controls and menu do not open the note editor');

  await page.keyboard.press('Control+k');assert.equal(await page.locator('#bigSearchDialog').evaluate(e=>e.open),true);await page.keyboard.press('Escape');
  await page.evaluate(()=>window.OrionOS.navigate('properties'));await page.waitForTimeout(180);
  await page.locator('[data-property-id="qa-property-a"] .big-card-menu summary').click();
  const popupPromise=context.waitForEvent('page');await page.locator('#bigCardPopover button').click();
  const popup=await popupPromise;await popup.waitForLoadState();await popup.waitForFunction(()=>document.querySelector('#orionWidgetContent [data-property-id]'));
  assert.equal(await popup.locator('#orionWidgetContent [data-property-id]').getAttribute('data-property-id'),'qa-property-a');
  await page.locator('#osPropertySort').selectOption('name');
  await popup.reload();await popup.waitForFunction(()=>document.querySelector('#orionWidgetContent [data-property-id]'));
  assert.equal(await popup.locator('#orionWidgetContent [data-property-id]').getAttribute('data-property-id'),'qa-property-a');await popup.close();
  passed.push('Pinned property remains the same after sorting and reloading');

  assert.equal(await page.evaluate(()=>window.OrionOS.dateValid('2026-02-31')),false);
  assert.equal(await page.evaluate(()=>window.OrionOS.dateValid('2028-02-29')),true);
  for(const [hash,id]of [['studio','bigStudio'],['agents','bigAgents'],['widgets','bigWidgets']]){
   await page.goto(base+'/#'+hash);await page.reload();await page.waitForFunction(()=>window.ORIONBig);
   assert.equal(await page.locator('#'+id).isVisible(),true);
  }
  passed.push('Direct links and reloads open the requested workspace page');
  await page.evaluate(()=>{window.OrionOS.navigate('home');chooseTheme('emerald');});
  await page.locator('#studio').scrollIntoViewIfNeeded();await page.waitForTimeout(120);
  const stepBounds=await page.locator('#studio .step-card').evaluateAll(cards=>cards.map(card=>{
   const visual=card.querySelector('.step-visual').getBoundingClientRect(),menu=card.querySelector('summary').getBoundingClientRect();
   return menu.left>=visual.left-1&&menu.right<=visual.right+1&&menu.top>=visual.top-1&&menu.bottom<=visual.bottom+1;
  }));assert.ok(stepBounds.every(Boolean));
  const oldDraft=await page.locator('#textInput').inputValue();
  await page.locator('#studio .step-card summary').first().click();
  assert.equal(await page.locator('#textInput').inputValue(),oldDraft);
  await page.screenshot({path:artifacts+'/after-steps-menu.png'});await page.keyboard.press('Escape');
  await page.locator('#overview').scrollIntoViewIfNeeded();await page.screenshot({path:artifacts+'/after-overview.png'});
  passed.push('Step-card menu stays inside the visual without triggering a chat prompt');
  const overflows=[];
  for(const width of [1380,1024,768,390,360]){
   await page.setViewportSize({width,height:900});
   for(const route of ['home','finance','notes','properties','notebook','statistics','studio','agents','widgets','profile']){
    await page.evaluate(route=>window.OrionOS.navigate(route),route);await page.waitForTimeout(80);
    const check=await page.evaluate(()=>({route:window.OrionOS.route,width:innerWidth,scroll:document.documentElement.scrollWidth}));
    if(check.scroll>width+2)overflows.push(check);
   }
   await page.evaluate(()=>window.OrionOS.navigate('finance'));await page.screenshot({path:artifacts+'/after-finance-'+width+'.png',fullPage:true});
  }
  await page.setViewportSize({width:390,height:844});
  await page.locator('#bigMobileSearch').click();
  await page.locator('#bigSearchInput').fill('Poster');
  assert.equal(await page.locator('[data-search-result]').count(),1);
  await page.screenshot({path:artifacts+'/after-mobile-search.png'});await page.keyboard.press('Escape');
  await page.reload();await page.waitForFunction(()=>window.ORIONBig);
  assert.equal(Number(await page.locator('#osAccountsTotalValue').getAttribute('data-total')),1425.5);
  passed.push('Mobile search and persisted finance state after reload');
  const panel=await context.newPage();panel.on('pageerror',error=>errors.push(error.message));
  for(const width of [740,540,390,360]){
   await panel.setViewportSize({width,height:width>540?260:440});await panel.goto(base+'/panel');
   await panel.waitForSelector('#homeView:not([hidden])');
   assert.equal(await panel.locator('.quick-grid').isVisible(),true);
   assert.equal(await panel.locator('.quick-grid button:visible').count(),4);
   const overflow=await panel.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2);assert.equal(overflow,false);
   await panel.screenshot({path:artifacts+'/after-panel-'+width+'.png'});
  }
  await panel.locator('.quick-grid [data-mode="chat"]').click();
  await panel.waitForSelector('#chatView:not([hidden])');
  passed.push('All four robot-panel home actions remain reachable at narrow widths');
  await panel.close();
  console.log(JSON.stringify({passed,errors,overflows,artifacts},null,2));
  assert.deepEqual(errors,[]);assert.deepEqual(overflows,[]);
 }finally{await browser?.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
