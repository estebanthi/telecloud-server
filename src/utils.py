import bson
import json
import datetime as dt
import shutil


def make_json_serializable(data):
    if isinstance(data, list):
        return [make_json_serializable(item) for item in data]
    elif isinstance(data, dict):
        return {key: make_json_serializable(value) for key, value in data.items()}
    elif isinstance(data, bson.ObjectId):
        return str(data)
    elif isinstance(data, dt.datetime):
        return data.isoformat()
    else:
        return data


def load_json_from_string(string):
    string = string.replace("'", '"')
    return json.loads(string)


def clear_temp_folder():
    path = "temp"
    if shutil.os.path.exists(path):
        shutil.rmtree(path)
    shutil.os.mkdir(path)


def rename_duplicates(names):
    names = names.copy()
    for i in range(len(names)):
        if names[i] in names[:i]:
            names[i] = f"{names[i]} ({names[:i].count(names[i])})"
    return names
