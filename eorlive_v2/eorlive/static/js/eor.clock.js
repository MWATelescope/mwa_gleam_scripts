EoR.clock = {};

EoR.clock.CLOCKS = [
  ["UTC", 0],
  ["Perth (MWA)", +8]
];

EoR.clock.LOCAL_SIZE = 80;
EoR.clock.SIZE = 80;

EoR.clock.create_div = function(name, tz, size, seconds){
  var no_seconds = seconds? ":" : ":noSeconds",
    tz_string = tz !==null && (":"+tz) || "",
    option = "CoolClock:eor:"+size+no_seconds+tz_string;
  return $("<div/>")
    .addClass("clock_div")
    .append($("<canvas/>").attr("id", name).attr("class", option))
    .append($("<span/>").text(name));
};

EoR.clock.init = function(){
  $(".clocks.container").append(EoR.clock.create_div("Local", null, EoR.clock.LOCAL_SIZE, false));
  $.each(EoR.clock.CLOCKS, function(i,v){
    $(".clocks.container").append(EoR.clock.create_div(v[0], v[1], EoR.clock.SIZE, false));
  });
  CoolClock.findAndCreateClocks();
};
