EoR.admin = {};

EoR.pages = ["users"];
EoR.transitioned_to = [false];

EoR.admin.init = function(){

  $.ajaxSetup({type:"json"});

  // Handle hash change event and navbar component updates
  function hashChanged(){
    if( EoR.isAnimating ) {
      setTimeout(hashChanged, 300);
      return;
    }
    var content_id = (window.location.hash.replace("#", "")) || "users";
    if(EoR.pages.indexOf(content_id) < 0) return;
    EoR.view_translate(content_id);
    $(".navbar .nav.navbar-nav li").removeClass("active");
    $(".navbar .nav.navbar-nav li."+content_id).addClass("active");
  }
  $(window).on('hashchange', hashChanged);
  hashChanged();

  EoR.render_logged_in_message();

  EoR.admin.render_users_ui();
  EoR.admin.fetch_users();
};


// Users - fetches users and render the table and other ui components in users container
EoR.admin.render_users_ui = function(){
  $("#users")
    .append(EoR.create_loading())
    .append(EoR.admin.create_users_table());
}

EoR.admin.create_users_table = function(){
  return table = $("<table/>").addClass("user_table table table-striped")
    .append($("<thead>")
      .append($("<tr/>")
        .append($("<th/>").text("ID"))
        .append($("<th/>").text("Username"))
        .append($("<th/>").text("Name"))
        .append($("<th/>").text("Deactivated"))
        .append($("<th/>").text("Admin?"))
        .append($("<th/>").text("   "))
      )
    )
    .append($("<tbody>"))
    .delegate("button.deativate", "click", function(el){
      if(!confirm("Really deactivate?")) return false;
      var id = $(this).data("user_id");

    })
    .delegate("button.edit", "click", function(el){
      var user = $(this).data("user");

    });
};

EoR.admin.fetch_users = function(){
  var loading = $("#users .loading").show();
  $.ajax({
    url: '/api/users',
    method:"GET",
    success: function(data){
      var tbody = $("#users .user_table tbody");
      $.each(data.users, function(i,v){
        tbody.append($("<tr/>").attr("id", "user_tr_"+v.id)
          .append($("<td/>").text(v.id))
          .append($("<td/>").text(v.username))
          .append($("<td/>").text(v.name))
          .append($("<td/>").text(v.deactivated_date?"Yes":"No"))
          .append($("<td/>").text(v.admin_level?"Yes":"No"))
          .append($("<td/>")
            .append(
              $("<div>")
                // deactivate button
                .append( (!v.admin_level && !v.deactivated_date)? $("<button/>")
                  .attr("type", "button")
                  .addClass("btn btn-danger deactivate")
                  .text("Deactivate")
                  .data("user_id", v.id) : ""
                )
                // reactivate button
                .append( (v.deactivated_date)? $("<button/>")
                  .attr("type", "button")
                  .addClass("btn btn-default reactivate")
                  .text("Reactivate")
                  .data("user_id", v.id) : ""
                )
                // Edit button
                .append( $("<button/>")
                  .attr("type", "button")
                  .addClass("btn btn-default edit")
                  .text("Edit")
                  .data("user", v)
                )
            )
          )
        );
      });
    },
    error: function(xhr, status, err){
      alert("Something went wrong while getting users");
    },
    complete: function(){
      loading.hide();
    }
  });
};
