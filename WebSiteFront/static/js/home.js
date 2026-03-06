/* Безопасность: экранирование для вставки в HTML (защита от XSS) */
function escapeHtml(str) {
  if (str == null) return '';
  var s = String(str);
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/* Безопасность полей формы: санитизация ввода */
function sanitizeName(val) {
  if (val == null) return '';
  return String(val).trim().replace(/[<>\"'&]/g, '').slice(0, 200);
}
function sanitizeEmail(val) {
  if (val == null) return '';
  return String(val).trim().toLowerCase().slice(0, 254);
}
function sanitizePhone(val) {
  if (val == null) return '';
  return String(val).replace(/[^0-9\s\+\-\(\)]/g, '').trim().slice(0, 20);
}

/* THEME — базовый белый фон, иконка = текущая тема (☀️ светлая, 🌙 тёмная) */
const html = document.documentElement;
const ball = document.getElementById('themeBall');
function updateThemeIcon() {
  ball.innerHTML = html.getAttribute('data-theme') === 'light' ? 
    '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>' : 
    '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>';
}
document.getElementById('themeToggle').onclick = () => {
  const isDark = html.getAttribute('data-theme') === 'dark';
  const newTheme = isDark ? 'light' : 'dark';
  html.setAttribute('data-theme', newTheme);
  localStorage.setItem('theme', newTheme);
  updateThemeIcon();
};

/* Инициализация темы из localStorage */
const savedTheme = localStorage.getItem('theme') || 'light';
html.setAttribute('data-theme', savedTheme);
updateThemeIcon();

/* MOBILE NAV */
const burger = document.getElementById('navBurger');
const mobile = document.getElementById('navMobile');
burger.onclick = () => {
  burger.classList.toggle('open');
  mobile.classList.toggle('open');
  document.body.style.overflow = mobile.classList.contains('open') ? 'hidden' : '';
};
mobile.querySelectorAll('a').forEach(link => {
  link.onclick = () => {
    burger.classList.remove('open');
    mobile.classList.remove('open');
    document.body.style.overflow = '';
  };
});

/* Форма заявки на главной: санитизация полей и безопасная отправка */
(function(){
  var form = document.getElementById('heroLeadForm');
  if (!form) return;
  var nameEl = document.getElementById('heroName');
  var emailEl = document.getElementById('heroEmail');
  var phoneEl = document.getElementById('heroPhone');
  var agreeEl = document.getElementById('heroAgree');

  function applySanitize(el, fn) {
    if (!el) return;
    el.addEventListener('blur', function() {
      var v = fn(el.value);
      if (v !== el.value) el.value = v;
    });
    el.addEventListener('input', function() {
      var pos = el.selectionStart;
      var v = fn(el.value);
      if (v !== el.value) {
        el.value = v;
        el.setSelectionRange(Math.min(pos, v.length), Math.min(pos, v.length));
      }
    });
  }
  applySanitize(nameEl, sanitizeName);
  applySanitize(emailEl, sanitizeEmail);
  applySanitize(phoneEl, sanitizePhone);

  form.addEventListener('submit', function(e) {
    e.preventDefault();
    if (nameEl) nameEl.value = sanitizeName(nameEl.value);
    if (emailEl) emailEl.value = sanitizeEmail(emailEl.value);
    if (phoneEl) phoneEl.value = sanitizePhone(phoneEl.value);
    if (agreeEl && !agreeEl.checked) {
      agreeEl.focus();
      return;
    }
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }
    var url = form.getAttribute('data-register-url') || '/register/';
    if (url) window.location.href = url;
  });
})();

/* CTA — пригласительный блок: переключение темы и интерактивное свечение */
(function(){
  const section = document.getElementById('cta');
  const box = section && section.querySelector('.cta-invite-box');
  const glow = document.getElementById('ctaGlow');
  const toggleBtn = document.getElementById('ctaThemeToggle');
  const toggleIcon = document.getElementById('ctaThemeIcon');
  if(!section || !box || !glow || !toggleBtn) return;

  var savedCta = localStorage.getItem('ctaInviteTheme') || '';
  if(savedCta === 'invite-light'){
    section.setAttribute('data-cta-theme', 'invite-light');
    if(toggleIcon) toggleIcon.textContent = '🌙';
    toggleBtn.title = 'Тёмное оформление';
  }

  toggleBtn.addEventListener('click', function(){
    var isLight = section.getAttribute('data-cta-theme') === 'invite-light';
    if(isLight){
      section.removeAttribute('data-cta-theme');
      localStorage.setItem('ctaInviteTheme', '');
      if(toggleIcon) toggleIcon.textContent = '☀';
      toggleBtn.title = 'Светлое оформление';
    } else {
      section.setAttribute('data-cta-theme', 'invite-light');
      localStorage.setItem('ctaInviteTheme', 'invite-light');
      if(toggleIcon) toggleIcon.textContent = '🌙';
      toggleBtn.title = 'Тёмное оформление';
    }
  });

  box.addEventListener('mousemove', function(e){
    var rect = box.getBoundingClientRect();
    var x = e.clientX - rect.left;
    var y = e.clientY - rect.top;
    glow.style.left = x + 'px';
    glow.style.top = y + 'px';
    glow.style.opacity = '1';
  });
  box.addEventListener('mouseleave', function(){ glow.style.opacity = '0'; });
})();

/* COUNTDOWN */
(function(){
  const end = new Date(); end.setDate(end.getDate()+1); end.setHours(13,29,11,0);
  function tick(){
    const diff = Math.max(0, end - Date.now());
    const d = Math.floor(diff/86400000);
    const h = String(Math.floor((diff%86400000)/3600000)).padStart(2,'0');
    const m = String(Math.floor((diff%3600000)/60000)).padStart(2,'0');
    const s = String(Math.floor((diff%60000)/1000)).padStart(2,'0');
    const el = document.getElementById('timer');
    if(el) el.textContent = `${d} дн ${h}:${m}:${s}`;
  }
  tick(); setInterval(tick,1000);
})();

/* COURSES CAROUSEL */
(function(){
  const track = document.getElementById('courseTrack');
  const cards = track.querySelectorAll('.course-card');
  let idx = 0;
  const cardW = 240 + 20;
  function update(){
    track.style.transform = `translateX(-${idx * cardW}px)`;
    cards.forEach((c,i) => c.classList.toggle('course-active', i===idx));
  }
  document.getElementById('cNext').onclick = () => { idx = Math.min(idx+1, cards.length-1); update(); };
  document.getElementById('cPrev').onclick = () => { idx = Math.max(idx-1, 0); update(); };
  // Auto-advance
  setInterval(() => { idx = (idx+1) % cards.length; update(); }, 3500);
})();

/* FREE MATERIALS SCROLL */
(function(){
  const track = document.getElementById('freeTrack');
  const cards = track.querySelectorAll('.free-card');
  let idx = 0;
  const cardW = 300 + 18;
  function update(){ track.style.transform = `translateX(-${idx * cardW}px)`; }
  document.getElementById('freeNext').onclick = () => { idx = Math.min(idx+1, cards.length-2); update(); };
  document.getElementById('freePrev').onclick = () => { idx = Math.max(idx-1, 0); update(); };
})();

/* ABOUT TABS */
function setAbTab(btn, panelId){
  document.querySelectorAll('.ab-tab').forEach(b=>b.classList.remove('act'));
  document.querySelectorAll('.about-panel').forEach(p=>p.classList.remove('act'));
  btn.classList.add('act');
  document.getElementById(panelId).classList.add('act');
}

/* POPULAR TABS */
function setPopTab(btn, tabId){
  document.querySelectorAll('.pop-tab').forEach(b=>b.classList.remove('act'));
  btn.classList.add('act');
  document.getElementById('ptab-paid').style.display = tabId==='ptab-paid'?'':'none';
  document.getElementById('ptab-free').style.display = tabId==='ptab-free'?'':'none';
}

/* PROFTEST — баллы по профилям [ai_business, design_content, python_ml, analytics] */
const qs = [
  {q:'Сколько вам лет',o:['До 18','От 18 до 24','От 25 до 34','От 35 до 44','От 45 до 54','55 и старше'],scores:[[0,1,1,0],[1,1,2,1],[2,1,1,2],[2,0,0,1],[2,0,0,1],[2,1,0,0]]},
  {q:'Ваш текущий уровень в IT',o:['Полный новичок','Базовые знания','Средний уровень','Опытный специалист'],scores:[[2,2,0,0],[2,1,1,1],[1,0,2,2],[0,0,2,2]]},
  {q:'Цель обучения',o:['Сменить профессию','Повысить эффективность','Запустить свой продукт','Из интереса'],scores:[[0,0,3,2],[3,1,0,1],[1,1,2,2],[1,2,1,1]]},
  {q:'Сколько времени готовы уделять',o:['1–3 ч/неделю','4–7 ч/неделю','8–15 ч/неделю','Интенсивно'],scores:[[2,2,0,0],[2,1,1,1],[0,0,2,2],[0,0,3,2]]},
  {q:'Какое направление AI интересует',o:['Контент и дизайн','Аналитика и данные','Разработка и код','Автоматизация бизнеса'],scores:[[0,3,0,0],[1,0,0,3],[0,0,3,1],[3,0,0,1]]}
];
const ptResults = {
  ai_business:{title:'AI для бизнеса',emoji:'📊',desc:'Вам подойдут курсы по автоматизации, ChatGPT, Midjourney и AI-инструментам для повышения эффективности.'},
  design_content:{title:'Контент и дизайн',emoji:'🎨',desc:'Ваша ниша — генерация изображений и текстов с помощью нейросетей. Рекомендуем Midjourney, DALL·E, ChatGPT для креатива.'},
  python_ml:{title:'Python и машинное обучение',emoji:'🐍',desc:'Вам интересна разработка и данные. Подойдут курсы по Python, ML и созданию AI-продуктов.'},
  analytics:{title:'Аналитика и данные',emoji:'📈',desc:'Вам близка работа с данными. Рекомендуем курсы по Data Science и аналитике с AI.'}
};
let qi = 0;
let ptAnswers = [];
function selOpt(el){
  document.querySelectorAll('.pt-o').forEach(o=>o.classList.remove('sel'));
  el.classList.add('sel');
}
function nextQ(){
  const sel = document.querySelector('.pt-o.sel');
  if(!sel) return;
  const opts = document.getElementById('ptOpts');
  const idx = Array.prototype.indexOf.call(opts.children, sel);
  ptAnswers.push(idx);
  qi = Math.min(qi+1, qs.length-1);
  const pct = Math.round((qi/qs.length)*100);
  document.getElementById('qLbl').textContent = qs[qi].q;
  document.getElementById('qPct').textContent = pct+'%';
  document.getElementById('ptFill').style.width = pct+'%';
  document.getElementById('ptOpts').innerHTML = qs[qi].o.map((o,i)=>'<div class="pt-o" onclick="selOpt(this)"><span>'+escapeHtml(o)+'</span><div class="pt-radio"></div></div>').join('');
  if(qi===qs.length-1){
    const btn=document.getElementById('ptNext');
    btn.textContent='Узнать результат';
    btn.onclick=()=>{
      const sel = document.querySelector('.pt-o.sel');
      if(!sel) return;
      const opts = document.getElementById('ptOpts');
      ptAnswers.push(Array.prototype.indexOf.call(opts.children, sel));
      const scores = {ai_business:0,design_content:0,python_ml:0,analytics:0};
      const keys = ['ai_business','design_content','python_ml','analytics'];
      for(let i=0;i<qs.length;i++){
        const s = qs[i].scores[ptAnswers[i]];
        if(s) for(let k=0;k<4;k++) scores[keys[k]]+=s[k];
      }
      let max=-1, win='ai_business';
      keys.forEach(k=>{ if(scores[k]>max){ max=scores[k]; win=k; } });
      const r = ptResults[win];
      if (!r) return;
      document.querySelector('.pt-r').innerHTML='<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:280px;text-align:center;padding:48px 36px"><div style="width:64px;height:64px;border-radius:50%;background:linear-gradient(135deg,#8b5cf6,#06b6d4);display:flex;align-items:center;justify-content:center;font-size:1.8rem;margin:0 auto 20px">'+escapeHtml(r.emoji)+'</div><h3 style="font-family:Unbounded,sans-serif;font-weight:900;font-size:1.25rem;margin-bottom:12px;letter-spacing:-.5px">Ваша ниша — '+escapeHtml(r.title)+'</h3><p style="color:var(--tx2);font-size:.85rem;line-height:1.7;margin-bottom:24px;max-width:320px">'+escapeHtml(r.desc)+'</p><a href="/register/?goal='+encodeURIComponent(win)+'" class="btn-p" style="text-decoration:none">Записаться на курс →</a><a href="/proftest/" style="display:block;margin-top:12px;font-size:.8rem;color:var(--tx3)">Пройти полный тест (7 вопросов) →</a></div>';
    };
  }
}

/* FAQ */
function tog(el){
  const item=el.closest('.fq');
  const open=item.classList.contains('open');
  document.querySelectorAll('.fq.open').forEach(i=>i.classList.remove('open'));
  if(!open) item.classList.add('open');
}

/* LMS TABS */
function setLt(el){
  document.querySelectorAll('.lt').forEach(t=>t.classList.remove('act'));
  el.classList.add('act');
}

/* SCROLL REVEAL */
const obs = new IntersectionObserver(entries=>{
  entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add('on');obs.unobserve(e.target);}});
},{threshold:0.07,rootMargin:'0px 0px -40px 0px'});
document.querySelectorAll('.rv').forEach(el=>obs.observe(el));

/* FLOATING TECH ICONS */
(function(){
  const icons = [
    '/static/img/tech/python.svg',
    '/static/img/tech/pycharm.svg',
    '/static/img/tech/chatgpt.svg',
    '/static/img/tech/tensorflow.svg',
    '/static/img/tech/jupyter.svg',
    '/static/img/tech/numpy.svg',
    '/static/img/tech/pytorch.svg',
  ];
  const container = document.getElementById('techIconsBg');
  if(!container) return;
  function spawnIcon(){
    const src = icons[Math.floor(Math.random()*icons.length)];
    const el = document.createElement('div');
    el.className = 'tech-icon';
    const size = 44 + Math.random()*20;
    const dur = 7 + Math.random()*7;
    const delay = Math.random()*2;
    el.style.cssText = `width:${size}px;height:${size}px;left:${30+Math.random()*55}%;bottom:${15+Math.random()*15}%;animation:floatIcon ${dur}s ${delay}s ease-in-out forwards;opacity:0.7;`;
    const img = document.createElement('img');
    img.src = src; img.style.cssText='width:26px;height:26px;object-fit:contain;border-radius:4px;';
    img.onerror = () => el.remove();
    el.appendChild(img);
    container.appendChild(el);
    setTimeout(()=>el.remove(), (dur+delay+1)*1000);
  }
  for(let i=0;i<5;i++) setTimeout(spawnIcon, i*1000);
  setInterval(spawnIcon, 1600);
})();

/* ANIMATED COUNTERS */
(function(){
  const countObs = new IntersectionObserver(entries=>{
    entries.forEach(e=>{
      if(!e.isIntersecting) return;
      const el = e.target;
      const text = el.textContent;
      const num = parseInt(text.replace(/\D/g,''));
      if(isNaN(num)||num<10) return;
      const hasSuffix = el.querySelector('em');
      const suffix = hasSuffix ? escapeHtml(hasSuffix.textContent || '') : '';
      const suffixTag = hasSuffix ? '<em>' + suffix + '</em>' : '';
      const dur = 1600; const startTime = performance.now();
      function step(now){
        const p = Math.min((now-startTime)/dur,1);
        const val = Math.floor((1-Math.pow(1-p,3))*num);
        el.innerHTML = val.toLocaleString('ru') + suffixTag;
        if(p<1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
      countObs.unobserve(el);
    });
  },{threshold:0.5});
  document.querySelectorAll('.mx-n').forEach(el=>countObs.observe(el));
})();