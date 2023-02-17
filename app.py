from quart import Quart, request
from telethon import TelegramClient, events, errors
from telethon.tl.types import InputMessagesFilterPhotos
import os
from json import dumps as jsonify
import asyncio

api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')

client = TelegramClient(api_id=api_id, api_hash=api_hash, session="session")
client.start()

app = Quart(__name__)
app.config['MAX_CONTENT_LENGTH'] = -1

@app.route('/upload', methods=['POST'])
async def upload():
    files = await request.files
    file = files['file']
    filename = file.filename

    if 'Content-Range' in request.headers:
        # extract starting byte from Content-Range header string
        range_str = request.headers['Content-Range']
        start_bytes = int(range_str.split(' ')[1].split('-')[0])

        # append chunk to the file on disk, or create new
        async with open(filename, 'a') as f:
            f.seek(start_bytes)
            f.write(file.stream.read())

    else:
        # this is not a chunked request, so just save the whole file
        await file.save(filename)

    # send response with appropriate mime type header
    return jsonify({"name": file.filename,
                    "size": os.path.getsize(filename),
                    "url": 'uploads/' + file.filename,
                    "thumbnail_url": None,
                    "delete_url": None,
                    "delete_type": None, })


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    app.run(loop=loop)
