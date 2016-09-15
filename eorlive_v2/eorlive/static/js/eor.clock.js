EoR.clock = {};
EoR.clock.update_thread = null;

EoR.clock.init = function(){
  EoR.clock.update_thread = setTimeout(EoR.clock.update, 1000);
};

EoR.clock.update = function(){
  var now = new Date();
  $("#utc_time").text("UTC Time: " + now.getUTCFullYear() + "-" + (now.getUTCMonth()+1) + "-" + now.getUTCDate() + " " + now.getUTCHours() + ":" + now.getUTCMinutes());
};
