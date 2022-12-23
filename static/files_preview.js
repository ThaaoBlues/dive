function preview(media_src){



   // 1. Create a new XMLHttpRequest object
    let xhr = new XMLHttpRequest();

    xhr.open('GET', media_src);

    xhr.setRequestHeader("Access-Control-Allow-Origin", "*");
    xhr.setRequestHeader("Access-Control-Allow-Methods", "DELETE, POST, GET, OPTIONS");
    xhr.setRequestHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With");

    try {
        xhr.send();

    } catch (error) {
        // discord cdn cors error ...
        window.location.href = media_src;
    }


    xhr.onload = function() {
    if (xhr.status != 200) { 
        document.getElementById("iframe-preview").innerHTML = xhr.responseText;

    } else { // show the result
        document.getElementById("iframe-preview").innerHTML = "Im unable to preview this document, sorry :/";

    }
    };

}

