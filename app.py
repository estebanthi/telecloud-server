from quart import Quart, request
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

app = Quart(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024 * 2 * 10  # 20 GB



@app.route('/files', methods=['GET'])
async def download_files():
    tags = request.args.getlist('tags')
    file_types = request.args.getlist('types')
    directories = request.args.get('directories')

    file_ids = await handlers_files.get_files(tags, file_types, directories, db)

    responses = []
    pbar = tqdm(total=len(file_ids), unit="files", desc="Downloading files")
    for file_id in file_ids:
        response = await handlers_files.download_file(file_id, db, telegram, chunker)
        responses.append(response)
        pbar.update(1)

    return jsonify(responses)


@app.route('/files', methods=['POST'])
async def upload_files():
    files = await request.files
    files = files.getlist("files")

    form_data = await request.form
    data = form_data.getlist("data")

    responses = []
    pbar = tqdm(total=len(files), unit="files", desc="Uploading files")
    for file, file_data in zip(files, data):
        file_data = utils.load_json_from_string(file_data)
        response = await handlers_files.upload_file(file, file_data, db, telegram, chunker)
        responses.append(response)
        pbar.update(1)

    return jsonify(responses)



@app.route('/files/meta', methods=['GET'])
async def get_files():
    tags = request.args.getlist('tag')
    file_types = request.args.getlist('type')
    directory = request.args.get('directory')

    response = await handlers_files.get_files(tags, file_types, directory, db)
    return jsonify(response)


@app.route('/files', methods=['DELETE'])
async def delete_files():
    tags = request.args.getlist('tag')
    file_types = request.args.getlist('type')
    directory = request.args.get('directory')

    file_ids = await handlers_files.get_files(tags, file_types, directory, db)
    response = await handlers_files.delete_files(file_ids, db, telegram)
    return jsonify(response)


@app.route('/files/directory', methods=['PATCH'])
async def patch_files_directory():
    tags = request.args.getlist('tag')
    file_types = request.args.getlist('type')
    directory = request.args.get('directory')

    form = await request.form
    new_directory = form.get("new_directory")

    file_ids = await handlers_files.get_files(tags, file_types, directory, db)
    response = await handlers_files.patch_files(file_ids, db, new_directory=new_directory)
    return jsonify(response)


@app.route('/files/tags', methods=['DELETE'])
async def delete_files_tags():
    tags = request.args.getlist('tag')
    file_types = request.args.getlist('type')
    directory = request.args.get('directory')

    form = await request.form
    tags_to_delete = form.getlist("tags")

    file_ids = await handlers_files.get_files(tags, file_types, directory, db)
    response = await handlers_files.delete_files_tags(file_ids, db, tags_to_delete)
    return jsonify(response)


@app.route('/files/tags', methods=['POST'])
async def post_files_tags():
    tags = request.args.getlist('tag')
    file_types = request.args.getlist('type')
    directory = request.args.get('directory')

    form = await request.form
    new_tags = form.getlist("tags")

    file_ids = await handlers_files.get_files(tags, file_types, directory, db)
    response = await handlers_files.post_files_tags(file_ids, db, new_tags)
    return jsonify(response)


@app.route('/files/tags', methods=['PATCH'])
async def patch_files_tags():
    tags = request.args.getlist('tag')
    file_types = request.args.getlist('type')
    directory = request.args.get('directory')

    form = await request.form
    new_tags = form.getlist("tags")

    file_ids = await handlers_files.get_files(tags, file_types, directory, db)
    response = await handlers_files.patch_files(file_ids, db, new_tags=new_tags)
    return jsonify(response)


@app.route('/files/<file_id>/meta', methods=['GET'])
async def get_file(file_id):
    response = await handlers_files.get_file(file_id, db)
    return jsonify(response)


@app.route('/files/<file_id>', methods=['DELETE'])
async def delete_file(file_id):
    response = await handlers_files.delete_file(file_id, db, telegram)
    return jsonify(response)


@app.route('/files/<file_id>/directory', methods=['PATCH'])
async def patch_file_directory(file_id):
    form = await request.form
    new_directory = form.get("new_directory")
    response = await handlers_files.patch_file(file_id, db, new_directory=new_directory)
    return jsonify(response)


@app.route('/files/<file_id>/tags', methods=['DELETE'])
async def delete_file_tags(file_id):
    form = await request.form
    tags = form.getlist('tags')
    response = await handlers_files.delete_file_tags(file_id, db, tags)
    return jsonify(response)


@app.route('/files/<file_id>/tags', methods=['POST'])
async def post_file_tags(file_id):
    form = await request.form
    tags = form.getlist('tags')
    response = await handlers_files.post_file_tags(file_id, db, tags)
    return jsonify(response)


@app.route('/files/<file_id>/tags', methods=['PATCH'])
async def patch_file_tags(file_id):
    form = await request.form
    new_tags = form.getlist("tags")
    response = await handlers_files.patch_file(file_id, db, new_tags=new_tags)
    return jsonify(response)


@app.route('/files/<file_id>', methods=['GET'])
async def download_file(file_id):
    response = await handlers_files.download_file(file_id, db, telegram, chunker)
    return jsonify(response)


@app.route('/directories/meta', methods=['GET'])
async def get_directories():
    response = await handlers_directories.get_directories(db)
    return jsonify(response)


@app.route('/directories', methods=['GET'])
async def download_directories():
    parent = request.args.get('parent')

    directory_ids = await handlers_directories.get_directories(parent, db)

    responses = []
    pbar = tqdm(total=len(directory_ids), unit="directories", desc="Downloading directories")
    for directory_id in directory_ids:
        response = await handlers_directories.download_directory(directory_id, db, telegram, chunker)
        responses.append(response)
        pbar.update(1)


@app.route('/directories', methods=['POST'])
async def post_directories():
    form = await request.form
    directory_name = form.get("name")
    directory_parent = form.get("parent")
    response = await handlers_directories.post_directory(directory_name, directory_parent, db)
    return jsonify(response)


@app.route('/directories', methods=['DELETE'])
async def delete_directories():
    parent = request.args.get('parent')

    directory_ids = await handlers_directories.get_directories(parent, db)
    response = await handlers_directories.delete_directories(directory_ids, db)
    return jsonify(response)


@app.route('/directories/parent', methods=['PATCH'])
async def patch_directories():
    form = await request.form
    directory_parent = request.args.get('parent')
    new_parent = form.get("new_parent")

    directory_ids = await handlers_directories.get_directories(directory_parent, db)
    response = await handlers_directories.patch_directories(directory_ids, db, new_parent=new_parent)
    return jsonify(response)


@app.route('/directories/<directory_id>/meta', methods=['GET'])
async def get_directory(directory_id):
    response = await handlers_directories.get_directory(directory_id, db)
    return jsonify(response)


@app.route('/directories/<directory_id>', methods=['GET'])
async def download_directory(directory_id):
    response = await handlers_directories.download_directory(directory_id, db, telegram, chunker)
    return jsonify(response)


@app.route('/directories/<directory_id>', methods=['DELETE'])
async def delete_directory(directory_id):
    response = await handlers_directories.delete_directory(directory_id, db)
    return jsonify(response)


@app.route('/directories/<directory_id>/parent', methods=['PATCH'])
async def patch_directory_parent(directory_id):
    form = await request.form
    new_parent = form.get("new_parent")
    response = await handlers_directories.patch_directory(directory_id, db, new_parent=new_parent)
    return jsonify(response)


@app.route('/directories/<directory_id>/files', methods=['GET'])
async def get_directory_files(directory_id):
    tags = request.args.getlist('tag')
    file_types = request.args.getlist('type')

    response = await handlers_directories.get_directory_files(directory_id, tags, file_types, db)
    return jsonify(responses)



if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    app.run(loop=loop)
