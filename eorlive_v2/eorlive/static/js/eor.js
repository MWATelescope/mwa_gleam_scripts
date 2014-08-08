var EoR = {};

EoR.pages = ["home", "obs", "logs", "links", "account"];
EoR.transitioned_to = [false, false, false, false, false]; // keeps track of whether a page has been viewed since load

EoR.init = function(){

  $.ajaxSetup({type:"json"});

  // Handle hash change event and navbar component updates
  function hashChanged(){
    if( EoR.isAnimating ) {
      setTimeout(hashChanged, 300);
      return;
    }
    var content_id = (window.location.hash.replace("#", "")) || "home";
    if(EoR.pages.indexOf(content_id) < 0) return;
    EoR.view_translate(content_id);
    $(".navbar .nav.navbar-nav li").removeClass("active");
    $(".navbar .nav.navbar-nav li."+content_id).addClass("active");
  }
  $(window).on('hashchange', hashChanged);
  hashChanged();

  EoR.render_logged_in_message();
  // Initiate content boxes
  EoR.clock.init(); // Clocks widget
  EoR.obs.init(); // Observation data from MIT database
  EoR.img.init(); // Load Beam Images
  EoR.graph.init(); // Load graphs
  EoR.logs.init();
  EoR.account.init(); // Account settings render

  EoR.obs.fetch_observations(EoR.obs.fetch_future_observation_counts);
  EoR.graph.fetch_data();
};

EoR.render_logged_in_message = function(){
  $(".navbar .logging_in_msg").remove();
  $(".navbar .logged_in_msg").empty()
    .append("Hello " + EoR.current_user.name + " (")
    .append($("<a/>").attr("href", "#").text("Log out").click(EoR.logout))
    .append(")");
};

EoR.create_loading = function(){
  return $("<img>").addClass("loading").attr("src", STATIC_PATH+"/img/loading.gif");
};


EoR.check_user = function(cb){
  $.ajax({
    method: "GET",
    url: "/api/current_user",
    type: "json",
    success: function(data){
      EoR.current_user = data;
      if(cb) cb();
    },
    error: function(xhr, status, err){
      window.location = "/login";
    }
  });
};

EoR.logout = function(e){
  $.ajax({
    method: "POST",
    url: "/api/logout",
    type: "json",
    success: function(data){
      window.location = "/login";
    },
    error: function(xhr, status, err){
      alert("something went wrong...");
    }
  });
};

EoR.render_user_info = function(){

};

// Per Page Events
EoR.onPageTransition = function(page_id){
  console.log("onPageTransition  " + page_id);
  var index = EoR.pages.indexOf(page_id);
  if(!page_id) page_id = "_null";
  var transitioned_to = EoR.transitioned_to[index];

  switch(page_id){
    case 'home':
      break;
    case 'obs':
      break;
    case 'logs':
      if(!transitioned_to){
        EoR.logs.fetch_observation_logs(true);
      }
      break;
    case 'links':
      break;
    case 'account':
      break;
    case '_null':
      break;
  }

  EoR.transitioned_to[index] = true;
}


// Things needed for view translation
EoR.isAnimating = false;
EoR.endCurrPage = false;
EoR.endNextPage = false;
EoR.animEndEventNames = {
  'WebkitAnimation' : 'webkitAnimationEnd',
  'OAnimation' : 'oAnimationEnd',
  'msAnimation' : 'MSAnimationEnd',
  'animation' : 'animationend'
};
EoR.animEndEventName = EoR.animEndEventNames[ Modernizr.prefixed( 'animation' ) ],
EoR.css_support = Modernizr.cssanimations;
EoR.onEndAnimation = function(from, to, to_id){
  EoR.isAnimating = false;
  from.removeClass("pt-page-current pt-page-moveToLeft pt-page-moveToRight").hide();
  to.removeClass("pt-page-moveFromRight pt-page-moveFromLeft pt-page-current");
  EoR.onPageTransition(to_id);
};

EoR.view_translate = function(to_id){

  if( EoR.isAnimating ) return;

  var from = $(".content_container:visible").addClass( 'pt-page-current' ), to = $("#"+to_id),
    order = EoR.pages,
    is_left = order.indexOf(to_id) > order.indexOf(from.attr("id")),
    in_class = is_left ? "pt-page-moveFromRight": "pt-page-moveFromLeft",
    out_class = is_left ? "pt-page-moveToLeft": "pt-page-moveToRight";

  if (from.attr("id") == to_id) return;

  EoR.isAnimating = true;
  EoR.endCurrPage = false;
  EoR.endNextPage = false;

  from.addClass( out_class ).on( EoR.animEndEventName, function() {
    from.off( EoR.animEndEventName );
    EoR.endCurrPage = true;
    if(EoR.endNextPage)
      EoR.onEndAnimation( from, to );
  });

  to.show().addClass( in_class ).on( EoR.animEndEventName, function() {
    to.off( EoR.animEndEventName );
    EoR.endNextPage = true;
    if(EoR.endCurrPage)
      EoR.onEndAnimation( from, to, to_id );
  });

	if( !EoR.css_support  ) {
		EoR.onEndAnimation( from, to, to_id );
	}
};
