EoR.graph = {};

EoR.chart1;
EoR.chartData1 = [];
EoR.chartCursor1;

EoR.chart2;
EoR.chartData2 = [];
EoR.chartCursor2;


EoR.graph.create_graph_container = function(){
  return $("<div/>")
    .addClass("graphs_container")
    .append( $('<form/>').addClass("form-inline graph_date_range_form")
      .append( $("<div/>")
        .addClass("form-group form-horizontal")
        .append('<label for="graph_date_range">Data Range:&nbsp;</label>')
        .append( $("<select>").addClass("form-control").attr("id","graph_date_range")
          .attr("name", "graph_date_range")
          .append("<option value=1>Last Month</option>")
          .append("<option value=3>Last 3 Months</option>")
          .append("<option value=6>Last 6 Months</option>")
          .append("<option value=12>Last Year</option>")
          .append("<option value=0>All Time</option>")
          .on('change', EoR.graph.fetch_data)
        )
      )
    )
    .append( $("<div/>")
      .addClass("graph_container col-md-6")
      .append("<h4>Hours observed/scheduled</h4>")
      .append( $("<div/>")
        .attr("id", "_graph_0")
      )
    )
    .append( $("<div/>")
      .addClass("graph_container col-md-6")
      .append("<h4>Data transfer rate (hours of data transfered per hour elapsed)</h4>")
      .append( $("<div/>")
        .attr("id", "_graph_1")
      )
    );
};

EoR.graph.fetch_data = function(){
  $("#graphs .loading").show();
  $("#graphs .graph_date_range_form").hide();
  var last_x_months = $("#graph_date_range").val();
  $.ajax({
    url: "/api/graph_data" + ((last_x_months>0)?("?last_x_months="+last_x_months):""),
    type: "json",
    method: "GET",
    success: function(data){
      $("#graphs .graph_date_range_form").show();
      // Process Data
      EoR.chartData1 = [];
      EoR.chartData2 = [];
      $.each(data.graph_data, function(i,v){
        EoR.chartData1.push({
          date: new Date(v.created_date),
          hours_scheduled: v.hours_scheduled,
          hours_observed: v.hours_observed,
          hours_with_data: v.hours_with_data,
          hours_with_uvfits: v.hours_with_uvfits
        });
        if(v.data_transfer_rate !== null){ // data_transfer_rate can be null sometimes. No need to push those. They don't mean 0.
          EoR.chartData2.push({
            date: new Date(v.created_date),
            data_transfer_rate: v.data_transfer_rate
          });
        }
      });
      EoR.graph.render();
    },
    error: function(xhr, status, err){
      $("#graphs .graphs_container").append("<p>There had been an error fetching graph data...</p>");
    },
    complete: function(){
      $("#graphs .loading").hide();
    }
  })
};

EoR.graph.render = function(){

  // Hours Chart
  $("#_graph_0").empty();
  EoR.chart1 = new AmCharts.AmSerialChart();
  EoR.chart1.pathToImages = STATIC_PATH+"/img/";
  EoR.chart1.dataProvider = EoR.chartData1;
  EoR.chart1.categoryField = "date";
  EoR.chart1.balloon.bulletSize = 5;
  // Data transfer rate chart
  $("#_graph_1").empty();
  EoR.chart2 = new AmCharts.AmSerialChart();
  EoR.chart2.pathToImages = STATIC_PATH+"/img/";
  EoR.chart2.dataProvider = EoR.chartData2;
  EoR.chart2.categoryField = "date";
  EoR.chart2.balloon.bulletSize = 5;

  // AXES
  $.each([EoR.chart1, EoR.chart2], function(i,v){
    var categoryAxis = v.categoryAxis;
    categoryAxis.parseDates = true; // as our data is date-based, we set parseDates to true
    categoryAxis.minPeriod = "hh";
    categoryAxis.dashLength = 1;
    categoryAxis.minorGridEnabled = true;
    categoryAxis.dateFormats = [{
        period: 'fff',
        format: 'JJ:NN:SS'
    }, {
        period: 'ss',
        format: 'JJ:NN:SS'
    }, {
        period: 'mm',
        format: 'JJ:NN'
    }, {
        period: 'hh',
        format: 'JJ:NN'
    }, {
        period: 'DD',
        format: 'DD'
    }, {
        period: 'WW',
        format: 'DD'
    }, {
        period: 'MM',
        format: 'MMM'
    }, {
        period: 'YYYY',
        format: 'YYYY'
    }];

    categoryAxis.axisColor = "#DADADA";

    var valueAxis = new AmCharts.ValueAxis();
    valueAxis.axisAlpha = 1;
    valueAxis.dashLength = 1;
    v.addValueAxis(valueAxis);

    // CURSOR
    chartCursor = new AmCharts.ChartCursor();
    chartCursor.cursorPosition = "mouse";
    chartCursor.pan = true; // set it to fals if you want the cursor to work in "select" mode
    v.addChartCursor(chartCursor);

    // SCROLLBAR
    var chartScrollbar = new AmCharts.ChartScrollbar();
    v.addChartScrollbar(chartScrollbar);
    v.creditsPosition = "bottom-right";

    // LEGEND
    var legend = new AmCharts.AmLegend();
    legend.marginLeft = 100;
    legend.spacing = 30;
    legend.useGraphSettings = true;
    legend.valueAlign = "left";
    v.addLegend(legend);

    // Need something like below code if the data is really big - commented out for now
    var d_length = EoR["chartData"+(i+1)].length;
    if(d_length > 100){
      v.addListener("dataUpdated", function(){
        v.zoomToIndexes(d_length - 80, d_length- 1);
      });
    }
  });

  // GRAPHS - do this individually per graph
  // Hours
  var colors = ["#5fb503", "#8b5d62", "#c9bd5a", "#271c85"];
  $.each(["hours_scheduled", "hours_observed", "hours_with_data", "hours_with_uvfits"], function(i,v){
    var graph = new AmCharts.AmGraph();
    graph.title = v.replace(/_/g, " ");
    graph.valueField = v;
    graph.bullet = "round";
    graph.bulletBorderColor = "#FFFFFF";
    graph.bulletBorderThickness = 2;
    graph.bulletBorderAlpha = 1;
    graph.lineThickness = 2;
    graph.lineColor = colors[i];
    graph.hideBulletsCount = 50; // this makes the chart to hide bullets when there are more than 50 series in selection
    EoR.chart1.addGraph(graph);
  });

  // Data transfer rate
  var dtr_graph = new AmCharts.AmGraph();
  dtr_graph.title = "data transfer rate";
  dtr_graph.valueField = "data_transfer_rate";
  dtr_graph.bullet = "round";
  dtr_graph.bulletBorderColor = "#FFFFFF";
  dtr_graph.bulletBorderThickness = 2;
  dtr_graph.bulletBorderAlpha = 1;
  dtr_graph.lineThickness = 2;
  dtr_graph.lineColor = "#b7303c";
  dtr_graph.hideBulletsCount = 50; // this makes the chart to hide bullets when there are more than 50 series in selection
  EoR.chart2.addGraph(dtr_graph);

  // WRITE
  EoR.chart1.write("_graph_0");
  EoR.chart2.write("_graph_1");

};

EoR.graph.init = function(){
  $("#graphs")
    .append("<h4>Graphs</h4>")
    .append(EoR.create_loading())
    .append(EoR.graph.create_graph_container());
  //EoR.graph.fetch_data();
};
