EoR.graph = {};

EoR.chart1;
EoR.chartData1 = [];
EoR.chartCursor1;

EoR.chart2;
EoR.chartData2 = [];
EoR.chartCursor2;


EoR.graph.create_graph_container = function(){
  return $("<div/>")
    .addClass("container graph_container")
    .append("<h4>Hours observed/scheduled</h4>")
    .append( $("<div/>")
      .attr("id", "_graph_0")
    )
    .append("<h4>Data transfer rate (hours of data transfered per hour elapsed)</h4>")
    .append( $("<div/>")
      .attr("id", "_graph_1")
    )
};

EoR.graph.fetch_data = function(){
  $("#graphs .loading").show();
  $("#graphs .graph_container").hide();
  $.ajax({
    url: "/api/graph_data",
    type: "json",
    method: "GET",
    success: function(data){
      $("#graphs .graph_container").show();
      // Process Data
      $.each(data.graph_data, function(i,v){
        EoR.chartData1.push({
          date: new Date(v.created_date),
          hours_scheduled: v.hours_scheduled,
          hours_observed: v.hours_observed,
          hours_with_data: v.hours_with_data,
          hours_with_uvfits: v.hours_with_uvfits
        });
        EoR.chartData2.push({
          date: new Date(v.created_date),
          data_transfer_rate: v.data_transfer_rate
        });
      });
      EoR.graph.render();
    },
    error: function(xhr, status, err){
      $("#graphs .graph_container").append("<p>There had been an error fetching graph data...</p>");
    },
    complete: function(){
      $("#graphs .loading").hide();
    }
  })
};

EoR.graph.render = function(){
  // Hours Chart
  EoR.chart1.dataProvider = EoR.chartData1;
  EoR.chart1.categoryField = "date";
  EoR.chart1.balloon.bulletSize = 5;
  // Data transfer rate chart
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
    legend.showEntries = false;
    v.addLegend(legend);

    // Need something like below code if the data is really big - commented out for now
    // v.addListener("dataUpdated", function(){
    //   v.zoomToIndexes(EoR.chartData1.length - 40, EoR.chartData1.length - 1);
    // });
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
  EoR.chart1 = new AmCharts.AmSerialChart();
  EoR.chart2 = new AmCharts.AmSerialChart();
  EoR.chart1.pathToImages = STATIC_PATH+"/img/";
  EoR.chart2.pathToImages = STATIC_PATH+"/img/";
  $("#graphs").append(EoR.graph.create_graph_container().hide());
  $("#graphs").append(EoR.create_loading());
  //EoR.graph.fetch_data();
};
