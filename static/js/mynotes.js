$(document).on("click",".j-lista",function(){
    $(this).parent().find(".list-group-item").removeClass("active");
    $(this).addClass("active");
    $that = $(this);
    $.ajax({
        url: $that.data("url"),
        type: "get",
        dataType: "html",
        data: $("#regform").serialize()
    }).done(function(html){
       $("#" + $that.parent().data("contentid")).html(html);

    }).fail(function(){
        alert(" Failed ! Try another time.");
       // console.log("fail .. .")
    });
});

var activeid = $(".list-group").data("activeid");
if (activeid) {
     $(".list-group").find(".list-group-item").removeClass("active");
     $(".list-group").find("#" + activeid).addClass("active");

}