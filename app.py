this_file = "venv/bin/activate_this.py"
exec(open(this_file).read(), {'__file__': this_file})

from flask import Flask, render_template, jsonify, request,redirect, url_for
from mongo_database import DataBase

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

blueprint = make_discord_blueprint(
    client_id=constants.discord["client_id"],
    client_secret=constants.discord["client_secret"],
    scope=["identify","guilds"],
    redirect_url="/login"

)

application.register_blueprint(blueprint, url_prefix="/login")

# init database handler
db = DataBase()


# redirect all http requests to https
@application.before_request
def before_request():
    if not request.is_secure:
        url = request.url.replace('http://', 'https://', 1)
        code = 301
        return redirect(url, code=code)




#home
@application.route("/")
def home():
    return render_template("index.html")


@application.route("/login")
def login():


    if not discord.authorized:
        return redirect(url_for("discord.login"))
    
    resp = discord.get("/api/users/@me")

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
    for s in resp:
        if db.server_registered(s["id"]):
            user_servers.append(
                {
                    "icon_url":"https://cdn.discordapp.com/icons/"+str(s['id'])+"/"+str(s["icon"])+".webp" if s["icon"] != None else "https://cdn4.iconfinder.com/data/icons/basic-user-interface-elements/700/cloud-storage-data-weather-512.png",
                    "name":s["name"],
                    "id":s["id"]
                }
            )

    return render_template("user_dashboard.html",user = user,user_servers = user_servers)


@application.route("/revoke")
def revoke():

    if not discord.authorized:
        return redirect("/")
    
    token = blueprint.token["access_token"]
    resp = discord.post(
        "https://discord.com/api/oauth2/token/revoke",
        params={
            "client_id":constants.discord["client_id"],
            "client_secret":constants.discord["client_secret"],
            "token": token},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    assert resp.ok, resp.text

    del blueprint.token  # Delete OAuth token from storage

    return redirect("/")


#direct url to server's drive
@application.route("/drive/<server_id>",defaults={"channel_name":None})
@application.route("/drive/<server_id>/<channel_name>")
def drive(server_id:str,channel_name:str):

    # check server_id composition
    try:
        int(server_id)
    except ValueError:
        return render_template("error.html",error_msg="This server is not in our database, Please make sure that you interacted with Dive in the server.")


    # check if a user is logged in
    if not discord.authorized:
        return redirect("/login")


    # if a user is logged in, check that he's in the server
    if not server_id in str(discord.get("/api/users/@me/guilds").json()):
        return render_template("error.html",error_msg="Sorry, w've searched everywhere but you are not in this server !")

    # check server id presence
    if not db.server_registered(server_id):
        return render_template("error.html",error_msg="This server is not in our database, Please make sure that you interacted with Dive in the server.")


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
        print(start)

        return render_template("drive_channel.html",medias=db.get_channel_medias(server_id,channel_name,limit=limit,skip=start),c_chunk=c_chunk)
    
    # default drive page
    else:
        return render_template("drive_default.html",channels=db.get_server_channels(server_id))


@application.errorhandler(404)
def not_found(err):
    return render_template("error.html",error_msg=f"Sorry, {request.base_url} is not on our website. But you can still go back and find what you've been searching for :D")


if __name__ == "__main__":
    application.run()