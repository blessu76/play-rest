/* Sunmeld: first visit to "/" -> the visitor's browser language (inlined into the root home page only; build_site fills in the list).
   Order: the language the visitor picked on the site (localStorage "cb-lang") > first match in navigator.languages
   (exact tag, then its first part: ko-KR -> ko, zh-TW -> zh) > stay on the English root. No server redirect: crawlers see "/" as English. */
(function(){
  var S=/*SUPPORTED*/[];
  try{
    if(location.pathname!=='/')return;
    var to='',saved='';
    try{saved=localStorage.getItem('cb-lang')||''}catch(e){}
    if(S.indexOf(saved)>=0)to=saved;
    else{
      var L=(navigator.languages&&navigator.languages.length)?navigator.languages:[navigator.language||''];
      for(var i=0;i<L.length&&!to;i++){
        var c=String(L[i]||'').toLowerCase().replace(/_/g,'-');
        /* legacy codes: Android/old browsers say "in" for Indonesian. Traditional Chinese (zh-Hant) has no pages yet, so it goes to zh. */
        if(c.split('-')[0]==='in')c='id'+c.slice(2);
        if(S.indexOf(c)>=0)to=c;else if(S.indexOf(c.split('-')[0])>=0)to=c.split('-')[0];
      }
    }
    if(to&&to!=='en')location.replace('/'+to+'/'+location.search+location.hash);
  }catch(e){}
})();
