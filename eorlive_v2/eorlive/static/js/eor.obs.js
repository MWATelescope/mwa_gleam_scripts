EoR.obs = {};

EoR.obs.create_mit_observations = function(){
  return $("<div/>")
    .attr("id", "mit_observations_container")
    .append("<h5>Current And Past observations</h5>")
    .append( $("<table/>")
      .addClass("gs_table table table-striped")
      .append("<thead><tr><th>Obs. Number</th><th>Obs. Name</th><th>Project ID</th><th>Start Time</th><th>Stop Time</th><th>Files</th></tr></thead>")
      .append("<tbody></tbody>")
      .hide()
    )
    .append(EoR.create_loading());
};

EoR.obs.create_mit_future_observation_counts = function(){
  return $("<div/>")
    .attr("id", "mit_future_obs_div")
    .append("<h5>Scheduled Observation Counts</h5>")
    .append( $("<table/>")
      .addClass("gs_table table table-striped")
      .append("<thead><tr><th>Total Scheduled</th><th>Next 24 Hours</th></tr></thead>")
      .append("<tbody></tbody>")
      .hide()
    )
    .append(EoR.create_loading());
};

EoR.obs.fetch_observations = function(callback){

  var tb = $("#mit_observations_container table"),
    tbody = tb.find("tbody").empty(),
    loading = $("#mit_observations_container .loading");

  tb.hide();
  loading.show();

  $.ajax({
    url: "/api/mit_data/observations",
    type: "json",
    method: "GET",
    success: function(data){
      $.each(data.observations, function(i,v){
        tbody.append( $("<tr/>")
          .append("<td>"+v["observation_number"]+"</td>")
          .append("<td>"+v["obsname"]+"</td>")
          .append("<td>"+v["projectid"]+"</td>")
          .append("<td>"+(new Date(v["start_time"])).toISOString()+"</td>")
          .append("<td>"+(new Date(v["stop_time"])).toISOString()+"</td>")
          .append("<td>"+v["files"]+"</td>")
        )
      });
    },
    error: function(xhr, status, err){
      tbody.append("<tr><td colspan=\"6\">Failed to get data...</td></tr>")
    },
    complete: function(){
      tb.show();
      loading.hide();
      if(callback) callback();
    }
  });
};

EoR.obs.fetch_future_observation_counts = function(callback){
  var tb = $("#mit_future_obs_div table"),
    tbody = tb.find("tbody").empty(),
    loading = $("#mit_future_obs_div .loading");

  tb.hide();
  loading.show();

  $.ajax({
    url: "/api/mit_data/future_observation_counts",
    type: "json",
    method: "GET",
    success: function(data){
      tbody.append( $("<tr/>")
        .append("<td>"+data.total+"</td>")
        .append("<td>"+data.next_24+"</td>")
      );
    },
    error: function(xhr, status, err){
      tbody.append("<tr><td colspan=\"2\">Failed to get data...</td></tr>")
    },
    complete: function(){
      tb.show();
      loading.hide();
      if(callback) callback();
    }
  });

};

EoR.obs.init = function(){
  $("#mit_observations")
    .append('<h4 class="title-with-link">Observations</h4>')
    .append( $("<span/>").addClass("link refresh")
      .text("refresh")
      .click(function(e){
        EoR.obs.fetch_observations(EoR.obs.fetch_future_observation_counts);
      })
    )
    .append(EoR.obs.create_mit_observations())
    .append(EoR.obs.create_mit_future_observation_counts());
  //EoR.obs.fetch_observations(EoR.obs.fetch_future_observation_counts);
};
