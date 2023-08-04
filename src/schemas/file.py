from dataclasses import dataclass
from bson import ObjectId

import datetime as dt


@dataclass
class File:
    _id: ObjectId
    directory: ObjectId
    tags: [ObjectId]
    name: str
    size: int
    extension: str
    created_at: dt.datetime
    uploaded_at: dt.datetime
    chunks: [ObjectId]