EoR.img = {};
EoR.img.IMAGE_MAX = 10;

EoR.img.fetch_images = function(callback){
  var div = $("#beam_image_container"), ol = div.find("ol"),
    div_outer = div.find(".outer")
    div_inner = div.find(".carousel-inner"),
    loading = div.find(".loading");

  div_outer.css('visibility', 'hidden');
  loading.show();

  ol.empty();
  div_inner.empty();

  $.ajax({
    url: "/api/beam_images?limit="+EoR.img.IMAGE_MAX,
    type: "json",
    method: "GET",
    success: function(data){
      $.each(data.images, function(i,v){
        ol.append(
          $("<li>")
            .attr("data-target","#beam_image")
            .attr("data-slide-to", ""+i)
            .addClass(i===0?"active":"")
        );
        div_inner.append(
          $("<div>")
            .addClass(i===0?"item active":"item")
            .append( $("<img/>").attr("src", "/beam_images/"+v) )
            .append('<div class="carousel-caption"></div>')
        )
      });
    },
    error: function(xhr, status, err){
      div_outer.append("<p>Something went wrong. Could not load images.</p>");
    },
    complete: function(){
      loading.hide();
      div_outer.css('visibility', 'visible');
      if(callback){callback();}
    }
  });
};

EoR.img.create_img_slider = function(){
  return $("<div>").addClass("carousel slide outer").attr("data-ride", "carousel").attr("id", "beam_image").attr("data-interval", false)
    .append('<ol class="carousel-indicators">')
    .append('<div class="carousel-inner">')
    .append('<a class="left carousel-control" href="#beam_image" role="button" data-slide="prev">' +
      '<span class="glyphicon glyphicon-chevron-left"></span>' +
      '</a>' +
      '<a class="right carousel-control" href="#beam_image" role="button" data-slide="next">' +
      '<span class="glyphicon glyphicon-chevron-right"></span>' +
      '</a>').css("visibility","hidden");
};

EoR.img.init = function(){
  var div = $("#beam_image_container");
  div
    .append('<h4 class="title-with-link">Beam Images</h4>')
    .append( $("<span/>").addClass("link refresh")
      .text("refresh")
      .click(function(e){
        EoR.img.fetch_images();
      })
    )
    .append(EoR.img.create_img_slider())
    .append(EoR.create_loading());
  EoR.img.fetch_images();
};
