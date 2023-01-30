from json import dumps, loads
from pymongo import MongoClient
import constants
from datetime import datetime
from dateutil.relativedelta import relativedelta

class DataBase():

    def __init__(self) -> None:
        
        client = MongoClient(f"mongodb+srv://dive:{constants.mongodb['password']}@dive.eg7imsn.mongodb.net/?retryWrites=true&w=majority")
        self.db = client["dive"]



    def register_server(self,server_id:str,server_name:str):

        # no need to keep time as we want to use it to compare days
        date = datetime.today().replace(hour=0,minute=0,second=0,microsecond=0)


        self.db["servers"].insert_one({
            "server_id":server_id,
            "server_name":server_name,
            "date": date,
            "img_auto_save":True
        })


    def server_registered(self,server_id:str) -> bool:
        """
        checks if a specific server is already in the database
        """
        return self.db["servers"].find_one({"server_id":int(server_id)}) != None


    def add_media(self,server_id:str,media_url:str,channel_name:str,file_name:str,proxy_url=None,content_type=None,version_limit=30):
        


        # no need to keep time as we want to use it to compare days
        date = datetime.today().replace(hour=0,minute=0,second=0,microsecond=0)
        
        # get the number of files with the same name already sent
        # to make versionning
        count = self.db["medias"].find({
            "server_id":int(server_id),
            "channel_name":channel_name,
            "file_name":file_name
            },projection={'_id':True})

        count = len(list(count))

        # check if we don't overpass version limit (30 copies by default)
        if count > version_limit:
            return


        self.db["medias"].insert_one({
            "server_id":server_id,
            "media_url":media_url,
            "proxy_url": proxy_url,
            "content_type": content_type,
            "channel_name":channel_name,
            "file_name":file_name,
            "date": date,
            "version": count + 1
            })


    def get_server_medias(self,server_id:str)->dict:
        """
        returns a json dict containing medias classified by channels

        {

            "channel1"{
                [
                    {
                        "file_name":"baguette.txt",
                        "media_url":"https://..."
                    }
                ]
            }
        }

        """

        ret = self.db["medias"].find({"server_id":int(server_id)},projection={'_id':False})
        ret = list(ret)
        ret = loads(dumps(ret,default=str))

        json_data = {}

        # build useful json data
        for media in ret:

            # if the channel already has data in json dict
            # append the new media description to the list
            if media["channel_name"] in json_data.keys():
                json_data[media["channel_name"]].append({
                        "file_name":media["file_name"],
                        "media_url":media["media_url"]
                    })

            # else, create the json list associated with the channel
            else:

                json_data[media["channel_name"]] = [{
                    "file_name":media["file_name"],
                    "media_url":media["media_url"]
                }]

        return json_data





    def get_server_channels(self,server_id:str) -> set:
        """
        get only the channels on a server to load the first
        page of the drive
        
        """

        ret = self.db["medias"].find({"server_id":int(server_id)},projection={'_id':False,"channel_name":True})
        ret = list(ret)
        ret = loads(dumps(ret,default=str))

        json_data = set([media["channel_name"] for media in ret])

        return json_data


    def get_channel_medias(self,server_id:str,channel_name:str,limit=0,skip=0)->list:
        
        # sorting by decrementing id to we have the lastest objects first
        sorting_order = [('_id',-1)]

        ret = self.db["medias"].find({"server_id":int(server_id),"channel_name":channel_name},projection={'_id':False},limit=limit,skip=skip,sort=sorting_order)
        ret = list(ret)
        json_data = loads(dumps(ret,default=str))

        return json_data
    

    def delete_after_180_days(self):
        """
        this method will delete all entries that have more than 180 days old
        """

        date = datetime.today().replace(hour=0,minute=0,second=0,microsecond=0)


        # 180 days lifespan of discord's cdn files is an average of 6 months
        self.db["medias"].delete_many({"date":date - relativedelta(months=6)})


    def enqueue_file_update(self,file:dict):

        """
        this method will enqueue a file updated from Dive edit page
        """

        self.db["update_queue"].insert_one(file)

    def check_update_queue(self)->list:
        """
        retrieve all update queue and delete its content right after
        """
        queue = self.db["update_queue"].find({})

        queue = list(queue)
        queue = loads(dumps(queue,default=str))

        return queue

    def delete_update_queue(self):
        
        """
        it's in the name
        """

        self.db["update_queue"].delete_many({})


    def delete_media(self,media_url:str,version:int):

        self.db["medias"].delete_one(
            {
                "media_url":media_url,
                "version":version
            }
        )


    def get_server_infos(self,server_id:str):

        server_id = int(server_id)

        return self.db["servers"].find_one({"server_id":server_id},projection={'_id':False})


    def set_server_info(self,server_id:str,key:str,value:str):

        server_id = int(server_id)

        self.db["servers"].update_one({"server_id":server_id},{"$set":{key:value}})