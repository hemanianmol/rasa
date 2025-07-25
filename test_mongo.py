import os
from pymongo import MongoClient

uri = os.getenv("MONGODB_URI")
client = MongoClient(uri)
try:
    db = client["homelead"]
    print(db.list_collection_names())
    print("Connection successful!")
except Exception as e:
    print("Connection failed:", e)