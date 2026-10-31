(function(){
  /* an explicit language choice wins over the browser language the root page follows (see langpick.js) */
  document.addEventListener('click',function(e){
    var a=e.target.closest&&e.target.closest('.langsw a[hreflang],.foot-langs a[hreflang],.langs a[hreflang]');
    if(a){try{localStorage.setItem('play-lang',a.getAttribute('hreflang'))}catch(x){}}
  });
})();
