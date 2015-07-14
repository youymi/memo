$(document).on("click",".j-reg",function(){
    $.ajax({
        url:"/user/create",
        type: "POST",
        dataType: "json",
        data: $("#regform").serialize()
    }).done(function(res){
        if(res && res.code == 200) {
            alert("Regiser Success !");
        }
        console.log(res);
    }).fail(function(){
        alert("Regiser Failed ! Tay another eamil.");
        console.log("fail .. .")
    });
})
