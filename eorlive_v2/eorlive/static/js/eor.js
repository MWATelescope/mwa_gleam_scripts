var EoR = {};

EoR.init = function(){

  $.ajaxSetup({type:"json"});

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

  EoR.check_user(function(){
    $(".navbar .logging_in_msg").remove();
    $(".navbar .logged_in_msg")
      .append("Hello " + EoR.current_user.name + " (")
      .append($("<a/>").attr("href", "#").text("Log out").click(EoR.logout))
      .append(")");
    // Initiate content boxes
    EoR.clock.init(); // Clocks widget
    EoR.google.init(); // Logs and Graphs based on Google APIs
  });
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
