/* play.ipe.rest: first visit to "/" -> the visitor's browser language (inlined into the root home page only; build_site fills in the list).
   Order: the language saved on the site (localStorage "ipe_lang") > first match in navigator.languages
   (exact tag, then its base: pt-PT -> pt-BR, id-ID -> id, ko-KR -> ko; zh-TW/zh-HK/zh-MO -> zh-Hant; other unbuilt tags -> stay on the English root).
   Crawlers are never redirected. No server redirect: they see "/" as English. */
(function(){
  var S=/*SUPPORTED*/[];
  var M={};S.forEach(function(t){M[t.toLowerCase()]=t});
  function pick(c){
    c=String(c||'').toLowerCase().replace(/_/g,'-');
    if(c.split('-')[0]==='in')c='id'+c.slice(2);
    if(/^zh-(tw|hk|mo|hant)(-|$)/.test(c))c='zh-hant';
    if(c.split('-')[0]==='pt'&&!M[c])c='pt-br';
    return M[c]||M[c.split('-')[0]]||'';
  }
  try{
    if(location.pathname!=='/')return;
    if(/bot|crawl|spider|slurp|mediapartners|lighthouse/i.test(navigator.userAgent||''))return;
    var to='',saved='';
    try{saved=localStorage.getItem('ipe_lang')||''}catch(e){}
    if(M[saved.toLowerCase()])to=M[saved.toLowerCase()];
    else{
      var L=(navigator.languages&&navigator.languages.length)?navigator.languages:[navigator.language||''];
      for(var i=0;i<L.length&&!to;i++)to=pick(L[i]);
    }
    if(to&&to!=='en')location.replace('/'+to+'/'+location.search+location.hash);
  }catch(e){}
})();
