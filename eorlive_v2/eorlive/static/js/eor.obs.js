EoR.obs = {};

EoR.obs.create_mit_observations = function(){
  return $("<div/>")
    .attr("id", "mit_observations_container")
    .append("<h3>Observation Table</h3>")
    .append( $("<table/>")
      .addClass("gs_table table table-striped")
      .append("<thead><tr><th>Obs. Number</th><th>Obs. Name</th><th>Project ID</th><th>Start Time</th><th>Stop Time</th><th>Files</th></tr></thead>")
      .append("<tbody></tbody>")
      .hide()
    )
    .append(EoR.create_loading());
};

EoR.obs.fetch_observations = function(){

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
          .append("<td>"+v["start_time"]+"</td>")
          .append("<td>"+v["stop_time"]+"</td>")
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
    }
  });
};

EoR.obs.init = function(){
  $("#mit_observations").append(EoR.obs.create_mit_observations());
  EoR.obs.fetch_observations();
};
