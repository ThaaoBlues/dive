"""
this file is used into a cronjob to clear all entries 
from more than 180 days in the database

"""
from mongo_database import DataBase


if __name__ == "__main__":
    
    db = DataBase()

    db.delete_after_180_days()