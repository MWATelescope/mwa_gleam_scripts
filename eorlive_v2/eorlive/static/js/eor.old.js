// Override some of the stuff from EoR

EoR.pages = ["logs", "charts"];

EoR.init = function(){

  $.ajaxSetup({type:"json"});

  // Handle hash change event and navbar component updates
  function hashChanged(){
    if( EoR.isAnimating ) {
      setTimeout(hashChanged, 300);
      return;
    }
    var content_id = (window.location.hash.replace("#", "")) || "logs";
    console.log(content_id);
    if(EoR.pages.indexOf(content_id) < 0) return;
    EoR.view_translate(content_id);
    $(".navbar .nav.navbar-nav li").removeClass("active");
    $(".navbar .nav.navbar-nav li."+content_id).addClass("active");
  }
  $(window).off('hashchange').on('hashchange', hashChanged);
  hashChanged();
  EoR.google.init(); // Logs and Graphs based on Google APIs
};

// Per Page Events
EoR.onPageTransition = function(page_id){
  //console.log("onPageTransition  " + page_id);
  var index = EoR.pages.indexOf(page_id);
  if(!page_id) page_id = "_null";
  var transitioned_to = EoR.transitioned_to[index];

  switch(page_id){
    case 'charts':
      break;
    case 'logs':
      break;
  }

  EoR.transitioned_to[index] = true;
}
