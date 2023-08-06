import bson
import src.handlers.files as handlers_files
import src.utils as utils


def get_directories_query(names, parents):
    query = {}
    if names:
        query["name"] = {"$in": names}
    if parents:
        query["parent"] = {"$in": [bson.ObjectId(parent) for parent in parents]}
    return query


async def get_directories(db, names=None, parents=None, recursive=None):
    query = get_directories_query(names, parents)
    directories = await db.directories.find(query).to_list(None)
    if recursive:
        for directory in directories:
            children, code = await get_directories(db, parents=[directory["_id"]], recursive=True)
            directories.extend([child for child in children if child not in directories])

    return utils.make_json_serializable(directories), 200


async def get_directory(db, directory_id):
    directory = await db.directories.find_one({"_id": bson.ObjectId(directory_id)})
    if directory:
        return utils.make_json_serializable(directory), 200
    else:
        return "Directory not found", 404


async def create_directory(db, name, parent):
    if parent == "/":
        parent = None
    directory = await db.directories.find_one({"name": name, "parent": bson.ObjectId(parent)})
    if directory:
        return "Directory already exists", 409
    else:
        if parent:
            try:
                parent = bson.ObjectId(parent)
            except bson.errors.InvalidId:
                return "Invalid parent id", 400
        directory = {"name": name, "parent": parent}
        await db.directories.insert_one(directory)
        return utils.make_json_serializable(directory["_id"]), 200


async def delete_directory(directory_id, db, telegram):
    directory = await db.directories.find_one({"_id": bson.ObjectId(directory_id)})
    if directory:
        await db.directories.delete_one({"_id": bson.ObjectId(directory_id)})

        directories, code = await get_directories(db, parents=[directory_id], recursive=True)
        directories_ids = [directory["_id"] for directory in directories]

        await delete_directories(directories_ids, db, telegram)

        directory_files, code = await handlers_files.get_files(db, directories=[directory_id] + directories_ids)
        await handlers_files.delete_files([file["_id"] for file in directory_files], db, telegram)
        return utils.make_json_serializable(directory["_id"]), 200
    else:
        return "Directory not found", 404


async def delete_directories(directories_ids, db, telegram):
    responses = []
    for _id in directories_ids:
        res = await delete_directory(_id, db, telegram)
        responses.append(res)

    return [response[0] for response in responses], 200


async def patch_directories(directories_ids, db, telegram, new_name=None, new_parent=None):
    responses = []
    for _id in directories_ids:
        res = await patch_directory(_id, db, telegram, new_name, new_parent)
        responses.append(res)

    return [response[0] for response in responses], 200


async def patch_directory(directory_id, db, telegram, new_name=None, new_parent=None):
    directory = await db.directories.find_one({"_id": bson.ObjectId(directory_id)})
    if directory:
        if new_name:
            directory["name"] = new_name
        if new_parent:
            directory["parent"] = bson.ObjectId(new_parent)
        await db.directories.update_one({"_id": bson.ObjectId(directory_id)}, {"$set": directory})

        await merge_similar_directories(db, telegram, directory_id)
        return utils.make_json_serializable(directory["_id"]), 200
    else:
        return "Directory not found", 404


async def get_directory_children(directory_id, db, recursive=None):
    directory = await db.directories.find_one({"_id": bson.ObjectId(directory_id)})
    if directory:
        children, code = await get_directories(db, parents=[directory_id], recursive=recursive)
        return utils.make_json_serializable([child["_id"] for child in children]), 200
    else:
        return "Directory not found", 404


async def add_directory_children(directory_id, db, children_ids):
    directory = await db.directories.find_one({"_id": bson.ObjectId(directory_id)})
    if directory:
        for child_id in children_ids:
            await db.directories.update_one({"_id": bson.ObjectId(child_id)}, {"$set": {"parent": bson.ObjectId(directory_id)}})
        return utils.make_json_serializable(directory["_id"]), 200
    else:
        return "Directory not found", 404


async def remove_directory_children(directory_id, db, children_ids, recursive=None):
    directory = await db.directories.find_one({"_id": bson.ObjectId(directory_id)})
    if directory:
        directories = await get_directories(db, parents=[directory_id], recursive=recursive)
        for child_id in children_ids:
            if child_id in [directory["_id"] for directory in directories]:
                await db.directories.update_one({"_id": bson.ObjectId(child_id)}, {"$set": {"parent": None}})
        return utils.make_json_serializable(directory["_id"]), 200
    else:
        return "Directory not found", 404


async def merge_similar_directories(db, telegram, directory_id):
    directory_data, code = await get_directory(db, directory_id)
    if code == 200:
        directory = directory_data
        parents = [directory["parent"]] if directory["parent"] else []
        similar_directories, code = await get_directories(db, names=[directory["name"]], parents=parents)
        if len(similar_directories) > 1:
            files, code = await handlers_files.get_files(db, directories=[directory_["_id"] for directory_ in similar_directories])
            files_ids = [file["_id"] for file in files]
            await handlers_files.patch_files(files_ids, db, telegram, new_directory=directory["_id"])
            await delete_directories([similar_directory["_id"] for similar_directory in similar_directories[1:]], db, telegram)
        return utils.make_json_serializable(directory["_id"]), 200