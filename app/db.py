import os
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI)
db = client.get_database("jobdb")
results = db.get_collection("results")

def save_result(job_type: str, input_data, result, meta=None):
    doc = {
        "type": job_type,
        "input": input_data,
        "result": result,
        "meta": meta or {},
        "timestamp": datetime.utcnow().isoformat()
    }
    inserted = results.insert_one(doc)
    return str(inserted.inserted_id)

def get_all_results():
    out = []
    for d in results.find({}, {"_id": 1, "type": 1, "input": 1, "result": 1, "meta": 1, "timestamp": 1}):
        d["id"] = str(d["_id"])
        d.pop("_id", None)
        out.append(d)
    return out

def get_result_by_id(str_id):
    d = results.find_one({"_id": ObjectId(str_id)})
    if not  d:
        return None
    d["id"] = str(d["_id"])
    d.pop("_id", None)
    return d
