import bson
from quart import send_file
import os
from tqdm.auto import tqdm
import datetime as dt
import io
import asyncio

import src.utils as utils
import src.validators as validators
import src.zipper as zipper

global pbar
global prev_curr


def get_files_query(tags, file_types, directories):
    query = {}

    if tags:
        query["tags"] = {"$all": tags}

    if file_types:
        query["file_type"] = {"$in": file_types}

    if directories:
        query["$or"] = [{"directory": bson.ObjectId(directory)} for directory in directories]

    return query


async def progress(current, total, index=None, max_file_size=None):
    global pbar
    global prev_curr

    progress = current - prev_curr
    progress += index * max_file_size if (index is not None and max_file_size is not None) else progress
    pbar.update(progress)

    prev_curr = current
    prev_curr += index * max_file_size if (index is not None and max_file_size is not None) else prev_curr


async def get_files(tags, file_types, directories, db):
    query = get_files_query(tags, file_types, directories)

    files = []
    async for file in db["files"].find(query):
        files.append(file)
    return utils.make_json_serializable(files), 200


async def get_file(file_id, db):
    file = await db["files"].find_one({"_id": bson.ObjectId(file_id)})
    file = utils.make_json_serializable(file)

    if file is None:
        return "File not found", 404
    return file, 200


async def delete_files(file_ids, db, telegram):
    responses = []

    for file_id in file_ids:
        response = await delete_file(file_id, db, telegram)
        responses.append(response)

    ids = [response[0] for response in responses if response[1] == 200]
    return ids, 200 if len(ids) > 0 else 404


async def delete_file(file_id, db, telegram):
    file_data = await db["files"].find_one({"_id": bson.ObjectId(file_id)})
    if file_data is None:
        return "File not found", 404

    chunks_ids = file_data["chunks"]
    await telegram.client.delete_messages(telegram.chanel_name, chunks_ids)

    delete_result = await db["files"].delete_one({"_id": bson.ObjectId(file_id)})
    return utils.make_json_serializable(file_data), 200


async def patch_files(file_ids, db, new_directory=None, new_tags=None):
    responses = []

    for file_id in file_ids:
        response = await patch_file(file_id, db, new_directory, new_tags)
        responses.append(response)

    ids = [response[0] for response in responses if response[1] == 200]
    return ids, 200 if len(ids) > 0 else 404


async def patch_file(file_id, db, new_directory=None, new_tags=None):
    file_data = await db["files"].find_one({"_id": bson.ObjectId(file_id)})
    if file_data is None:
        return "File not found", 404

    print(new_directory)
    file_data["directory"] = new_directory or file_data["directory"]
    file_data["tags"] = new_tags or file_data["tags"]
    await db["files"].update_one({"_id": bson.ObjectId(file_id)}, {"$set": file_data})
    return utils.make_json_serializable(file_data["_id"]), 200


async def post_files_tags(file_ids, db, tags):
    responses = []

    for file_id in file_ids:
        response = await post_file_tags(file_id, db, tags)
        responses.append(response)

    ids = [response[0] for response in responses if response[1] == 200]
    return ids, 200 if len(ids) > 0 else 404


async def post_file_tags(file_id, db, tags):
    file_data = await db["files"].find_one({"_id": bson.ObjectId(file_id)})
    if file_data is None:
        return "File not found", 404

    file_data["tags"] = list(set(file_data["tags"] + tags))
    await db["files"].update_one({"_id": bson.ObjectId(file_id)}, {"$set": file_data})
    file_data = utils.make_json_serializable(file_data)
    return file_data["_id"], 200


async def delete_files_tags(file_ids, db, tags):
    responses = []

    for file_id in file_ids:
        response = await delete_file_tags(file_id, db, tags)
        responses.append(response)

    ids = [response[0] for response in responses if response[1] == 200]
    return ids, 200 if len(ids) > 0 else 404


async def delete_file_tags(file_id, db, tags):
    file_data = await db["files"].find_one({"_id": bson.ObjectId(file_id)})
    if file_data is None:
        return "File not found", 404

    file_data["tags"] = [tag for tag in file_data["tags"] if tag not in tags]
    await db["files"].update_one({"_id": bson.ObjectId(file_id)}, {"$set": file_data})
    file_data = utils.make_json_serializable(file_data)
    return file_data["_id"], 200


async def add_tags_to_files(file_ids, db, tags):
    responses = []

    for file_id in file_ids:
        response = await add_tags_to_file(file_id, db, tags)
        responses.append(response)

    ids = [response[0] for response in responses if response[1] == 200]
    return ids, 200 if len(ids) > 0 else 404


async def add_tags_to_file(file_id, db, tags):
    file_data = await db["files"].find_one({"_id": bson.ObjectId(file_id)})
    if file_data is None:
        return "File not found", 404

    file_data["tags"] = list(set(file_data["tags"] + tags))
    await db["files"].update_one({"_id": bson.ObjectId(file_id)}, {"$set": file_data})
    file_data = utils.make_json_serializable(file_data)
    return file_data["_id"], 200


async def remove_tags_from_files(file_ids, db, tags):
    responses = []

    for file_id in file_ids:
        response = await remove_tags_from_file(file_id, db, tags)
        responses.append(response)

    ids = [response[0] for response in responses if response[1] == 200]
    return ids, 200 if len(ids) > 0 else 404


async def remove_tags_from_file(file_id, db, tags):
    file_data = await db["files"].find_one({"_id": bson.ObjectId(file_id)})
    if file_data is None:
        return "File not found", 404

    file_data["tags"] = [tag for tag in file_data["tags"] if tag not in tags]
    await db["files"].update_one({"_id": bson.ObjectId(file_id)}, {"$set": file_data})
    file_data = utils.make_json_serializable(file_data)
    return file_data["_id"], 200


async def delete_all_tags_from_files(file_ids, db):
    responses = []

    for file_id in file_ids:
        response = await delete_all_tags_from_file(file_id, db)
        responses.append(response)

    ids = [response[0] for response in responses if response[1] == 200]
    return ids, 200 if len(ids) > 0 else 404


async def delete_all_tags_from_file(file_id, db):
    file_data = await db["files"].find_one({"_id": bson.ObjectId(file_id)})
    if file_data is None:
        return "File not found", 404

    file_data["tags"] = []
    await db["files"].update_one({"_id": bson.ObjectId(file_id)}, {"$set": file_data})
    return file_id, 200


async def delete_files_directory(file_ids, db):
    responses = []

    for file_id in file_ids:
        response = await delete_file_directory(file_id, db)
        responses.append(response)

    ids = [response[0] for response in responses if response[1] == 200]
    return ids, 200 if len(ids) > 0 else 404


async def delete_file_directory(file_id, db):
    file_data = await db["files"].find_one({"_id": bson.ObjectId(file_id)})
    if file_data is None:
        return "File not found", 404

    file_data["directory"] = None
    await db["files"].update_one({"_id": bson.ObjectId(file_id)}, {"$set": file_data})
    return file_id, 200


async def upload_files(files, files_data, db, telegram, chunker):
    responses = []

    bar = tqdm(total=len(files), unit="files", desc="Uploading files")
    for file, file_data in zip(files, files_data):
        file_data = utils.load_json_from_string(file_data)
        response = await upload_file(file, file_data, db, telegram, chunker)
        responses.append(response)
        bar.update(1)
    bar.close()

    ids = [response[0] for response in responses if response[1] == 200]
    return ids, 200 if len(ids) > 0 else 404


async def upload_file(file, file_data, db, telegram, chunker):
    global pbar
    global prev_curr
    global total_progress

    name = file.filename

    if not validators.validate_file_upload(file_data):
        return f"Invalid file data for file {name}", 400

    type_ = file_data["type"]
    size = file_data["size"]
    tags = file_data["tags"] if "tags" in file_data else []
    directory = file_data["directory"] if "directory" in file_data else None
    created_at = file_data["created_at"] if "created_at" in file_data else None
    uploaded_at = dt.datetime.now()

    file_exists = await db["files"].find_one({"name": name, "type": type_, "size": size, "directory": directory})
    if file_exists:
        return "File already exists", 400

    chunks = chunker.split(file) if size > telegram.max_file_size else [file]
    chunks_ids = []

    chunks_pbar = tqdm(total=len(chunks), unit="chunk", desc="Uploading chunks")
    prev_curr = 0
    pbar = tqdm(total=file_data["size"], unit="B", unit_scale=True, desc=name, initial=prev_curr)
    for index, chunk in enumerate(chunks):

        message = await telegram.client.send_file(telegram.chanel_name, chunk, caption=f"{name} - {index + 1}/{len(chunks)}", progress_callback=lambda current, total: progress(current, total, index, telegram.max_file_size))
        chunks_ids.append(message.id)

        chunks_pbar.update(1)

    chunks_pbar.close()
    pbar.close()

    file_data = {
        "name": name,
        "size": size,
        "type": type_,
        "tags": tags,
        "directory": bson.ObjectId(directory) if directory else None,
        "created_at": created_at,
        "uploaded_at": uploaded_at,
        "chunks": chunks_ids,
    }

    res = await db["files"].insert_one(file_data)
    return utils.make_json_serializable(res.inserted_id), 200


async def download_files(file_ids, db, telegram, chunker):
    files = []
    bar = tqdm(total=len(file_ids), unit="files", desc="Downloading files")
    for file_id in file_ids:
        file = await download_file(file_id, db, telegram, chunker)
        files.append(file)
        bar.update(1)
    bar.close()

    files = [file[0] for file in files if file is not None]
    return await send_files(files)


async def download_file(file_id, db, telegram, chunker):
    global pbar
    global prev_curr

    file_data = await db["files"].find_one({"_id": bson.ObjectId(file_id)})
    if file_data is None:
        return "File not found", 404

    chunks_ids = file_data["chunks"]
    chunks = []
    chunks_pbar = tqdm(total=len(chunks_ids), unit="chunk", desc="Downloading chunks")
    for chunk_id in chunks_ids:
        message = await telegram.client.get_messages(telegram.chanel_name, ids=chunk_id)

        if not os.path.exists("temp"):
            os.mkdir("temp")
        file_path = f"temp/{chunk_id}"

        prev_curr = 0
        pbar = tqdm(total=message.file.size, unit="B", unit_scale=True, desc=file_data["name"])

        await message.download_media(file_path, progress_callback=progress)
        chunks.append(file_path)
        chunks_pbar.update(1)

    chunks_pbar.close()
    pbar.close()

    bytes = chunker.join(chunks)

    utils.clear_temp_folder()

    file_name = file_data["name"]
    return (file_name, bytes), 200


async def send_files(files):
    files_zipper = zipper.Zipper()
    zip_file = files_zipper.zip(files, "temp/telecloud.zip")
    return_data = io.BytesIO()
    with open(zip_file, "rb") as f:
        return_data.write(f.read())
    return_data.seek(0)

    utils.clear_temp_folder()

    return await send_file(return_data, as_attachment=True, attachment_filename="telecloud.zip"), 200


async def send_single_file(file):
    file_name = file[0]
    bytes = file[1]

    return_data = io.BytesIO()
    return_data.write(bytes)
    return_data.seek(0)

    return await send_file(return_data, as_attachment=True, attachment_filename=file_name), 200
