this_file = "venv/bin/activate_this.py"
exec(open(this_file).read(), {'__file__': this_file})

from flask import Flask, render_template, jsonify, request,redirect, url_for,make_response
from mongo_database import DataBase
from requests import get
from oauthlib.oauth2.rfc6749.errors import TokenExpiredError

from flask_dance.contrib.discord import discord, make_discord_blueprint
import constants

# for secret key
from random import choices
from string import printable


#init flask app
application = Flask(__name__)
application.secret_key = choices(printable,k=256)

# to tell i'm using https but flask is behind the proxy
from werkzeug.middleware.proxy_fix import ProxyFix

application.wsgi_app = ProxyFix(
    application.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)


# discord oauth blueprint
discord_blueprint = make_discord_blueprint(
    client_id=constants.discord["client_id"],
    client_secret=constants.discord["client_secret"],
    scope=["identify","guilds"],
    redirect_url="/login"

)

application.register_blueprint(discord_blueprint, url_prefix="/login")


db = DataBase()


# redirect all http requests to https
@application.before_request
def before_request():
    if not request.is_secure:
        url = request.url.replace('http://', 'https://', 1)
        code = 301
        return redirect(url, code=code)



# a function that makes all login and server-registration verifications
def login_check(server_id):

    # check server_id composition
    try:
        int(server_id)
    except ValueError:
        return render_template("error.html",error_msg=constants.API_MSG["error"]["server_not_registered"])


    # check if a user is logged in
    if not discord.authorized:
        return redirect("/login")

    # if a user is logged in, check that he's in the server
    if not server_id in request.cookies["user_servers"]:
        return render_template("error.html",error_msg=constants.API_MSG["error"]["not_in_server"])

    # check server id presence
    if not db.server_registered(server_id):
        return render_template("error.html",error_msg=constants.API_MSG["error"]["server_not_registered"])

    return None


def api_login_check(server_id:int):
    # check if a user is logged in
    if not discord.authorized:
        return redirect("/login")

    # if a user is logged in, check that he's in the server
    if not server_id in request.cookies["user_servers"]:
        return jsonify({"error":constants.API_MSG["error"]["not_in_server"]})

    # check server id presence
    if not db.server_registered(server_id):
        return jsonify({"error":constants.API_MSG["error"]["server_not_registered"]})

    return None








#home
@application.route("/")
def home():
    return render_template("index.html")


@application.route("/login")
def login():


    if not discord.authorized:
        return redirect(url_for("discord.login"))
    
    # for some reasons, sometimes a TokenExpiredError is thrown
    try:
        resp = discord.get("/api/users/@me")
    except TokenExpiredError:
        return redirect(url_for("discord.login"))


    if not resp.ok:
        return redirect(url_for("discord.login"))

    resp = resp.json()
    
    user = {
        "username" : resp["username"],
        "avatar" : resp["avatar"],
        "discriminator" : resp["discriminator"],
        "banner_color" : resp["banner_color"]
    }

    resp = discord.get("/api/users/@me/guilds").json()
    user_servers = []
    cookie_user_servers = set()
    for s in resp:
        if db.server_registered(s["id"]):
            user_servers.append(
                {
                    "icon_url":"https://cdn.discordapp.com/icons/"+str(s['id'])+"/"+str(s["icon"])+".webp" if s["icon"] != None else "https://cdn4.iconfinder.com/data/icons/basic-user-interface-elements/700/cloud-storage-data-weather-512.png",
                    "name":s["name"],
                    "id":s["id"]
                }
            )

            cookie_user_servers.add(s["id"])

    # store user servers in cookies to make far less discord api requests
    response = make_response(render_template("user_dashboard.html",user = user,user_servers = user_servers))
    response.set_cookie("user_servers",str(cookie_user_servers))
    return response


@application.route("/revoke")
def revoke():

    if not discord.authorized:
        return redirect("/")
    
    token = discord_blueprint.token["access_token"]
    resp = discord.post(
        "https://discord.com/api/oauth2/token/revoke",
        data={
            "client_id":constants.discord["client_id"],
            "client_secret":constants.discord["client_secret"],
            "token": token},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    if not resp.ok or not resp.text:
        return render_template("error.html",error_msg="Auto logout is not yet finished, you can still revoke access from your discord app !")

    del discord_blueprint.token  # Delete OAuth token from storage
    
    return redirect("/")



#direct url to server's drive
@application.route("/drive/<server_id>",defaults={"channel_name":None})
@application.route("/drive/<server_id>/<channel_name>")
def drive(server_id:str,channel_name:str):

    login_error = login_check(server_id)
    if login_error:
        return login_error

    if channel_name:
        # set a limit of files rendered to limit bandwith usage
        # chunk of  10 files are displayed
        # we can switch to next chunck on the table in the web page
        
        c_chunk=request.args.get('page',default=1,type=int)

        # check if a cringe m@st3r h@x0r is not trying to put a negative number
        c_chunk = 1 if c_chunk < 1 else c_chunk

        limit = 10
        
        # define a starting point to skip the n precedent chunks
        start = (c_chunk-1)*10

        return render_template("drive_channel.html",medias=db.get_channel_medias(server_id,channel_name,limit=limit,skip=start),c_chunk=c_chunk)
    
    # default drive page
    else:
        return render_template("drive_default.html",channels=db.get_server_channels(server_id))



@application.route("/edit/<server_id>/<channel_name>")
def edit_file(server_id,channel_name):
    
    login_error = login_check(server_id)
    if login_error:
        return login_error

    file = {
        "file_name" : request.args.get("file_name"),
        "file_url" : request.args.get("file_url"),
        "server_id" : server_id,
        "channel_name" : channel_name
    }

    return render_template("edit.html",file=file)



    
@application.route("/informations")
def info():
    return render_template("informations.html")


@application.route("/server_settings/<server_id>")
def server_settings(server_id):

    login_error = login_check(server_id)
    if login_error:
        return login_error

    server={"server_id":server_id}
    
    return render_template("server_settings.html",server=server)




@application.errorhandler(404)
def not_found(err):
    return render_template("error.html",error_msg=constants.API_MSG["error"]["404"].format(request.base_url))






# api endpoints

@application.route("/api/request_file_content",methods=["POST"])
def request_file_content():

    file = request.json

    login_error = api_login_check(str(file["server_id"]))
    if login_error:
        return login_error

    return jsonify(
        {
            "file_content":get(file["file_url"],allow_redirects=True).text
        }
    )



@application.route("/api/update_file_content",methods=["POST"])
def uppdate_file_content():

    file = request.json

    
    login_error = api_login_check(file["server_id"])
    if login_error:
        return login_error


    file["server_id"] = int(file["server_id"])

    # add username to file modification so the bot can say who has done it
    # into the channel
        # for some reasons, sometimes a TokenExpiredError is thrown
    try:
        resp = discord.get("/api/users/@me").json()
    except TokenExpiredError:
        return redirect(url_for("discord.login"))

    file["user_id"] = resp["id"]

    db.enqueue_file_update(file)
    return jsonify({"msg":constants.API_MSG["success"]["file_update"]})


@application.route("/api/delete_media",methods=["POST"])
def delete_media():

    media = request.json

    login_error = api_login_check(media["server_id"])
    if login_error:
        return login_error

  
    db.delete_media(media["media_url"],media["version"])

    return jsonify({"msg":constants.API_MSG["success"]["file_delete"]})


@application.route("/api/get_server_infos",methods=["POST"])

def get_server_infos():

    server = request.json

    login_error = api_login_check(server["server_id"])
    if login_error:
        return login_error

    return jsonify(db.get_server_infos(server["server_id"]))



@application.route("/api/set_server_infos",methods=["POST"])

def set_server_infos():

    server = request.json

    login_error = api_login_check(str(server["server_id"]))
    if login_error:
        return login_error
    
    db.set_server_info(
        server["server_id"],
        "img_auto_save",
        server["img_auto_save"]
    )

    return jsonify({"msg":constants.API_MSG["success"]["server_info_update"]})


if __name__ == "__main__":
    application.run(debug=True)