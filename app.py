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

    files, code = await handlers_files.get_files(db, tags=tags, file_types=file_types, directories=directories)
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

    files, code = await handlers_files.get_files(db, tags=tags, file_types=file_types, directories=directories)
    file_ids = [file["_id"] for file in files]

    return await handlers_files.delete_files(file_ids, db, telegram)

@app.route('/files/id', methods=['GET'])
async def get_files_ids():
    tags = request.args.getlist('tags')
    file_types = request.args.getlist('types')
    directories = request.args.getlist('directories')

    files, code = await handlers_files.get_files(db, tags=tags, file_types=file_types, directories=directories)
    file_ids = [file["_id"] for file in files]

    return file_ids, 200


@app.route('/files/meta', methods=['GET'])
async def get_files():
    tags = request.args.getlist('tag')
    file_types = request.args.getlist('type')
    directories = request.args.get('directories')

    return await handlers_files.get_files(db, tags=tags, file_types=file_types, directories=directories)


@app.route('/files/meta', methods=['PATCH'])
async def patch_files():
    tags = request.args.getlist('tags')
    file_types = request.args.getlist('types')
    directories = request.args.get('directories')

    form = await request.form
    new_tags = form.getlist("tags")
    new_directory = form.get("directory")

    files, code = await handlers_files.get_files(db, tags=tags, file_types=file_types, directories=directories)
    file_ids = [file["_id"] for file in files]
    return await handlers_files.patch_files(file_ids, db, new_tags=new_tags, new_directory=new_directory)


@app.route('/files/meta/tags', methods=['POST'])
async def add_tags_to_files():
    tags = request.args.getlist('tags')
    file_types = request.args.getlist('types')
    directories = request.args.get('directories')

    form = await request.form
    tags_to_add = form.getlist("tags")

    files, code = await handlers_files.get_files(db, tags=tags, file_types=file_types, directories=directories)
    file_ids = [file["_id"] for file in files]
    return await handlers_files.add_tags_to_files(file_ids, db, tags_to_add)


@app.route('/files/meta/tags', methods=['PATCH'])
async def remove_tags_in_files():
    tags = request.args.getlist('tags')
    file_types = request.args.getlist('types')
    directories = request.args.get('directories')

    form = await request.form
    tags_to_remove = form.getlist("tags")

    files, code = await handlers_files.get_files(db, tags=tags, file_types=file_types, directories=directories)
    file_ids = [file["_id"] for file in files]
    return await handlers_files.remove_tags_from_files(file_ids, db, tags_to_remove)


@app.route('/files/meta/tags', methods=['DELETE'])
async def delete_all_tags_in_files():
    tags = request.args.getlist('tags')
    file_types = request.args.getlist('types')
    directories = request.args.get('directories')

    files, code = await handlers_files.get_files(db, tags=tags, file_types=file_types, directories=directories)
    file_ids = [file["_id"] for file in files]
    return await handlers_files.delete_all_tags_from_files(file_ids, db)


@app.route('/files/meta/directory', methods=['DELETE'])
async def delete_files_directory():
    tags = request.args.getlist('tags')
    file_types = request.args.getlist('types')
    directories = request.args.get('directories')

    files, code = await handlers_files.get_files(db, tags=tags, file_types=file_types, directories=directories)
    file_ids = [file["_id"] for file in files]
    return await handlers_files.delete_files_directory(file_ids, db)


@app.route('/files/<file_id>', methods=['GET'])
async def download_file(file_id):
    response, code = await handlers_files.download_file(file_id, db, telegram, chunker)
    if code == 404:
        return "File not found", 404

    return await handlers_files.send_single_file(response)


@app.route('/files/<file_id>', methods=['DELETE'])
async def delete_file(file_id):
    return await handlers_files.delete_file(file_id, db, telegram)


@app.route('/files/<file_id>/meta', methods=['GET'])
async def get_file(file_id):
    return await handlers_files.get_file(file_id, db)


@app.route('/files/<file_id>/meta', methods=['PATCH'])
async def patch_file(file_id):
    form = await request.form
    new_tags = form.getlist("tags")
    new_directory = form.get("directory")

    return await handlers_files.patch_file(file_id, db, new_tags=new_tags, new_directory=new_directory)


@app.route('/files/<file_id>/meta/tags', methods=['POST'])
async def add_tags_to_file(file_id):
    form = await request.form
    tags_to_add = form.getlist("tags")

    return await handlers_files.add_tags_to_file(file_id, db, tags_to_add)


@app.route('/files/<file_id>/meta/tags', methods=['PATCH'])
async def remove_tags_in_file(file_id):
    form = await request.form
    tags_to_remove = form.getlist("tags")

    return await handlers_files.remove_tags_from_file(file_id, db, tags_to_remove)


@app.route('/files/<file_id>/meta/tags', methods=['DELETE'])
async def delete_all_tags_in_file(file_id):
    return await handlers_files.delete_all_tags_from_file(file_id, db)


@app.route('/files/<file_id>/meta/directory', methods=['DELETE'])
async def delete_file_directory(file_id):
    return await handlers_files.delete_file_directory(file_id, db)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    app.run(loop=loop)
