EoR.google = {};

EoR.google.SPREADSHEET = "https://docs.google.com/a/mindbloom.com/spreadsheet/ccc?key=0Ate0sqkDCwhydEpHMnlHckFSRjRhaE5IdHFUcDd2enc#gid=0";

// What to render for the google fusion table iframes.
// array of [source, title, width, height]
EoR.google.FT_SOURCES = [
  [
    "https://www.google.com/fusiontables/embedviz?containerId=googft-gviz-canvas&viz=GVIZ&t=LINE_AGGREGATE&isXyPlot=true&bsize=0&q=select+col0%2C+col1%2C+col5%2C+col4%2C+col25+from+1UspWE7G7ccKncYTUbEkpSaSitomsN-7vLkNdx-I&qrs=+where+col0+%3E%3D+&qre=+and+col0+%3C%3D+&qe=+order+by+col0+asc&uiversion=2&gco_hasLabelsColumn=true&width=<width>&height=<height>",
    "Hours of Observing",
    1000, 600
  ],
  [
    "https://www.google.com/fusiontables/embedviz?containerId=gviz_canvas&viz=GVIZ&t=LINE_AGGREGATE&isXyPlot=true&bsize=0&q=select+col0%2C+col24+from+1UspWE7G7ccKncYTUbEkpSaSitomsN-7vLkNdx-I&qrs=+where+col0+%3E%3D+&qre=+and+col0+%3C%3D+&qe=+order+by+col0+asc&uiversion=2&gco_hasLabelsColumn=true&width=<width>&height=<height>",
    "", 1000, 600
  ]
  /*
  [
    "https://www.google.com/fusiontables/embedviz?containerId=gviz_canvas&viz=GVIZ&t=LINE_AGGREGATE&isXyPlot=true&bsize=0&q=select+col0%2C+col7%2C+col6%2C+col8%2C+col9%2C+col10%2C+col11%2C+col12%2C+col13%2C+col14%2C+col15%2C+col16%2C+col18%2C+col19%2C+col20%2C+col21+from+1UspWE7G7ccKncYTUbEkpSaSitomsN-7vLkNdx-I&qrs=+where+col0+%3E%3D+&qre=+and+col0+%3C%3D+&qe=+order+by+col0+asc&uiversion=2&gco_hasLabelsColumn=true&width=<width>&height=<height>",
    "Failure Rate", 1000, 600
  ]
  */
];

function prepend_zero(d){
  if (d<10) return "0"+d;
  return d;
}

EoR.google.create_sheetrock_options = function(loading_indicator){
  return {
    url: EoR.google.SPREADSHEET,
    sql: "select A,B,C,D,E order by A desc",
    chunkSize: 15,
    loading: loading_indicator,
    cellHandler: function(cell){
      if(cell instanceof Date)
        return cell.getUTCFullYear() + "/" + (cell.getUTCMonth()+1) + "/" + cell.getUTCDate() +
          " " + prepend_zero(cell.getUTCHours()) + ":" + prepend_zero(cell.getUTCMinutes()) +
          ":" + prepend_zero(cell.getUTCSeconds());
      return cell;
    },
    userCallback: function(){
      $("#logs .button_container button.load_more").prop("disabled", false);
    }
  };
};

EoR.google.create_log_spreadsheet = function(opt){
  return table = $("<table/>").addClass("gs_table table table-striped")
    .sheetrock(opt);
};

EoR.google.create_fb_iframe = function(src, title, width, height){
  src = src.replace("<width>", width).replace("<height>", height);

  var iframe = $("<iframe/>")
    .attr("src", src)
    .attr("width", width)
    .attr("height", height)
    .attr("scrolling", "no")
    .attr("frameborder", "no");

  return $("<div/>")
    .addClass("iframe_container")
    .append("<h3>"+title+"</h3>")
    .append(iframe);
};

EoR.google.init = function(){
  // Logs Spreadsheet from Google
  var loading_indicator = EoR.create_loading();
  $("#logs")
    .append( $("<div>").addClass("table_container") )
    .append(loading_indicator)
    .append( $("<div>").addClass("container button_container")
      .append( $("<button/>").attr("type", "button").addClass("btn btn-default")
        .text("Open Full Page")
        .click(function(e){
          window.open("https://docs.google.com/spreadsheet/ccc?key=0Ate0sqkDCwhydEpHMnlHckFSRjRhaE5IdHFUcDd2enc#gid=0", "_blank");
        }).hide()
      )
      .append( $("<button/>").attr("type", "button").addClass("btn btn-default")
        .text("Post Log")
        .click(function(e){
          window.open("https://docs.google.com/forms/d/1TbSXkRDUajoVls3tg6df9ZoJsnCf0Eu5LD2juNPEn0M/viewform", "_blank");
        })
      )
      .append( $("<button/>").attr("type", "button").addClass("btn btn-primary load_more")
        .text("Load More")
        .click(function(e){
          // TODO request more
          $("#logs .table_container .gs_table").sheetrock(EoR.google.create_sheetrock_options(loading_indicator));
        })
        .prop("disabled", true)
      )
    );

  $("#logs .table_container")
    .append(EoR.google.create_log_spreadsheet(EoR.google.create_sheetrock_options(loading_indicator)));

  // Fusion Tables
  // Render them in overview for now
  $.each(EoR.google.FT_SOURCES, function(i,v){
    $("#fb_graphs_container")
      .append(EoR.google.create_fb_iframe(v[0], v[1], v[2], v[3]));
  });

};
