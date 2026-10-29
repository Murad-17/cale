// Password Meter by vividsites, integrated into ORION; all scoring stays in this page.
(() => {
  if (window.__vsPasswordMeter) return; window.__vsPasswordMeter = true;
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');
  const COMMON = new Set(('password passw0rd password1 password123 123456 1234567 12345678 123456789 1234567890 12345 1234 111111 000000 123123 654321 666666 121212 112233 abc123 abcdef qwerty qwertyuiop qwerty123 asdfgh asdfghjkl zxcvbn zxcvbnm 1q2w3e4r 1qaz2wsx letmein welcome welcome1 admin administrator login master monkey dragon shadow sunshine princess football baseball basketball soccer hockey iloveyou trustno1 superman batman starwars whatever freedom hello secret access flower cheese summer winter autumn spring michael charlie jordan hunter ranger buster tigger cookie orange banana computer internet pepper ginger killer mustang maggie jessica ashley daniel thomas robert matthew andrew joshua love lovely loveme angel angels friends family forever blessed jesus master1 qazwsx zaq12wsx passpass test test123 guest changeme default root toor pass letmein1 hello123 iloveu nothing').split(' '));
  const LEET = { '0': 'o', '1': 'l', '3': 'e', '4': 'a', '5': 's', '7': 't', '8': 'b', '@': 'a', '$': 's', '!': 'i', '+': 't' };
  const deleet = (s) => s.replace(/[0134578@$!+]/g, (c) => LEET[c]);
  const isCommon = (pw) => {
    const l = pw.toLowerCase(); if (COMMON.has(l) || COMMON.has(deleet(l))) return true;
    const core = l.replace(/^[^\p{L}]+|[^\p{L}]+$/gu, ''); // "Summer2024!" -> "summer"
    return core.length >= 4 && core.length >= l.length - 5 && (COMMON.has(core) || COMMON.has(deleet(core)));
  };
  const seqRun = (s) => { if (s.length < 3) return false; const d = s.charCodeAt(1) - s.charCodeAt(0); if (Math.abs(d) !== 1) return false;
    for (let i = 2; i < s.length; i++) if (s.charCodeAt(i) - s.charCodeAt(i - 1) !== d) return false; return true; };
  const ROWS = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm', '1234567890'];
  const keyRun = (s) => s.length >= 4 && ROWS.some((r) => r.includes(s.toLowerCase()) || [...r].reverse().join('').includes(s.toLowerCase()));
  // bits of entropy, pricing human patterns far below random characters
  function estimate(pw) {
    if (!pw) return 0;
    if (isCommon(pw)) return Math.min(8, 2 + pw.length * .5);
    const runs = pw.match(/\p{L}+|\d+|[^\p{L}\d]+/gu) || []; let bits = 0;
    for (const r of runs) {
      const n = r.length;
      if (/^(.)\1+$/.test(r)) { bits += Math.log2(/\d/.test(r) ? 10 : /\p{L}/u.test(r) ? 26 : 33) + Math.log2(n); continue; }
      if (seqRun(r) || keyRun(r)) { bits += 4 + Math.log2(n); continue; }
      if (/^\p{L}+$/u.test(r)) {
        const lower = r.toLowerCase(), caps = (r.match(/\p{Lu}/gu) || []).length;
        if (COMMON.has(lower) || COMMON.has(deleet(lower))) { bits += 9; continue; }
        const capBits = caps === 0 ? 0 : (caps === 1 && /^\p{Lu}/u.test(r)) || caps === n ? 1 : Math.min(n, caps * 2.2);
        bits += (n <= 3 ? n * 4.7 : n * 2.6) + capBits; // runs of 4+ letters read as words
      } else if (/^\d+$/.test(r)) {
        bits += n === 4 && /^(19|20)\d\d$/.test(r) ? 6.6 : n * 3.32;
      } else bits += n * 5;
    }
    bits += Math.log2(runs.length) * 1.5;
    return Math.max(0, bits);
  }
  const crackTime = (bits) => {
    const s = Math.pow(2, bits) / 2 / 1e10; // average guesses, offline at 10 billion a second
    if (s < 1) return 'ani';
    const u = [[60, 'san'], [60, 'dəq'], [24, 'saat'], [30.4, 'gün'], [12, 'ay'], [100, 'il']];
    let v = s, i = 0; for (; i < u.length && v >= u[i][0]; i++) v /= u[i][0];
    if (i >= u.length) return 'əsrlərlə';
    const n = Math.max(1, Math.round(v)); return '~' + n + ' ' + u[i][1] ;
  };
  const LABELS = ['Çox qısa', 'Zəif', 'Orta', 'Güclü', 'Çox güclü'];
  const hex = (c) => { const m = c.trim().match(/^#?([\da-f]{6})$/i); if (!m) return [200, 100, 90]; const n = parseInt(m[1], 16); return [n >> 16, (n >> 8) & 255, n & 255]; };
  let uid = 0;

  function mount(root) {
    if (root.__vsPm) return; root.__vsPm = true;
    const id = 'vs-password-meter-' + (++uid), $ = (s) => root.querySelector(s);
    const input = $('.vs-password-meter-input'), label = $('.vs-password-meter-label'), track = $('.vs-password-meter-track');
    const eye = $('.vs-password-meter-eye'), fills = [...root.querySelectorAll('.vs-password-meter-bars b')];
    const word = $('.vs-password-meter-word'), crack = $('.vs-password-meter-crack'), sr = $('.vs-password-meter-sr');
    const rulesEl = $('.vs-password-meter-rules'), rules = {}; root.querySelectorAll('[data-rule]').forEach((li) => (rules[li.dataset.rule] = li));
    const lidU = eye.querySelector('.lid-u'), lidL = eye.querySelector('.lid-l'), pupil = eye.querySelector('.pupil'), lash = eye.querySelector('.lash');
    input.id ||= id + '-input'; label.htmlFor = input.id; if (root.dataset.label) label.textContent = root.dataset.label;
    input.name = root.dataset.name || input.name || 'password';
    rulesEl.id = id + '-rules'; word.id = id + '-word';
    const capsNote = $('.vs-password-meter-caps'); capsNote.id = id + '-caps';
    // each rule gets a hidden "done / not done" suffix for screen readers
    Object.values(rules).forEach((li) => { const s = document.createElement('span'); s.className = 'vs-password-meter-sr'; s.textContent = ', hələ yox'; li.appendChild(s); li.__sr = s; });
    const minLen = () => Math.max(1, +root.dataset.minLength || 8);
    const syncAttrs = () => { input.disabled = root.hasAttribute('data-disabled'); eye.disabled = input.disabled; input.setAttribute('aria-describedby', root.dataset.mode === 'login' ? capsNote.id : word.id + ' ' + rulesEl.id + ' ' + capsNote.id); root.querySelectorAll('[data-min]').forEach((n) => (n.textContent = minLen())); };
    syncAttrs();

    /* ── rAF loop, alive only while something moves ── */
    const tasks = new Set(); let raf = 0, last = 0;
    const frame = (now) => { const dt = Math.min(.05, (now - last) / 1000 || .016); last = now; for (const t of tasks) if (!t(dt, now)) tasks.delete(t); raf = tasks.size ? requestAnimationFrame(frame) : 0; };
    const run = (t) => { tasks.add(t); if (!raf) { last = performance.now(); raf = requestAnimationFrame(frame); } };
    const spring = (x, k, c, on, eps = .001) => {
      const s = { x, v: 0, g: x, k, c };
      s.step = (dt) => { const n = Math.max(1, Math.ceil(dt * 240)), h = dt / n;
        for (let i = 0; i < n; i++) { s.v += (-s.k * (s.x - s.g) - s.c * s.v) * h; s.x += s.v * h; }
        const rest = Math.abs(s.v) < eps * 4 && Math.abs(s.x - s.g) < eps; if (rest) { s.x = s.g; s.v = 0; } on(s.x, s.v); return !rest; };
      s.to = (g) => { s.g = g; if (reduce.matches) { s.x = g; s.v = 0; on(g, 0); return; } run(s.step); };
      return s;
    };

    /* ── meter: one continuous value 0..4 fills the segments and blends the colour ── */
    const stops = () => { const cs = getComputedStyle(root); return [0, 1, 2, 3, 4].map((i) => hex(cs.getPropertyValue('--vs-password-meter-c' + i))); };
    let pal = stops();
    const colourAt = (m) => { const t = Math.max(0, Math.min(4, m)), i = Math.min(3, Math.floor(t)), f = t - i, a = pal[i], b = pal[i + 1];
      return `rgb(${a.map((v, k) => Math.round(v + (b[k] - v) * f)).join(',')})`; };
    let lastM = 0;
    const meter = spring(0, 170, 17, (m) => {
      fills.forEach((b, i) => { const f = Math.max(0, Math.min(1.06, m - i)); b.style.transform = `scaleX(${f.toFixed(4)})`; });
      root.style.setProperty('--vs-password-meter-c', colourAt(m));
    });
    // bits roll like a counter
    let shownBits = 0, bitsText = '';
    const bitSpring = spring(0, 120, 22, (b) => { shownBits = Math.max(0, Math.round(b)); paintCrack(); });
    const paintCrack = () => { const t = shownBits + ' bit · ' + bitsText; if (crack.textContent !== t) crack.textContent = t; };

    /* ── strength word crossfade ── */
    let wordNow = word.firstElementChild;
    const setWord = (text) => {
      if (wordNow.textContent === text) return;
      const nx = document.createElement('span'); nx.textContent = text; nx.setAttribute('data-in', ''); word.appendChild(nx);
      const old = wordNow; wordNow = nx; old.setAttribute('data-out', ''); old.removeAttribute('data-in');
      requestAnimationFrame(() => requestAnimationFrame(() => nx.removeAttribute('data-in')));
      setTimeout(() => old.remove(), reduce.matches ? 0 : 420);
    };

    /* ── mirror: per-character slots over the native field ── */
    const meas = document.createElement('input'); meas.setAttribute('aria-hidden', 'true'); meas.tabIndex = -1;
    meas.style.cssText = 'position:absolute;left:-9999px;top:0;width:1px;padding:0;border:0;visibility:hidden;';
    let advHidden = 10, advShown = 10;
    const measure = () => {
      const cs = getComputedStyle(input); meas.style.font = cs.font; meas.style.letterSpacing = cs.letterSpacing;
      root.appendChild(meas);
      meas.type = 'password'; meas.value = 'x'.repeat(40); advHidden = meas.scrollWidth / 40;
      meas.type = 'text'; advShown = meas.scrollWidth / 40; meas.remove();
      if (!(advHidden > 1)) advHidden = parseFloat(cs.fontSize) * .6; if (!(advShown > 1)) advShown = parseFloat(cs.fontSize) * .6;
      layout();
    };
    let chars = [], shown = false, val = '';
    const mix = spring(0, 300, 30, () => layout());
    const layout = () => { const a = advHidden + (advShown - advHidden) * mix.x;
      chars.forEach((c, i) => { c.style.transform = `translate3d(${(i * a).toFixed(2)}px,0,0)`; c.style.width = a.toFixed(2) + 'px'; }); syncScroll(); };
    const syncScroll = () => { track.style.transform = `translate3d(${-input.scrollLeft}px,0,0)`; };
    const GLYPHS = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789#$%&*+=?@';
    const scramble = (c, ch, delay, dur) => {
      if (reduce.matches) { c.firstChild.textContent = ch; return; }
      const t0 = performance.now() + delay; let lastSwap = 0;
      c.classList.add('is-scr');
      run((dt, now) => { if (!c.isConnected) return false;
        if (now < t0) return true;
        if (now - t0 > dur) { c.firstChild.textContent = ch; c.classList.remove('is-scr'); return false; }
        if (now - lastSwap > 38) { lastSwap = now; c.firstChild.textContent = GLYPHS[(Math.random() * GLYPHS.length) | 0]; }
        return true; });
    };
    const makeChar = (ch) => { const c = document.createElement('span'); c.className = 'vs-password-meter-ch'; c.innerHTML = '<b></b><i></i>'; c.firstChild.textContent = ch; return c; };
    const render = (next) => {
      // diff: common prefix + suffix; the middle is removed / inserted
      const a = [...val], b = [...next]; let p = 0; while (p < a.length && p < b.length && a[p] === b[p]) p++;
      let s = 0; while (s < a.length - p && s < b.length - p && a[a.length - 1 - s] === b[b.length - 1 - s]) s++;
      const gone = chars.splice(p, a.length - p - s), added = b.slice(p, b.length - s).map(makeChar);
      // removed characters drop away, right to left when many go at once (select all + delete)
      gone.forEach((c, k) => { if (reduce.matches) return c.remove();
        const d = Math.min((gone.length - 1 - k) * 14, 260);
        c.animate([{ opacity: 1, transform: c.style.transform }, { opacity: 0, transform: c.style.transform + ' translateY(.45em) scale(.4)' }], { duration: 200, delay: d, easing: 'cubic-bezier(.4,0,1,1)', fill: 'forwards' }).onfinish = () => c.remove(); });
      const ref = chars[p] || null; added.forEach((c) => track.insertBefore(c, ref));
      chars.splice(p, 0, ...added); val = next; layout();
      if (!reduce.matches) added.forEach((c, k) => {
        c.firstElementChild.nextElementSibling.animate([{ transform: 'scale(0)', opacity: 0 }, { transform: 'scale(1.35)', opacity: 1, offset: .5 }, { transform: 'scale(1)', opacity: 1 }], { duration: 300, delay: k * 12, easing: 'cubic-bezier(.2,0,0,1)', fill: 'backwards' });
        if (shown) { c.firstChild.animate([{ transform: 'translateY(.35em) scale(.7)', opacity: 0, filter: 'blur(3px)' }, { transform: 'none', opacity: 1, filter: 'none' }], { duration: 320, delay: k * 12, easing: 'cubic-bezier(.34,1.56,.64,1)', fill: 'backwards' }); }
      });
    };

    /* ── eye: lids part, the pupil grows, the lashes fade ── */
    const eyeSpring = spring(0, 260, 20, (o) => {
      const u = 15 - 11 * o, l = 15 + 3.5 * o;
      lidU.setAttribute('d', `M2.5 12.2 C 7 ${u.toFixed(2)} 17 ${u.toFixed(2)} 21.5 12.2`);
      lidL.setAttribute('d', `M2.5 12.2 C 7 ${l.toFixed(2)} 17 ${l.toFixed(2)} 21.5 12.2`);
      pupil.setAttribute('r', Math.max(0, 3.1 * o).toFixed(2)); pupil.setAttribute('cy', (12.4 + .6 * (1 - o)).toFixed(2));
      const k = Math.max(0, 1 - o * 1.6);
      lash.setAttribute('d', `M6.2 ${15.3 + 0}l-1.2 ${2.2 * k} M12 16.6l0 ${2.4 * k} M17.8 15.3l1.2 ${2.2 * k}`); lash.style.opacity = k.toFixed(3);
    });
    eyeSpring.to(0); eyeSpring.step(1 / 60);
    const reveal = (on) => {
      on = !!on; if (on === shown) return; shown = on;
      const a = input.selectionStart, b = input.selectionEnd, dir = input.selectionDirection;
      input.type = on ? 'text' : 'password';
      try { if (document.activeElement === input) input.setSelectionRange(a, b, dir); } catch (e) {}
      root.classList.toggle('is-shown', on); eye.setAttribute('aria-pressed', String(on)); eye.setAttribute('aria-label', on ? 'Şifrəni gizlət' : 'Şifrəni göstər');
      eyeSpring.to(on ? 1 : 0); mix.to(on ? 1 : 0);
      // a left-to-right wave: each glyph scrambles in, or folds back into a dot
      const n = chars.length, step = Math.min(22, 300 / Math.max(1, n)), arr = [...val];
      chars.forEach((c, i) => {
        const b = c.firstChild, d = c.firstChild.nextSibling; b.style.transitionDelay = d.style.transitionDelay = (i * step) + 'ms';
        setTimeout(() => { b.style.transitionDelay = d.style.transitionDelay = ''; }, i * step + 450);
        if (on) scramble(c, arr[i], i * step, 150 + Math.random() * 90);
      });
      // swapping the type resets the field's scroll in some browsers: keep the caret in view
      requestAnimationFrame(() => {
        if (document.activeElement === input) { try { input.setSelectionRange(a, b, dir); } catch (e) {} const cs = getComputedStyle(input), inner = input.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
          const cx = (input.selectionEnd || 0) * (on ? advShown : advHidden);
          if (cx - input.scrollLeft > inner) input.scrollLeft = cx - inner + 2; else if (cx < input.scrollLeft) input.scrollLeft = cx; }
        syncScroll(); });
      say(on ? 'Şifrə göstərilir' : 'Şifrə gizlədildi');
    };
    eye.addEventListener('pointerdown', (e) => { if (e.pointerType === 'mouse') e.preventDefault(); }); // keep focus (and the caret) in the field
    eye.addEventListener('click', () => reveal(!shown));

    /* ── scoring ── */
    let level = 0, lastLevel = -1, sayT = 0;
    const say = (t) => { sr.textContent = ''; setTimeout(() => (sr.textContent = t), 40); };
    const update = () => {
      const pw = input.value, n = [...pw].length, min = minLen();
      const bits = estimate(pw), common = n > 0 && isCommon(pw);
      const r = { length: n >= min, case: /\p{Ll}/u.test(pw) && /\p{Lu}/u.test(pw), number: /\d/.test(pw), symbol: /[^\p{L}\p{N}\s]/u.test(pw), common: n >= 4 && !common };
      level = !n ? 0 : n < min ? 0 : common ? 1 : bits < 28 ? 1 : bits < 45 ? 2 : bits < 64 ? 3 : 4;
      const m = !n ? 0 : n < min ? Math.min(.92, .12 + .8 * n / min) : level;
      // the segment that just filled gets a brief lift of light
      if (!reduce.matches && Math.floor(m) > Math.floor(lastM) && fills[Math.floor(m) - 1]) fills[Math.floor(m) - 1].animate([{ filter: 'brightness(1)' }, { filter: 'brightness(1.7)', offset: .3 }, { filter: 'brightness(1)' }], { duration: 650, delay: 120, easing: 'cubic-bezier(.2,0,0,1)' });
      lastM = m; meter.to(m);
      root.classList.toggle('is-empty', !n);
      setWord(!n ? 'Şifrəni daxil et' : n < min ? LABELS[0] : common ? 'Çox yayılmış' : LABELS[level]);
      bitsText = n ? crackTime(bits) : ''; bitSpring.to(bits); paintCrack();
      for (const k in r) { const li = rules[k]; if (!li) continue; const was = li.classList.contains('is-met');
        if (was !== r[k]) { li.classList.toggle('is-met', r[k]); li.classList.remove('is-settled'); li.__sr.textContent = r[k] ? ', hazırdır' : ', hələ yox'; if (r[k]) setTimeout(() => li.classList.add('is-settled'), 260); } }
      if (level !== lastLevel || !n) { lastLevel = level; clearTimeout(sayT); sayT = setTimeout(() => { if (input.value && root.dataset.mode !== 'login') say('Şifrənin gücü: ' + (common ? 'çox yayılmış' : n < min ? 'çox qısa' : LABELS[level])); }, 700); }
      root.dispatchEvent(new CustomEvent('vs-password-meter-change', { bubbles: true, detail: { level: n < min ? 0 : level, label: n < min ? LABELS[0] : LABELS[level], bits: Math.round(bits), rules: r } }));
    };
    const syncValue = () => { render(input.value); update(); requestAnimationFrame(syncScroll); };
    input.addEventListener('input', syncValue);
    input.addEventListener('change', syncValue);
    input.addEventListener('focus', () => { if (input.value !== val) syncValue(); });
    input.form?.addEventListener('reset', () => requestAnimationFrame(() => { reveal(false); syncValue(); }));
    ['keyup', 'click', 'select', 'scroll', 'focus'].forEach((t) => input.addEventListener(t, () => requestAnimationFrame(syncScroll)));
    const caps = (e) => { if (!e.getModifierState) return; const on = e.getModifierState('CapsLock'); if (on && !root.classList.contains('is-caps')) say('Caps Lock aktivdir'); root.classList.toggle('is-caps', on); };
    input.addEventListener('keydown', caps); input.addEventListener('keyup', caps);
    input.addEventListener('blur', () => root.classList.remove('is-caps'));
    new MutationObserver(() => { syncAttrs(); pal = stops(); update(); }).observe(root, { attributes: true, attributeFilter: ['data-min-length', 'data-disabled', 'data-theme', 'data-mode'] });
    // The entry mounts inside a closed dialog. Measure again when it opens or
    // changes width, rather than retaining fallback character spacing.
    new ResizeObserver(measure).observe(input);
    if (document.fonts) { document.fonts.ready.then(measure); document.fonts.addEventListener('loadingdone', measure); } measure();
    if (input.value) { render(input.value); }
    update();
    Object.defineProperty(root, 'value', { get: () => input.value, configurable: true });
    root.reveal = reveal;
    root.setValue = (v) => { input.value = String(v ?? ''); input.dispatchEvent(new Event('input', { bubbles: true })); };
    root.reset = () => { input.value = ''; render(''); reveal(false); track.replaceChildren(); root.classList.remove('is-caps'); update(); sr.textContent = ''; };
    root.refresh = syncValue;
    root.dataset.enhanced = "true";
  }
  const init = () => document.querySelectorAll('.vs-password-meter').forEach(mount);
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', init) : init();
  window.vsPasswordMeter = { mount };
})();
