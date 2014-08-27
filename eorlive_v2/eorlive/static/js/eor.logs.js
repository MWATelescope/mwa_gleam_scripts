EoR.logs = {};
EoR.logs.LIMIT = 10;
EoR.logs.offset = 0;
// DO NOT CHANGE THE TAGS!!! YOU CAN ONLY ADD MORE. DO NOT REMOVE OR CHANGE THE ORDER!!
EoR.logs.tags = ["bad", "fine", "no data", "hardware issue", "dataflow issue", "correlation issue", "got email from ops"];
EoR.logs.saved_tags_value = 0;
EoR.logs.log_being_edited = null;

EoR.logs.create_fetch_interface = function(){
  now = new Date();
  return $("<div>").addClass("fetch_interface")
    .append(EoR.logs.create_tag_interface("fetch"))
    .append("<br/>")
    .append($("<div/>").addClass("form-group form-inline")
      .css("clear", "both").css("text-align", "left")
      .append($("<input/>").attr("placeholder", "from").addClass("from_date form-control")
        .datepicker({
          format: 'yyyy-mm-dd',
          onRender: function(date) {
            return date.valueOf() >= now.valueOf() ? 'disabled' : '';
          }
        })
        .on('changeDate', function(ev) {
          var to = $(".fetch_interface input.to_date");
          if (ev.date.valueOf() > to.data('datepicker').date.valueOf()) {
            to.data('datepicker').setValue(new Date(ev.date));
          }
          $(this).datepicker("hide");
          to[0].focus();
        })
      )
      .append($("<input/>").attr("placeholder", "to").addClass("to_date form-control")
        .datepicker({
          format: 'yyyy-mm-dd',
          onRender: function(date) {
            var from = $(".fetch_interface input.from_date");
            if(from && from.data('datepicker')){
              return date.valueOf() < from.data('datepicker').date.valueOf() || date.valueOf() >= now.valueOf()  ? 'disabled' : '';
            }
            return date.valueOf() >= now.valueOf() ? 'disabled' : '';
          }
        })
        .on('changeDate', function(ev) {
          var from = $(".fetch_interface input.from_date");
          if (ev.date.valueOf() < from.data('datepicker').date.valueOf()) {
            from.data('datepicker').setValue(new Date(ev.date));
          }
          $(this).datepicker("hide");
        })
      )
      .append( $("<button/>").attr("type", "button").addClass("btn btn-primary load_more")
        .text("Filter")
        .click(function(e){
          EoR.logs.fetch_observation_logs(true);
        })
      )
    );
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
    var span = "<span class=\"" + v.replace(/ /g, "-") + "\">" + v + "</span>";
    str += (i==tags.length-1) ? span : span + ", ";
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
    .append($("<tbody>"))
    .delegate("button.delete", "click", function(el){
      if(!confirm("Really delete?")) return false;
      var id = $(this).data("log_id");
      $(this).text("deleting...").prop("disabled", true);
      EoR.logs.delete_observation_log(id, function(){
        $("#log_tr_"+id).remove();
      });
    })
    .delegate("button.edit", "click", function(el){
      var log = $(this).data("log");
      EoR.logs.log_being_edited = log.id;
      EoR.logs.populate_post_interface(log);
      EoR.logs.show_post_interface();
    })
    .delegate("button.post", "click", function(el){
      window.location.hash = "logs";
      EoR.logs.show_post_interface();
    });
};

EoR.logs.populate_post_interface = function(log){
  var div = $("#observation_logs .post_interface");
  div.find(".note").val(log.note);
  if(log.observed_date){
    var obs_date = new Date(log.observed_date);
    div.find(".observed_date").val(obs_date.getUTCFullYear() + "-" + (obs_date.getUTCMonth()+1) + "-" + obs_date.getUTCDate());
  }  else
    div.find(".observed_date").val(null);

  // Tags
  div.find(".obs_tags li").each(function(i,el){
    $(el).find("input").prop("checked", !!(Math.pow(2,i) & log.tags) );
  });
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
          EoR.logs.log_being_edited = null;
          EoR.logs.populate_post_interface({note:"", tag:0});
          EoR.logs.show_post_interface();
        })
      )
    )
    .append( $("<div/>").addClass("post_interface").hide()
      .append("<hr/>")
      .append( $("<form>")
        .append($("<textarea/>").attr("placeholder", "Brief note about this observation").addClass("note form-control"))
        .append("<br/>")
        .append($("<input/>").attr("placeholder", "observed date").addClass("observed_date form-control")
          .datepicker({
    				format: 'yyyy-mm-dd'
    			})
          .on('changeDate', function(ev) {
            $(this).datepicker("hide")
          })
        )
        .append($("<div/>").append(EoR.logs.create_tag_interface()))
      )
      .append( $("<div/>").addClass("buttons")
        .append( $("<button/>").attr("type", "button").addClass("btn btn-default")
          .text("Cancel")
          .click(function(e){
            EoR.logs.hide_post_interface();
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
    $("#observation_logs .bottom_buttons .load_more").show();
  }

  $("#observation_logs .loading").show();
  $("#observation_logs .btn").prop("disabled", true);

  var to_date = $("#observation_logs .fetch_interface .to_date").val(),
    from_date = $("#observation_logs .fetch_interface .from_date").val()
  $.ajax({
    url: "/api/observation_logs?tags="+EoR.logs.saved_tags_value+"&limit="+EoR.logs.LIMIT+"&offset="+EoR.logs.offset+
      "&from_date="+from_date + "&to_date="+to_date,
    type: "json",
    method: "GET",
    success: function(data){
      var tbody = $("#observation_logs .logs_table tbody");
      $.each(data.observation_logs, function(i,v){
        o_d = new Date(v.observed_date);
        tbody.append( EoR.logs.create_table_row(v));
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
      $("#observation_logs .btn").prop("disabled", false);
    }
  });
};

EoR.logs.create_table_row = function(v, post_button){

  var buttons = "";
  if(!EoR.current_user){
    // Not sure if we need to render anything. Probably not.
  }
  else if(post_button){
    buttons = $("<div>")
      // Delete button
      .append(  $("<button/>")
        .attr("type", "button")
        .addClass("btn btn-primary post")
        .text("Post New Log >>")
        .data("log_id", v.id)
      )
  } else if(v.author_user_id == EoR.current_user.id || (EoR.current_user.admin_level >= 1)){
    buttons = $("<div>")
      // Delete button
      .append(  $("<button/>")
        .attr("type", "button")
        .addClass("btn btn-danger delete")
        .text("Delete")
        .data("log_id", v.id)
      )
      // Edit button
      .append(  $("<button/>")
        .attr("type", "button")
        .addClass("btn btn-default edit")
        .text("Edit")
        .data("log", v)
      );
  }

  return $("<tr/>").attr("id", "log_tr_"+v.id)
    .append($("<td/>").addClass("date-cell").text(o_d.getUTCFullYear() + "-" + (o_d.getUTCMonth()+1) + "-" + o_d.getUTCDate()))
    .append($("<td/>").text(v.author_user_name))
    .append($("<td/>").text(v.note))
    .append($("<td/>").html(EoR.logs.get_tags_str_from_values(v.tags)))
    .append($("<td/>").append( buttons)
  );
}

EoR.logs.post_observation_log = function(){
  var observed_date = $("#observation_logs .post_interface .observed_date").val(),
    note =  $("#observation_logs .post_interface .note").val(),
    tags = EoR.logs.get_tags_value( $("#observation_logs .post_interface ul.obs_tags") );

  if(!/^\d{4}[\/\-](0?[1-9]|1[012])[\/\-](0?[1-9]|[12][0-9]|3[01])$/.test(observed_date)){
    alert("Please enter a valid date in yyyy-mm-dd format");
    return
  }

  if(!tags){
    alert("Your log entry must contain at least one tag (most likely either fine or bad)");
    return
  }

  var put_id = EoR.logs.log_being_edited;

  $("#observation_logs .loading").show();
  $("#observation_logs .btn").prop("disabled", true);
  $.ajax({
    url: "/api/observation_logs" + (put_id?("/"+put_id):"/new"),
    type: "json",
    method: put_id?"PUT":"POST",
    data: {observed_date: observed_date, note: note, tags: tags},
    success: function(data){
      if(put_id){
        $("#log_tr_"+put_id).replaceWith(EoR.logs.create_table_row(data));
      } else{
        EoR.logs.fetch_observation_logs(true);
      }

      EoR.logs.hide_post_interface();
    },
    error: function(xhr, status, err){
      alert("error posting a new log");
    },
    complete: function(){
      $("#observation_logs .loading").hide();
      $("#observation_logs .btn").prop("disabled", false);
    }
  })
};

EoR.logs.delete_observation_log = function(id, callback){
  $.ajax({
    url: "/api/observation_logs/"+id,
    method: "DELETE",
    type: "json",
    success:function(){
      callback();
    },
    error: function(){
      alert("An error has occurred");
    }
  });
};

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

EoR.logs.show_post_interface = function(){
  $("#observation_logs .tail_interface .bottom_buttons").hide();
  $("#observation_logs .fetch_interface").hide();
  $("#observation_logs .logs_table").hide();
  $("#observation_logs .tail_interface .post_interface").show();
}

EoR.logs.hide_post_interface = function(){
  $("#observation_logs .tail_interface .bottom_buttons").show();
  $("#observation_logs .fetch_interface").show();
  $("#observation_logs .logs_table").show();
  $("#observation_logs .tail_interface .post_interface").hide();
}

/***********************
********Latest Log******
*************************/

EoR.logs.fetch_latest_log = function(){

  $("#latest_observation_log .loading").show();

  $.ajax({
    url: "/api/observation_logs/latest",
    type: "json",
    method: "GET",
    success: function(data){
      var tbody = $("#latest_observation_log .logs_table tbody");
      tbody.empty();
      o_d = new Date(data.observed_date);
      tbody.append( EoR.logs.create_table_row(data,true));
    },
    error: function(xhr, status, err){
      alert("an error occurred during fetching the latest log data");
    },
    complete: function(){
      $("#latest_observation_log .loading").hide();
    }
  });
};

EoR.logs.init = function(){
  $("#observation_logs")
    .append(EoR.logs.create_fetch_interface())
    .append(EoR.logs.create_table())
    .append(EoR.create_loading().hide())
    .append(EoR.logs.create_post_interface());

  $("#latest_observation_log")
    .append('<h4 class="title-with-link">Latest Observation Log</h4>')
    .append( $("<span/>").addClass("link refresh")
      .text("refresh")
      .click(function(e){
        EoR.logs.fetch_latest_log(EoR.obs.fetch_future_observation_counts);
      })
    )
    .append(EoR.logs.create_table())
    .append(EoR.create_loading().hide());

  $("ul.obs_tags.fetch li input").each(function(i,el){
    $(el).prop("checked", true);
  });


};
