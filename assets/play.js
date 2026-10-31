(function(){
  /* an explicit language choice wins over the browser language the root page follows (see langpick.js) */
  document.addEventListener('click',function(e){
    var a=e.target.closest&&e.target.closest('.langsw a[hreflang],.foot-langs a[hreflang],.langs a[hreflang]');
    if(a){try{localStorage.setItem('play-lang',a.getAttribute('hreflang'))}catch(x){}}
  });
  /* the language menu (<details>) closes on a click outside it and on Escape (focus goes back to its summary) */
  var sw=document.querySelector&&document.querySelector('details.langsw');
  if(!sw)return;
  document.addEventListener('click',function(e){if(sw.open&&!sw.contains(e.target))sw.open=false});
  document.addEventListener('keydown',function(e){
    if(sw.open&&(e.key==='Escape'||e.key==='Esc')){sw.open=false;var s=sw.querySelector('summary');if(s)s.focus()}
  });
})();
(function(){
  /* theme switch: the head script already set data-theme before first paint; this syncs the buttons and handles clicks */
  var root=document.documentElement,KEY='play-theme',T=['light','dark','noir'],
      C={light:'#fbfcfe',dark:'#0c1118',noir:'#0a0810'},
      dq=window.matchMedia&&matchMedia('(prefers-color-scheme:dark)'),
      rm=window.matchMedia&&matchMedia('(prefers-reduced-motion:reduce)'),
      btns=document.querySelectorAll('.themesw [data-theme-set]');
  function saved(){try{var v=localStorage.getItem(KEY);return T.indexOf(v)>=0?v:''}catch(e){return ''}}
  function paint(t){
    root.setAttribute('data-theme',t);
    var m=document.querySelectorAll('meta[name=theme-color]');for(var i=0;i<m.length;i++)m[i].content=C[t];
    for(var j=0;j<btns.length;j++)btns[j].setAttribute('aria-pressed',String(btns[j].getAttribute('data-theme-set')===t));
  }
  function system(){return dq&&dq.matches?'dark':'light'}
  paint(root.getAttribute('data-theme')||saved()||system());
  for(var k=0;k<btns.length;k++)btns[k].addEventListener('click',function(){
    var t=this.getAttribute('data-theme-set');
    if(!(rm&&rm.matches)){root.classList.add('theme-anim');setTimeout(function(){root.classList.remove('theme-anim')},250)}
    paint(t);try{localStorage.setItem(KEY,t)}catch(e){}
  });
  if(dq&&dq.addEventListener)dq.addEventListener('change',function(){if(!saved())paint(system())});
})();
