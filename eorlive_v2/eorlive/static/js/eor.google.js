EoR.google = {};

EoR.google.SPREADSHEET = "https://docs.google.com/a/mindbloom.com/spreadsheet/ccc?key=0Ate0sqkDCwhydEpHMnlHckFSRjRhaE5IdHFUcDd2enc#gid=0";

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
};
