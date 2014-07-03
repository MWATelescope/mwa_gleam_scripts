EoR.clock = {};

//TODO: the clock settings may need to be returned from the server

EoR.clock.CLOCKS = [
  ["UTC", 0],
  ["Boston", -4],
  ["Pheonix", -7],
  ["Sydney", +10],
  ["Bangalore", +5.5],
  ["Seattle", -7],
  ["Perth", +8]
];

EoR.clock.LOCAL_SIZE = 80;
EoR.clock.SIZE = 60;

EoR.clock.create_div = function(name, tz, size, seconds){
  var no_seconds = seconds? "" : ":noSeconds",
    tz_string = tz !==null && (":"+tz) || "",
    option = "CoolClock:swissRail:"+size+no_seconds+tz_string;
  console.log(option);
  return $("<div/>")
    .addClass("clock_div")
    .append($("<canvas/>").attr("id", name).attr("class", option))
    .append($("<span/>").text(name));
};

EoR.clock.init = function(){
  $(".clocks.container").append(EoR.clock.create_div("Local", null, EoR.clock.LOCAL_SIZE, true));
  $.each(EoR.clock.CLOCKS, function(i,v){
    $(".clocks.container").append(EoR.clock.create_div(v[0], v[1], EoR.clock.SIZE, false));
  });
  CoolClock.findAndCreateClocks();
};
