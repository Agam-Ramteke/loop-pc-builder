import pymongo
from pymongo import mongo_client

client = pymongo.MongoClient("localhost", 27017)

db = client['Recommendation_System']
