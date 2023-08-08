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
import src.handlers.tags as handlers_tags

import src.utils as utils


telegram = Telegram()
db = Database().db

telegram_max_file_size = telegram.max_file_size
chunker = Chunker(telegram_max_file_size)

utils.clear_temp_folder()

app = Quart(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024 * 2 * 10  # 20 GB


@app.route('/', methods=['GET'])
async def test_connection():
    return "Connection established", 200


@app.route('/files', methods=['GET'])
async def download_files():
    tags = request.args.getlist('tags')
    file_types = request.args.getlist('types')
    directories = request.args.getlist('directories')

    files, code = await handlers_files.get_files(db, tags=tags, file_types=file_types, directories=directories)
    file_ids = [file["_id"] for file in files]

    if not file_ids:
        return "No files found", 404

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
    tags = request.args.getlist('tags')
    file_types = request.args.getlist('types')
    directories = request.args.getlist('directories')

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
    return await handlers_files.patch_files(file_ids, db, telegram, new_tags=new_tags, new_directory=new_directory)


@app.route('/files/meta/tags', methods=['POST'])
async def add_tags_to_files():
    tags = request.args.getlist('tags')
    file_types = request.args.getlist('types')
    directories = request.args.get('directories')

    form = await request.form
    tags_to_add = form.getlist("tags")

    files, code = await handlers_files.get_files(db, tags=tags, file_types=file_types, directories=directories)
    file_ids = [file["_id"] for file in files]
    return await handlers_files.add_tags_to_files(file_ids, db, tags_to_add, telegram)


@app.route('/files/meta/tags', methods=['PATCH'])
async def remove_tags_in_files():
    tags = request.args.getlist('tags')
    file_types = request.args.getlist('types')
    directories = request.args.get('directories')

    form = await request.form
    tags_to_remove = form.getlist("tags")

    files, code = await handlers_files.get_files(db, tags=tags, file_types=file_types, directories=directories)
    file_ids = [file["_id"] for file in files]
    return await handlers_files.remove_tags_from_files(file_ids, db, tags_to_remove, telegram)


@app.route('/files/meta/tags', methods=['DELETE'])
async def delete_all_tags_in_files():
    tags = request.args.getlist('tags')
    file_types = request.args.getlist('types')
    directories = request.args.get('directories')

    files, code = await handlers_files.get_files(db, tags=tags, file_types=file_types, directories=directories)
    file_ids = [file["_id"] for file in files]
    return await handlers_files.delete_all_tags_from_files(file_ids, db, telegram)


@app.route('/files/meta/directory', methods=['DELETE'])
async def delete_files_directory():
    tags = request.args.getlist('tags')
    file_types = request.args.getlist('types')
    directories = request.args.get('directories')

    files, code = await handlers_files.get_files(db, tags=tags, file_types=file_types, directories=directories)
    file_ids = [file["_id"] for file in files]
    return await handlers_files.delete_files_directory(file_ids, db, telegram)


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
    new_name = form.get("name")

    return await handlers_files.patch_file(file_id, db, telegram, new_tags=new_tags, new_directory=new_directory, new_name=new_name)


@app.route('/files/<file_id>/meta/tags', methods=['POST'])
async def add_tags_to_file(file_id):
    form = await request.form
    tags_to_add = form.getlist("tags")

    return await handlers_files.add_tags_to_file(file_id, db, tags_to_add, telegram)


@app.route('/files/<file_id>/meta/tags', methods=['PATCH'])
async def remove_tags_in_file(file_id):
    form = await request.form
    tags_to_remove = form.getlist("tags")

    return await handlers_files.remove_tags_from_file(file_id, db, tags_to_remove, telegram)


@app.route('/files/<file_id>/meta/tags', methods=['DELETE'])
async def delete_all_tags_in_file(file_id):
    return await handlers_files.delete_all_tags_from_file(file_id, db, telegram)


@app.route('/files/<file_id>/meta/directory', methods=['DELETE'])
async def delete_file_directory(file_id):
    return await handlers_files.delete_file_directory(file_id, db, telegram)


@app.route('/directories', methods=['GET'])
async def download_directories():
    names = request.args.getlist('names')
    parents = request.args.getlist('parents')
    recursive = request.args.get('recursive')
    
    directories, code = await handlers_directories.get_directories(db, names=names, parents=parents, recursive=recursive)
    directories_ids = [directory["_id"] for directory in directories]
    
    files, code = await handlers_files.get_files(db, directories=directories_ids)
    files_ids = [file["_id"] for file in files]

    return await handlers_files.download_files(files_ids, db, telegram, chunker)


@app.route('/directories', methods=['POST'])
async def create_directory():
    form = await request.form
    name = form.get("name")
    parent = form.get("parent")
    return await handlers_directories.create_directory(db, name, parent)


@app.route('/directories', methods=['DELETE'])
async def delete_directories():
    names = request.args.getlist('names')
    parents = request.args.getlist('parents')
    recursive = request.args.get('recursive')

    directories, code = await handlers_directories.get_directories(db, names=names, parents=parents, recursive=recursive)
    directories_ids = [directory["_id"] for directory in directories]
    return await handlers_directories.delete_directories(directories_ids, db, telegram)


@app.route('/directories/id', methods=['GET'])
async def get_directories_ids():
    names = request.args.getlist('names')
    parents = request.args.getlist('parents')
    recursive = request.args.get('recursive')

    directories, code = await handlers_directories.get_directories(db, names=names, parents=parents, recursive=recursive)
    directories_ids = [directory["_id"] for directory in directories]

    return directories_ids, 200


@app.route('/directories/meta', methods=['GET'])
async def get_directories():
    names = request.args.getlist('names')
    parents = request.args.getlist('parents')
    return await handlers_directories.get_directories(db, names=names, parents=parents)


@app.route('/directories/meta', methods=['PATCH'])
async def patch_directories():
    form = await request.form
    names = request.args.getlist("names")
    parents = request.args.getlist("parents")

    new_name = form.get("name")
    new_parent = form.get("parent")

    directories, code = await handlers_directories.get_directories(db, names=names, parents=parents)
    directories_ids = [directory["_id"] for directory in directories]
    return await handlers_directories.patch_directories(directories_ids, db, telegram, new_name=new_name, new_parent=new_parent)


@app.route('/directories/<directory_id>', methods=['GET'])
async def download_directory(directory_id):
    directories, code = await handlers_directories.get_directory(db, directory_id)
    if code == 404:
        return "Directory not found", 404

    files, code = await handlers_files.get_files(db, directories=[directory_id])
    files_ids = [file["_id"] for file in files]

    return await handlers_files.download_files(files_ids, db, telegram, chunker)


@app.route('/directories/<directory_id>', methods=['DELETE'])
async def delete_directory(directory_id):
    return await handlers_directories.delete_directory(directory_id, db, telegram)


@app.route('/directories/<directory_id>/meta', methods=['GET'])
async def get_directory(directory_id):
    return await handlers_directories.get_directory(db, directory_id)


@app.route('/directories/<directory_id>/meta', methods=['PATCH'])
async def patch_directory(directory_id):
    form = await request.form
    name = form.get("name")
    parent = form.get("parent")

    return await handlers_directories.patch_directory(directory_id, db, telegram, new_name=name, new_parent=parent)


@app.route('/directories/<directory_id>/meta/children', methods=['GET'])
async def get_directory_children(directory_id):
    recursive = request.args.get('recursive')

    return await handlers_directories.get_directory_children(directory_id, db, recursive=recursive)


@app.route('/directories/<directory_id>/meta/children', methods=['POST'])
async def add_directory_children(directory_id):
    form = await request.form
    directories = form.getlist("directories")

    return await handlers_directories.add_directory_children(directory_id, db, directories)


@app.route('/directories/<directory_id>/meta/children', methods=['PUT'])
async def remove_directory_children(directory_id):
    form = await request.form
    directories = form.getlist("directories")
    recursive = request.args.get('recursive')

    return await handlers_directories.remove_directory_children(directory_id, db, directories, recursive=recursive)


@app.route('/tags', methods=['GET'])
async def get_tags():
    names = request.args.getlist('names')
    parents = request.args.getlist('parents')
    recursive = request.args.get('recursive')
    return await handlers_tags.get_tags(db, names=names, parents=parents, recursive=recursive)


@app.route('/tags', methods=['POST'])
async def create_tag():
    form = await request.form
    name = form.get("name")
    parent = form.get("parent")
    return await handlers_tags.create_tag(db, name, parent)


@app.route('/tags', methods=['DELETE'])
async def delete_tags():
    names = request.args.getlist('names')
    parents = request.args.getlist('parents')
    recursive = request.args.get('recursive')

    tags, code = await handlers_tags.get_tags(db, names=names, parents=parents, recursive=recursive)
    tags_ids = [tag["_id"] for tag in tags]
    return await handlers_tags.delete_tags(tags_ids, db, telegram)


@app.route('/tags/id', methods=['GET'])
async def get_tags_ids():
    names = request.args.getlist('names')
    parents = request.args.getlist('parents')
    recursive = request.args.get('recursive')

    tags, code = await handlers_tags.get_tags(db, names=names, parents=parents, recursive=recursive)
    tags_ids = [tag["_id"] for tag in tags]

    return tags_ids, 200


@app.route('/tags/<tag_id>', methods=['GET'])
async def get_tag(tag_id):
    return await handlers_tags.get_tag(db, tag_id)


@app.route('/tags/<tag_id>', methods=['PATCH'])
async def patch_tag(tag_id):
    form = await request.form
    new_name = form.get("new_name")
    new_parent = form.get("new_parent")

    return await handlers_tags.patch_tag(tag_id, db, telegram, new_name=new_name, new_parent=new_parent)


@app.route('/tags/<tag_id>', methods=['DELETE'])
async def delete_tag(tag_id):
    return await handlers_tags.delete_tag(tag_id, db, telegram)


@app.route('/tags/<tag_id>/children', methods=['GET'])
async def get_tag_children(tag_id):
    recursive = request.args.get('recursive')

    return await handlers_tags.get_tag_children(tag_id, db, recursive=recursive)


@app.route('/tags/<tag_id>/children', methods=['PUT'])
async def remove_tag_children(tag_id):
    form = await request.form
    recursive = request.args.get('recursive')

    return await handlers_tags.remove_tag_children(tag_id, db, telegram, recursive=recursive)


@app.route('/structure/directories', methods=['GET'])
async def get_directories_structure():
    directories, code = await handlers_directories.get_directories(db)

    structure = {}
    for directory in directories:
        if directory["parent"] is None:
            structure[f"/{directory['name']}"] = directory["_id"]
        else:
            parent = directory["parent"]
            path = f"/{directory['name']}"
            while parent is not None:
                parent_directory, code = await handlers_directories.get_directory(db, parent)
                path = f"/{parent_directory['name']}{path}"
                parent = parent_directory["parent"]

            structure[path] = directory["_id"]

    structure["/"] = '/'
    return structure, 200


@app.route('/structure/files', methods=['GET'])
async def get_files_structure():
    structure = {}

    files, code = await handlers_files.get_files(db)
    for file in files:
        path = f"/{file['name']}"
        directory_id = file["directory"]
        while directory_id is not None:
            directory, code = await handlers_directories.get_directory(db, directory_id)
            if code != 200:
                return
            path = f"/{directory['name']}{path}"
            directory_id = directory["parent"] if directory["parent"] is not None else None

        structure[path] = file["_id"]
    return structure, 200


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    app.run(loop=loop)
