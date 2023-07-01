from quart import Quart, request, after_this_request
from json import dumps as jsonify
import json
import asyncio
from tqdm.auto import tqdm

from src.telegram import Telegram
from src.database import Database
from src.chunker import Chunker

import src.handlers.files as handlers_files
import src.handlers.directories as handlers_directories

import src.utils as utils


telegram = Telegram()
db = Database().db

telegram_max_file_size = telegram.max_file_size
chunker = Chunker(telegram_max_file_size)

utils.clear_temp_folder()

app = Quart(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024 * 2 * 10  # 20 GB


@app.route('/files', methods=['GET'])
async def download_files():
    tags = request.args.getlist('tags')
    file_types = request.args.getlist('types')
    directories = request.args.getlist('directories')

    files= await handlers_files.get_files(tags, file_types, directories, db)
    file_ids = [file["_id"] for file in files]
    return await handlers_files.download_files(file_ids, db, telegram, chunker)


@app.route('/files', methods=['POST'])
async def upload_files():
    files = await request.files
    files = files.getlist("files")

    form_data = await request.form
    data = form_data.getlist("data")

    return await handlers_files.upload_files(files, data, db, telegram, chunker)


@app.route('/files', methods=['DELETE'])
async def delete_files():
    tags = request.args.getlist('tags')
    file_types = request.args.getlist('types')
    directories = request.args.getlist('directories')

    files = await handlers_files.get_files(tags, file_types, directories, db)
    file_ids = [file["_id"] for file in files]
    response = await handlers_files.delete_files(file_ids, db, telegram)
    return jsonify(response)


@app.route('/files/id', methods=['GET'])
async def get_files_ids():
    tags = request.args.getlist('tags')
    file_types = request.args.getlist('types')
    directories = request.args.getlist('directories')

    files = await handlers_files.get_files(tags, file_types, directories, db)
    file_ids = [file["_id"] for file in files]
    return jsonify(file_ids)


@app.route('/files/meta', methods=['GET'])
async def get_files():
    tags = request.args.getlist('tag')
    file_types = request.args.getlist('type')
    directory = request.args.get('directory')

    response = await handlers_files.get_files(tags, file_types, directory, db)
    return jsonify(response)


@app.route('/files/meta', methods=['PATCH'])
async def patch_files():
    tags = request.args.getlist('tags')
    file_types = request.args.getlist('types')
    directory = request.args.get('directories')

    form = await request.form
    new_tags = form.getlist("tags")
    new_directory = form.get("directory")

    files = await handlers_files.get_files(tags, file_types, directory, db)
    file_ids = [file["_id"] for file in files]
    response = await handlers_files.patch_files(file_ids, db, new_tags=new_tags, new_directory=new_directory)
    return jsonify(response)


@app.route('/files/meta/tags', methods=['POST'])
async def add_tags_to_files():
    tags = request.args.getlist('tags')
    file_types = request.args.getlist('types')
    directory = request.args.get('directories')

    form = await request.form
    tags_to_add = form.getlist("tags")

    files = await handlers_files.get_files(tags, file_types, directory, db)
    file_ids = [file["_id"] for file in files]
    response = await handlers_files.add_tags_to_files(file_ids, db, tags_to_add)
    return jsonify(response)


@app.route('/files/meta/tags', methods=['PATCH'])
async def remove_tags_in_files():
    tags = request.args.getlist('tags')
    file_types = request.args.getlist('types')
    directory = request.args.get('directories')

    form = await request.form
    tags_to_remove = form.getlist("tags")

    files = await handlers_files.get_files(tags, file_types, directory, db)
    file_ids = [file["_id"] for file in files]
    response = await handlers_files.remove_tags_from_files(file_ids, db, tags_to_remove)
    return jsonify(response)


@app.route('/files/meta/tags', methods=['DELETE'])
async def delete_all_tags_in_files():
    tags = request.args.getlist('tags')
    file_types = request.args.getlist('types')
    directory = request.args.get('directories')

    files = await handlers_files.get_files(tags, file_types, directory, db)
    file_ids = [file["_id"] for file in files]
    response = await handlers_files.delete_all_tags_from_files(file_ids, db)
    return jsonify(response)


@app.route('/files/meta/directory', methods=['PUT'])
async def replace_files_directory():
    tags = request.args.getlist('tags')
    file_types = request.args.getlist('types')
    directory = request.args.get('directories')

    form = await request.form
    new_directory = form.get("directory")

    files = await handlers_files.get_files(tags, file_types, directory, db)
    file_ids = [file["_id"] for file in files]
    response = await handlers_files.patch_files(file_ids, db, new_directory=new_directory)
    return jsonify(response)



if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    app.run(loop=loop)
