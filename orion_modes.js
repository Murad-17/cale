/* Shared ORION behavior and expression presets. These use the configured AI model. */
(()=>{'use strict';
 const modes=[
  {id:'companion',name:'Orbit',role:'Gündəlik köməkçi',icon:'chat',mood:'happy',shape:'orb',desc:'Bir sual, bir fikir, rahat bir söhbət.',color:'#73ddb5',hue:30},
  {id:'code',name:'Vector',role:'Kod və texniki iş',icon:'cube',mood:'focus',shape:'square',desc:'Kod yaz, xətanı tap və həlli yoxla.',color:'#78bff5',hue:92},
  {id:'research',name:'Nova',role:'Dərin araşdırma',icon:'spark',mood:'curious',shape:'star',desc:'Mənbələri müqayisə et, mövzunu aydınlaşdır.',color:'#a596f3',hue:145},
  {id:'creative',name:'Muse',role:'Yaradıcılıq',icon:'orbit',mood:'surprised',shape:'drop',desc:'Dizayn, motion və 3D ideyalarını böyüt.',color:'#f5a6c9',hue:205},
  {id:'planner',name:'Atlas',role:'Plan və büdcə',icon:'activity',mood:'idle',shape:'pill',desc:'Prioritetləri və növbəti addımını müəyyən et.',color:'#efcc7e',hue:285}
 ];
 let selected='companion',feeling='calm',busy=false;
 const e=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function avatar(id,small=false){
  const mode=modes.find(m=>m.id===id)||modes[0],hue=mode.hue;
  const eyes=mode.id==='code'?'<path d="M452 643h96m228 0h96"/>':mode.id==='creative'?'<path d="M451 658q48-72 96 0m228-5q48 22 96-8"/>':mode.id==='research'?'<ellipse cx="500" cy="645" rx="33" ry="49"/><ellipse cx="824" cy="651" rx="31" ry="38"/>':'<path d="M452 658q48-64 96 0m228 0q48-64 96 0"/>';
  const mouth=mode.id==='code'?'M629 795h67':mode.id==='planner'?'M625 786q37 25 74 0':'M612 780q50 65 100 0';
  return '<span class="mode-avatar orion-kin persona-'+mode.id+(small?' small':'')+'" style="--persona:'+mode.color+';--persona-hue:'+hue+'deg" aria-hidden="true"><span class="mode-robot-pose"><img class="mode-shell" src="/panel-assets/orion-shell.png" alt="" draggable="false"><svg class="mode-face" viewBox="0 0 1280 1280"><g class="mode-leds" fill="none" stroke="currentColor" stroke-width="21" stroke-linecap="round" stroke-linejoin="round"><g class="mode-led-eyes">'+eyes+'</g><path class="mode-led-brows" d="M454 545q44-27 90-3m234 0q44-27 90 3" stroke-width="11"/><path class="mode-led-mouth" d="'+mouth+'" stroke-width="15"/></g></svg></span></span>';
 }
 function sync(settings={}){const before=selected+'|'+feeling;if(modes.some(m=>m.id===settings.assistantMode))selected=settings.assistantMode;if(['calm','focused','energized'].includes(settings.assistantMood))feeling=settings.assistantMood;document.documentElement.dataset.assistantMode=selected;document.documentElement.dataset.assistantMood=feeling;for(const el of document.querySelectorAll('[data-mode-select]'))el.value=selected;for(const el of document.querySelectorAll('[data-feeling-select]'))el.value=feeling;for(const el of document.querySelectorAll('[data-persona]')){const active=el.dataset.persona===selected;el.classList.toggle('is-selected',active);el.setAttribute('aria-pressed',String(active));}for(const el of document.querySelectorAll('[data-mode-name]'))el.textContent=modes.find(m=>m.id===selected).name;window.ORIONRobot?.setPersona?.(selected);if(before!==selected+'|'+feeling)window.dispatchEvent(new CustomEvent('orion:mode',{detail:{mode:selected,mood:feeling}}));}
 async function choose(id,mood=feeling){if(!modes.some(m=>m.id===id)||busy)return;busy=true;try{const response=await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({settings:{assistantMode:id,assistantMood:mood}})});const data=await response.json();if(!response.ok)throw Error(data.error||'Rejim saxlanılmadı.');sync({assistantMode:id,assistantMood:mood});if(window.OrionOS){OrionOS.state.assistantMode=id;OrionOS.state.assistantMood=mood;OrionOS.persist();}window.ORIONRobot?.react(modes.find(m=>m.id===id).mood,2000);}finally{busy=false;}}
 const options=()=>modes.map(m=>'<option value="'+m.id+'">'+m.name+' · '+m.role+'</option>').join('');
 document.addEventListener('change',event=>{if(event.target.matches('[data-mode-select]'))void choose(event.target.value).catch(error=>{sync();window.showToast?.(error.message);});if(event.target.matches('[data-feeling-select]'))void choose(selected,event.target.value).catch(error=>window.showToast?.(error.message));});
 if(document.getElementById('homeView')){const select='<label class="panel-mode-label">Köməkçin<select data-mode-select aria-label="ORION iş rejimi">'+options()+'</select></label>';document.querySelector('#homeView>div').insertAdjacentHTML('beforeend',select);document.querySelector('.chat-drag').insertAdjacentHTML('beforeend','<select class="panel-chat-mode" data-mode-select aria-label="Çat iş rejimi">'+options()+'</select>');}
 window.ORIONModes={modes,avatar,options,choose,sync,get mode(){return selected;},get mood(){return feeling;}};
 if(typeof publicSettings==='function'){const original=publicSettings;publicSettings=()=>({...original(),assistantMode:selected,assistantMood:feeling});}
 async function refresh(){try{const response=await fetch('/api/settings');if(response.ok)sync((await response.json()).settings);}catch{}}
 void refresh();setInterval(()=>{if(!document.hidden)void refresh();},8000);
})();
