
function send_event(url,data,callback){

    xhr = new XMLHttpRequest();
    xhr.onload = callback;
    xhr.open("POST",url,true);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    data = JSON.stringify(data);
    xhr.send(data);
    
}