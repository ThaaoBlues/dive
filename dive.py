# to specify the intents to use
from discord import Intents
# to detect commands
from discord.ext import commands
# to update files each 10 seconds
from discord.ext.tasks import loop as d_task_loop
from discord import File as DiscordFile
from os import remove

import constants
from mongo_database import DataBase
from string import punctuation

intents = Intents.default()
intents.message_content = True
bot = commands.bot.Bot(command_prefix="!",intents=intents)

db = DataBase()


# command to get the drive's url
@bot.command(name="durl",help=constants.bot_help["durl"])
async def get_drive_url(ctx):
    
    # insert server into servers table if not already in it
    if not db.server_registered(ctx.guild.id):
        db.register_server(ctx.guild.id,ctx.guild.name)

    await ctx.channel.send(f"Your very own drive address : {constants.ovh['server_url']}/drive/{ctx.guild.id}")

# command to add content to the drive from url
@bot.command(name="dadd",help=constants.bot_help["dadd"])
async def get_drive_url(ctx,*args):
    file_url = ""
    file_name = ""


    if len(args) != 2:
        await ctx.channel.send(f"You didn't read how to use this command, did you ?\n here : {constants.ovh['server_url']}")
        return

    file_url = args[0]
    file_name = args[1]

    # insert server into servers table if not already in it
    if not db.server_registered(ctx.guild.id):
        db.register_server(ctx.guild.id,ctx.guild.name)

    # check url validity
    if (file_url == ""):
        await ctx.channel.send(f"You didn't read how to use this command, did you ?\n here : {constants.ovh['server_url']}")
        return
 
    # if not matched the ReGex, send the appropriate response
    for c in file_url:
        if c not in constants.url_whitelist:
        
            await ctx.channel.send("Invalid file url :/ You really think you're smarter than me ?")
            return

    # check file name validity

    if file_name == "":
        await ctx.channel.send("Invalid file name :/ You really think you're smarter than me ?")
        return

    file_name = file_name.replace(" ","_") # as some dumb ass users are using spaces in fucking file name
    for c in file_name:
        if c not in constants.chars_whitelist:
            await ctx.channel.send("Invalid file name :/ You really think you're smarter than me ?")
            return

    # add this media to the medias table
    db.add_media(ctx.guild.id,file_url,ctx.channel.name,file_name)

    await ctx.channel.send(f"Saving this media into Dive : {file_name}\n Dive URL : {constants.ovh['server_url']}/drive/{ctx.guild.id}")

@bot.command("dhelp",help=constants.bot_help["dhelp"])
async def help_cmd(ctx):
    await ctx.channel.send(constants.bot_help["bot_help_msg"])

@bot.command("dstat",help=constants.bot_help["dhelp"])
async def help_cmd(ctx):
    await ctx.channel.send(f"I'm currently active on {len(bot.guilds)} servers.")

@bot.event
async def on_message(msg):

    if msg.content:
        # check if the message is not a command
        if msg.content[0] in punctuation:
            # INCLUDES THE COMMANDS FOR THE BOT. WITHOUT THIS LINE, YOU CANNOT TRIGGER YOUR COMMANDS.
                
            if msg.content.split()[0] in constants.discord["bot_commands"]:
                await bot.process_commands(msg)
                
            return


    # detect if a cloud provider url is present in the message
    # to check this, we split the message by spaces
    # and compare each word with the urls
    for word in msg.content.split():

        for provider in constants.DRIVE_PROVIDERS.keys():

            for url in constants.DRIVE_PROVIDERS[provider]:
                # match ?
                if url in word:
                    db.add_media(msg.guild.id,word,msg.channel.name,f"shared_from_{provider}")
                    
                    await msg.channel.send(f"Saving this media into Dive : shared_from_{provider}\n Dive URL : {constants.ovh['server_url']}/drive/{msg.guild.id}")

    # detect if the message contains media
    if len(msg.attachments) > 0:

        for media in msg.attachments:
            
            # insert server into servers table if not already in it
            if not db.server_registered(msg.guild.id):
                db.register_server(msg.guild.id,msg.guild.name)

            # add this media to the medias table
            db.add_media(msg.guild.id,media.url,msg.channel.name,media.filename)

            await msg.channel.send(f"Saving this media into Dive : {media.filename}\n Dive URL : {constants.ovh['server_url']}/drive/{msg.guild.id}")

@bot.event
async def on_guild_join(guild):
    await guild.system_channel.send(constants.bot_help["welcome_msg"])

@bot.event
async def on_ready():
    check_update_queue.start()
    remove_old_data.start()

@d_task_loop(seconds=10.0)
async def check_update_queue():
    
    for file in db.check_update_queue():
        guild = bot.get_guild(file["server_id"])
        
        channel = None

        for chan in guild.channels:
            if chan.name == file["channel_name"]:
                channel = chan
            
        await channel.send(f"{file['file_name']} as been updated from Dive.")
        
        with open(f"{file['file_name']}","w") as f:

            f.write(file["new_content"])

        with open(f"{file['file_name']}","rb") as f:
            await channel.send(file = DiscordFile(f,file['file_name']))
        
        remove(f"{file['file_name']}")
    
    db.delete_update_queue()

@d_task_loop(hours=12.0)
async def remove_old_data():
    # removes all data that is more than 180 days old
    db.delete_after_180_days()


bot.run(constants.discord["bot_token"])