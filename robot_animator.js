/* ORION's transparent shell, with a live LED face and deliberate gaze/pose. */
(()=>{
 'use strict';
 const reduced=matchMedia('(prefers-reduced-motion: reduce)'),rigs=[];
 let persona='companion';
 let waveUntil=0,waveStart=0,waveTimer=0,nodAt=-1000;
 let mood='idle',moodUntil=0,winkAt=-1000,nextBlink=performance.now()+3200,blinkAt=-1000;
 let pointer=null,lastInput=0,frame=0,previous=0,nextGlance=0,glance={x:0,y:0},caret=null,caretKey='',mirror=null,reading=null;
 let geometryDirty=true,measuredAt=-1000;
 const clamp=(v,a,b)=>Math.max(a,Math.min(b,v)),lerp=(a,b,t)=>Math.abs(b-a)<.0004?b:a+(b-a)*t,q=v=>Math.round(v*10)/10;
 const written=new WeakMap();
 function attr(node,name,value){let cache=written.get(node);if(!cache){cache={};written.set(node,cache);}if(cache[name]!==value){cache[name]=value;node.setAttribute(name,value);}}
 function style(node,name,value){let cache=written.get(node);if(!cache){cache={};written.set(node,cache);}if(cache['style:'+name]!==value){cache['style:'+name]=value;node.style[name]=value;}}
 function invalidate(){geometryDirty=true;caretKey='';start();}
 function measureRigs(now){
  if(!geometryDirty&&now-measuredAt<250)return;
  // Read every visible rectangle before writing any SVG/transform attributes.
  for(const rig of rigs){const rect=rig.el.getBoundingClientRect();rig.rect=rect;rig.visible=rect.width>0&&rect.height>0&&rect.bottom>0&&rect.top<innerHeight;}
  geometryDirty=false;measuredAt=now;
 }
 function setPersona(value){
  persona=['companion','code','research','creative','planner'].includes(value)?value:'companion';
  const selected=window.ORIONModes?.modes.find(m=>m.id===persona);
  if(selected)for(const rig of rigs){
   rig.el.dataset.robotPersona=persona;rig.el.style.setProperty('--robot-persona-color',selected.color);rig.el.style.setProperty('--robot-persona-hue',selected.hue+'deg');
   rig.el.setAttribute('aria-label',selected.name+' — '+selected.role);
   for(const face of [rig.leds,rig.hand]){face.setAttribute('fill',selected.color);face.setAttribute('stroke',selected.color);}
  }
  start();
 }
 const poses={idle:{open:.78,smile:.68,brow:0,mouth:.7,opening:.35},focus:{open:1,smile:.08,brow:-.15,mouth:.18,opening:.05},happy:{open:.72,smile:.95,brow:.5,mouth:1,opening:.85},wink:{open:.75,smile:.9,brow:.4,mouth:.9,opening:.65},curious:{open:1,smile:.25,brow:.65,mouth:.35,opening:.25},concerned:{open:.85,smile:.1,brow:-.6,mouth:-.4,opening:.04},surprised:{open:1.2,smile:.02,brow:.9,mouth:.05,opening:.9}};
 function mount(image,index){
  const wrapper=document.createElement('span');wrapper.className=image.className+' robot-animated';
  if(image.id)wrapper.id=image.id;
  wrapper.setAttribute('role','img');wrapper.setAttribute('aria-label',image.alt||'ORION robotu');
  if(image.hasAttribute('data-robot'))wrapper.dataset.robot='';wrapper.dataset.expression='idle';
  const clip='orion-face-'+index;
  wrapper.innerHTML='<span class="robot-pose"><img class="robot-shell" src="/panel-assets/orion-shell.png" alt="" draggable="false"><svg class="robot-face" viewBox="0 0 1280 1280" aria-hidden="true"><defs><clipPath id="'+clip+'"><path d="M440 446Q658 382 906 449Q1011 492 1012 681Q1016 872 904 921Q669 980 436 918Q322 873 323 680Q321 494 440 446Z"/></clipPath></defs><g clip-path="url(#'+clip+')"><g class="robot-leds" fill="#77ff9d" stroke="#77ff9d" stroke-linecap="round" stroke-linejoin="round"><g class="robot-eye-left"><path class="robot-eye-shape" stroke="none"/></g><g class="robot-eye-right"><path class="robot-eye-shape" stroke="none"/></g><path class="robot-brow-left" fill="none" stroke-width="11"/><path class="robot-brow-right" fill="none" stroke-width="11"/><path class="robot-mouth" stroke-width="10"/></g><g class="robot-hand" fill="#77ff9d" stroke="#77ff9d" stroke-linecap="round" stroke-linejoin="round" opacity="0"><path d="M590 815C550 797 515 747 505 719C499 699 519 685 535 700L574 744V574C574 548 605 548 605 574V665L613 533C613 507 645 507 645 533V653L658 518C658 490 691 490 691 518V657L705 560C708 535 738 538 734 564L730 713C755 674 789 685 777 712L748 785C737 818 710 836 690 850V881H600Z" stroke-width="4"/><path d="M801 583Q837 610 817 650M832 559Q883 607 851 671" fill="none" stroke-width="12" opacity=".65"/></g></g></svg></span>';
  image.replaceWith(wrapper);
  const nodes=wrapper.querySelectorAll('.robot-eye-shape');
  rigs.push({el:wrapper,pose:wrapper.querySelector('.robot-pose'),left:wrapper.querySelector('.robot-eye-left'),right:wrapper.querySelector('.robot-eye-right'),eyeL:nodes[0],eyeR:nodes[1],browL:wrapper.querySelector('.robot-brow-left'),browR:wrapper.querySelector('.robot-brow-right'),mouth:wrapper.querySelector('.robot-mouth'),leds:wrapper.querySelector('.robot-leds'),hand:wrapper.querySelector('.robot-hand'),x:0,y:0,state:{...poses.idle},visible:false,rect:null});
  geometryDirty=true;
 }
 document.querySelectorAll('img.robot-head').forEach(mount);
 function setMood(value,duration=0){
  const next=value==='error'?'concerned':poses[value]?value:'idle';
  if(next==='idle'&&moodUntil>performance.now())return;
  if(next!==mood){mood=next;if(next==='wink')winkAt=performance.now();if(next==='happy'||next==='surprised')nodAt=performance.now();}
  moodUntil=duration?performance.now()+duration:next==='wink'||next==='happy'?performance.now()+1800:0;
  start();
 }
 function wave(duration=3600){duration=clamp(Number(duration)||3600,1500,6000);waveStart=performance.now();waveUntil=waveStart+duration;setMood('happy',duration);clearTimeout(waveTimer);waveTimer=setTimeout(()=>{waveUntil=0;start();},duration+20);start();}
 function typingTarget(){
  const input=document.getElementById('draft');if(!input||document.activeElement!==input||input.disabled||(!input.value&&performance.now()-lastInput>800))return null;
  if(caretKey&&caret)return caret;
  if(!input.getClientRects().length)return null;
  const rect=input.getBoundingClientRect(),key=input.value+'|'+input.selectionStart+'|'+input.scrollTop+'|'+input.scrollLeft+'|'+rect.width+'|'+rect.top;
  if(key===caretKey&&caret)return caret;
  caretKey=key;
  if(!mirror){mirror=document.createElement('div');mirror.setAttribute('aria-hidden','true');mirror.style.cssText='position:fixed;visibility:hidden;pointer-events:none;white-space:pre-wrap;overflow-wrap:break-word;word-wrap:break-word;z-index:-1;box-sizing:border-box;';document.body.append(mirror);}
  const style=getComputedStyle(input);
  for(const property of ['fontFamily','fontSize','fontWeight','fontStyle','letterSpacing','lineHeight','paddingTop','paddingRight','paddingBottom','paddingLeft','borderTopWidth','borderLeftWidth','tabSize'])mirror.style[property]=style[property];
  mirror.style.width=rect.width+'px';mirror.style.left=rect.left+'px';mirror.style.top=rect.top+'px';
  mirror.textContent=input.value.slice(0,input.selectionStart);const marker=document.createElement('span');marker.textContent='\u200b';mirror.append(marker);
  const point=marker.getBoundingClientRect();
  caret={x:clamp(point.left-input.scrollLeft,rect.left+6,rect.right-8),y:clamp(point.top-input.scrollTop+parseFloat(style.lineHeight)/2,rect.top+8,rect.bottom-8)};
  return caret;
 }
 function eyePath(cx,cy,open,smile){
  const w=58,h=72*open,inner=h*smile*.79;
  return `M${q(cx-w)} ${q(cy+12)}C${q(cx-w)} ${q(cy-h)} ${q(cx+w)} ${q(cy-h)} ${q(cx+w)} ${q(cy+12)}Q${q(cx+w-4)} ${q(cy+34)} ${q(cx+w-21)} ${q(cy+17)}Q${q(cx)} ${q(cy-inner)} ${q(cx-w+21)} ${q(cy+17)}Q${q(cx-w+4)} ${q(cy+34)} ${q(cx-w)} ${q(cy+12)}Z`;
 }
 function draw(rig,now,dt,target,expression,blink,wink){
  if(!rig.visible)return;
  const rect=rig.rect,centerX=rect.left+rect.width/2,centerY=rect.top+rect.height*.56;
  const tx=target?Math.tanh((target.x-centerX)/Math.max(100,innerWidth*.42)):reduced.matches?0:glance.x;
  const ty=target?Math.tanh((target.y-centerY)/Math.max(80,innerHeight*.55)):reduced.matches?0:glance.y;
  const smoothing=reduced.matches?1:1-Math.exp(-dt*11);
  rig.x=lerp(rig.x,tx,smoothing);rig.y=lerp(rig.y,ty,smoothing);
  const desired=poses[expression==='idle'&&persona==='research'?'curious':expression]||poses.idle;
  for(const property of Object.keys(desired))rig.state[property]=lerp(rig.state[property],desired[property],smoothing);
  const open=rig.state.open*(persona==='code'?.88:persona==='research'?1.1:1),smile=persona==='creative'?Math.max(.55,rig.state.smile):rig.state.smile,brow=rig.state.brow,mouth=rig.state.mouth,opening=rig.state.opening,dx=q(rig.x*43),dy=q(rig.y*34),cy=q(655+dy);
  const leftBlink=Math.round(Math.max(.045,1-blink)*1000)/1000,rightBlink=Math.round(Math.max(.045,1-Math.max(blink,wink,persona==='creative'&&expression==='idle'?.75:0))*1000)/1000;
  const codeEye=(x,y)=>`M${x-48} ${y-9}h96q9 0 9 9t-9 9h-96q-9 0-9-9t9-9Z`,focusedCode=persona==='code'&&['idle','focus'].includes(expression);
  attr(rig.eyeL,'d',focusedCode?codeEye(500+dx,cy):eyePath(500+dx,cy,open,smile));attr(rig.eyeR,'d',focusedCode?codeEye(824+dx,cy):eyePath(824+dx,cy,open*(expression==='curious'?.76:1),smile));
  attr(rig.left,'transform',`translate(0 ${cy}) scale(1 ${leftBlink}) translate(0 ${-cy})`);
  attr(rig.right,'transform',`translate(0 ${cy}) scale(1 ${rightBlink}) translate(0 ${-cy})`);
  const tilt=q(brow*26),by=q(543+dy*.5);
  attr(rig.browL,'d',`M${q(450+dx)} ${q(by+tilt)}Q${q(493+dx)} ${q(by-20)} ${q(549+dx)} ${q(by-tilt)}`);
  const rightTilt=expression==='curious'?q(-tilt*.6):tilt;
  attr(rig.browR,'d',`M${q(775+dx)} ${q(by-rightTilt)}Q${q(826+dx)} ${q(by-20)} ${q(875+dx)} ${q(by+rightTilt)}`);
  const mx=q(662+dx*.6),my=q(790+dy*.6),width=expression==='focus'?32:48,curve=q(mouth*50),depth=q(opening*40);
  attr(rig.mouth,'d',focusedCode?`M${q(mx-33)} ${my}h66`:`M${q(mx-width)} ${my}Q${mx} ${q(my+curve)} ${q(mx+width)} ${my}Q${mx} ${q(my+curve+depth)} ${q(mx-width)} ${my}Z`);
  const waving=now<waveUntil,elapsed=(now-waveStart)/1000;
  style(rig.leds,'opacity',waving?'0':'1');style(rig.hand,'opacity',waving?'1':'0');
  const settle=clamp((now-waveStart)/220,0,1),waveAngle=reduced.matches?0:Math.sin(elapsed*Math.PI*3.8)*17*Math.min(1,(waveUntil-now)/500);
  if(waving)attr(rig.hand,'transform',`translate(657 758) rotate(${q(waveAngle)}) scale(${Math.round((reduced.matches?1:.78+.22*settle)*1000)/1000}) translate(-657 -758)`);
  const nodAge=(now-nodAt)/1000,nod=nodAge>=0&&nodAge<.8?Math.sin(nodAge*Math.PI*2/.8)*3.5*(1-nodAge/.8):0;
  style(rig.pose,'transform',reduced.matches?'none':`perspective(420px) rotateY(${q(rig.x*13)}deg) rotateX(${q(-rig.y*9+nod)}deg) translate(${q(rig.x*1.8)}px,${q(rig.y*1.2)}px)`);
  attr(rig.el,'data-expression',waving?'wave':expression);attr(rig.el,'data-gaze',target&&target===caret?'typing':target?.reading?'reading':target?'pointer':'idle');
 }
 function tick(now){
  frame=0;if(document.hidden)return;
  const dt=Math.min(.05,previous?(now-previous)/1000:.016);previous=now;
  if(moodUntil&&now>moodUntil){mood='idle';moodUntil=0;}
  const typing=typingTarget();let expression=mood;
  if(typing&&!['focus','concerned','wink','happy'].includes(mood)){
   const value=document.getElementById('draft').value;expression=/[?？]\s*$/.test(value)?'curious':/[!❤😊😍🎉]\s*$/.test(value)?'happy':'focus';
  }
  if(now>nextGlance){nextGlance=now+3600+Math.random()*3200;glance={x:(Math.random()-.5)*.38,y:(Math.random()-.5)*.24};}
  if(!reduced.matches&&now>nextBlink){blinkAt=now;nextBlink=now+3400+Math.random()*3800;}
  const age=now-blinkAt,blink=reduced.matches||age>190?0:Math.sin(Math.PI*age/190);
  const winkAge=now-winkAt,wink=reduced.matches||winkAge>420?0:Math.sin(Math.PI*clamp(winkAge/420,0,1));
  let readTarget=null;if(reading&&now<reading.until&&reading.element.isConnected&&reading.element.getClientRects().length){const rect=reading.element.getBoundingClientRect();readTarget={x:clamp(rect.left+rect.width*.5,20,innerWidth-20),y:clamp(rect.top+Math.min(36,rect.height/2),50,innerHeight-80),reading:true};}
  const target=typing||readTarget||(pointer&&now-pointer.at<5000?pointer:null);
  measureRigs(now);
  for(const rig of rigs)draw(rig,now,dt,target,expression,blink,wink);
  if(!reduced.matches)frame=requestAnimationFrame(tick);
 }
 function start(){if(!frame&&!document.hidden)frame=requestAnimationFrame(tick);}
 document.addEventListener('pointermove',event=>{pointer={x:event.clientX,y:event.clientY,at:performance.now()};start();},{passive:true});
 document.addEventListener('pointerleave',()=>{pointer=null;});
 document.addEventListener('input',event=>{if(event.target.id==='draft'){lastInput=performance.now();caretKey='';if(event.target.value&&waveUntil){waveUntil=0;mood='idle';moodUntil=0;clearTimeout(waveTimer);}start();}});
 document.addEventListener('selectionchange',()=>{caretKey='';start();});
 document.addEventListener('focusin',event=>{if(event.target.id==='draft')lastInput=performance.now();start();});document.addEventListener('focusout',()=>{caretKey='';caret=null;});
 window.addEventListener('resize',invalidate);
 window.addEventListener('orion-panel-mode',invalidate);
 document.addEventListener('scroll',invalidate,{passive:true,capture:true});
 if(window.ResizeObserver)new ResizeObserver(invalidate).observe(document.body);
 document.fonts?.ready.then(invalidate);
 document.addEventListener('visibilitychange',()=>{if(document.hidden){cancelAnimationFrame(frame);frame=0;previous=0;}else{nextBlink=performance.now()+2400;start();}});
 reduced.addEventListener('change',()=>{blinkAt=winkAt=-1000;start();});
 window.ORIONRobot={setPersona,setMood,wave,react:(value,duration=1800)=>setMood(value,duration),lookAt:(element,duration=2600)=>{if(element?.getBoundingClientRect){reading={element,until:performance.now()+duration};start();}},refresh:()=>{document.querySelectorAll('img.robot-head').forEach(image=>mount(image,rigs.length));setPersona(persona);caretKey='';start();},state:()=>({persona,mood,waving:performance.now()<waveUntil,typing:Boolean(typingTarget()),lastInput,reducedMotion:reduced.matches,rigs:rigs.filter(r=>r.el.getClientRects().length).map(r=>({persona:r.el.dataset.robotPersona,expression:r.el.dataset.expression,gaze:r.el.dataset.gaze,x:r.x,y:r.y}))})};
 start();
})();
