import bson
import json


def make_json_serializable(data):
    if isinstance(data, list):
        return [make_json_serializable(item) for item in data]
    elif isinstance(data, dict):
        return {key: make_json_serializable(value) for key, value in data.items()}
    elif isinstance(data, bson.ObjectId):
        return str(data)
    else:
        return data


def load_json_from_string(string):
    string = string.replace("'", '"')
    return json.loads(string)
