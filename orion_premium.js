/* Presentation layer. Existing workspace records, settings and actions stay authoritative. */
(()=>{
 'use strict';
 const O=window.OrionOS,B=window.ORIONBig;
 if(!O||!B)return;
 const $=id=>document.getElementById(id),e=O.esc,icon=O.icon;
 document.body.classList.add('premium-ui');
 const reduced=matchMedia('(prefers-reduced-motion: reduce)');
 const nav=document.querySelector('.os-navigation');
 document.querySelector('.icon-library defs').insertAdjacentHTML('beforeend','<symbol id="i-nav-wallet" viewBox="0 0 24 24"><path d="M20 7H5a2 2 0 0 1 0-4h13v4M3 5v14a2 2 0 0 0 2 2h15V7M16 12h5v5h-5a2.5 2.5 0 0 1 0-5Z"/></symbol><symbol id="i-nav-note" viewBox="0 0 24 24"><path d="M14 3H5v18h14V8l-5-5ZM14 3v5h5M8 12h8M8 16h5"/></symbol><symbol id="i-nav-book" viewBox="0 0 24 24"><path d="M12 5C8 2 5 3 3 4v15c3-1 6-1 9 2m0-16c4-3 7-2 9-1v15c-3-1-6-1-9 2V5Z"/></symbol><symbol id="i-nav-chart" viewBox="0 0 24 24"><path d="M3 3v18h18M8 16v-5M13 16V7M18 16v-9"/></symbol><symbol id="i-nav-sidebar" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="3"/><path d="M9 4v16M5.5 8h1M5.5 11h1"/></symbol>');
 const primary=[['home','grid','Ana səhifə'],['finance','nav-wallet','Maliyyə'],['notes','nav-note','İş sahəsi'],['studio','play','Studiya'],['agents','spark','Köməkçilər']];
 const secondary=[['widgets','expand','Tablarım'],['notebook','nav-book','Sual dəftəri'],['properties','cube','Mülklər'],['statistics','nav-chart','Statistika']];
 const routeButton=([route,ic,label])=>'<button type="button" class="os-nav-item" data-route="'+route+'" aria-label="'+label+'" title="'+label+'">'+icon(ic)+'<span>'+label+'</span></button>';
 const menuButton=(label,ic,attribute)=>'<button type="button" '+attribute+'>'+icon(ic)+'<span>'+label+'</span></button>';
 nav.innerHTML='<span id="premiumNavMarker" class="premium-nav-marker" aria-hidden="true"></span><div class="premium-nav-header"><a class="os-nav-brand" href="#home" data-route="home" aria-label="ORION ana səhifə">'+icon('orbit')+'<span>ORION<small>ŞƏXSİ İŞ SAHƏN</small></span></a><button type="button" id="premiumSidebarToggle" class="premium-plain-icon" aria-label="Sol menyunu yığ" title="Sol menyunu yığ" aria-expanded="true">'+icon('nav-sidebar')+'</button></div>'+
  '<div class="premium-nav-primary"><button type="button" id="premiumNewChat" class="premium-nav-new" title="Söhbəti aç">'+icon('plus')+'<span>ORION ilə danış</span><kbd>↵</kbd></button>'+primary.map(routeButton).join('')+'</div>'+
  '<div class="premium-nav-scroll"><span class="premium-nav-group">İş alətlərin</span>'+secondary.map(routeButton).join('')+'<span class="premium-nav-group">Son qeydlər</span><div id="premiumRecentNotes" class="premium-nav-recents"></div><span class="premium-nav-group">Son fəaliyyətlər</span><div id="premiumRecentActivity" class="premium-nav-recents"></div></div>'+
  '<details class="big-more"><summary aria-label="Digər bölmələr">'+icon('menu')+'<span>Daha çox</span></summary><div>'+secondary.map(routeButton).join('')+routeButton(['profile','lock','Profil'])+routeButton(['settings','settings','Ayarlar'])+menuButton('Giriş ekranı','lock','data-big="entry"')+'</div></details>'+
  '<div class="premium-nav-footer">'+routeButton(['settings','settings','Ayarlar'])+'<details id="premiumAccount" class="premium-account"><summary aria-label="Profil menyusu"><span id="premiumAccountAvatar" class="premium-account-avatar">O</span><span class="premium-account-copy"><strong id="premiumAccountName">Şəxsi profil</strong><small>Bu cihazdakı iş sahən</small></span>'+icon('down')+'</summary><div class="premium-account-menu"><span id="premiumAccountEmail">ORION · şəxsi iş sahəsi</span>'+menuButton('Profilim','lock','data-route="profile"')+menuButton('Ayarlar','settings','data-route="settings"')+menuButton('Giriş ekranı','orbit','data-big="entry"')+menuButton('Sessiyadan çıx','arrow','data-action="logout"')+'</div></details></div>';

 function closeMenus(){for(const menu of nav.querySelectorAll('details[open]'))menu.open=false;}
 nav.addEventListener('click',event=>{if(event.target.closest('[data-route],[data-big],[data-action],#premiumNewChat'))closeMenus();});
 document.addEventListener('click',event=>{if(!nav.contains(event.target))closeMenus();});
 document.addEventListener('keydown',event=>{if(event.key==='Escape'){const account=$('premiumAccount');if(account.open){account.open=false;account.querySelector('summary').focus({preventScroll:true});}for(const menu of nav.querySelectorAll('.big-more[open]')){menu.open=false;menu.querySelector('summary').focus({preventScroll:true});}}});
 let markerFrame=0;
 function sidebar(collapsed){
  document.body.dataset.sidebarCollapsed=String(collapsed);
  const toggle=$('premiumSidebarToggle');toggle.setAttribute('aria-expanded',String(!collapsed));
  toggle.setAttribute('aria-label',collapsed?'Sol menyunu genişləndir':'Sol menyunu yığ');toggle.title=toggle.getAttribute('aria-label');
  try{localStorage.setItem('orion.sidebar.v1',JSON.stringify({collapsed}));}catch{}
  scheduleMarker();
 }
 // The compact rail matches the layout reference. A previous explicit choice wins.
 let collapsed=true;
 try{const saved=JSON.parse(localStorage.getItem('orion.sidebar.v1')||'null');if(typeof saved?.collapsed==='boolean')collapsed=saved.collapsed;}catch{}
 sidebar(collapsed);
 $('premiumSidebarToggle').addEventListener('click',()=>sidebar(document.body.dataset.sidebarCollapsed!=='true'));
 $('premiumNewChat').addEventListener('click',()=>O.openChat());
 function scheduleMarker(){if(!markerFrame)markerFrame=requestAnimationFrame(updateMarker);}
 function updateMarker(){
  markerFrame=0;
  const marker=$('premiumNavMarker'),active=nav.querySelector('.premium-nav-primary>.os-nav-item.is-current,.premium-nav-scroll>.os-nav-item.is-current,.premium-nav-footer>.os-nav-item.is-current');
  if(!active||innerWidth<=760){marker.style.opacity='0';return;}
  const bounds=active.getBoundingClientRect(),rail=nav.getBoundingClientRect(),scroll=active.closest('.premium-nav-scroll'),viewport=scroll?.getBoundingClientRect();
  if(viewport&&(bounds.top<viewport.top||bounds.bottom>viewport.bottom)){marker.style.opacity='0';return;}
  marker.style.height=bounds.height+'px';marker.style.transform='translateY('+(bounds.top-rail.top-nav.clientTop)+'px)';marker.style.opacity='1';
 }
 nav.querySelector('.premium-nav-scroll').addEventListener('scroll',scheduleMarker,{passive:true});
 window.addEventListener('resize',scheduleMarker,{passive:true});
 nav.addEventListener('transitionend',event=>{if(event.propertyName==='width')scheduleMarker();});
 if('ResizeObserver'in window)new ResizeObserver(scheduleMarker).observe(nav);
 let sidebarSignature='';
 function renderSidebar(){
  const s=O.state,p=s.profile||{},notes=(s.notes||[]).slice(-5).reverse(),activities=(s.activities||[]).slice(0,5);
  const signature=JSON.stringify([p.name,p.username,p.email,notes.map(n=>[n.id,n.title]),activities.map(a=>[a.title,a.section,a.time])]);
  if(signature===sidebarSignature)return;sidebarSignature=signature;
  const name=String(p.name||p.username||'Şəxsi profil');
  $('premiumAccountName').textContent=name;
  $('premiumAccountAvatar').textContent=Array.from(name.trim())[0]?.toLocaleUpperCase('az')||'O';
  $('premiumAccountEmail').textContent=p.email||'ORION · şəxsi iş sahəsi';
  $('premiumRecentNotes').innerHTML=notes.length?notes.map(n=>'<button type="button" class="premium-recent" data-route="notes" title="'+e(n.title||'Başlıqsız qeyd')+'">'+icon('memory')+'<span>'+e(n.title||'Başlıqsız qeyd')+'</span></button>').join(''):'<p class="premium-recent-empty">Yeni qeydlərin burada görünəcək.</p>';
  const routes=new Set([...primary,...secondary].map(x=>x[0]).concat(['profile','chat']));
  $('premiumRecentActivity').innerHTML=activities.length?activities.map(a=>'<button type="button" class="premium-recent" data-route="'+(routes.has(a.section)?a.section:'home')+'" title="'+e(a.title||'Fəaliyyət')+'">'+icon('activity')+'<span>'+e(a.title||'Fəaliyyət')+'</span></button>').join(''):'<p class="premium-recent-empty">İşlədikcə son fəaliyyətlərin burada görünəcək.</p>';
 }
 O.subscribers.push(renderSidebar);renderSidebar();

 // Keep the complete first-screen hero. Only the personal overview below it
 // is rearranged into the compact banner/cards/calendar composition.
 const overview=$('osHome'),board=document.createElement('div'),boardMain=document.createElement('div');
 board.className='premium-overview-board';boardMain.className='premium-overview-main';
 const originalOverview=Array.from(overview.children).filter(x=>!x.classList.contains('os-section-heading'));
 boardMain.append(...originalOverview);board.append(boardMain);overview.append(board);
 const calendar=document.createElement('aside');calendar.className='premium-calendar';calendar.setAttribute('aria-label','Plan və qeydlər təqvimi');
 const sideStack=document.createElement('div');sideStack.className='premium-overview-side';sideStack.append(calendar);board.append(sideStack);
 function alignOverview(){
  const container=$('osHomeBento');
  const originals=Array.from(container.querySelectorAll('article.os-card,button.os-stat-card,article.nb-card,article.os-note,article.node,article.step-card,article.big-receipt,article.big-compare-card'));
  // Pinned tabs retain their original source/index when a card changes column.
  for(const [index,card]of originals.entries())if(!card.dataset.premiumSource){card.dataset.premiumSource=container.id;card.dataset.premiumIndex=String(index);}
  for(const name of ['os-home-profile','os-assistant-card']){
   const card=container.querySelector(':scope>.'+name);if(!card)continue;
   sideStack.querySelector(':scope>.'+name)?.remove();sideStack.append(card);
  }
 }
 O.subscribers.push(alignOverview);alignOverview();
 const dateKey=(year,month,day)=>year+'-'+String(month+1).padStart(2,'0')+'-'+String(day).padStart(2,'0');
 const monthNames=['Yanvar','Fevral','Mart','Aprel','May','İyun','İyul','Avqust','Sentyabr','Oktyabr','Noyabr','Dekabr'];
 const today=()=>{const parts=Object.fromEntries(new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Baku',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()).map(p=>[p.type,p.value]));return parts.year+'-'+parts.month+'-'+parts.day;};
 let selectedDay=today(),calendarMonth=selectedDay.slice(0,7),calendarSignature='';
 function renderCalendar(){
  const monthRows=B.occurrences(calendarMonth).map(p=>({date:p.date,title:p.name+' · '+O.money(p.amount,p.currency),route:'finance',icon:'activity'}));
  const rows=[...(O.state.notes||[]).map(n=>({date:n.date,title:n.title||'Başlıqsız qeyd',route:'notes',icon:'memory'})),...monthRows];
  const current=today(),signature=JSON.stringify([calendarMonth,selectedDay,current,rows]);if(signature===calendarSignature)return;calendarSignature=signature;
  const [year,month]=calendarMonth.split('-').map(Number),first=new Date(year,month-1,1,12),count=new Date(year,month,0,12).getDate(),offset=(first.getDay()+6)%7;
  const monthTitle=monthNames[month-1]+' '+year;
  const agenda=rows.filter(r=>r.date===selectedDay),dots=new Set(rows.map(r=>r.date));
  calendar.innerHTML='<div class="premium-calendar-head"><h3>'+e(monthTitle)+'</h3><div><button type="button" data-calendar="prev" aria-label="Əvvəlki ay">'+icon('down')+'</button><button type="button" data-calendar="next" aria-label="Növbəti ay">'+icon('down')+'</button></div></div>'+
   '<div class="premium-calendar-week" aria-hidden="true">'+['B.e','Ç.a','Ç.','C.a','C.','Ş.','B.'].map(d=>'<span>'+d+'</span>').join('')+'</div><div class="premium-calendar-days" role="group" aria-label="'+e(monthTitle)+' tarixləri">'+Array.from({length:offset},()=>'<span aria-hidden="true"></span>').join('')+Array.from({length:count},(_,i)=>{const key=dateKey(year,month-1,i+1);return '<button type="button" data-calendar-day="'+key+'" data-today="'+(key===current)+'" class="'+(dots.has(key)?'has-event':'')+'" aria-pressed="'+(key===selectedDay)+'" aria-label="'+key+(dots.has(key)?' · qeyd və ya ödəniş var':'')+'">'+(i+1)+'</button>';}).join('')+'</div>'+
   '<button type="button" class="premium-calendar-today" data-calendar="today">Bu günə qayıt</button><div class="premium-calendar-agenda"><h4>'+e(selectedDay===current?'Bugünün planı':Number(selectedDay.slice(8))+' '+monthNames[Number(selectedDay.slice(5,7))-1].toLocaleLowerCase('az'))+'</h4>'+(agenda.length?agenda.slice(0,4).map(r=>'<button type="button" data-route="'+r.route+'">'+icon(r.icon)+'<span>'+e(r.title)+'</span></button>').join(''):'<p>Bu tarixə qeyd və ödəniş planı əlavə edilməyib.</p>')+'</div>';
 }
 calendar.addEventListener('click',event=>{
  const day=event.target.closest('[data-calendar-day]'),button=event.target.closest('[data-calendar]');
  if(day){selectedDay=day.dataset.calendarDay;renderCalendar();calendar.querySelector('[data-calendar-day="'+selectedDay+'"]').focus({preventScroll:true});}
  if(button){const action=button.dataset.calendar;if(action==='today'){selectedDay=today();calendarMonth=selectedDay.slice(0,7);}else{const [y,m]=calendarMonth.split('-').map(Number),d=new Date(y,m-1+(action==='prev'?-1:1),1,12);selectedDay=dateKey(d.getFullYear(),d.getMonth(),1);calendarMonth=selectedDay.slice(0,7);}renderCalendar();calendar.querySelector('[data-calendar="'+action+'"]').focus({preventScroll:true});}
 });
 O.subscribers.push(renderCalendar);renderCalendar();

 // Reuse the original controls and handlers; only their presentation changes.
 const settings=$('settingsDialog'),settingsNav=settings.querySelector('.settings-nav');
 settings.classList.add('settings-studio');
 const settingsLinks=document.createElement('div');settingsLinks.className='premium-settings-links';
 const sectionButtons=Array.from(settingsNav.querySelectorAll('.settings-nav-link'));
 if(sectionButtons.length){settingsNav.querySelector('.nav-group-label').after(settingsLinks);settingsLinks.append(...sectionButtons);}
 const settingsCrumb=document.createElement('span');settingsCrumb.className='premium-settings-crumb';
 $('settingsTitle').after(settingsCrumb);
 function reflectSettings(){
  const active=settingsNav.querySelector('.settings-nav-link.is-active');
  settingsCrumb.textContent=active?.querySelector('span:not(.nav-symbol):not(.nav-arrow)')?.textContent.trim()||'Şəxsi iş sahən';
  if(active&&settings.open&&matchMedia('(max-width:760px), (max-width:1000px) and (max-height:500px)').matches){
   const button=active.getBoundingClientRect(),list=settingsLinks.getBoundingClientRect();
   if(button.left<list.left)settingsLinks.scrollLeft-=list.left-button.left+8;
   else if(button.right>list.right)settingsLinks.scrollLeft+=button.right-list.right+8;
  }
 }
 new MutationObserver(reflectSettings).observe(settingsLinks,{attributes:true,subtree:true,attributeFilter:['class']});reflectSettings();
 // The curated light collection uses the same persistent theme buttons as the
 // classic collection. Moving a button preserves click, hover and focus behavior.
 const themeSection=$('themesSection'),themeGrid=$('themeChoices');
 const lightHeading=document.createElement('div');lightHeading.className='settings-collection-head';
 lightHeading.innerHTML='<div><span class="settings-overline">RƏNG VƏ İŞIQ</span><h4 id="gradientCollectionTitle">İşıq kolleksiyası</h4></div><span class="settings-new-badge">5 yeni mövzu</span>';
 const lightGrid=document.createElement('div');lightGrid.id='gradientThemeChoices';lightGrid.className='theme-grid gradient-theme-grid';lightGrid.setAttribute('role','group');lightGrid.setAttribute('aria-labelledby','gradientCollectionTitle');
 themeGrid.before(lightHeading,lightGrid);
 for(const id of ['prism','cobalt','ember','lagoon','auroraglow']){
  const button=themeGrid.querySelector('[data-theme-choice="'+id+'"]');if(!button)continue;
  button.classList.add('gradient-theme-choice');
  button.querySelector('.theme-swatch').innerHTML='<span class="swatch-brand">'+icon('orbit')+'<span>ORION</span></span><span class="swatch-line"></span>';
  lightGrid.append(button);
 }
 const classicHeading=document.createElement('div');classicHeading.className='settings-collection-head settings-classic-head';
 classicHeading.innerHTML='<div><h4 id="classicCollectionTitle">Klassik palitralar</h4><p>Tanış rənglər, sənə uyğun atmosfer.</p></div><span class="settings-collection-count">12 mövzu</span>';
 themeGrid.before(classicHeading);themeGrid.setAttribute('role','group');themeGrid.setAttribute('aria-labelledby','classicCollectionTitle');
 const preview=themeSection.querySelector('.theme-preview');preview.classList.add('settings-live-preview');
 preview.setAttribute('aria-label','Seçilmiş mövzunun canlı önizləməsi');
 preview.innerHTML='<div class="settings-preview-copy"><span class="settings-live-label"><i></i> CANLI ÖNİZLƏMƏ</span><h4>Sənin iş sahən.<br><em>Sənin rənglərin.</em></h4><p>İşıq, rəng və detallar — hamısı bir ahəngdə.</p><span class="settings-preview-palette" aria-hidden="true"><i></i><i></i><i></i><i></i></span></div><div class="settings-preview-stage" aria-hidden="true"><div class="settings-preview-glass"><div class="settings-preview-brand">'+icon('orbit')+'<span>ORION</span><span class="settings-preview-spark">'+icon('spark')+'</span></div><strong>Bir az işıq.<br>Daha çox ilham.</strong><div class="settings-preview-bottom"><span id="settingsPreviewName"></span><span>'+icon('arrow')+'</span></div></div></div>';
 themeSection.querySelector('.settings-section-head').after(preview);
 function reflectPalette(){const name=$('currentThemeName').textContent.replace(/^Önizləmə · /,'');$('settingsPreviewName').textContent=name;}
 new MutationObserver(reflectPalette).observe($('currentThemeName'),{childList:true,characterData:true,subtree:true});reflectPalette();
 $('aboutSection').insertAdjacentHTML('beforeend','<article class="premium-release-note" aria-labelledby="premiumReleaseTitle"><span class="big-eyebrow">BU BURAXILIŞDA</span><h4 id="premiumReleaseTitle">ORION 0.6.0 · Premium UI</h4><ul><li>Beş yeni gradient: İnci işığı, Kobalt işığı, Mərcan alovu, Mavi laqun və Qütb parıltısı.</li><li>İşıq kolleksiyası, 12 klassik palitra və canlı rəng önizləməsi.</li><li>Səliqəli Ayarlar, işıqlı kart kənarları və gradient yadda saxlama düyməsi.</li><li>Mobil axtarış sətri, sürüşən bölmə menyusu və aydın klaviatura fokusları.</li><li>Yadda qalan tema seçimi və ayrıca chatbot paneli ilə rəng uyğunluğu.</li><li>Paketdə şriftlərin, şifrə göstəricisinin və buraxılış adının qorunması.</li></ul><p>Tam siyahı üçün “Buraxılış qeydləri” düyməsini aç.</p></article>');
 settings.addEventListener('close',()=>{
  if(document.activeElement===document.body||!document.activeElement?.checkVisibility?.()){
   const target=innerWidth<=760?nav.querySelector('.big-more>summary'):$('premiumAccount').querySelector('summary');
   target?.focus({preventScroll:true});
  }
 });
 for(const label of settings.querySelectorAll('.settings-card>.field-label')){
  const control=label.nextElementSibling;
  if(!control||!control.matches('select,input:not([type=checkbox]):not([type=range])')||label.htmlFor!==control.id)continue;
  const row=document.createElement('div');row.className='premium-setting-row';label.before(row);row.append(label,control);
 }
 // Match each detached-card menu to the visible card rather than the larger
 // column containing its description. IDs/definitions used by pinned tabs stay.
 function alignCardMenus(){
  alignOverview();
  for(const menu of document.querySelectorAll('.big-card-menu:not([data-premium-menu])')){
   menu.dataset.premiumMenu='true';
   // Menus are controls of their own. A click must not also trigger the
   // surrounding card's "open chat/node" handler. Keep native details and
   // the existing pin button listener working normally.
   menu.addEventListener('click',event=>event.stopPropagation());
   menu.addEventListener('keydown',event=>{
    if(event.key==='Enter'||event.key===' ')event.stopPropagation();
    if(event.key==='Escape'&&menu.open){event.preventDefault();event.stopPropagation();menu.open=false;menu.querySelector('summary').focus({preventScroll:true});}
   });
  }
  for(const card of document.querySelectorAll('.step-card')){
   const visual=card.querySelector('.step-visual');if(!visual)continue;
   let stage=card.querySelector('.premium-step-stage');
   if(!stage){stage=document.createElement('div');stage.className='premium-step-stage';visual.before(stage);stage.append(visual);}
   // The disclosure must be a sibling of the action button, never nested in it.
   const menu=card.querySelector(':scope>.big-card-menu,.step-visual>.big-card-menu');
   if(menu)stage.append(menu);
   card.classList.add('premium-menu-aligned');
  }
  for(const edit of document.querySelectorAll('.os-card>.os-card-menu.floating')){
   const card=edit.parentElement,pin=card.querySelector(':scope>.big-card-menu');if(!pin)continue;
   const actions=document.createElement('div');actions.className='premium-card-actions';
   actions.setAttribute('role','group');actions.setAttribute('aria-label','Kart əməliyyatları');
   card.append(actions);actions.append(edit,pin);card.classList.add('premium-has-actions');
  }
  for(const button of document.querySelectorAll('.premium-overview-banner .big-button,#bigEntrySubmit,#bigHomeDetails .big-button,.os-assistant-card .os-button')){
   button.classList.add('premium-capsule');
   if(button.id==='bigEntrySubmit'||button.closest('.premium-overview-banner'))button.classList.add('premium-capsule-fill');
  }
 }
 document.addEventListener('click',event=>{for(const menu of document.querySelectorAll('.big-card-menu[open]'))if(!menu.contains(event.target))menu.open=false;});
 document.addEventListener('toggle',event=>{const menu=event.target;if(menu.matches?.('.big-card-menu[open]'))for(const other of document.querySelectorAll('.big-card-menu[open]'))if(other!==menu)other.open=false;},true);
 const entranceSelector='.premium-section-hero,.os-card,.os-stat-card,.nb-card,.os-note,.metric-card,.bento-card,.premium-step-stage,.big-agent-card,.big-saved-widget,.premium-calendar';
 const observed=new WeakSet(),cardAnimations=new WeakMap(),activeCards=new Set(),revealedKeys=new Set(),cardKeys=new WeakMap();
 const canMove=()=>!reduced.matches&&!document.documentElement.classList.contains('performance-mode')&&!document.body.classList.contains('performance-mode');
 function animateCard(card,index=0){
  cardAnimations.get(card)?.cancel();
  if(!canMove()||!card.animate)return;
  const animation=card.animate([{opacity:0,transform:'translate3d(0,24px,0) scale(.96)'},{opacity:1,transform:'none'}],{duration:560,delay:Math.min(index,7)*55,easing:'cubic-bezier(.16,1,.3,1)',fill:'backwards'});
  cardAnimations.set(card,animation);activeCards.add(animation);animation.finished.catch(()=>{}).finally(()=>activeCards.delete(animation));
 }
 const entrances='IntersectionObserver'in window?new IntersectionObserver(entries=>{
  entries.filter(item=>item.isIntersecting).forEach((item,index)=>{entrances.unobserve(item.target);const key=cardKeys.get(item.target);if(key&&revealedKeys.has(key))return;if(key)revealedKeys.add(key);animateCard(item.target,index);});
 },{threshold:.04,rootMargin:'0px 0px -20px 0px'}):null;
 function observeCards(){
  for(const head of document.querySelectorAll('.os-page>.os-section-heading,.os-page>.big-heading')){
   if(head.classList.contains('premium-section-hero'))continue;
   head.classList.add('premium-section-hero');
   const mark=document.createElement('span');mark.className='premium-header-mark';mark.setAttribute('aria-hidden','true');mark.innerHTML=icon('orbit');head.append(mark);
  }
  if(!entrances)return;
  for(const card of document.querySelectorAll(entranceSelector)){
   if(observed.has(card)||card.closest('#hero,#settingsDialog,#bigEntry'))continue;
   const parent=card.parentElement.closest('[id]')||card.parentElement;
   const key=(parent.id||O.route)+':'+card.classList[0]+':'+Array.from(parent.querySelectorAll(entranceSelector)).indexOf(card);
   cardKeys.set(card,key);
   observed.add(card);entrances.observe(card);
  }
 }
 const cardObserver=new MutationObserver(()=>{if(alignCardMenus.frame)return;alignCardMenus.frame=requestAnimationFrame(()=>{alignCardMenus.frame=0;alignCardMenus();observeCards();});});
 cardObserver.observe($('workspace'),{childList:true,subtree:true});alignCardMenus();observeCards();

 // Replace the stretched egg with a centered, circular ORION emblem. Its
 // movement uses only compositor transforms, not per-frame layout or blur.
 const emblem=$('bigEntry').querySelector('.big-entry-orbits');
 emblem.innerHTML='<span class="premium-entry-halo"></span><span class="premium-entry-orbit" style="--orbit-angle:0deg"></span><span class="premium-entry-orbit"></span><span class="premium-entry-orbit"></span><span class="premium-entry-core">'+icon('orbit')+'</span>';
 const entryStory=$('bigEntry').querySelector('.big-entry-story');
 entryStory.insertAdjacentHTML('beforeend','<div class="premium-entry-caption"><span>'+icon('spark')+'Fikirdən ilk addıma</span><span>'+icon('memory')+'Hər şey bir yerdə</span></div>');
 // Stop the idle artwork while the full-screen entry is closed.
 function reflectEntry(){document.body.classList.toggle('premium-entry-open',$('bigEntry').open);}
 new MutationObserver(reflectEntry).observe($('bigEntry'),{attributes:true,attributeFilter:['open']});reflectEntry();

 let route=O.route,routeFrame=0,animations=[];
 function animateRoute(){
  if(routeFrame)return;
  routeFrame=requestAnimationFrame(()=>{
   routeFrame=0;for(const a of nav.querySelectorAll('[data-route]')){const selected=a.dataset.route===O.route;a.classList.toggle('is-current',selected);a.setAttribute('aria-current',selected?'page':'false');}
   scheduleMarker();
   if(route===O.route)return;route=O.route;
   if(route==='home')window.orionGreeting?.refit?.();
   for(const a of animations)a.cancel();animations=[];
   if(reduced.matches||document.documentElement.classList.contains('performance-mode')||document.body.classList.contains('performance-mode'))return;
   const page=document.querySelector('[data-view="'+route+'"]')||(route==='home'?$('hero'):null);
   if(page&&!page.hidden){
    animations.push(page.animate([{opacity:0,transform:'translate3d(0,12px,0)'},{opacity:1,transform:'none'}],{duration:320,easing:'cubic-bezier(.22,1,.36,1)'}));
    if(route!=='home')Array.from(page.querySelectorAll(entranceSelector)).slice(0,10).forEach(animateCard);
   }
  });
 }
 const navigate=O.navigate;
 O.navigate=(...args)=>{const result=navigate(...args);animateRoute();return result;};
 document.addEventListener('click',event=>{if(event.target.closest('[data-route],[data-open-section]'))animateRoute();});
 window.addEventListener('hashchange',animateRoute);
 const viewObserver=new MutationObserver(records=>{if(records.some(r=>r.target.hasAttribute('data-view')||r.target.id==='hero'))animateRoute();});
 viewObserver.observe($('workspace'),{attributes:true,subtree:true,attributeFilter:['hidden']});
 animateRoute();
 // Do not spend GPU frames drawing an obscured ambient scene behind a modal.
 // This is temporary render state and never changes the user's saved choices.
 function modalBackground(){window.orionView?.suspend?.(Boolean(document.querySelector('dialog[open]')));}
 new MutationObserver(records=>{if(records.some(r=>r.target.tagName==='DIALOG'))modalBackground();}).observe(document.body,{attributes:true,subtree:true,attributeFilter:['open']});
 modalBackground();
 reduced.addEventListener?.('change',()=>{if(reduced.matches){for(const a of animations)a.cancel();for(const a of activeCards)a.cancel();}});
 window.ORIONPremium={renderSidebar,renderCalendar,alignCardMenus,sidebar,observeCards,version:'0.6.0',font:'Euclid Circular'};
})();
