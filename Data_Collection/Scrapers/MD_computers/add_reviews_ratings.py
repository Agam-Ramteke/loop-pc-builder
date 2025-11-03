from pymongo import MongoClient
import pandas as pd
import time
import numpy as np
import datetime
import sys
import os
import matplotlib.pyplot as plt

# Settings
DB_NAME = "PC_Parts"
COLLECTION_NAME = None
CONNECTION_STRING = "mongodb://localhost:27017/"


def access_data(CONNECTION_STRING, DB_NAME, COLLECTION_NAME):
    # connect to MongoDB
    client = MongoClient(CONNECTION_STRING)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    # fetch only specific fields
    data = list(collection.find({}, {"_id": 0, "name": 1, "specifications": 1}))
    df = pd.json_normalize(data)

    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)
    print(df[["name","specifications.GPU","specifications.Chipset"]].head())  # print only first few rows for readability

    df.to_excel("GPU.xlsx", index=False)


    return df


if __name__ == "__main__":
    access_data(CONNECTION_STRING, DB_NAME, "GPUs")
