import bson
from quart import send_file
import os
from tqdm.auto import tqdm

import src.utils as utils

global pbar
global prev_curr


async def get_files(tags, file_types, directories, db):
    query = get_files_query(tags, file_types, directories)

    files = []
    async for file in db["files"].find(query):
        files.append(file["_id"])
    return utils.make_json_serializable(files)


def get_files_query(tags, file_types, directories):
    query = {}

    if tags:
        query["tags"] = {"$all": tags}

    if file_types:
        query["file_type"] = {"$in": file_types}

    if directories:
        query["$or"] = [{"directory": bson.ObjectId(directory)} for directory in directories]

    return query


async def get_file(file_id, db):
    file = await db["files"].find_one({"_id": bson.ObjectId(file_id)})
    file = utils.make_json_serializable(file)
    return file


async def upload_file(file, file_data, db, telegram, chunker):
    global pbar
    global prev_curr

    name = file.filename

    if not validate_upload(file_data):
        return f"Invalid file data for file {name}", 400

    type_ = file_data["type"]
    size = file_data["size"]
    tags = file_data["tags"] if "tags" in file_data else []
    directory = file_data["directory"] if "directory" in file_data else None

    file_exists = await db["files"].find_one({"name": name, "type": type_, "size": size, "directory": directory})
    if file_exists:
        return "File already exists", 400

    chunks = chunker.split(file) if size > telegram.max_file_size else [file]
    chunks_ids = []

    chunks_pbar = tqdm(total=len(chunks), unit="chunk", desc="Uploading chunks")
    for index, chunk in enumerate(chunks):

        prev_curr = 0
        pbar = tqdm(total=file_data["size"], unit="B", unit_scale=True, desc=name, initial=prev_curr)

        message = await telegram.client.send_file(telegram.chanel_name, chunk, caption=f"{name} - {index + 1}/{len(chunks)}", progress_callback=progress)
        chunks_ids.append(message.id)

        chunks_pbar.update(1)

    file_data = {
        "name": name,
        "size": size,
        "type": type_,
        "tags": tags,
        "directory": bson.ObjectId(directory) if directory else None,
        "chunks": chunks_ids,
    }

    res = await db["files"].insert_one(file_data)
    file_data["_id"] = str(res.inserted_id)
    return utils.make_json_serializable(file_data), 200


def validate_upload(file_data):
    return "type" in file_data and "size" in file_data


# tqdm bar
async def progress(current, total):
    global pbar
    global prev_curr
    pbar.update(current - prev_curr)
    prev_curr = current

async def delete_files(file_ids, db, telegram):
    responses = []

    for file_id in file_ids:
        response = await delete_file(file_id, db, telegram)
        responses.append(response)

    return responses


async def delete_file(file_id, db, telegram):
    file_data = await db["files"].find_one({"_id": bson.ObjectId(file_id)})
    if file_data is None:
        return "File not found", 404

    chunks_ids = file_data["chunks"]
    await telegram.client.delete_messages(telegram.chanel_name, chunks_ids)

    delete_result = await db["files"].delete_one({"_id": bson.ObjectId(file_id)})
    return utils.make_json_serializable(file_data), 200


async def delete_files_tags(file_ids, db, tags):
    responses = []

    for file_id in file_ids:
        response = await delete_file_tags(file_id, db, tags)
        responses.append(response)

    return responses


async def delete_file_tags(file_id, db, tags):
    file_data = await db["files"].find_one({"_id": bson.ObjectId(file_id)})
    if file_data is None:
        return "File not found", 404

    file_data["tags"] = [tag for tag in file_data["tags"] if tag not in tags]
    await db["files"].update_one({"_id": bson.ObjectId(file_id)}, {"$set": file_data})
    file_data = utils.make_json_serializable(file_data)
    return file_data


async def post_files_tags(file_ids, db, tags):
    responses = []

    for file_id in file_ids:
        response = await post_file_tags(file_id, db, tags)
        responses.append(response)

    return responses


async def post_file_tags(file_id, db, tags):
    file_data = await db["files"].find_one({"_id": bson.ObjectId(file_id)})
    if file_data is None:
        return "File not found", 404

    file_data["tags"] = list(set(file_data["tags"] + tags))
    await db["files"].update_one({"_id": bson.ObjectId(file_id)}, {"$set": file_data})
    file_data = utils.make_json_serializable(file_data)
    return file_data


async def patch_files(file_ids, db, new_directory=None, new_tags=None):
    responses = []

    for file_id in file_ids:
        response = await patch_file(file_id, db, new_directory, new_tags)
        responses.append(response)

    return responses


async def patch_file(file_id, db, new_directory=None, new_tags=None):
    file_data = await db["files"].find_one({"_id": bson.ObjectId(file_id)})
    if file_data is None:
        return "File not found", 404

    file_data["directory"] = new_directory or file_data["directory"]
    file_data["tags"] = new_tags or file_data["tags"]
    await db["files"].update_one({"_id": bson.ObjectId(file_id)}, {"$set": file_data})
    file_data = utils.make_json_serializable(file_data)
    return file_data


async def download_file(file_id, db, telegram, chunker):
    global pbar
    global prev_curr

    file_data = await db["files"].find_one({"_id": bson.ObjectId(file_id)})
    if file_data is None:
        return "File not found", 404

    chunks_ids = file_data["chunks"]
    chunks = []
    for chunk_id in chunks_ids:
        message = await telegram.client.get_messages(telegram.chanel_name, ids=chunk_id)

        if not os.path.exists("temp"):
            os.mkdir("temp")
        file_path = f"temp/{chunk_id}"

        print(f"Downloading chunk {chunks_ids.index(chunk_id) + 1}/{len(chunks_ids)} of {file_data['name']}")
        prev_curr = 0
        pbar = tqdm(total=message.file.size, unit="B", unit_scale=True, desc=file_data["name"])

        await message.download_media(file_path, progress_callback=progress)
        chunks.append(file_path)

    file = chunker.join(chunks)
    return await send_file(file, as_attachment=True, attachment_filename=file_data["name"])
