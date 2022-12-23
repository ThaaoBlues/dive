document.getElementById("search_form").onsubmit = function (ev){
    window.open("/drive/"+ document.getElementsByClassName("search-input")[0].value,'_blank');
}