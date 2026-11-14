/* play.ipe.rest: first visit to "/" -> the visitor's language (inlined into the root home page only; build_site fills in the list).
   Order: the language saved on the site (localStorage "ipe_lang", copied once from the old "play-lang") > first match in navigator.languages
   (exact tag, then its base: pt-PT -> pt-BR, id-ID -> id, ko-KR -> ko; zh-TW/zh-HK/zh-MO -> zh-Hant; other unbuilt tags -> stay on the English root).
   A saved zh (no region) is Traditional like zh-TW; a saved zh-CN/zh-SG stays English on purpose: the site has no Simplified Chinese,
   so a Simplified choice is not sent to Traditional. Choosing English in the header select adds ?lang=en, so the visitor is not
   sent back here when localStorage is blocked. Crawlers are never redirected. No server redirect: they see "/" as English. */
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
    if(/bot|crawl|spider|slurp|mediapartners|lighthouse|facebookexternalhit|google-inspectiontool|headlesschrome|bingpreview/i.test(navigator.userAgent||''))return;
    if(/[?&]lang=en(&|$)/.test(location.search))return;
    var to='',saved='';
    try{
      var old=localStorage.getItem('play-lang');
      if(old!==null){
        if(!localStorage.getItem('ipe_lang'))localStorage.setItem('ipe_lang',old);
        localStorage.removeItem('play-lang');
      }
      saved=localStorage.getItem('ipe_lang')||'';
    }catch(e){}
    var sv=saved.toLowerCase();
    if(sv==='zh')sv='zh-tw';
    if(/^zh-(cn|sg)$/.test(sv))to='en';
    else to=pick(sv);
    if(!to){
      var L=(navigator.languages&&navigator.languages.length)?navigator.languages:[navigator.language||''];
      for(var i=0;i<L.length&&!to;i++)to=pick(L[i]);
    }
    if(to&&to!=='en')location.replace('/'+to+'/'+location.search+location.hash);
  }catch(e){}
})();
