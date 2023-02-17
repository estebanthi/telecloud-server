from quart import Quart, request, send_file
from telethon import TelegramClient, events, errors
import os
from json import dumps as jsonify
import asyncio
import yaml
from motor.motor_asyncio import AsyncIOMotorClient
import bson

from file_splitter import FileSplitter


config = yaml.safe_load(open("config.yml", "r"))

telegram_api_id = config["telegram_api_id"]
telegram_api_hash = config["telegram_api_hash"]

telegram_client = TelegramClient("session", telegram_api_id, telegram_api_hash)
telegram_client.start()
telegram_max_file_size = int(1024 * 1024 * 1024 * 2)

motor_client = AsyncIOMotorClient(config["mongo_uri"])
db = motor_client["telecloud"]

app = Quart(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024 * 2  * 10  # 20 GB


@app.route('/upload', methods=['POST'])
async def upload():
    files = await request.files
    file = files['file']
    file_name = file.filename

    form_data = await request.form
    file_type = form_data['type']
    file_size = int(form_data['size'])
    tags = form_data.getlist('tags')

    chunks = [file]
    if file_size >= telegram_max_file_size:
        file_splitter = FileSplitter(telegram_max_file_size)
        chunks = file_splitter.split(file)

    chunks_ids = []
    for index, chunk in enumerate(chunks):
        message = await telegram_client.send_file(config["telegram_channel"], chunk, caption=f"{file_name} - {index + 1}/{len(chunks)}")
        chunks_ids.append(message.id)

    file_data = {
        "file_name": file_name,
        "file_size": file_size,
        "file_type": file_type,
        "tags": tags,
        "chunks": chunks_ids,
    }

    await db["files"].insert_one(file_data)

    file_data["_id"] = str(file_data["_id"])
    return jsonify(file_data)


@app.route('/download/<file_id>', methods=['GET'])
async def download(file_id):
    file_data = await db["files"].find_one({"_id": bson.ObjectId(file_id)})
    if file_data is None:
        return "File not found", 404

    chunks_ids = file_data["chunks"]
    chunks = []
    for chunk_id in chunks_ids:
        message = await telegram_client.get_messages(config["telegram_channel"], ids=chunk_id)
        if not os.path.exists("temp"):
            os.mkdir("temp")
        file_path = f"temp/{chunk_id}"
        await message.download_media(file_path)
        chunk = open(file_path, "rb").read()
        chunks.append(chunk)

    file = FileSplitter.join(chunks)

    for chunk_id in chunks_ids:
        os.remove(f"temp/{chunk_id}")

    return await send_file(file, attachment_filename=file_data["file_name"], as_attachment=True)


@app.route('/clear', methods=['GET'])
async def clear():
    await db["files"].delete_many({})
    await telegram_client.delete_messages(config["telegram_channel"], await telegram_client.get_messages(config["telegram_channel"]))
    return "Cleared"


@app.route('/files', methods=['GET'])
async def files():
    query = {}
    tags = request.args.getlist('tags')
    if tags:
        query["tags"] = {"$all": tags}

    file_types = request.args.getlist('types')
    if file_types:
        query["file_type"] = {"$in": file_types}

    files = []
    async for file in db["files"].find(query):
        file["_id"] = str(file["_id"])
        files.append(file)
    return jsonify(files)


@app.route('/files/<file_id>', methods=['DELETE'])
async def delete_file(file_id):
    file_data = await db["files"].find_one({"_id": bson.ObjectId(file_id)})
    if file_data is None:
        return "File not found", 404

    chunks_ids = file_data["chunks"]
    await telegram_client.delete_messages(config["telegram_channel"], chunks_ids)
    await db["files"].delete_one({"_id": bson.ObjectId(file_id)})

    return "Deleted"


@app.route('/files/<file_id>', methods=['GET'])
async def get_file(file_id):
    file_data = await db["files"].find_one({"_id": bson.ObjectId(file_id)})
    if file_data is None:
        return "File not found", 404

    file_data["_id"] = str(file_data["_id"])
    return jsonify(file_data)


@app.route('/files/<file_id>/tags', methods=['POST'])
async def add_tags(file_id):
    form_data = await request.form
    tags = form_data.getlist('tags')

    file_data = await db["files"].find_one({"_id": bson.ObjectId(file_id)})
    if file_data is None:
        return "File not found", 404

    file_data["tags"] = list(set(file_data["tags"] + tags))
    await db["files"].update_one({"_id": bson.ObjectId(file_id)}, {"$set": file_data})

    file_data["_id"] = str(file_data["_id"])
    return jsonify(file_data)


@app.route('/files/<file_id>/tags', methods=['DELETE'])
async def remove_tags(file_id):
    form_data = await request.form
    tags = form_data.getlist('tags')

    file_data = await db["files"].find_one({"_id": bson.ObjectId(file_id)})
    if file_data is None:
        return "File not found", 404

    file_data["tags"] = list(set(file_data["tags"]) - set(tags))
    await db["files"].update_one({"_id": bson.ObjectId(file_id)}, {"$set": file_data})

    file_data["_id"] = str(file_data["_id"])
    return jsonify(file_data)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    app.run(loop=loop)
