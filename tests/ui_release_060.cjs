/* ORION 0.6.0 supported-workflow browser check.
 * Exercises the controls present in this release; older ui_smoke/ui_mini_update
 * suites retain their separate expectations for unintegrated features.
 */
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {spawn}=require('node:child_process');
const {chromium}=require(process.env.ORION_PLAYWRIGHT_MODULE||'playwright');

(async()=>{
 const server=spawn(process.env.ORION_UI_PYTHON||'python',[path.join(__dirname,'ui_server.py')]);
 const artifacts=process.env.ORION_UI_ARTIFACTS||fs.mkdtempSync(path.join(os.tmpdir(),'orion-release-060-'));
 fs.mkdirSync(artifacts,{recursive:true});
 let browser,page;const passed=[],errors=[];
 try{
  const base=await new Promise((resolve,reject)=>{server.stdout.once('data',data=>resolve(String(data).trim()));server.once('error',reject);});
  browser=await chromium.launch({headless:true,...(process.env.ORION_UI_CHROMIUM?{executablePath:process.env.ORION_UI_CHROMIUM}:{}),args:JSON.parse(process.env.ORION_UI_BROWSER_ARGS||'[]')});
  const context=await browser.newContext({viewport:{width:1380,height:900},reducedMotion:'reduce'});
  page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));
  await page.request.post(base+'/api/updates/preferences',{data:{consent:false,automatic:false}});
  await page.goto(base);await page.evaluate(()=>localStorage.setItem('orion.entry.v1','1'));await page.reload();
  await page.waitForFunction(()=>window.ORIONBig&&document.body.classList.contains('premium-ui'));
  let nodes={blender:{status:'qoşulmayıb'},roblox:{status:'qoşulmadı'},forge:{status:'qoşulmayıb'}};
  await page.route('**/api/status',route=>route.fulfill({json:{nodes}}));
  await page.evaluate(()=>pollStatus(true));await page.waitForFunction(()=>document.getElementById('statNodes').textContent==='0');
  assert.equal(await page.locator('#nodeCount').textContent(),'0');
  for(const id of ['blenderBridgeStatus','robloxApiStatus'])assert.equal(await page.locator('#'+id).evaluate(el=>el.classList.contains('online')),false);
  nodes={blender:{status:'hazır'},roblox:{status:'qoşuldu'},forge:{status:'qoşulmayıb'}};
  await page.evaluate(()=>pollStatus(true));await page.waitForFunction(()=>document.getElementById('statNodes').textContent==='2');
  assert.equal(await page.locator('#nodeCount').textContent(),'2');
  for(const id of ['blenderBridgeStatus','robloxApiStatus'])assert.equal(await page.locator('#'+id).evaluate(el=>el.classList.contains('online')),true);
  await page.unroute('**/api/status');await page.evaluate(()=>pollStatus(true));
  passed.push('Disconnected Azerbaijani statuses stay offline; ready/connected statuses update both counts and badges');

  await page.evaluate(()=>{
   const O=window.OrionOS,s=O.state,m=O.monthKey();
   s.profile.name='Release QA';
   s.notes=[{id:'release-note',title:'Release review',text:'Gradient and workflow review',tag:'Dizayn',column:'new',priority:'high',color:'green',date:m+'-15',updated:new Date().toISOString(),checklist:[{done:false,text:'Review menus'}]},{id:'release-done',title:'Tamamlanmış qeyd',text:'',tag:'',column:'done',priority:'normal',color:'blue',date:m+'-12',updated:new Date().toISOString(),checklist:[]}];
   s.transactions=[{id:'release-income',date:m+'-05',type:'income',signed:true,amount:1200,currency:'AZN',status:'completed',account:'cash',category:'Dizayn',note:'Poster layihəsi'},{id:'release-expense',date:m+'-07',type:'expense',signed:true,amount:-200,currency:'AZN',status:'completed',account:'card',category:'Abunəlik',note:'Creative tools'},{id:'release-pending',date:m+'-09',type:'income',signed:true,amount:450,currency:'AZN',status:'pending',account:'card',category:'Motion',note:'Animasiya ödənişi'}];
   O.touch();
  });
  await page.evaluate(()=>window.ORIONBig.whenSaved());
  assert.equal(await page.locator('#completionRate').textContent(),'50%');
  await page.locator('#refreshOverview').click();
  await page.waitForFunction(()=>!document.getElementById('refreshOverview').disabled);
  assert.equal(await page.locator('#completionRate').textContent(),'50%');
  passed.push('Workspace-note completion remains 50% after refreshing backend tasks and status');

  await page.evaluate(()=>window.OrionOS.navigate('finance'));
  assert.equal(await page.locator('#osTransactions tbody tr').count(),3);
  await page.locator('#osTransactionFilter').selectOption('pending');assert.equal(await page.locator('#osTransactions tbody tr').count(),1);
  assert.match(await page.locator('#osTransactions tbody').textContent(),/Animasiya/);
  await page.locator('#osTransactionFilter').selectOption('income');assert.equal(await page.locator('#osTransactions tbody tr').count(),2);
  await page.locator('#osTransactionFilter').selectOption('expense');assert.equal(await page.locator('#osTransactions tbody tr').count(),1);
  assert.match(await page.locator('#osTransactions tbody').textContent(),/Creative tools/);
  await page.locator('#osTransactionFilter').selectOption('all');await page.locator('#osTransactionSearch').fill('Poster');
  assert.equal(await page.locator('#osTransactions tbody tr').count(),1);
  await page.locator('#osTransactionSearch').fill('');assert.equal(await page.locator('#osTransactions tbody tr').count(),3);
  await page.locator('#osAccounts [data-action="finance-inline"]').first().click();
  await page.locator('[data-inline-amount]').fill('1500,50');await page.locator('[data-inline-amount]').press('Enter');
  assert.equal(Number(await page.locator('#osAccountsTotalValue').getAttribute('data-total')),1300.5);
  await page.locator('#osFinance .os-toolbar [data-action="income-new"]').click();
  await page.locator('#osEditor [name="amount"]').fill('125');await page.locator('#osEditor [name="category"]').fill('UI işi');
  await page.locator('#osEditor [type="submit"]').click();
  await page.waitForFunction(()=>!document.getElementById('osEditor').open);
  await page.waitForFunction(()=>Number(document.getElementById('osAccountsTotalValue').dataset.total)===1425.5);
  assert.equal(Number(await page.locator('#osAccountsTotalValue').getAttribute('data-total')),1425.5);
  await page.evaluate(()=>window.ORIONBig.whenSaved());
  await page.screenshot({path:path.join(artifacts,'finance-desktop.png')});
  passed.push('Existing finance type/status filters, text search, balance editing, and income creation work');

  await page.evaluate(()=>window.OrionOS.navigate('notes'));
  await page.locator('[data-note-id="release-note"] [data-action="check-toggle"]').click();
  assert.equal(await page.locator('#osEditor').evaluate(el=>el.open),false);
  assert.equal(await page.evaluate(()=>window.OrionOS.state.notes.find(note=>note.id==='release-note').checklist[0].done),true);
  await page.evaluate(()=>window.ORIONBig.whenSaved());
  await page.reload();await page.waitForFunction(()=>window.ORIONBig);
  assert.equal(await page.evaluate(()=>window.OrionOS.state.notes.find(note=>note.id==='release-note').checklist[0].done),true);
  await page.evaluate(()=>window.OrionOS.navigate('finance'));
  assert.equal(Number(await page.locator('#osAccountsTotalValue').getAttribute('data-total')),1425.5);
  passed.push('Note checklist controls retain state without opening the editor; note and finance edits survive reload');

  for(const [route,id] of [['studio','bigStudio'],['agents','bigAgents'],['widgets','bigWidgets']]){
   await page.goto(base+'/#'+route);await page.waitForFunction(()=>window.ORIONBig);
   assert.equal(await page.locator('#'+id).isVisible(),true);
  }
  const overflow=[];
  for(const width of [1380,1024,768,390,360]){
   await page.setViewportSize({width,height:900});
   await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
   for(const route of ['home','finance','notes','properties','notebook','statistics','studio','agents','widgets','profile']){
    await page.evaluate(route=>window.OrionOS.navigate(route),route);
    await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(resolve)));
    const measurement=await page.evaluate(()=>({route:window.OrionOS.route,width:innerWidth,scroll:document.documentElement.scrollWidth}));
    if(measurement.scroll>width+2)overflow.push(measurement);
   }
  }
  assert.deepEqual(overflow,[]);
  passed.push('Direct links open studio/agents/widgets; ten supported routes fit five viewport widths');

  const panel=await context.newPage();panel.on('pageerror',error=>errors.push(error.message));
  for(const width of [740,540,390,360]){
   await panel.setViewportSize({width,height:width>540?260:440});await panel.goto(base+'/panel');
   await panel.waitForFunction(()=>window.ORIONPanel);
   await panel.waitForSelector('#homeView:not([hidden])');
   if(width>520)assert.equal(await panel.locator('.quick-grid button:visible').count(),4);
   else{
    assert.equal(await panel.locator('.quick-grid').isVisible(),false);
    for(const id of ['homeButton','chatButton','fileButton','settingsButton']){
     assert.equal(await panel.locator('#'+id).isVisible(),true);
     const box=await panel.locator('#'+id).boundingBox();assert.ok(box.x>=0&&box.x+box.width<=width);
    }
   }
   assert.equal(await panel.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2),false);
  }
  await panel.locator('#chatButton').click();await panel.waitForSelector('#chatView:not([hidden])');
  await panel.setViewportSize({width:560,height:900});
  await panel.locator('#draft').fill('0.6.0 saxlanılan qaralama');
  await panel.locator('#closeChatButton').click();assert.equal(await panel.locator('body').getAttribute('data-mode'),'home');
  await panel.locator('#collapseButton').click();await panel.setViewportSize({width:300,height:56});
  assert.equal(await panel.locator('body').getAttribute('data-mode'),'peek');
  await panel.locator('#expandButton').click();await panel.setViewportSize({width:560,height:900});
  assert.equal(await panel.locator('body').getAttribute('data-mode'),'home');await panel.locator('#chatButton').click();
  assert.equal(await panel.locator('#draft').inputValue(),'0.6.0 saxlanılan qaralama');
  await panel.screenshot({path:path.join(artifacts,'panel-chat.png')});
  passed.push('Panel quick actions and compact navigation match their responsive layouts; returning home and collapsing preserve the chat draft');
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({passed,errors,overflow,artifacts},null,2));
 }catch(error){
  const diagnostic=await page?.evaluate(()=>({editorOpen:document.getElementById('osEditor').open,error:document.getElementById('osEditorError').textContent,invalid:[...document.querySelectorAll('#osEditor input,#osEditor select,#osEditor textarea')].filter(field=>!field.checkValidity()).map(field=>({name:field.name,value:field.value,message:field.validationMessage})),transactions:window.OrionOS.state.transactions,month:window.OrionOS.finance.selectedMonth()}));
  await page?.screenshot({path:path.join(artifacts,'failure.png')});
  console.error(JSON.stringify({passed,errors,diagnostic,artifacts}));throw error;
 }
 finally{await browser?.close();server.kill();}
})().catch(error=>{console.error(error);process.exitCode=1;});
