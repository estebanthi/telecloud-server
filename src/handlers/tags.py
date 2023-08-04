import bson
import src.utils as utils
import src.handlers.files as handlers_files


def get_tags_query(names, parents):
    query = {}
    if names:
        query["name"] = {"$in": names}
    if parents:
        query["parent"] = {"$in": [bson.ObjectId(parent) for parent in parents]}
    return query


async def get_tags(db, names=None, parents=None, recursive=None):
    print("get_tags")
    query = get_tags_query(names, parents)
    tags = await db.tags.find(query).to_list(None)
    if recursive:
        for tag in tags:
            children, code = await get_tags(db, parents=[tag["_id"]], recursive=True)
            tags.extend([child for child in children if child not in tags])

    return utils.make_json_serializable(tags), 200


async def get_tag(db, tag_id):
    tag = await db.tags.find_one({"_id": bson.ObjectId(tag_id)})
    if tag:
        return utils.make_json_serializable(tag), 200
    else:
        return "Tag not found", 404


async def create_tag(db, name, parent):
    if not name:
        return "Name is required", 400
    tag = await get_tags(db, names=[name])
    if tag:
        return "Tag already exists", 409
    else:
        if parent:
            try:
                parent = bson.ObjectId(parent)
            except bson.errors.InvalidId:
                return "Invalid parent id", 400
        tag = {"name": name, "parent": parent}
        await db.tags.insert_one(tag)
        return utils.make_json_serializable(tag["_id"]), 200


async def delete_tag(tag_id, db, telegram):
    tag = await db.tags.find_one({"_id": bson.ObjectId(tag_id)})
    if tag:
        await db.tags.delete_one({"_id": bson.ObjectId(tag_id)})
        return utils.make_json_serializable(tag["_id"]), 200
    else:
        return "Tag not found", 404


async def delete_tags(tags_ids, db, telegram):
    for tag_id in tags_ids:
        tag = await db.tags.find_one({"_id": bson.ObjectId(tag_id)})
        if tag:
            await db.tags.delete_one({"_id": bson.ObjectId(tag_id)})
    return utils.make_json_serializable(tags_ids), 200


async def patch_tag(tag_id, db, telegram, new_name=None, new_parent=None):
    tag = await db.tags.find_one({"_id": bson.ObjectId(tag_id)})
    if tag:
        if new_name:
            tag["name"] = new_name
        if new_parent:
            tag["parent"] = bson.ObjectId(new_parent)
        await db.tags.update_one({"_id": bson.ObjectId(tag_id)}, {"$set": tag})
        await merge_similar_tags(db, telegram, tag_id)
        return utils.make_json_serializable(tag["_id"]), 200
    else:
        return "Tag not found", 404


async def get_tag_children(tag_id, db, recursive=None):
    tag = await db.tags.find_one({"_id": bson.ObjectId(tag_id)})
    if tag:
        children, code = await get_tags(db, parents=[tag_id], recursive=recursive)
        return utils.make_json_serializable(children), 200
    else:
        return "Tag not found", 404


async def remove_tag_children(tag_id, db, telegram, recursive=None):
    tag = await db.tags.find_one({"_id": bson.ObjectId(tag_id)})
    if tag:
        children, code = await get_tags(db, parents=[tag_id], recursive=recursive)
        for child in children:
            await delete_tag(child["_id"], db, telegram)
        return utils.make_json_serializable(children), 200
    else:
        return "Tag not found", 404


async def merge_similar_tags(db, telegram, tag_id):
    tag_data, code = await get_tag(db, tag_id)
    if code == 200:
        tag = tag_data
        parents = [tag["parent"]] if tag["parent"] else []
        similar_tags, code = await get_tags(db, names=[tag["name"]], parents=parents)
        if len(similar_tags) > 1:
            files, code = await handlers_files.get_files(db, tags=[tag["_id"] for tag in similar_tags])
            files_ids = [file["_id"] for file in files]
            await handlers_files.delete_files_tags(files_ids, db, [tag["_id"] for tag in similar_tags[1:]], telegram)
            await delete_tags([tag["_id"] for tag in similar_tags[1:]], db, telegram)
        return utils.make_json_serializable(tag["_id"]), 200
