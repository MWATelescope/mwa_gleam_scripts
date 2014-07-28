EoR.logs = {};
EoR.logs.LIMIT = 10;
EoR.logs.offset = 0;
// DO NOT CHANGE THE TAGS!!! YOU CAN ONLY ADD MORE. DO NOT REMOVE OR CHANGE THE ORDER!!
EoR.logs.tags = ["bad", "fine", "no data", "hardware issue", "dataflow issue", "correlation issue", "got email from ops"];
EoR.logs.saved_tags_value = 0;

EoR.logs.create_fetch_interface = function(){
  return $("<div>").addClass("fetch_interface")
    .append(EoR.logs.create_tag_interface("fetch"))
    .append( $("<button/>").attr("type", "button").addClass("btn btn-primary load_more")
      .text("Fetch Data")
      .css("float","left")
      .click(function(e){
        EoR.logs.fetch_observation_logs(true);
      })
    )
};

EoR.logs.get_tags_value = function(ul){
  var total_val = 0;
  ul.children('li').each(function(i,el){
    var input = $(el).find("input");
    var val = input.data("index");
    if(input.is(":checked")){
      total_val += Math.pow(2, val);
    }
  });
  return total_val;
};

EoR.logs.get_tags_str_from_values = function(val){
  var tags = [];
  $.each(EoR.logs.tags, function(i,v){
    if(val & Math.pow(2,i)) tags.push(v);
  });
  var str = "";
  $.each(tags, function(i,v){
    str += (i==tags.length-1) ? v : v + ", ";
  });
  return str;
};

EoR.logs.create_table = function(){
  return table = $("<table/>").addClass("logs_table table table-striped")
    .append($("<thead>")
      .append($("<tr/>")
        .append($("<th/>").text("Observed Date"))
        .append($("<th/>").text("Observer Name"))
        .append($("<th/>").text("Note"))
        .append($("<th/>").text("Tags"))
        .append($("<th/>").text("   "))
      )
    )
    .append($("<tbody>"));
};

EoR.logs.create_post_interface = function(){
  return $("<div/>").addClass("tail_interface")
    .append( $("<div/>").addClass("bottom_buttons")
      .append( $("<button/>").attr("type", "button").addClass("btn btn-default load_more")
        .text("Load More")
        .click(function(e){
          EoR.logs.fetch_observation_logs();
        })
      )
      .append( $("<button/>").attr("type", "button").addClass("btn btn-primary show_post")
        .text("Post Log")
        .click(function(e){
          $("#observation_logs .tail_interface .bottom_buttons").hide();
          $("#observation_logs .tail_interface .post_interface").show();
        })
      )
    )
    .append( $("<div/>").addClass("post_interface").hide()
      .append("<hr/>")
      .append( $("<form>")
        .append($("<textarea/>").attr("placeholder", "Brief note about this observation").addClass("note"))
        .append("<br/>")
        .append($("<input/>").attr("placeholder", "observed date in yyyy-mm-dd format").addClass("observed_date"))
        .append($("<div/>").append(EoR.logs.create_tag_interface()))
      )
      .append( $("<div/>").addClass("buttons")
        .append( $("<button/>").attr("type", "button").addClass("btn btn-default")
          .text("Cancel")
          .click(function(e){
            $("#observation_logs .tail_interface .bottom_buttons").show();
            $("#observation_logs .tail_interface .post_interface").hide();
          })
        )
        .append( $("<button/>").attr("type", "button").addClass("btn btn-primary post")
          .text("Submit")
          .click(function(e){
            EoR.logs.post_observation_log();
          })
        )
      )
    );
};

EoR.logs.fetch_observation_logs = function(reset){

  if(reset){
    EoR.logs.offset = 0;
    EoR.logs.saved_tags_value = EoR.logs.get_tags_value($("ul.obs_tags.fetch"));
    $("#observation_logs .logs_table tbody").empty();
    $("#observation_logs .bottom_buttns .load_more").show();
  }

  $("#observation_logs .loading").show();
  $("#observation_logs .button").prop("disabled", false);
  $.ajax({
    url: "/api/observation_logs?tags="+EoR.logs.saved_tags_value+"&limit="+EoR.logs.LIMIT+"&offset="+EoR.logs.offset,
    type: "json",
    method: "GET",
    success: function(data){
      var tbody = $("#observation_logs .logs_table tbody");
      $.each(data.observation_logs, function(i,v){
        o_d = new Date(v.observed_date);
        tbody.append($("<tr/>")
          .append($("<td/>").text(o_d.getUTCFullYear() + "-" + (o_d.getUTCMonth()+1) + "-" + o_d.getUTCDate()))
          .append($("<td/>").text(v.author_user_name))
          .append($("<td/>").text(v.note))
          .append($("<td/>").text(EoR.logs.get_tags_str_from_values(v.tags)))
          .append($("<td/>")
            .append( $("<div>") // delete/edit buttons
            )
          )
        );
      });
      EoR.logs.offset += EoR.logs.LIMIT;
      if(data.observation_logs.length < EoR.logs.LIMIT){
        $("#observation_logs .bottom_buttons .load_more").hide();
      }
    },
    error: function(xhr, status, err){
      alert("an error occurred during fetching logs data");
    },
    complete: function(){
      $("#observation_logs .loading").hide();
      $("#observation_logs .button").prop("disabled", false);
    }
  });
};

EoR.logs.post_observation_log = function(){
  var observed_date = $("#observation_logs .post_interface .observed_date").val(),
    note =  $("#observation_logs .post_interface .note").val(),
    tags = EoR.logs.get_tags_value( $("#observation_logs .post_interface ul.obs_tags") );

  if(!/^\d{4}[\/\-](0?[1-9]|1[012])[\/\-](0?[1-9]|[12][0-9]|3[01]))$/.test(observed_date)){
    alert("Please enter a valid date in yyyy-mm-dd format");
    return
  }

  $("#observation_logs .loading").show();
  $("#observation_logs .button").prop("disabled", false);
  $.ajax({
    url: "/api/observation_logs",
    type: "json",
    method: "POST",
    data: {observed_date: observed_date, note: note, tags: tags},
    success: function(data){
      EoR.logs.fetch_observation_logs(true);
    },
    error: function(xhr, status, err){
      alert("error posting a new log");
    },
    complete: function(){
      $("#observation_logs .loading").hide();
      $("#observation_logs .button").prop("disabled", false);
    }
  })
}

EoR.logs.create_tag_interface = function(cls){
  var ul = $("<ul/>").addClass("obs_tags").addClass(cls);
  $.each(EoR.logs.tags, function(i,v){
    var id = v.replace(/ /g, "_");
    ul.append(
      $("<li/>")
        .append($("<label/>").attr("for", id).text(v))
        .append($("<input/>").attr("type","checkbox").data("index", i).attr("name",id).attr("id",id))
    );
  });
  return ul;
};

EoR.logs.init = function(){
  $("#observation_logs")
    .append(EoR.logs.create_fetch_interface())
    .append(EoR.logs.create_table())
    .append(EoR.create_loading().hide())
    .append(EoR.logs.create_post_interface());
};
