var EoR = {};

EoR.init = function(){

  // Handle hash change event and navbar component updates
  function hashChanged(){
    $(".content_container").hide();
    var content_id = (window.location.hash.replace("#", "")) || "home";
    $("#"+content_id).show();
    $(".navbar .nav.navbar-nav li").removeClass("active");
    $(".navbar .nav.navbar-nav li."+content_id).addClass("active");
  }
  $(window).on('hashchange', hashChanged);
  hashChanged();

  // Initiate content boxes
  EoR.clock.init();
};
