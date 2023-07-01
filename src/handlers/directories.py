import bson

import src.utils as utils


async def get_directories(parent, db):

    query = {}

    if parent:
        query["parent"] = bson.ObjectId(parent)

    directories = await db.directories.find(query).to_list(None)
    directories_ids = [directory["_id"] for directory in directories]
    return utils.make_json_serializable(directories_ids)


async def get_directory(directory_id, db):
    directory = await db.directories.find_one({"_id": bson.ObjectId(directory_id)})
    if directory is None:
        return "Directory not found", 404
    return utils.make_json_serializable(directory)



async def post_directory(name, parent, db):
    if parent:
        parent = bson.ObjectId(parent)
    directory = {
        "name": name,
        "parent": parent
    }
    result = await db.directories.insert_one(directory)
    directory["_id"] = result.inserted_id
    return utils.make_json_serializable(directory)


async def delete_directory(directory_id, db):
    result = await db.directories.delete_one({"_id": bson.ObjectId(directory_id)})

    if result.deleted_count == 0:
        return "Directory not found", 404
    return "Directory deleted", 200


async def delete_directories(directory_ids, db):
    responses = []

    for directory_id in directory_ids:
        response = await delete_directory(directory_id, db)
        responses.append(response)

    return responses


async def patch_directory(directory_id, db, new_name=None, new_parent=None):
    directory = await db.directories.find_one({"_id": bson.ObjectId(directory_id)})
    if directory is None:
        return "Directory not found", 404

    if new_name:
        directory["name"] = new_name
    if new_parent:
        directory["parent"] = bson.ObjectId(new_parent)

    await db.directories.update_one({"_id": bson.ObjectId(directory_id)}, {"$set": directory})
    return utils.make_json_serializable(directory)


async def patch_directories(directory_ids, db, new_name=None, new_parent=None):
    responses = []

    for directory_id in directory_ids:
        response = await patch_directory(directory_id, db, new_name, new_parent)
        responses.append(response)

    return responses