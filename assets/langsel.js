/* header language select (inlined on every page right after the select, so it works even if play.js fails to load).
   Choosing a language saves it ("ipe_lang") and opens that language's page; English goes to "/?lang=en" (see langpick.js).
   The select always shows this page's own language, also after back/forward or a reload. */
(function(){
  var s=document.getElementById('lang-select');
  if(!s)return;
  function sync(){for(var j=0;j<s.options.length;j++)s.options[j].selected=s.options[j].defaultSelected}
  sync();
  s.addEventListener('change',function(){
    var l=this.options[this.selectedIndex].getAttribute('data-lang'),u=this.value;
    try{localStorage.setItem('ipe_lang',l)}catch(e){}
    if(l==='en')u+='?lang=en';
    location.href=u;
  });
  window.addEventListener('pageshow',function(e){if(e.persisted)sync()});
})();
